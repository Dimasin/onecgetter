import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TgtDirFresh: list[str] | None = None
    TgtBaseFresh: list[str] | None = None
    TgtUrlFresh: str | None = None
    UserFresh: str | None = None
    PassFresh: str | None = None
    TgtDirGrm: str | None = None
    TgtUrlGrm: str | None = None
    UserGrm: str | None = None
    PassGrm: str | None = None
    ntfy_url: str | None = None
    ntfy_cred: str | None = None

    # Пустой конфиг, так как мы управляем файлами вручную через аргументы
    model_config = SettingsConfigDict(extra='ignore')

def get_settings(credential_id: str, fallback_filename: str) -> Settings:
    """
    Универсальная загрузка:
    1. Ищет секрет в CREDENTIALS_DIRECTORY (systemd 247+)
    2. Если нет, ищет файл в текущей рабочей директории (WorkingDirectory)
    3. Если файлов нет, берет данные из окружения (EnvironmentFile или export)
    """
    # 1. Пытаемся взять LoadCredential
    creds_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if creds_dir:
        cred_path = Path(creds_dir) / credential_id
        if cred_path.exists():
            return Settings(_env_file=cred_path)

    # 2. Пытаемся взять файл из WorkingDirectory (или текущей папки)
    # resolve() сделает путь абсолютным для надежности
    fallback_path = Path.cwd() / fallback_filename
    if fallback_path.exists():
        return Settings(_env_file=fallback_path)

    # 3. Крайний случай: всё берется из реального окружения (os.environ)
    # Это сработает для EnvironmentFile в старых systemd
    return Settings()

# Использование в коде:
# "oneconf" - это ID в LoadCredential=ID:PATH
# "configfo.env" - имя файла для EnvironmentFile или локальной разработки
settings = get_settings("oneconf","configfo.env")
print(f"Connecting to {settings.TgtUrlFresh}")
print("Bye")
