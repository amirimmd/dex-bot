# === بخش ۱: کتابخانه‌های لازم ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import time
import os

# === بخش ۲: متغیرهای سراسری ===
latest_data = []
api_error = None 

# === بخش ۳: منطق اصلی برنامه (با فیلترهای جدید شما) ===
def fetch_data_and_update():
    global latest_data, api_error
    
    # ارسال یک درخواست کلی برای تمام ارزهای با نقدینگی بالای ۵۰ هزار
    base_url = "https://api.dexscreener.com/latest/dex/search"
    params = {'q': 'solana liquidity > 50000'}
    
    try:
        print("در حال ارسال درخواست به Dexscreener با فیلتر نقدینگی بالای ۵۰ هزار...")
        response = requests.get(base_url, params=params, timeout=30) # افزایش تایم‌اوت به ۳۰ ثانیه برای درخواست‌های بزرگتر
        response.raise_for_status()
        data = response.json()
        
        raw_pairs = data.get('pairs', [])
        print(f"تعداد {len(raw_pairs)} ارز اولیه دریافت شد. در حال فیلتر کردن دستی...")
        
        filtered_pairs = []
        for pair in raw_pairs:
            try:
                # *** شروع فیلترهای دقیق و دستی با شرایط جدید شما ***
                if (
                    # شرط نقدینگی بالای ۵۰ هزار (این شرط توسط API اعمال شده اما برای اطمینان چک می‌کنیم)
                    pair.get('liquidity', {}).get('usd', 0) > 50000 and
                    
                    # شرط مارکت کپ بالای ۵۰۰ هزار
                    pair.get('fdv', 0) > 500000 and
                    
                    # شرط حجم معاملات ۲۴ ساعته بالای ۵۰ هزار
                    pair.get('volume', {}).get('h24', 0) > 50000 and
                    
                    # شرط رشد قیمت ۶ ساعته بالای نیم درصد
                    pair.get('priceChange', {}).get('h6', 0) > 0.5 and
                    
                    # شرط رشد قیمت ۲۴ ساعته بالای نیم درصد
                    pair.get('priceChange', {}).get('h24', 0) > 0.5
                ):
                    filtered_pairs.append(pair)
            except (TypeError, ValueError):
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
        # هر ۱۵ دقیقه یک‌بار اجرا می‌شود
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
