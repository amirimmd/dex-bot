# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import time
import os

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
api_error = None 

# === بخش ۳: منطق اصلی برنامه (با فیلتر دستی) ===
def fetch_data_and_update():
    global latest_data, api_error
    
    # ما یک کوئری کلی‌تر ارسال می‌کنیم تا شانس پیدا کردن ارزها بیشتر شود
    # و سپس خودمان در کد فیلترهای دقیق را اعمال می‌کنیم
    base_url = "https://api.dexscreener.com/latest/dex/search"
    params = {'q': 'solana fdv > 500000'} # فقط با یک فیلتر اصلی جستجو می‌کنیم
    
    all_pairs = {}
    
    try:
        print("در حال ارسال درخواست به Dexscreener...")
        response = requests.get(base_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        raw_pairs = data.get('pairs', [])
        print(f"تعداد {len(raw_pairs)} ارز اولیه دریافت شد. در حال فیلتر کردن دستی...")
        
        filtered_pairs = []
        for pair in raw_pairs:
            try:
                # *** شروع فیلترهای دقیق و دستی ***
                if (pair.get('chainId') == 'solana' and
                    pair.get('liquidity', {}).get('usd', 0) > 50000 and
                    pair.get('fdv', 0) > 500000 and
                    pair.get('volume', {}).get('h24', 0) > 50000 and
                    pair.get('priceChange', {}).get('h6', 0) > 5 and
                    pair.get('priceChange', {}).get('h24', 0) > 5):
                    
                    filtered_pairs.append(pair)
            except (TypeError, ValueError):
                # اگر داده‌ای ناقص بود، از آن صرف نظر می‌کنیم
                continue

        latest_data = filtered_pairs
        api_error = None
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] عملیات با موفقیت تمام شد. تعداد ارزهای نهایی پس از فیلتر: {len(latest_data)}")
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching data from Dexscreener: {e}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}")
        api_error = error_message
        latest_data = []

# بقیه کد بدون تغییر است
def background_task():
    while True:
        fetch_data_and_update()
        time.sleep(900)

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify({'data': latest_data, 'error': api_error})

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("در حال اجرای عملیات اولیه...")
    task_thread = Thread(target=fetch_data_and_update)
    task_thread.daemon = True
    task_thread.start()
    run_web_server()
