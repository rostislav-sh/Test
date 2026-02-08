import asyncio
import logging
from datetime import time as dt_time
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PollSchedulerBot:
    def __init__(self):
        self.bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

    async def send_weekly_poll(self):
        """Отправка еженедельного опроса"""
        try:
            logger.info("🕗 Отправка еженедельного опроса...")

            message = await self.bot.send_poll(
                chat_id=settings.CHAT_ID,
                question="📊 Планы на эту неделю?",
                options=[
                    "Работа над основными задачами",
                    "Митинги и синхронизация",
                    "Обучение и развитие",
                    "Документация и отчёты",
                    "Другое"
                ],
                is_anonymous=False,
                allows_multiple_answers=True,
                disable_notification=False
            )

            logger.info(f"✅ Опрос отправлен! Message ID: {message.message_id}")

        except TelegramAPIError as e:
            logger.error(f"❌ Ошибка Telegram API: {e}")
        except Exception as e:
            logger.exception(f"❌ Критическая ошибка при отправке опроса: {e}")

    async def send_test_poll(self, message_text: str = "Тестовый опрос"):
        """Ручная отправка тестового опроса (для отладки)"""
        try:
            await self.bot.send_message(
                chat_id=settings.CHAT_ID,
                text=f"🔧 {message_text}"
            )
            await self.send_weekly_poll()
            logger.info("✅ Тестовый опрос отправлен")
        except Exception as e:
            logger.exception(f"❌ Ошибка тестовой отправки: {e}")

    def setup_scheduler(self):
        """Настройка расписания"""
        # Каждый понедельник в 9:30 утра
        self.scheduler.add_job(
            self.send_weekly_poll,
            trigger=CronTrigger(
                day_of_week="mon",
                hour=9,
                minute=30,
                timezone=settings.tz_info
            ),
            id="weekly_poll",
            name="Еженедельный опрос по понедельникам",
            replace_existing=True,
            misfire_grace_time=300  # 5 минут на компенсацию задержки
        )
        logger.info(f"⏰ Планировщик настроен: понедельник 09:30 ({settings.TIMEZONE})")

    @asynccontextmanager
    async def lifespan(self, dp: Dispatcher):
        """Контекстный менеджер для корректного старта/остановки"""
        # Старт
        self.setup_scheduler()
        self.scheduler.start()
        logger.info("🚀 Бот запущен и готов к работе")

        # Отправка тестового сообщения при старте (опционально)
        # await self.send_test_poll("✅ Бот перезапущен и работает")

        yield

        # Остановка
        logger.info("🛑 Остановка планировщика...")
        self.scheduler.shutdown(wait=True)
        await self.bot.session.close()
        logger.info("👋 Бот остановлен")

    async def start(self):
        """Запуск бота"""
        # Регистрация lifespan
        self.dp.workflow_data.update({"bot": self.bot})
        self.dp.startup.register(lambda: logger.info("🔄 Запуск бота..."))
        self.dp.shutdown.register(lambda: logger.info("⏹️ Завершение работы..."))

        # Запуск поллинга с контекстом
        await self.dp.start_polling(
            self.bot,
            allowed_updates=self.dp.resolve_used_update_types(),
            close_bot_session=True
        )


async def main():
    bot_instance = PollSchedulerBot()

    try:
        await bot_instance.start()
    except KeyboardInterrupt:
        logger.info("⚠️ Получен сигнал прерывания (Ctrl+C)")
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("🏁 Приложение завершено")


if __name__ == "__main__":
    asyncio.run(main())