import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Загрузка .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    CHAT_ID: int = int(os.getenv("CHAT_ID", "0"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")

    # Валидация
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не указан в .env файле")
    if CHAT_ID == 0:
        raise ValueError("CHAT_ID не указан в .env файле")

    @property
    def tz_info(self):
        return ZoneInfo(self.TIMEZONE)


settings = Settings()