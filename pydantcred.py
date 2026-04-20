import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TgtDirFresh: list[str]
    TgtBaseFresh: list[str]
    TgtUrlFresh: str

    # Настройки загрузки
    model_config = SettingsConfigDict(
        # По умолчанию ищем .env в текущей папке (для разработки)
        env_file=".env", 
        extra='ignore'
    )

def get_settings(fall_over) -> Settings:
    # Проверяем, есть ли секреты от systemd
    creds_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    
    if creds_dir:
        cred_path = Path(creds_dir) / "oneconf"
        if cred_path.exists():
            # Если нашли системный секрет, заставляем Pydantic читать его
            return Settings(_env_file=cred_path)
    
    # Иначе он просто подтянет локальный .env или переменные окружения
    return Settings(_env_file=fall_over)

# Использование
settings = get_settings("configfo.env")
print(f"Connecting to {settings.TgtUrlFresh}")
print("Bye")
