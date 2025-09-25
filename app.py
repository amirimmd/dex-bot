# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import json
import time

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
# متغیر جدید برای ذخیره پیام خطا
api_error = None 

# === بخش ۳: منطق اصلی برنامه شما ===
def fetch_data_and_update():
    global latest_data, api_error
    url = "https://api.dexscreener.com/api/v2/sdk/pairs/search?q=liquidity_gt_50000 AND fdv_gt_500000 AND volume_h24_gt_50000"
    
    try:
        response = requests.get(url, timeout=10) # اضافه کردن تایم‌اوت ۱۰ ثانیه‌ای
        response.raise_for_status() # اگر خطایی مثل 404 یا 500 رخ داد، به except می‌رود
        data = response.json()
        latest_data = data.get('pairs', [])
        api_error = None # اگر موفق بود، پیام خطا را پاک می‌کنیم
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] داده‌ها با موفقیت آپدیت شدند. تعداد: {len(latest_data)}")
    
    # *** تغییر اصلی برای نمایش خطا ***
    except requests.exceptions.RequestException as e:
        # اگر خطایی در اتصال رخ داد، آن را در متغیر خطا ذخیره می‌کنیم
        error_message = f"Error fetching data from Dexscreener: {e}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}")
        api_error = error_message
        latest_data = [] # لیست داده‌ها را خالی می‌کنیم

# === بخش ۴: حلقه تکرار در پس‌زمینه ===
def background_task():
    while True:
        fetch_data_and_update()
        time.sleep(600)

# === بخش ۵: وب‌سرور Flask ===
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    # حالا هم داده‌ها و هم پیام خطا را ارسال می‌کنیم
    return jsonify({
        'data': latest_data,
        'error': api_error
    })

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# === بخش ۶: اجرای برنامه ===
if __name__ == "__main__":
    print("در حال دریافت داده‌های اولیه...")
    fetch_data_and_update()

    task_thread = Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()
    
    run_web_server()
