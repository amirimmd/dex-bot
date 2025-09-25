# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import time

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
api_error = None 

# === بخش ۳: منطق اصلی برنامه (با فیلترهای جدید) ===
def fetch_data_and_update():
    global latest_data, api_error
    
    # بازه‌های نقدینگی برای جستجوی دقیق‌تر
    liquidity_ranges = [
        (50000, 75000), (75000, 100000), (100000, 150000),
        (150000, 250000), (250000, 500000), (500000, 1000000)
    ]
    
    all_pairs = {}
    base_url = "https://api.dexscreener.com/latest/dex/search"
    
    try:
        for min_liq, max_liq in liquidity_ranges:
            # *** تغییر اصلی اینجاست: اضافه شدن فیلترهای h6 و h24 ***
            # priceChange > 5 یعنی تغییر قیمت بیش از ۵٪ مثبت باشد
            query = (f"solana liquidity > {min_liq} AND liquidity < {max_liq} "
                     f"AND fdv > 500000 AND volume > 50000 "
                     f"AND priceChange.h6 > 5 AND priceChange.h24 > 5")
            
            params = {'q': query}
            
            print(f"در حال جستجو با فیلترهای جدید برای نقدینگی بین ${min_liq} و ${max_liq}...")
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            pairs = data.get('pairs', [])
            if pairs:
                for pair in pairs:
                    all_pairs[pair['pairAddress']] = pair
            
            time.sleep(1)

        latest_data = list(all_pairs.values())
        api_error = None
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] عملیات با موفقیت تمام شد. تعداد ارزهای فیلتر شده: {len(latest_data)}")
    
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
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    print("در حال اجرای عملیات اولیه...")
    task_thread = Thread(target=fetch_data_and_update)
    task_thread.daemon = True
    task_thread.start()
    run_web_server()
