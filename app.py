# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import json
import time

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
api_error = None 

# === بخش ۳: منطق اصلی برنامه شما ===
def fetch_data_and_update():
    global latest_data, api_error
    
    # *** تغییر اصلی اینجاست: URL صحیح جایگزین شد ***
    # به جای یک URL طولانی، ما پارامترها را به شکل استاندارد ارسال می‌کنیم
    base_url = "https://api.dexscreener.com/latest/dex/search"
    params = {'q': 'liquidity > 50000 AND fdv > 500000 AND volume > 50000'}
    
    try:
        # ارسال درخواست با پارامترهای جداگانه
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # در API جدید، کلید اصلی 'pairs' است
        latest_data = data.get('pairs', [])
        api_error = None
        print(f"[{time.strftime('%Y-%-m-%d %H:%M:%S')}] داده‌ها با موفقیت آپدیت شدند. تعداد: {len(latest_data)}")
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching data from Dexscreener: {e}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}")
        api_error = error_message
        latest_data = []

# === بخش ۴: حلقه تکرار در پس‌زمینه ===
def background_task():
    while True:
        fetch_data_and_update()
        time.sleep(600) # ۱۰ دقیقه

# === بخش ۵: وب‌سرور Flask ===
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
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
