import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)
from database import get_games_by_mood
from questions import QUESTIONS, analyze_answers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

Q1, Q2, Q3, Q4, Q5 = range(5)

BOT_TOKEN   = os.getenv("BOT_TOKEN",   "ВАШ_ТОКЕН_ЗДЕСЬ")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["answers"] = []
    await update.message.reply_text(
        "🎮 Привет! Я подберу игру под твоё настроение.\n"
        "Отвечай на 5 вопросов — и получишь рекомендации прямо с игровых сайтов!\n\n"
        "Напиши /cancel, чтобы прервать.",
    )
    question = QUESTIONS[0]
    keyboard = ReplyKeyboardMarkup(
        [[opt] for opt in question["options"]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(question["text"], reply_markup=keyboard)
    return Q1


async def _ask(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int) -> None:
    context.user_data["answers"].append(update.message.text)
    q = QUESTIONS[q_index]
    keyboard = ReplyKeyboardMarkup(
        [[opt] for opt in q["options"]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text(q["text"], reply_markup=keyboard)


async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _ask(update, context, 1)
    return Q2

async def q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _ask(update, context, 2)
    return Q3

async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _ask(update, context, 3)
    return Q4

async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _ask(update, context, 4)
    return Q5


async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["answers"].append(update.message.text)
    answers = context.user_data["answers"]

    await update.message.reply_text(
        "🔍 Ищу игры для тебя...",
        reply_markup=ReplyKeyboardRemove()
    )

    mood, mood_label = analyze_answers(answers)
    games = await get_games_by_mood(mood, count=3)

    if not games:
        await update.message.reply_text(
            "😅 Не смог получить игры — попробуй /start снова!"
        )
        return ConversationHandler.END

    # Иконка источника
    source_icon = {"RAWG": "🎮", "FreeToGame": "🆓", "local": "📋"}

    response = f"🎯 Твоё настроение: *{mood_label}*\n\n"
    response += "🎮 *Рекомендую эти игры:*\n\n"

    for i, game in enumerate(games, 1):
        icon = source_icon.get(game.get("source", "local"), "🎮")
        url_line = f"\n   🔗 [Подробнее]({game['url']})" if game.get("url") else ""
        response += (
            f"{i}. {icon} *{game['title']}*\n"
            f"   🕹 Жанр: {game['genre']}\n"
            f"   📝 {game['description']}\n"
            f"   💻 Платформа: {game['platform']}\n"
            f"   💡 {game['why']}"
            f"{url_line}\n\n"
        )

    response += "Хочешь ещё? Напиши /start!"

    await update.message.reply_text(
        response,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 До встречи! Напиши /start, когда захочешь найти игру.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Как пользоваться ботом:*\n\n"
        "/start — начать подбор игры\n"
        "/cancel — отменить текущий диалог\n"
        "/help — эта справка\n\n"
        "Бот использует базы RAWG и FreeToGame для актуальных рекомендаций!",
        parse_mode="Markdown"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, q2)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, q5)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
