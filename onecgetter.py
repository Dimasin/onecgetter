from playwright.sync_api import sync_playwright
import time
import random
import subprocess
import os
from urllib.parse import urlparse
import zipfile
import requests
import re
from dateutil.parser import parse
from datetime import datetime
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

def random_sleep(start=1, end=5, step=0.2):
    """
    Выдает случайное число в диапазоне min,max с указанным шагом
    """
    # Вычисляем количество возможных "шагов"
    # Для 1-5 сек с шагом 0.2 это будет: 1.0, 1.2, 1.4 ... 5.0
    steps = int((end - start) / step)
    delay = start + random.randint(0, steps) * step
    time.sleep(delay)

def to_str(data):
    """
    Корректно преобразует последовательность байт b'' в строку
    """
    # 1. Если это None, возвращаем пустую строку
    if data is None:
        return ""
    # 2. Если это байты, декодируем их
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='replace')
    # 3. Если это уже строка (str), возвращаем как есть
    return str(data)

def getUrlGrm(target_url: str, username: str, password: str):
    """
    Вытаскивает URL с сайта target_url
    """
    with sync_playwright() as p:
        # Запускаем Browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=False)
        page = context.new_page()
        page.goto(target_url)
        # 1. АВТОРИЗАЦИЯ
        random_sleep()
        page.get_by_placeholder('Телефон начните с символа "+"').fill(username)
        random_sleep()
        page.get_by_placeholder("Введите пароль").fill(password)
        random_sleep()
        page.get_by_text("Войти").click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9)
        # 2. Проход по ссылкам
        page.get_by_text("Управление базами").click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9)
        page.get_by_title("Сделать выгрузку").click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9)
        with page.expect_popup() as popup_info:
            page.get_by_alt_text("Кнопка скачать").first.click()
        new_tab = popup_info.value
        # Ждем появления тега meta в head
        new_tab.wait_for_selector('meta[http-equiv="refresh"]', state="attached")
        # Получаем содержимое атрибута content
        refresh_content = new_tab.locator('meta[http-equiv="refresh"]').get_attribute("content")
        random_sleep()
        # Извлекаем URL (отсекаем "0; url=")
        if refresh_content and "url=" in refresh_content:
            # Разделяем строку по 'url=' и берем вторую часть
            download_url = refresh_content.split("url=")[1].strip()
            print(f"Info getUrl: found URL: {download_url}")
        else:
            download_url = ""
            print("Error getUrl: not found URL")
        browser.close()
        return download_url

def downFileGrm(download_url: str, target_dir: str):
    """
    Парсит download_url и загружет файл в target_dir
    """
    os.makedirs(target_dir, exist_ok=True)
    # 1. Парсим URL, чтобы достать только путь (без ?x-amz...)
    path = urlparse(download_url).path
    # 2. Берем последнюю часть пути (имя файла)
    filename = os.path.basename(path)
    # 3. Собираем полный путь для сохранения
    full_path = os.path.join(target_dir, filename)
    print(f"Info downFile: Download using wget to: {target_dir} / {filename}")
    # Команда wget:
    # -c (продолжить закачку), --no-check-certificate (если нужно), -P (куда сохранить)
    if (filename!=""):
        command = ["wget", "-c", "--no-check-certificate", "--progress=bar:force:noscroll", "-O", full_path, download_url]
    else:
        command = ["wget", "-c", "--no-check-certificate", "--progress=bar:force:noscroll", "-P", target_dir, download_url]
    try:
        # Запускаем закачку
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=3600)
        print(f"Info downFile: file down success: {full_path}", result.stdout)
        return full_path
    except subprocess.CalledProcessError as e:
        print(f"Error downFile: {to_str(e.stdout)},{to_str(e.stderr)}")
    except subprocess.TimeoutExpired as e:
        print(f"Timeout downFile: {to_str(e.stdout)},{to_str(e.stderr)}")
    return ""

def testFile(full_path: str):
    """
    Тест zip архива
    """
    report_lines = [f"Info testFile: checking {full_path}"]
    try:
        with zipfile.ZipFile(full_path, 'r') as z:
            if z.testzip():
                report_lines.append("Error testFile: file not found or corrupt")
            else:
                for info in z.infolist():
                    # Не пишем в отчет файлы меньше 100 MB
                    fsize = round(info.file_size/1024**2, 2)
                    if (fsize > 100):
                        info_file = f"{info.filename} — {fsize} MB"
                        report_lines.append(info_file)
                report_lines.append("Info testFile: file check success")
    except Exception as e:
        report_lines.append(f"Error testFile: {e}")
    rep = "\n".join(report_lines)
    print(rep)
    return rep

