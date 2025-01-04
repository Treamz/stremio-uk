from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    name: str = "UAKino.me"
    main_url: str = "https://uakino.me/"

settings = Settings()
