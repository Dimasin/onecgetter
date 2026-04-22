import os
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Класс параметров. Основные: UrlFresh, UrlGrm и ntfy_url. От них зависит выполнение части кода
    для которого эти переменные обязательно используются. Остальные переменные группы
    должны быть обязательно заданы, если заданы основные, иначе выполнение класса завершится ошибкой.
    Исключение ntfy_cred может отсутствовать даже если задана ntfy_url.
    Если основная переменная не задана, зависимая от нее часть кода не выполнится.
    Например, если не задана ntfy_url, сообщения отправлены не будут.
    """
    # Группа Fresh
    UrlFresh: str | None = None
    UserFresh: str | None = None
    PassFresh: str | None = None
    BasesFresh: list[str] | None = None
    DirsFresh: list[str] | None = None
    # группа GRM
    UrlGrm: str | None = None
    UserGrm: str | None = None
    PassGrm: str | None = None
    DirGrm: str | None = None
    # Группа ntfy
    ntfy_url: str | None = None
    ntfy_cred: str | None = None

    @model_validator(mode='after')
    def validate_dependencies(self) -> 'Settings':
        # Словарь: {главное_поле: [список_зависимых]}
        dependencies = {
            'UrlFresh': ['UserFresh', 'PassFresh', 'BasesFresh', 'DirsFresh'],
            'UrlGrm': ['UserGrm', 'PassGrm', 'DirGrm']
        }
        for master, slaves in dependencies.items():
            master_val = getattr(self, master)
            if master_val is not None and str(master_val).strip() != "":
                # Если главный задан, проверяем зависимые
                for slave in slaves:
                    slave_val = getattr(self, slave)
                    if slave_val is None or (isinstance(slave_val, str) and slave_val.strip() == ""):
                        raise RuntimeError(f"Missing {slave} because {master} is set")
            else:
                setattr(self, master, None) # Устанавливаем в None реальную переменную, дальше в коде можно проверять None или нет
        return self

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
try:
    settings = get_settings("oneconf","configfo.env")
except Exception as e:
    print(e)
    exit(10)
 
print(f"Connecting to {settings.UrlFresh}")
print("Bye")