import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from claude_client import analyze_fridge_and_get_recipes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ─── Handlers ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message."""
    await update.message.reply_text(
        "👋 Привет! Я твой персональный кулинарный помощник.\n\n"
        "📸 Сфотографируй содержимое своего холодильника и отправь мне фото — "
        "я предложу 3 вкусных рецепта из того, что у тебя есть!\n\n"
        "Команды:\n"
        "/start — начало\n"
        "/help — помощь\n"
        "/diet — указать диетические предпочтения"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🍽 Как пользоваться ботом:\n\n"
        "1. Сфотографируй холодильник (или отдельные продукты)\n"
        "2. Отправь фото боту\n"
        "3. Получи 3 рецепта!\n\n"
        "💡 Советы для лучшего результата:\n"
        "• Хорошее освещение\n"
        "• Все полки в кадре\n"
        "• Если что-то не попало — напиши список дополнительных продуктов\n\n"
        "⚙️ /diet — настроить диетические предпочтения"
    )


async def diet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Let user pick dietary preferences."""
    keyboard = [
        [
            InlineKeyboardButton("🥗 Вегетарианское", callback_data="diet_vegetarian"),
            InlineKeyboardButton("🌱 Веганское", callback_data="diet_vegan"),
        ],
        [
            InlineKeyboardButton("🚫 Без глютена", callback_data="diet_gluten_free"),
            InlineKeyboardButton("🥩 Без ограничений", callback_data="diet_none"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выбери диетические предпочтения:", reply_markup=reply_markup
    )


async def diet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle diet preference selection."""
    query = update.callback_query
    await query.answer()

    diet_map = {
        "diet_vegetarian": "вегетарианское",
        "diet_vegan": "веганское",
        "diet_gluten_free": "без глютена",
        "diet_none": None,
    }

    chosen = diet_map.get(query.data)
    context.user_data["diet"] = chosen

    if chosen:
        await query.edit_message_text(f"✅ Предпочтение сохранено: {chosen}.\n\nТеперь отправь фото холодильника!")
    else:
        await query.edit_message_text("✅ Без ограничений. Теперь отправь фото холодильника!")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main handler: receive photo → analyze → return recipes."""
    user = update.effective_user
    logger.info(f"Photo received from user {user.id} (@{user.username})")

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🔍 Анализирую содержимое холодильника...\n\n"
        "Это займёт несколько секунд ⏳"
    )

    try:
        # Get the highest-resolution photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        # Diet preference (if set)
        diet = context.user_data.get("diet")

        # Call Claude
        result = await analyze_fridge_and_get_recipes(bytes(photo_bytes), diet)

        # Delete "thinking" message
        await thinking_msg.delete()

        # Send ingredients found
        await update.message.reply_text(
            f"🧺 *Нашёл в холодильнике:*\n{result['ingredients']}",
            parse_mode="Markdown",
        )

        # Send each recipe as a separate message
        for i, recipe in enumerate(result["recipes"], 1):
            recipe_text = (
                f"🍳 *Рецепт {i}: {recipe['name']}*\n\n"
                f"⏱ Время: {recipe['time']}\n"
                f"📊 Сложность: {recipe['difficulty']}\n\n"
                f"*Ингредиенты:*\n{recipe['ingredients']}\n\n"
                f"*Приготовление:*\n{recipe['steps']}"
            )

            keyboard = [[
                InlineKeyboardButton("♻️ Другие рецепты", callback_data="regenerate"),
                InlineKeyboardButton("❤️ Сохранить", callback_data=f"save_{i}"),
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                recipe_text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await thinking_msg.edit_text(
            "❌ Что-то пошло не так. Попробуй отправить фото ещё раз.\n\n"
            "Убедись, что фото чёткое и хорошо освещённое."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text — treat as extra ingredients to add."""
    text = update.message.text

    if context.user_data.get("last_ingredients"):
        # User is adding more ingredients
        context.user_data["extra_ingredients"] = text
        await update.message.reply_text(
            f"✅ Добавил: {text}\n\nТеперь отправь фото холодильника — "
            "учту эти продукты тоже!"
        )
    else:
        await update.message.reply_text(
            "📸 Отправь фото холодильника, и я подберу рецепты!\n\n"
            "Или напиши /help если нужна помощь."
        )


async def regenerate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'show other recipes' button."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📸 Отправь фото ещё раз — подберу другие рецепты!"
    )


async def save_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'save recipe' button."""
    query = update.callback_query
    await query.answer("❤️ Рецепт сохранён!", show_alert=True)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("diet", diet_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(diet_callback, pattern="^diet_"))
    app.add_handler(CallbackQueryHandler(regenerate_callback, pattern="^regenerate$"))
    app.add_handler(CallbackQueryHandler(save_callback, pattern="^save_"))

    logger.info("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
