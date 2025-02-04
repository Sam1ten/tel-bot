from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
from telegram import Bot
import asyncio
import time

# Налаштування Selenium
CHROME_DRIVER_PATH = "F:\\Bot\\chromedriver.exe"  # Вкажіть ваш шлях до chromedriver
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

# Telegram бот
TELEGRAM_TOKEN = "7730806224:AAGtig-wTbaJhljMElOM4aO5ZYTvkDOlHfY"
CHAT_ID = "725474643"

API_URL = "https://landing-sports-api.sbk-188sports.com"

AUTH_TOKEN_API = "https://sports.sbk-188sports.com/ftlessaue-me-would-The-good-Levaine-That-I-Pings?d=sports.sbk-188sports.com"

# Отримання динамічного токена та куків через Selenium
def get_dynamic_headers():
    service = Service(CHROME_DRIVER_PATH)
    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get("https://sports.sbk-188sports.com/en-gb/sports?c=207&u=https://www.188bet.com")
        time.sleep(10)  # Очікуємо, поки сторінка завантажиться

        # Отримуємо токен Authorization із JavaScript
        token = driver.execute_script("return localStorage.getItem('auth_token');")
        print(f"token is: {token}")
        cookies = driver.get_cookies()
        cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

        headers = {
            "Authorization": f"Bearer {token}",
            "Cookie": cookie_str,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        }
        return headers

# Перевірка з'єднання з API
def check_api_connection(headers):
    try:
        response = requests.get(API_URL, headers=headers, timeout=100)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Помилка: Код відповіді {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Помилка з'єднання з API: {e}")
        return None

# Надсилання повідомлення в Telegram
async def send_notification(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

# Перевірка та сповіщення
async def check_and_notify():
    headers = get_dynamic_headers()  # Отримуємо оновлені заголовки
    data = check_api_connection(headers)
    if data:
        message = f"API з'єднання успішне. Дані:\n{data}"
        print(message)
        await send_notification(message)
    else:
        message = "Помилка з'єднання з API або дані відсутні."
        print(message)
        await send_notification(message)

# Основний цикл
if __name__ == "__main__":
    while True:
        try:
            asyncio.run(check_and_notify())
        except Exception as e:
            print(f"Непередбачена помилка: {e}")
        time.sleep(300)
