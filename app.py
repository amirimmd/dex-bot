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

# Define filter criteria globally to be passed to the frontend
FILTER_CRITERIA = {
    "min_liquidity_usd": 50000,
    "min_fdv": 500000,
    "min_volume_h24": 50000,
    "min_price_change_h6_percent": 0.5, # Corresponds to 0.005
    "min_price_change_h24_percent": 0.5 # Corresponds to 0.005
}


# === Section 3: Main Data Fetching and Filtering Logic ===
def fetch_data_and_update():
    global all_known_pairs, api_error, latest_data
    
    base_url = "https://api.dexscreener.com/latest/dex/search"
    temp_latest_data = []
    
    try:
        # Loop through each chain in our defined order
        for chain in CHAINS_TO_SCAN:
            print(f"--- Starting scan for {chain.upper()} ---")
            # The initial query is broad to get a good pool of candidates
            params = {'q': f'fdv > {FILTER_CRITERIA["min_fdv"]}'}
            
            print(f"Sending initial request for {chain.upper()}...")
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_pairs = data.get('pairs', [])
            
            # Update our master list of pairs for the chain
            for pair in raw_pairs:
                all_known_pairs[chain][pair['pairAddress']] = pair

            validated_pairs = {}
            for pair_address, pair in all_known_pairs[chain].items():
                try:
                    # Apply the detailed filters
                    if (
                        pair.get('chainId') == chain and
                        pair.get('liquidity', {}).get('usd', 0) > FILTER_CRITERIA["min_liquidity_usd"] and
                        pair.get('fdv', 0) > FILTER_CRITERIA["min_fdv"] and
                        pair.get('volume', {}).get('h24', 0) > FILTER_CRITERIA["min_volume_h24"] and
                        pair.get('priceChange', {}).get('h6', 0) > (FILTER_CRITERIA["min_price_change_h6_percent"] / 100) and
                        pair.get('priceChange', {}).get('h24', 0) > (FILTER_CRITERIA["min_price_change_h24_percent"] / 100)
                    ):
                        validated_pairs[pair_address] = pair
                except (TypeError, ValueError):
                    # Skip pair if data is malformed
                    continue
            
            # Clean up the list for the chain, keeping only currently valid pairs
            all_known_pairs[chain] = validated_pairs
            
            # NEW: Add chain data along with the count of found pairs
            temp_latest_data.append({
                "chain": chain,
                "pairs": list(validated_pairs.values()),
                "count": len(validated_pairs)  # Add the count here
            })
            print(f"Scan for {chain.upper()} complete. Final valid pairs: {len(validated_pairs)}")

        # Atomically update the global variable with the fresh data
        latest_data = temp_latest_data
        api_error = None
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] All chains updated successfully.")
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error during data fetch: {e}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_message}")
        api_error = error_message

def background_task():
    """Runs the data fetching process in a loop."""
    while True:
        fetch_data_and_update()
        # Sleep for 5 minutes (300 seconds) before the next run
        time.sleep(300)

# === Section 4: Flask Web Server Setup ===
app = Flask(__name__)

@app.route('/')
def home():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API endpoint to provide the fetched data to the frontend."""
    return jsonify({
        'data': latest_data,
        'filters': FILTER_CRITERIA, # Send filters to frontend
        'error': api_error
    })

def run_web_server():
    """Starts the Flask web server."""
    # Use the PORT environment variable provided by the platform, or default to 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# === Section 5: Application Entry Point ===
if __name__ == "__main__":
    print("Starting background data fetching task...")
    task_thread = Thread(target=background_task)
    task_thread.daemon = True
    task_thread.start()
    
    print("Starting web server...")
    run_web_server()
