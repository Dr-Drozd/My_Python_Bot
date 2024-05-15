from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    WEATHER_TOKEN: str
    NEWS_TOKEN: str
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def get_database_url(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def get_bot_token(self):
        return f"{self.BOT_TOKEN}"

    @property
    def get_weather_token(self):
        return f"{self.WEATHER_TOKEN}"

    @property
    def get_news_token(self):
        return f"{self.NEWS_TOKEN}"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
