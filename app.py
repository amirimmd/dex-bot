# === Section 1: Required Libraries ===
from flask import Flask, jsonify, render_template
from threading import Thread
import requests
import time
import os

# === Section 2: Global Variables & Configuration ===
CHAINS_TO_SCAN = ['solana', 'ethereum', 'bsc', 'base']
all_known_pairs = {chain: {} for chain in CHAINS_TO_SCAN}
# latest_data is now a list to preserve order
latest_data = [] 
api_error = None 

# === Section 3: Main Data Fetching and Filtering Logic ===
def fetch_data_and_update():
    global all_known_pairs, api_error, latest_data
    
    base_url = "https://api.dexscreener.com/latest/dex/search"
    temp_latest_data = []
    
    try:
        # Loop through each chain in our defined order
        for chain in CHAINS_TO_SCAN:
            print(f"--- Starting scan for {chain.upper()} ---")
            params = {'q': f'{chain} fdv > 500000'}
            
            print(f"Sending initial request for {chain.upper()}...")
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_pairs = data.get('pairs', [])
            
            for pair in raw_pairs:
                all_known_pairs[chain][pair['pairAddress']] = pair

            validated_pairs = {}
            for pair_address, pair in all_known_pairs[chain].items():
                try:
                    if (
                        pair.get('chainId') == chain and
                        pair.get('liquidity', {}).get('usd', 0) > 50000 and
                        pair.get('fdv', 0) > 500000 and
                        pair.get('volume', {}).get('h24', 0) > 50000 and
                        pair.get('priceChange', {}).get('h6', 0) > 0.005 and
                        pair.get('priceChange', {}).get('h24', 0) > 0.005
                    ):
                        validated_pairs[pair_address] = pair
                except (TypeError, ValueError):
                    continue
            
            all_known_pairs[chain] = validated_pairs
            # *** تغییر اصلی: ساخت یک لیست از آبجکت‌ها برای حفظ ترتیب ***
            temp_latest_data.append({
                "chain": chain,
                "pairs": list(validated_pairs.values())
            })
            print(f"Scan for {chain.upper()} complete. Final valid pairs: {len(validated_pairs)}")

        # Update the global variable at the end
        latest_data = temp_latest_data
        api_error = None
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] All chains updated successfully.")
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error during data fetch: {e}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}")
        api_error = error_message

# بقیه کد بدون تغییر است
def background_task():
    while True:
        fetch_data_and_update()
        time.sleep(300)

app = Flask(__name__)
@app.route('/')
def home(): return render_template('index.html')
@app.route('/api/data')
def get_data(): return jsonify({'data': latest_data, 'error': api_error})
def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Starting background data fetching task...")
    task_thread = Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()
    run_web_server()
