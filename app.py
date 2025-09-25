# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import json
import time

# === بخش ۲: متغیر سراسری برای ذخیره آخرین داده‌ها ===
latest_data = []

# === بخش ۳: منطق اصلی برنامه شما ===
def fetch_data_and_update():
    global latest_data
    url = "https://api.dexscreener.com/api/v2/sdk/pairs/search?q=liquidity_gt_50000 AND fdv_gt_500000 AND volume_h24_gt_50000"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        latest_data = data.get('pairs', [])
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] داده‌ها با موفقیت آپدیت شدند. تعداد: {len(latest_data)}")
    
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] خطایی در هنگام ارسال درخواست رخ داد: {e}")

# === بخش ۴: حلقه تکرار در پس‌زمینه ===
def background_task():
    while True:
        # 10 دقیقه صبر کن و بعد داده‌ها را آپدیت کن
        time.sleep(600) 
        fetch_data_and_update()

# === بخش ۵: وب‌سرور Flask ===
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify(latest_data)

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# === بخش ۶: اجرای برنامه ===
if __name__ == "__main__":
    # *** تغییر اصلی اینجاست ***
    # ۱. ابتدا یک بار داده‌ها را بلافاصله دریافت می‌کنیم
    print("در حال دریافت داده‌های اولیه...")
    fetch_data_and_update()

    # ۲. سپس وظیفه پس‌زمینه را برای آپدیت‌های بعدی شروع می‌کنیم
    task_thread = Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()
    
    # ۳. و در نهایت وب‌سرور را اجرا می‌کنیم
    run_web_server()
