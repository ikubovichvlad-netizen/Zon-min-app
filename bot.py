import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "artemkasquare")  # ← ТВОЙ USERNAME

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

def get_next_order_id():
    try:
        with open("order_counter.txt", "r") as f:
            n = int(f.read().strip()) + 1
    except:
        n = 1
    with open("order_counter.txt", "w") as f:
        f.write(str(n))
    return n

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот магазина ZONA51BY.\n"
        "Открой магазин через кнопку меню внизу 👇"
    )

async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получает данные из Mini App при оформлении заказа"""
    
    if not update.message or not update.message.web_app_data:
        return
    
    try:
        order = json.loads(update.message.web_app_data.data)
    except json.JSONDecodeError:
        log.error("Не удалось разобрать JSON")
        await update.message.reply_text("❌ Ошибка данных заказа")
        return
    
    if "items" not in order:
        return
    
    log.info(f"📨 Получен заказ от {update.effective_user.id}")
    
    order_id = get_next_order_id()
    order_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    buyer_name = order.get("name", "—")
    buyer_phone = order.get("phone", "—")
    delivery = "🏪 Самовывоз" if order.get("delivery") == "pick" else "📦 Белпочта"
    address = order.get("address") or "Самовывоз (Гродно, Южный, пав. 51/1Б)"
    total = order.get("total", 0)
    items = order.get("items", [])
    buyer_tg_id = update.effective_user.id
    buyer_tg = update.effective_user.username or "нет username"
    
    items_text = ""
    for item in items:
        emoji = item.get("emoji", "📦")
        name = item.get("name", "Товар")
        size = item.get("size", "—")
        color = item.get("color", "—")
        price = item.get("price", 0)
        items_text += f"  {emoji} {name}\n     р-р {size} · {color} · {price} BYN\n"
    
    if not items_text:
        items_text = "  (список пуст)"
    
    admin_text = (
        f"🛒 *ЗАКАЗ #{order_id}*  |  {order_time}\n"
        f"{'─' * 30}\n"
        f"👤 *Покупатель:* {buyer_name}\n"
        f"📞 *Телефон:* `{buyer_phone}`\n"
        f"🔗 *Telegram:* @{buyer_tg} (`{buyer_tg_id}`)\n"
        f"{'─' * 30}\n"
        f"*Способ:* {delivery}\n"
        f"*Адрес:* {address}\n"
        f"{'─' * 30}\n"
        f"*Товары:*\n{items_text}"
        f"{'─' * 30}\n"
        f"💰 *ИТОГО: {total} BYN*"
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Написать покупателю", url=f"tg://user?id={buyer_tg_id}"),
        InlineKeyboardButton(f"✅ Подтвердить заказ #{order_id}", callback_data=f"confirm_{order_id}_{buyer_tg_id}")
    ]])
    
    # Отправляем админу по USERNAME
    await ctx.bot.send_message(
        chat_id=f"@{ADMIN_USERNAME}",  # ← ОТПРАВКА ПО USERNAME
        text=admin_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    await update.message.reply_text(
        f"✅ *Заказ #{order_id} принят!*\n\n"
        f"Менеджер @{ADMIN_USERNAME} свяжется с тобой для подтверждения.",
        parse_mode="Markdown"
    )
    
    log.info(f"Заказ #{order_id} от {buyer_name} — {total} BYN")

async def handle_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    order_id = parts[1]
    buyer_tg_id = int(parts[2])
    
    try:
        await ctx.bot.send_message(
            chat_id=buyer_tg_id,
            text=f"🎉 *Ваш заказ #{order_id} подтверждён!*\n\nМенеджер @{ADMIN_USERNAME} скоро свяжется с вами.",
            parse_mode="Markdown"
        )
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Подтверждено", callback_data="done")
        ]]))
    except Exception as e:
        log.error(f"Ошибка отправки: {e}")

async def handle_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Уже подтверждено ✅")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_confirm, pattern=r"^confirm_"))
    app.add_handler(CallbackQueryHandler(handle_done, pattern=r"^done$"))
    
    log.info(f"🤖 ZONA51BY бот запущен. Буду писать @{ADMIN_USERNAME}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
