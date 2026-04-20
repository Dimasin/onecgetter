import os
from pathlib import Path
from dotenv import load_dotenv

def load_secure_config():
    # 1. Сначала ищем системный секрет (самый безопасный путь)
    creds_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if creds_dir:
        p = Path(creds_dir) / "oneconf"
        if p.exists():
            load_dotenv(dotenv_path=p, override=True)
            return
    # 2. Fallback на WorkingDirectory/.env (ваш вариант с chmod 600)
    # Если прав не хватит, load_dotenv просто пропустит этот шаг (или можно добавить проверку)
    local_env = Path.cwd() / ".env"
    if local_env.exists():
        load_dotenv(dotenv_path=local_env)

# Использование
load_secure_config()
target_url = os.getenv("TgtUrlGrm")
username = os.getenv("UserGrm")
print(target_url)
print(username)