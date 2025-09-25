# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import time
import os # ماژول os برای خواندن متغیرهای محیطی اضافه شد

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
api_error = None 

# === بخش ۳: منطق اصلی برنامه ===
def fetch_data_and_update():
    global latest_data, api_error
    
    base_url = "https://api.dexscreener.com/latest/dex/search"
    params = {'q': 'solana liquidity > 50000 AND fdv > 500000 AND volume > 50000 AND priceChange.h6 > 5 AND priceChange.h24 > 5'}
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        latest_data = data.get('pairs', [])
        api_error = None
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] داده‌ها با موفقیت آپدیت شدند. تعداد: {len(latest_data)}")
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching data from Dexscreener: {e}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}")
        api_error = error_message
        latest_data = []

# === بخش ۴: حلقه تکرار در پس‌زمینه ===
def background_task():
    while True:
        fetch_data_and_update()
        time.sleep(900) 

# === بخش ۵: وب‌سرور Flask ===
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify({'data': latest_data, 'error': api_error})

def run_web_server():
    # *** تغییر اصلی اینجاست ***
    # پورت را از متغیر محیطی Render می‌خوانیم. اگر وجود نداشت، از ۱۰۰۰۰ استفاده می‌کنیم.
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# === بخش ۶: اجرای برنامه ===
if __name__ == "__main__":
    print("در حال اجرای عملیات اولیه...")
    task_thread = Thread(target=fetch_data_and_update)
    task_thread.daemon = True
    task_thread.start()
    
    run_web_server()
