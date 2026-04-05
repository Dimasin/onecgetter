from playwright.sync_api import sync_playwright
import time
import random
import subprocess
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
import zipfile
import requests
import ast

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

def getUrlGrm():
    """
    Вытаскивает URL с сайта target_url
    """
    target_url = os.getenv("TgtUrlGrm")
    username = os.getenv("UserGrm")
    password = os.getenv("PassGrm")
    with sync_playwright() as p:
        # Запускаем Browser
        browser = p.chromium.launch(channel="chrome", headless=True)
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
        random_sleep(6,9);
        # 2. Проход по ссылкам
        page.get_by_text("Управление базами").click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9);
        page.get_by_title("Сделать выгрузку").click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9);
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

def downFileGrm(download_url: str):
    """
    Парсит download_url и загружет файл в target_dir
    """
    target_dir = os.getenv("TgtDirGrm")
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
    
def downFileFresh():
    """
    Загружает бэкапы target_base с сайта target_url в каталоги target_dir
    """
    target_url = os.getenv("TgtUrlFresh")
    username = os.getenv("UserFresh")
    password = os.getenv("PassFresh")
    target_dir = ast.literal_eval(os.getenv("TgtDirFresh"))
    target_base = ast.literal_eval(os.getenv("TgtBaseFresh"))
    out_files = []
    with sync_playwright() as p:
        # Запускаем Browser
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(target_url)
        # 1. АВТОРИЗАЦИЯ
        random_sleep();
        page.get_by_placeholder("Пользователь").fill(username)
        random_sleep();
        page.get_by_placeholder("Пароль").fill(password)
        random_sleep();
        page.get_by_role("button", name="Войти").click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9);
        # 2. Проход по ссылкам
        page.locator('span[title="Архивирование"]').click()
        page.wait_for_load_state("networkidle")
        random_sleep(6,9);       
        page.locator(".gridLine").first.wait_for(state="attached", timeout=60000)
        rows = page.locator("#grid_form1_Список > .gridBody > .gridLine")
        count = rows.count()
        random_sleep(6,9);
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
                if match:
                    target_folder = target_dir[index]
                    os.makedirs(target_folder, exist_ok=True)
                    # Ждем 10 минут, пока сервер готовит файл
                    with page.expect_download(timeout=600000) as download_info:
                        page.locator("[id=\"form1_ФормаВыгрузитьРезервнуюКопию\"]").click()
                    download = download_info.value
                    save_path = os.path.join(target_folder, download.suggested_filename)
                    print(f"Download: {match} to {save_path}")
                    download.save_as(save_path)
                    target_base.pop(index)
                    target_dir.pop(index)
                    out_files.append(save_path)
                    print(f"Download success: {match} to {save_path}")
            except Exception as e:
                print(f"Download error {match}: file {save_path}: {e}")
    return out_files

# Bcap GRM
url = getUrlGrm()
fp = downFileGrm(url)
rep = testFile(fp)
send_ntfy_message(rep)

# Bcap Fresh
out_files = downFileFresh()
for file in out_files:
    rep = testFile(file)
    send_ntfy_message(rep)