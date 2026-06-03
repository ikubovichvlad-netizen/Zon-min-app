import json
import logging
import os
import sys
import traceback
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5121654036")

# Максимально подробное логирование
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.DEBUG,  # ← DEBUG вместо INFO
    stream=sys.stdout
)
log = logging.getLogger(__name__)

def get_next_order_id():
    try:
        with open("order_counter.txt", "r") as f:
            n = int(f.read().strip()) + 1
    except:
        n = 1
    try:
        with open("order_counter.txt", "w") as f:
            f.write(str(n))
    except Exception as e:
        log.error(f"Не удалось записать order_counter.txt: {e}")
    return n

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    log.info(f"Команда /start от user_id={update.effective_user.id}")
    await update.message.reply_text(
        "👋 Привет! Я бот магазина ZONA51BY.\n"
        "Открой магазин через кнопку меню внизу 👇"
    )

async def cmd_myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"Команда /myid от user_id={user.id}, username=@{user.username or 'нет'}")
    await update.message.reply_text(
        f"🆔 Твой Telegram ID: `{user.id}`\n"
        f"👤 Username: @{user.username or 'нет'}",
        parse_mode="Markdown"
    )

async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    log.info("=== НАЧАЛО ОБРАБОТКИ ЗАКАЗА ===")
    
    if not update.message or not update.message.web_app_data:
        log.warning("Нет web_app_data в сообщении!")
        return
    
    log.info(f"Получены данные: {update.message.web_app_data.data[:500]}")
    
    try:
        order = json.loads(update.message.web_app_data.data)
    except json.JSONDecodeError as e:
        log.error(f"Ошибка парсинга JSON: {e}")
        await update.message.reply_text("❌ Ошибка данных заказа")
        return
    
    if "items" not in order:
        log.warning("В заказе нет поля 'items'")
        return
    
    user = update.effective_user
    log.info(f"Заказ от user_id={user.id}, username=@{user.username or 'нет'}")
    
    order_id = get_next_order_id()
    order_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    buyer_name = order.get("name", "—")
    buyer_phone = order.get("phone", "—")
    delivery = "🏪 Самовывоз" if order.get("delivery") == "pick" else "📦 Белпочта"
    address = order.get("address") or "Самовывоз (Гродно, Южный, пав. 51/1Б)"
    total = order.get("total", 0)
    items = order.get("items", [])
    buyer_tg_id = user.id
    buyer_tg = user.username or "нет username"
    
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
        InlineKeyboardButton(f"✅ Подтвердить #{order_id}", callback_data=f"confirm_{order_id}_{buyer_tg_id}")
    ]])
    
    # === ОТПРАВКА АДМИНУ С МАКСИМАЛЬНЫМ ЛОГИРОВАНИЕМ ===
    log.info(f"ADMIN_CHAT_ID из env: '{ADMIN_CHAT_ID}'")
    
    if not ADMIN_CHAT_ID:
        log.error("ADMIN_CHAT_ID пустой!")
        return
    
    try:
        admin_id = int(ADMIN_CHAT_ID)
        log.info(f"ADMIN_CHAT_ID как int: {admin_id}")
    except ValueError as e:
        log.error(f"Не удалось преобразовать ADMIN_CHAT_ID в int: {e}")
        return
    
    log.info(f"Попытка отправки сообщения админу (chat_id={admin_id})...")
    
    try:
        sent_message = await ctx.bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        log.info(f"✅ Сообщение УСПЕШНО отправлено! message_id={sent_message.message_id}")
    except Exception as e:
        log.error(f"❌ ОШИБКА отправки админу: {type(e).__name__}: {e}")
        log.error(f"Traceback: {traceback.format_exc()}")
    
    # Ответ покупателю
    try:
        await update.message.reply_text(
            f"✅ *Заказ #{order_id} принят!*\n\n"
            f"Менеджер скоро свяжется с тобой.",
            parse_mode="Markdown"
        )
        log.info("Ответ покупателю отправлен")
    except Exception as e:
        log.error(f"Ошибка отправки ответа покупателю: {e}")
    
    log.info("=== КОНЕЦ ОБРАБОТКИ ЗАКАЗА ===")

async def handle_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    order_id = parts[1]
    buyer_tg_id = int(parts[2])
    
    try:
        await ctx.bot.send_message(
            chat_id=buyer_tg_id,
            text=f"🎉 *Ваш заказ #{order_id} подтверждён!*\n\nМенеджер скоро свяжется с вами.",
            parse_mode="Markdown"
        )
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Подтверждено", callback_data="done")
        ]]))
    except Exception as e:
        log.error(f"Ошибка в handle_confirm: {e}")

async def handle_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Уже подтверждено ✅")

def main():
    log.info(f"🤖 Запуск бота...")
    log.info(f"ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")
    log.info(f"BOT_TOKEN длина: {len(BOT_TOKEN) if BOT_TOKEN else 'НЕ ЗАДАН!'}")
    
    if not BOT_TOKEN:
        log.error("BOT_TOKEN не задан! Бот не может работать.")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_confirm, pattern=r"^confirm_"))
    app.add_handler(CallbackQueryHandler(handle_done, pattern=r"^done$"))
    
    log.info("🤖 ZONA51BY бот запущен. Ожидаю заказы...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
