# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import time
import os

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
api_error = None 

# === بخش ۳: منطق اصلی برنامه (ترکیب استراتژی‌ها) ===
def fetch_data_and_update():
    global latest_data, api_error
    
    # بازه‌های نقدینگی برای جستجوی سبک و تکه تکه
    liquidity_ranges = [
        (50000, 100000), (100000, 250000), (250000, 500000), (500000, 1000000)
    ]
    
    all_pairs = {}
    base_url = "https://api.dexscreener.com/latest/dex/search"
    
    try:
        # برای هر بازه نقدینگی، یک درخواست جداگانه ارسال می‌کنیم
        for min_liq, max_liq in liquidity_ranges:
            # کوئری سبک‌تر برای دریافت لیست اولیه
            query = f"solana liquidity > {min_liq} AND liquidity < {max_liq}"
            params = {'q': query}
            
            print(f"در حال دریافت داده برای نقدینگی بین ${min_liq} و ${max_liq}...")
            response = requests.get(base_url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            raw_pairs = data.get('pairs', [])
            
            # حالا روی لیست کوچک دریافت شده، فیلترهای دقیق را اعمال می‌کنیم
            for pair in raw_pairs:
                try:
                    if (pair.get('fdv', 0) > 500000 and
                        pair.get('volume', {}).get('h24', 0) > 50000 and
                        pair.get('priceChange', {}).get('h6', 0) > 5 and
                        pair.get('priceChange', {}).get('h24', 0) > 5):
                        
                        # از آدرس جفت‌ارز به عنوان کلید برای جلوگیری از تکرار استفاده می‌کنیم
                        all_pairs[pair['pairAddress']] = pair
                except (TypeError, ValueError):
                    continue
            
            time.sleep(1) # وقفه کوتاه بین درخواست‌ها

        latest_data = list(all_pairs.values())
        api_error = None
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] عملیات با موفقیت تمام شد. تعداد ارزهای نهایی: {len(latest_data)}")
    
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
