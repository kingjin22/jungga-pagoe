from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "sqlite:///./jungga_pagoe.db"

    # Supabase (optional)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # 쿠팡 파트너스
    COUPANG_ACCESS_KEY: str = ""
    COUPANG_SECRET_KEY: str = ""

    # 네이버 쇼핑 API
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