def send_ntfy_message(message: str, ntfy_url: str, ntfy_cred = None):
    """
    Отправляет уведомление в ntfy
    Тестировалось только с ntfy_cred is not None, по идее должно работать и с ntfy_cred = None
    """
    try:
        if (ntfy_cred is not None and str(ntfy_cred).strip() != ""):
            response = requests.post(
                ntfy_url,
                data=message.encode('utf-8'),
                headers={
                    "Authorization": f"Basic {ntfy_cred}",
                    "Title": "Bcapper 1C",  # Заголовок уведомления
                    "Priority": "low", # Можно менять на min, low, high, max
                }
            )
        else:
            response = requests.post(
                ntfy_url,
                data=message.encode('utf-8'),
                headers={
                    "Title": "Bcapper 1C",  # Заголовок уведомления
                    "Priority": "low", # Можно менять на min, low, high, max
                }
            )
        if response.status_code == 200:
            print("Info ntfy: Alert success!")
            return True
        else:
            print(f"Error ntfy: Sending alert error: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error ntfy: Unknow alert error: {e}")
        return False

def get_closest_past_date(date_str):
    """
    Поиск правильного формата даты, ближайшей к текущей не из будущего 
    """
    now = datetime.now()
    try:
        option1 = parse(date_str, dayfirst=True)
        option2 = parse(date_str, dayfirst=False)
        past_options = [d for d in {option1, option2} if d <= now]
        if not past_options:
            return ""
        return max(past_options).date().isoformat()
    except:
        return ""

def smart_date_search(text):
    """
    Поиск ближайшей (не из будущего) даты, к текущей из входной строки 
    """
    pattern = r'\d{1,4}[.\-/]\d{1,2}[.\-/]\d{1,4}'  
    matches = re.findall(pattern, text)
    found_dates = []
    for m in matches:
        result = get_closest_past_date(m)
        if result:
            found_dates.append(result)
    if not found_dates:
        return f"_{datetime.now().date().isoformat()}"
    return max(found_dates)

def downFileFresh(target_url: str, username: str, password: str, target_dir: str, target_base: str):
    """
    Загружает бэкапы target_base с сайта target_url в каталоги target_dir
    """
    out_files = []
    with sync_playwright() as p:
        # Запускаем Browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            page.goto(target_url)
            # 1. АВТОРИЗАЦИЯ
            random_sleep()
            page.get_by_placeholder("Пользователь").fill(username)
            random_sleep()
            page.get_by_placeholder("Пароль").fill(password)
            random_sleep()
            page.get_by_role("button", name="Войти").click()
            page.wait_for_load_state("networkidle")
            random_sleep(6,9)
            # 2. Проход по ссылкам
            # page.locator('span[title="Архивирование"]').click()
            # page.wait_for_load_state("networkidle")
            target = page.locator('span[title="Архивирование"]')
            target.wait_for(state="visible", timeout=60000)
            target.click(delay=500)
            random_sleep(6,9)
            page.locator(".gridLine").first.wait_for(state="attached", timeout=60000)
            rows = page.locator("#grid_form1_Список > .gridBody > .gridLine")
            count = rows.count()
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            page.screenshot(path=f"{timestamp}_fresh.png", full_page=True)
            raise RuntimeError(f"Error Fresh click: {e}")
        random_sleep(6,9)
        for i in range(1,count):
            if not target_base:
                break
            try:
                if (i==1):
                    page.locator(".dIB").first.click()
                else:
                    page.locator(f"div:nth-child({i}) > div > .gridBoxImg > .dIB").click()
                file_name = page.locator("#grid_form1_Список > .gridBody > .gridLine.select.eActivityBack").first.inner_text().strip()
                index, match = next(((i, name) for i, name in enumerate(target_base) if name in file_name), (None, None))
                date_str = smart_date_search(file_name)
                if match:
                    target_folder = target_dir[index]
                    os.makedirs(target_folder, exist_ok=True)
                    # Ждем 10 минут, пока сервер готовит файл
                    with page.expect_download(timeout=600000) as download_info:
                        page.locator("[id=\"form1_ФормаВыгрузитьРезервнуюКопию\"]").click()
                    download = download_info.value
                    save_path = os.path.join(target_folder, f"{date_str}-{download.suggested_filename}")
                    print(f"Download: {match} to {save_path}")
                    download.save_as(save_path)
                    target_base.pop(index)
                    target_dir.pop(index)
                    out_files.append(save_path)
                    print(f"Download success: {match} to {save_path}")
            except Exception as e:
                print(f"Download error {match}: file {save_path}: {e}")
    return out_files

def main():
    # Использование в коде:
    # "oneconf" - это ID в LoadCredential=ID:PATH
    # "configfo.env" - имя файла для EnvironmentFile или локальной разработки
    try:
        settings = get_settings("oneconf","configfo.env")
    except Exception as e:
        print(e)
        exit(10)

    # Bcap GRM
    if (settings.UrlGrm is not None):
        url = getUrlGrm(settings.UrlGrm, settings.UserGrm, settings.PassGrm)
        fp = downFileGrm(url, settings.DirGrm)
        rep = testFile(fp)
        if (settings.ntfy_url is not None):
            send_ntfy_message(rep, settings.ntfy_url, settings.ntfy_cred)

    # Bcap Fresh
    if (settings.UrlFresh is not None):
        out_files = downFileFresh(settings.UrlFresh, settings.UserFresh, settings.PassFresh, settings.DirsFresh, settings.BasesFresh)
        for file in out_files:
            rep = testFile(file)
            if (settings.ntfy_url is not None):
                send_ntfy_message(rep, settings.ntfy_url, settings.ntfy_cred)

if __name__ == "__main__":
    main()
