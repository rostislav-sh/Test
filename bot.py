import asyncio
import logging
import os
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Конфигурация из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # Может быть пустым при первом запуске
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не указан в .env файле!")

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)
router = Router()


@router.message(Command("getid"))
async def cmd_getid(message: Message):
    """Команда для получения ID чата и пользователя"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    response = (
        f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n"
        f"👤 <b>Ваш User ID:</b> <code>{user_id}</code>\n\n"
    )

    if message.chat.type != "private":
        response += (
            f"🔖 <b>Тип чата:</b> {message.chat.type}\n"
            f"📛 <b>Название:</b> {message.chat.title or 'без названия'}"
        )

    await message.answer(response, parse_mode="HTML")
    logger.info(f"Пользователь {user_id} запросил ID чата {chat_id}")


@router.message(Command("testpoll"))
async def cmd_testpoll(message: Message):
    """Тестовая отправка опроса"""
    try:
        await send_weekly_poll()
        await message.answer("✅ Тестовый опрос отправлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.exception("Ошибка при тестовой отправке опроса")


async def send_weekly_poll():
    """Отправка еженедельного опроса"""
    # Если CHAT_ID не задан в .env — используем значение из переменной окружения или падаем с ошибкой
    target_chat_id = int(CHAT_ID) if CHAT_ID else None

    if not target_chat_id:
        logger.error("❌ CHAT_ID не указан! Используйте команду /getid для получения ID чата.")
        return

    try:
        logger.info(f"🕗 Отправка опроса в чат {target_chat_id}...")

        await bot.send_poll(
            chat_id=target_chat_id,
            question="📊 Ваши планы на эту неделю?",
            options=[
                "Работа над проектами",
                "Митинги и планирование",
                "Обучение и развитие",
                "Административные задачи",
                "Другое"
            ],
            is_anonymous=False,
            allows_multiple_answers=True
        )

        logger.info("✅ Опрос успешно отправлен")

    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке опроса: {e}")


def setup_scheduler():
    """Настройка расписания (только если CHAT_ID задан)"""
    if not CHAT_ID:
        logger.warning("⚠️ CHAT_ID не указан — планировщик НЕ будет запущен")
        logger.warning("💡 Добавьте CHAT_ID в .env после получения через /getid")
        return

    scheduler.add_job(
        send_weekly_poll,
        trigger=CronTrigger(
            day_of_week="mon",
            hour=9,
            minute=30,
            timezone=ZoneInfo(TIMEZONE)
        ),
        id="weekly_poll",
        name="Еженедельный опрос",
        replace_existing=True,
        misfire_grace_time=300
    )
    logger.info(f"⏰ Планировщик настроен: понедельник 09:30 ({TIMEZONE})")


async def on_startup(bot: Bot):
    """Действия при старте бота"""
    logger.info("🚀 Бот запущен!")
    logger.info(f"ℹ️  Для получения CHAT_ID добавьте бота в чат и напишите /getid")

    if CHAT_ID:
        logger.info(f"✅ CHAT_ID задан: {CHAT_ID}")
        setup_scheduler()
        scheduler.start()
    else:
        logger.warning("⚠️  CHAT_ID не задан в .env — автоматическая отправка отключена")
        logger.warning("💡 Отправьте /getid в нужном чате, затем добавьте ID в .env и перезапустите бота")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    if scheduler.running:
        logger.info("🛑 Остановка планировщика...")
        scheduler.shutdown(wait=True)
    logger.info("👋 Бот остановлен")


async def main():
    # Регистрация роутера и хуков
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск поллинга
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")