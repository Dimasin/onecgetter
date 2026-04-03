from playwright.sync_api import sync_playwright
import time
import random
import subprocess
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
import zipfile
import requests

load_dotenv('config.env')

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

def getUrl():
    """
    Вытаскивает URL с сайта
    """
    target_url = os.getenv("TargetUrl")
    username = os.getenv("UserName")
    password = os.getenv("Password")
    with sync_playwright() as p:
        # Запускаем Browser
        browser = p.chromium.launch(channel="chrome", headless=True)
        # browser = p.firefox.launch(channel="firefox", headless=False)
        context = browser.new_context(accept_downloads=False)
        page = context.new_page()
        page.goto(target_url)
        # 1. АВТОРИЗАЦИЯ
        random_sleep();
        page.get_by_placeholder('Телефон начните с символа "+"').fill(username)
        random_sleep();
        page.get_by_placeholder("Введите пароль").fill(password)
        random_sleep();
        page.get_by_text("Войти").click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);
        # 2. Проход по ссылкам
        page.get_by_text("Управление базами").click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);
        page.get_by_title("Сделать выгрузку").click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);
        with page.expect_popup() as popup_info:
            page.get_by_alt_text("Кнопка скачать").first.click()
        new_tab = popup_info.value
        # Ждем появления тега meta в head
        new_tab.wait_for_selector('meta[http-equiv="refresh"]', state="attached")
        # Получаем содержимое атрибута content
        refresh_content = new_tab.locator('meta[http-equiv="refresh"]').get_attribute("content")
        random_sleep();
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

def downFile(download_url: str):
    """
    Парсит download_url и загружет файл в target_dir
    """
    target_dir = os.getenv("TargetDir")
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
        print(f"Info downFile: file down success: {full_path}\n", result.stdout)
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
    with zipfile.ZipFile(full_path, 'r') as z:
        if z.testzip():
            msg = "Error testFile: file not found or corrupt"
            print(msg)
            report_lines.append(msg)
            return 
        for info in z.infolist():
            # Не пишем в отчет нулевые файлы
            info_file = f"{info.filename} — {round(info.file_size/1024**2, 2)} MB"
            if '0.0 MB' not in info_file:
                report_lines.append(info_file)
        print(f"Info testFile: file check success")
    return "\n".join(report_lines)

def send_ntfy_message(message: str):
    """
    Отправляет уведомление в ntfy
    """
    ntfy_url = os.getenv("ntfy_url")
    ntfy_cred = os.getenv("ntfy_cred")
    try:
        response = requests.post(
            ntfy_url,
            data=message.encode('utf-8'),
            headers={
                "Authorization": f"Basic {ntfy_cred}",
                "Title": "Bcapper 1C GRM",  # Заголовок уведомления
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

url = getUrl()
fp = downFile(url)
rep = testFile(fp)
send_ntfy_message(rep)
