from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
from telegram import Bot
import asyncio
import time

# Налаштування Selenium
CHROME_DRIVER_PATH = "/usr/local/bin/chromedriver"
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")


# Telegram бот
TELEGRAM_TOKEN = "7730806224:AAGtig-wTbaJhljMElOM4aO5ZYTvkDOlHfY"
CHAT_IDS = ['725474643', '7353625787']

# API URL для футболу та баскетболу
API_FOOTBALL_URL = "https://landing-sports-api.sbk-188sports.com/api/v2/en-gb/Japan/sport/1/mop/coupon/104/premium"
API_BASKETBALL_URL = "https://landing-sports-api.sbk-188sports.com/api/v2/en-gb/Japan/sport/2/mop/coupon/104/premium"

# Глобальний словник для зберігання старих даних
old_data = {
    "football": {},
    "basketball": {}
}

# Глобальний словник для зберігання старих значень голів
old_goals = {
    "football": {},
    "basketball": {}
}

# Отримання динамічного токена та куків через Selenium
def get_dynamic_headers():
    service = Service(CHROME_DRIVER_PATH)
    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get("https://sports.sbk-188sports.com/en-gb/sports?c=207&u=https://www.188bet.com")
        time.sleep(10)  # Очікуємо, поки сторінка завантажиться

        # Отримуємо jwt з sessionStorage
        jwt_token = driver.execute_script("return sessionStorage.getItem('JWT');")
        print(f"jwt token: {jwt_token}")

        cookies = driver.get_cookies()
        cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Cookie": cookie_str,
            "Accept": "application/json",
            "Origin": "https://sports.sbk-188sports.com",  # Додаємо Origin, якщо потрібно
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        }
        return headers


