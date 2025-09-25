# === بخش ۱: کتابخانه‌های لازم ===
# jsonify برای ارسال پاسخ JSON و render_template برای نمایش فایل HTML اضافه شده است
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import json
import time

# === بخش ۲: متغیر سراسری برای ذخیره آخرین داده‌ها ===
# این متغیر آخرین لیست ارزهای دریافت شده را در حافظه نگه می‌دارد
latest_data = []

# === بخش ۳: منطق اصلی برنامه شما ===
def fetch_data_and_update():
    """
    داده‌ها را از Dexscreener دریافت کرده و متغیر latest_data را آپدیت می‌کند.
    """
    global latest_data  # اعلام می‌کنیم که می‌خواهیم متغیر سراسری را تغییر دهیم
    url = "https://api.dexscreener.com/api/v2/sdk/pairs/search?q=liquidity_gt_50000 AND fdv_gt_500000 AND volume_h24_gt_50000"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # فقط لیست ارزها را در متغیر ذخیره می‌کنیم
        latest_data = data.get('pairs', [])
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] داده‌ها با موفقیت آپدیت شدند. تعداد: {len(latest_data)}")
    
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] خطایی در هنگام ارسال درخواست رخ داد: {e}")

# === بخش ۴: حلقه تکرار در پس‌زمینه ===
def background_task():
    while True:
        fetch_data_and_update()
        time.sleep(600) # ۱۰ دقیقه

# === بخش ۵: وب‌سرور Flask ===
app = Flask(__name__)

# این آدرس، صفحه اصلی وب‌سایت را نمایش می‌دهد
@app.route('/')
def home():
    # این تابع به دنبال فایلی به نام index.html در پوشه templates می‌گردد
    return render_template('index.html')

# این آدرس، داده‌های ارزها را به صورت JSON برمی‌گرداند
@app.route('/api/data')
def get_data():
    return jsonify(latest_data)

def run_web_server():
    # توجه: پوشه templates باید در کنار همین فایل app.py باشد
    app.run(host='0.0.0.0', port=8080)

# === بخش ۶: اجرای برنامه ===
if __name__ == "__main__":
    task_thread = Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()
    
    run_web_server()
