from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str
    ADMIN_GROUP_ID: int  # Telegram group chat id for admin notifications and review
    CHANNEL_ID: int

    # Публичная ссылка на канал (для кнопки и NOT_SUBSCRIBED)
    CHANNEL_LINK: str = "https://t.me/tm_academy_channel"
    # Username аккаунта поддержки
    SUPPORT_USERNAME: str = "@tm_support"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    REDIS_URL: str = "redis://localhost:6379/0"

    CARDS: dict[str, dict[str, str]] = {
        "kg": {"label": "🇰🇬 Кыргызстан", "number": "1234 5678 9012 3456", "bank": "Mbank / O!Деньги"},
        "uz": {"label": "🇺🇿 Узбекистан", "number": "9860 1001 2565 0000", "bank": "Xumo / Фаррух Норматов"},
        "kz": {"label": "🇰🇿 Казахстан",  "number": "9876 5432 1098 7654", "bank": "Kaspi"},
        "visa": {"label": "💳 Visa",      "number": "4278 3200 2873 8291", "bank": "Visa / Фаррух Норматов"},
    }

    COURSE_PRICE: str = "99 $"

    WEBHOOK_HOST: str = ""
    WEBHOOK_PATH: str = "/webhook"

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASS)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()