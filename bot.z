"""
ZONA51BY — Telegram Bot Backend
Запуск: python bot.py
"""

import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ── Загрузка настроек из .env ─────────────────────────────
load_dotenv()
BOT_TOKEN   = os.getenv("BOT_TOKEN")    # токен из .env файла
ADMIN_ID    = int(os.getenv("ADMIN_ID")) # твой Telegram ID из .env

# ── Логирование ───────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),             # в консоль
        logging.FileHandler("orders.log"),   # в файл orders.log
    ]
)
log = logging.getLogger(__name__)

# ── Счётчик заказов ───────────────────────────────────────
# Сохраняется в файл чтобы не сбрасываться при перезапуске
def get_next_order_id() -> int:
    try:
        with open("order_counter.txt", "r") as f:
            n = int(f.read().strip()) + 1
    except (FileNotFoundError, ValueError):
        n = 1
    with open("order_counter.txt", "w") as f:
        f.write(str(n))
    return n


# ── /start ────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот магазина ZONA51BY.\n"
        "Открой магазин через кнопку меню внизу 👇"
    )


# ── Приём заказа из Mini App ──────────────────────────────
async def handle_webapp_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получает данные из Mini App когда покупатель нажимает Подтвердить"""

    raw = update.effective_message.web_app_data
    if not raw:
        return

    try:
        order = json.loads(raw.data)
    except json.JSONDecodeError:
        log.error("Не удалось разобрать JSON из Mini App")
        await update.message.reply_text("❌ Ошибка данных. Попробуй ещё раз.")
        return

    # ── Номер и время заказа ──────────────────────────────
    order_id  = get_next_order_id()
    order_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    # ── Данные покупателя ─────────────────────────────────
    buyer_name  = order.get("name", "—")
    buyer_phone = order.get("phone", "—")
    delivery    = "🏪 Самовывоз" if order.get("delivery") == "pick" else "📦 Белпочта"
    address     = order.get("address") or "Самовывоз (Гродно, Южный, пав. 51/1Б)"
    total       = order.get("total", 0)
    items       = order.get("items", [])
    buyer_tg_id = update.effective_user.id
    buyer_tg    = update.effective_user.username or "нет username"

    # ── Список товаров ─────────────────────────────────────
    items_text = ""
    for item in items:
        emoji = item.get("emoji", "📦")
        name  = item.get("name", "Товар")
        size  = item.get("size", "—")
        color = item.get("color", "—")
        price = item.get("price", 0)
        items_text += f"  {emoji} {name}\n     р-р {size} · {color} · {price} BYN\n"

    if not items_text:
        items_text = "  (список пуст)"

    # ── Сообщение для тебя (администратора) ───────────────
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

    # ── Кнопка "Написать покупателю" ──────────────────────
    # При нажатии откроется чат с покупателем напрямую
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 Написать покупателю",
                url=f"tg://user?id={buyer_tg_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"✅ Подтвердить заказ #{order_id}",
                callback_data=f"confirm_{order_id}_{buyer_tg_id}"
            )
        ]
    ])

    # ── Отправляем уведомление тебе ───────────────────────
    await ctx.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    # ── Подтверждение покупателю ──────────────────────────
    await update.message.reply_text(
        f"✅ *Заказ #{order_id} принят!*\n\n"
        f"Менеджер @manager\\_zona51 свяжется с тобой в ближайшее время "
        f"для подтверждения и уточнения деталей.\n\n"
        f"📞 Или напиши сам: @manager\\_zona51",
        parse_mode="Markdown"
    )

    log.info(f"Заказ #{order_id} от {buyer_name} ({buyer_tg_id}) — {total} BYN")


# ── Нажатие кнопки "Подтвердить заказ" ───────────────────
async def handle_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Когда ты нажимаешь 'Подтвердить' — покупатель получает сообщение"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    order_id    = parts[1]
    buyer_tg_id = int(parts[2])

    # Сообщаем покупателю
    try:
        await ctx.bot.send_message(
            chat_id=buyer_tg_id,
            text=(
                f"🎉 *Ваш заказ #{order_id} подтверждён!*\n\n"
                f"Менеджер @manager\\_zona51 скоро свяжется с вами "
                f"для согласования деталей доставки.\n\n"
                f"Спасибо, что выбираете ZONA51BY! 🙌"
            ),
            parse_mode="Markdown"
        )
        # Обновляем кнопки у себя
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Подтверждено", callback_data="done")
            ]])
        )
    except Exception as e:
        log.error(f"Не удалось отправить подтверждение: {e}")
        await query.edit_message_text(
            query.message.text + "\n\n⚠️ Не удалось отправить сообщение покупателю"
        )


async def handle_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Уже подтверждено ✅")


# ── Запуск ────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден! Проверь файл .env")
    if not ADMIN_ID:
        raise ValueError("ADMIN_ID не найден! Проверь файл .env")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_order))
    app.add_handler(CallbackQueryHandler(handle_confirm, pattern=r"^confirm_"))
    app.add_handler(CallbackQueryHandler(handle_done, pattern=r"^done$"))

    log.info("🤖 ZONA51BY бот запущен. Жду заказы...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