# Перевірка з'єднання з API та отримання даних
def check_api_connection(headers, url):
    try:
        response = requests.get(url, headers=headers, timeout=100)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Помилка: Код відповіді {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Помилка з'єднання з API: {e}")
        return None


# Отримання значень коефіцієнтів фори та тоталу
def extract_v_values(data, sport_type="football"):
    try:
        # Отримуємо список категорій (categories)
        categories = data["d"]["s"]["c"]
    except (KeyError, IndexError) as e:
        print("Помилка при доступі до категорій:", e)
        return {}

    results = {}

    # Проходимо по всіх категоріях (від 0 до 2)
    for i in range(len(categories)):
        try:
            # Отримуємо список подій (events) для поточної категорії
            events = categories[i]["e"]
        except (KeyError, IndexError) as e:
            print(f"Помилка при доступі до подій у категорії {i}:", e)
            continue

        # Проходимо по всіх подіях (від 0 до 10)
        for j in range(len(events)):
            try:
                # Отримуємо основні ринки (main_markets) для поточної події
                main_markets = events[j]["fml"]["main_markets"]
                # Отримуємо назву матчу
                match_name = events[j]["h"] + " vs " + events[j]["a"]
                # Отримуємо голи домашньої та гостьової команди з об'єкта "i"
                goals_home = events[j].get("i", {}).get("h", 0)  # Голи домашньої команди
                goals_away = events[j].get("i", {}).get("a", 0)  # Голи гостьової команди
            except (KeyError, IndexError) as e:
                print(f"Помилка при доступі до основних ринків або даних матчу у події {j} категорії {i}:", e)
                continue

            # Ініціалізація змінних для коефіцієнтів фори та тоталу
            handicap = None
            total_points = None
            handicap_hh = None  # Значення hh для фори
            handicap_ah = None  # Значення ah для фори
            total_hh = None  # Значення hh для тоталу
            total_ah = None  # Значення ah для тоталу

            for market in main_markets:
                if market["n"] == "Handicap":
                    # Якщо це ринок фори, отримуємо коефіцієнти
                    handicap = {
                        "handicap_1": check_and_adjust_value(market["o"][0]["v"]),
                        "handicap_2": check_and_adjust_value(market["o"][1]["v"])
                    }
                    # Зберігаємо значення hh та ah для фори
                    handicap_hh = market.get("hh")
                    handicap_ah = market.get("ah")

                # Для футболу шукаємо "Goals: Over / Under", для баскетболу залишаємо "Total Points: Over / Under"
                elif sport_type == "football" and market["n"] == "Goals: Over / Under":
                    total_points = {
                        "total_1": check_and_adjust_value(market["o"][0]["v"]),
                        "total_2": check_and_adjust_value(market["o"][1]["v"])
                    }
                    # Зберігаємо значення hh та ah для тоталу
                    total_hh = market.get("hh")
                    total_ah = market.get("ah")

                elif sport_type == "basketball" and market["n"] == "Total Points: Over / Under":
                    total_points = {
                        "total_1": check_and_adjust_value(market["o"][0]["v"]),
                        "total_2": check_and_adjust_value(market["o"][1]["v"])
                    }
                    # Зберігаємо значення hh та ah для тоталу
                    total_hh = market.get("hh")
                    total_ah = market.get("ah")

            # Зберігаємо результати для поточної події
            results[match_name] = {
                "handicap": handicap,
                "total_points": total_points,
                "goals_home": goals_home,  # Додаємо голи домашньої команди
                "goals_away": goals_away,  # Додаємо голи гостьової команди
                "handicap_hh": handicap_hh,  # Додаємо значення hh для фори
                "handicap_ah": handicap_ah,  # Додаємо значення ah для фори
                "total_hh": total_hh,  # Додаємо значення hh для тоталу
                "total_ah": total_ah  # Додаємо значення ah для тоталу
            }

    # Повертаємо всі результати
    return results


# Функція для перевірки і коригування значення
def check_and_adjust_value(value):
    if value is None:
        return None
    try:
        # Перетворюємо рядок на число
        value = float(value)
        # Якщо значення від'ємне, додаємо 2
        if value < 0:
            value += 2
        return round(value, 2)  # Округляємо до двох знаків після коми
    except ValueError:
        print(f"Не вдалося конвертувати значення {value} в число.")
        return value


# Надсилання повідомлення в Telegram
async def send_notification(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    for chat_id in CHAT_IDS:  # Перебираємо всі CHAT_ID
        await bot.send_message(chat_id=chat_id, text=message)


# Порівняння старих і нових даних
def compare_data(old_data, new_data, sport_type):
    messages = []
    for match_name, new_values in new_data.items():
        if match_name in old_data:
            old_values = old_data[match_name]

            if (new_values["goals_home"] != old_values["goals_home"] or
                new_values["goals_away"] != old_values["goals_away"]):
                continue  # Пропускаємо, якщо голи змінилися

            message = f"Матч ({'Футбол' if sport_type == 'football' else 'Баскетбол'}): {match_name}\n"

            # Перевіряємо зміни фори незалежно від hh та ah
            if new_values["handicap"] and old_values["handicap"]:
                handicap_changes = []
                if (new_values["handicap_hh"] == old_values["handicap_hh"] and
                    new_values["handicap_ah"] == old_values["handicap_ah"]):
                    if (new_values["handicap"]["handicap_1"] not in [0, None] and
                        old_values["handicap"]["handicap_1"] not in [0, None] and
                        abs(new_values["handicap"]["handicap_1"] - old_values["handicap"]["handicap_1"]) >= 0.13):
                        handicap_changes.append(f"Фора 1: {old_values['handicap']['handicap_1']} → {new_values['handicap']['handicap_1']}")
                    if (new_values["handicap"]["handicap_2"] not in [0, None] and
                        old_values["handicap"]["handicap_2"] not in [0, None] and
                        abs(new_values["handicap"]["handicap_2"] - old_values["handicap"]["handicap_2"]) >= 0.13):
                        handicap_changes.append(f"Фора 2: {old_values['handicap']['handicap_2']} → {new_values['handicap']['handicap_2']}")
                if handicap_changes:
                    message += "Зміна фори:\n" + "\n".join(handicap_changes) + "\n"

            # Перевіряємо зміни тоталу незалежно від hh та ah
            if new_values["total_points"] and old_values["total_points"]:
                total_changes = []
                if (new_values["total_hh"] == old_values["total_hh"] and
                    new_values["total_ah"] == old_values["total_ah"]):
                    if (new_values["total_points"]["total_1"] not in [0, None] and
                        old_values["total_points"]["total_1"] not in [0, None] and
                        abs(new_values["total_points"]["total_1"] - old_values["total_points"]["total_1"]) >= 0.13):
                        total_changes.append(f"Over: {old_values['total_points']['total_1']} → {new_values['total_points']['total_1']}")
                    if (new_values["total_points"]["total_2"] not in [0, None] and
                        old_values["total_points"]["total_2"] not in [0, None] and
                        abs(new_values["total_points"]["total_2"] - old_values["total_points"]["total_2"]) >= 0.13):
                        total_changes.append(f"Under: {old_values['total_points']['total_2']} → {new_values['total_points']['total_2']}")
                if total_changes:
                    message += "Зміна тоталу:\n" + "\n".join(total_changes) + "\n"

            # Додаємо повідомлення, якщо є зміни
            if "Зміна" in message:
                messages.append(message)

    return messages



# Перевірка та сповіщення для футболу і баскетболу
async def check_and_notify():
    headers = get_dynamic_headers()

    # Отримуємо нові дані для футболу
    football_data = check_api_connection(headers, API_FOOTBALL_URL)
    if football_data:
        new_football_data = extract_v_values(football_data, sport_type="football")
        messages = compare_data(old_data["football"], new_football_data, "football")
        if messages:
            await send_notification("\n".join(messages))
        # Оновлюємо старі дані
        old_data["football"] = new_football_data

    # Отримуємо нові дані для баскетболу
    basketball_data = check_api_connection(headers, API_BASKETBALL_URL)
    if basketball_data:
        new_basketball_data = extract_v_values(basketball_data, sport_type="basketball")
        messages = compare_data(old_data["basketball"], new_basketball_data, "basketball")
        if messages:
            await send_notification("\n".join(messages))
        # Оновлюємо старі дані
        old_data["basketball"] = new_basketball_data


# Основний цикл
if __name__ == "__main__":
    while True:
        try:
            asyncio.run(check_and_notify())
        except Exception as e:
            print(f"Непередбачена помилка: {e}")
        time.sleep(1)