from playwright.sync_api import sync_playwright
import time
import random
import os
from dotenv import load_dotenv
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
        browser = p.chromium.launch(headless=False)
        # browser = p.firefox.launch(channel="firefox", headless=False)
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
        random_sleep(3,5);
        # 2. Проход по ссылкам
        page.locator('span[title="Архивирование"]').click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);       
        page.locator(".gridLine").first.wait_for(state="attached", timeout=60000)
        rows = page.locator("#grid_form1_Список > .gridBody > .gridLine")
        count = rows.count()
        for i in range(1,count):
            if not target_base:
                break
            # Получаем текст строки, но почему то rows.nth(i) не тот, что в page.locator(f"div:nth-child({i}) > div > .gridBoxImg > .dIB")
            # row = rows.nth(i)
            try:
                if (i==1):
                    page.locator(".dIB").first.click()
                else:
                    page.locator(f"div:nth-child({i}) > div > .gridBoxImg > .dIB").click()
                file_name = page.locator("#grid_form1_Список > .gridBody > .gridLine.select.eActivityBack").first.inner_text().strip()
                index, match = next(((i, name) for i, name in enumerate(target_base) if name in file_name), (None, None))
                # match = next((name for name in target_base if name in file_name), None)
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


def getCookies():
    target_url = os.getenv("TargetUrlFresh")
    username = os.getenv("UserNameFresh")
    password = os.getenv("PasswordFresh")
    target_dir = ast.literal_eval(os.getenv("TgtDirFresh"))
    target_base = ast.literal_eval(os.getenv("TargetBaseFresh"))
    target_url = os.getenv("TargetUrlFresh")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
    
        page.goto(target_url) # Ссылка на вход
        # 1. АВТОРИЗАЦИЯ
        random_sleep();
        page.get_by_placeholder("Пользователь").fill(username)
        random_sleep();
        page.get_by_placeholder("Пароль").fill(password)
        random_sleep();
        page.get_by_role("button", name="Войти").click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);
        # 2. Проход по ссылкам
        page.locator('span[title="Архивирование"]').click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);

        # Инструмент остановит выполнение. 
        # Вы сами логинитесь и доходите до нужной таблицы.
        page.pause() 
    
        # Как только дошли — нажимаете "Resume" в инспекторе или просто
        # закройте браузер, предварительно выполнив это в коде:
        context.storage_state(path="auth.json")

def debugUrl():
    target_dir = ast.literal_eval(os.getenv("TargetDirFresh"))
    target_base = ast.literal_eval(os.getenv("TargetBaseFresh"))
    target_url = os.getenv("TargetUrlFresh")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        # Загружаем сессию — логин не нужен
        context = browser.new_context(storage_state="auth.json",accept_downloads=True)
        page = context.new_page()

        # Переходим сразу на страницу с таблицей
        page.goto(target_url)
        random_sleep();

        # page.pause()

        page.locator('span[title="Архивирование"]').click()
        page.wait_for_load_state("networkidle")
        random_sleep(3,5);
        # Даем время таблице подгрузиться
        # page.wait_for_selector(".gridLine", timeout=60000)
        page.locator(".gridLine").first.wait_for(state="attached", timeout=60000)


        # Локатор формы, певый взят из самого playwright
        # locator("[id=\"form1_$scrl\"]") locator(".gridLine")
        # Проверка локатора в консоли
        # document.querySelectorAll('#grid_form1_Список .gridBody .gridLine')
        #rows = page.locator(".gridLine")
        #count = rows.count()

        rows = page.locator("#grid_form1_Список > .gridBody > .gridLine")
        count = rows.count()

        for i in range(1,count):
            if not target_base:
                break
            # Получаем текст строки, но почему то rows.nth(i) не тот, что в page.locator(f"div:nth-child({i}) > div > .gridBoxImg > .dIB")
            # row = rows.nth(i)
            try:
                if (i==1):
                    page.locator(".dIB").first.click()
                else:
                    page.locator(f"div:nth-child({i}) > div > .gridBoxImg > .dIB").click()
                file_name = page.locator("#grid_form1_Список > .gridBody > .gridLine.select.eActivityBack").first.inner_text().strip()
                index, match = next(((i, name) for i, name in enumerate(target_base) if name in file_name), (None, None))
                # match = next((name for name in target_base if name in file_name), None)
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
                    print(f"Download success: {match} to {save_path}")
            except Exception as e:
                print(f"Download error {match}: file {save_path}: {e}")
        
        # Для клика по самой левой иконке, самая верхняя, дальше начинается с индекса 2
        # locator(".dIB").first
        # locator("div:nth-child(2) > div > .gridBoxImg > .dIB")
        # locator("div:nth-child(13) > div > .gridBoxImg > .dIB")
        # Еще способ
        # locator(".checkbox").first
        # locator("div:nth-child(2) > div:nth-child(5) > .gridBoxImg > .checkbox")

        # Пробуем клик
        #page.get_by_text("Base one").nth(1).click()
        #page.get_by_text("Base Two").nth(1).click()
        #page.get_by_text("Base Three").nth(1).click()
        #with page.expect_download() as download_info:
        #    page.locator("[id=\"form1_ФормаВыгрузитьРезервнуюКопию\"]").click()
        
        #download = download_info.value
        #print(f"Скачиваем файл: {download.suggested_filename}")
        # Оставляем браузер открытым для осмотра результата
        #page.pause()

#getUrl()
#getCookies()
debugUrl()