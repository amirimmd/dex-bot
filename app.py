# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask
from threading import Thread
import requests
import json
import time

# === بخش ۲: منطق اصلی برنامه شما (همان تابع قبلی) ===
def fetch_and_save_data():
    """
    تابعی برای دریافت داده‌ها از Dexscreener و چاپ آن‌ها.
    """
    url = "https://api.dexscreener.com/api/v2/sdk/pairs/search?q=liquidity_gt_50000 AND fdv_gt_500000 AND volume_h24_gt_50000"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        filtered_pairs = data.get('pairs', [])

        if filtered_pairs:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] داده‌ها با موفقیت دریافت شدند. تعداد: {len(filtered_pairs)}")
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] هیچ جفت ارزی با معیارهای مشخص شده یافت نشد.")

    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] خطایی در هنگام ارسال درخواست رخ داد: {e}")


# === بخش ۳: حلقه تکرار که در پس‌زمینه اجرا می‌شود ===
def background_task():
    """
    این تابع در یک حلقه بی‌نهایت، تابع اصلی شما را هر ۱۰ دقیقه یک‌بار فراخوانی می‌کند.
    """
    while True:
        fetch_and_save_data()
        # ۱۰ دقیقه = ۶۰۰ ثانیه
        time.sleep(600)


# === بخش ۴: وب‌سرور برای زنده نگه داشتن Repl ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# === بخش ۵: اجرای همزمان وب‌سرور و حلقه تکرار ===
if __name__ == "__main__":
    # اجرای تابع background_task در یک نخ (Thread) جداگانه
    task_thread = Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()

    # اجرای وب‌سرور در نخ اصلی
    run_web_server()
