# To run this code, first install the required libraries:
# pip install --upgrade playwright playwright-stealth==1.0.6 requests
# playwright install

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import re
import json
from datetime import datetime
import webbrowser
import os
import time
import http.server
import socketserver
import threading
import requests
import hmac
import hashlib
import sys

# --- Configuration ---
PORT = 8000
HISTORY_FILE = "history.json"
DATA_FILE = "data.json"
# --- GoPlus API Credentials ---
# !!! IMPORTANT !!!
# Replace these keys if you get new ones from GoPlus support.
APP_KEY = "2gaQefjBCWdYWQhbtkX3"
APP_SECRET = "VhjkIxWZWsH3exvHPRUW6XFupcMzXDb"

# --- Access Token Manager ---
goplus_access_token = None
token_expiry_time = 0

def get_world_time():
    """
    Fetches the official UTC Unix timestamp from an independent world time server.
    Bypasses SSL verification for this specific request to work around local time issues.
    """
    try:
        # --- CRITICAL FIX: Added verify=False to bypass SSL errors caused by incorrect local time ---
        response = requests.get("http://worldtimeapi.org/api/timezone/Etc/UTC", timeout=10, verify=False)
        response.raise_for_status()
        return str(response.json()['unixtime'])
    except Exception as e:
        print(f"Warning: Could not fetch world time, falling back to local time. Error: {e}")
        return str(int(time.time()))

def get_access_token():
    """
    Generates a new access token using the official world time.
    """
    global goplus_access_token, token_expiry_time
    
    if goplus_access_token and time.time() < token_expiry_time - 300:
        return goplus_access_token

    try:
        print("Generating new GoPlus API access token using world time...")
        timestamp = get_world_time()
        
        message = APP_KEY + timestamp
        signature = hmac.new(APP_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-App-Key": APP_KEY,
            "X-Timestamp": timestamp,
            "X-Signature": signature
        }
        
        url = "https://api.gopluslabs.io/api/v1/token"
        # --- FINAL FIX: Added verify=False to the main API call ---
        response = requests.post(url, headers=headers, json={}, timeout=15, verify=False)
        
        if response.status_code != 200:
            print(f"Error from GoPlus API (Status Code: {response.status_code}): {response.text}")
            return None
            
        data = response.json()
        if data.get('code') == 1:
            goplus_access_token = data['result']['access_token']
            token_expiry_time = time.time() + data['result']['expires_in']
            print("Access token generated successfully.")
            return goplus_access_token
        else:
            print(f"Error getting access token: {data.get('message')} (API Code: {data.get('code')})")
            return None
    except requests.RequestException as e:
        print(f"Failed to get access token due to a network or request error: {e}")
        return None

def get_token_address_from_pair(pair_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_address}"
        # --- FINAL FIX: Added verify=False ---
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        pair_data = response.json().get('pair')
        if pair_data and 'baseToken' in pair_data:
            return pair_data['baseToken']['address']
    except requests.RequestException: pass
    return None

def get_batch_security_info(token_addresses):
    if not token_addresses: return {}
    access_token = get_access_token()
    if not access_token:
        print("Cannot get security info without a valid access token.")
        return {}
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://api.gopluslabs.io/api/v1/token_security/solana?contract_addresses={','.join(token_addresses)}"
        
        # --- FINAL FIX: Added verify=False ---
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        api_result = response.json().get('result', {})
        processed_results = {}
        for address, result in api_result.items():
            if not result: continue
            lp_burned_percentage = 0
            solana_burn_address = "11111111111111111111111111111111"
            if 'lp_holders' in result and result.get('lp_holders'):
                for holder in result['lp_holders']:
                    if holder.get('address') == solana_burn_address and holder.get('is_locked') == 0:
                         lp_burned_percentage += float(holder.get('percent', 0))
            
            top_10_holders_sum = 0
            if 'holders' in result and result.get('holders'):
                for holder in result['holders'][:10]:
                    top_10_holders_sum += float(holder.get('percent', 0))

            processed_results[address.lower()] = {
                'mint_revoked': result.get('is_mintable') == '0',
                'freeze_authority_revoked': result.get('is_honeypot') == '0',
                'lp_burned': lp_burned_percentage > 0.95,
                'top_10_percent': top_10_holders_sum * 100,
            }
        return processed_results
    except requests.RequestException as e:
        print(f"Error during batch security fetch: {e}")
        return {}

async def scrape_single_page(url: str):
    scraped_data = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36')
        page = await context.new_page()
        await stealth_async(page)
        try:
            print(f"Processing URL: {url}...")
            await page.goto(url, wait_until="networkidle", timeout=90000)
            captcha_locator = page.locator("text=/Cloudflare|Verifying you are human/i")
            first_row_selector = "a[href^='/solana/']"
            if await captcha_locator.count() > 0:
                print("\n!!! CAPTCHA detected. Please solve it manually in the browser window...")
                await page.wait_for_selector(first_row_selector, timeout=120000)
                print("CAPTCHA solved. Continuing...")
            else:
                await page.wait_for_selector(first_row_selector, timeout=30000)
            rows = await page.query_selector_all(first_row_selector)
            if not rows: return []
            
            pair_addresses = []
            row_data_map = {}
            for row_element in rows:
                href = await row_element.get_attribute('href')
                pair_address = href.split('/')[-1]
                pair_addresses.append(pair_address)
                row_data_map[pair_address] = { "element": row_element, "href": f"https://dexscreener.com{href}" }
            
            token_address_futures = [asyncio.to_thread(get_token_address_from_pair, pa) for pa in pair_addresses]
            token_addresses = await asyncio.gather(*token_address_futures)
            valid_token_addresses = list(set([addr for addr in token_addresses if addr]))
            
            print(f"Found {len(valid_token_addresses)} unique tokens. Performing batch security check...")
            security_info_batch = get_batch_security_info(valid_token_addresses)
            print("Batch security check complete. Parsing...")

            for i, (pair_address, token_address) in enumerate(zip(pair_addresses, token_addresses)):
                row_info = row_data_map[pair_address]
                security_info = security_info_batch.get(token_address.lower(), {}) if token_address else {}
                texts = await row_info['element'].inner_text()
                lines = [line.strip() for line in texts.split('\n') if line.strip()]
                if len(lines) < 8: continue
                
                data = { 'rank': lines[0], 'symbol': lines[1], 'name': 'N/A', 'price': 'N/A', 'volume': 'N/A', 'change_24h': 'N/A', 'liquidity': 'N/A', 'market_cap': 'N/A', 'href': row_info['href'], **security_info }
                
                try:
                    separator_index, price_index = -1, -1
                    for j, line in enumerate(lines):
                        if '/' in line and separator_index == -1: separator_index = j
                        if line.startswith('$') and price_index == -1: price_index = j
                    if separator_index != -1 and price_index != -1 and price_index > separator_index:
                        name_parts = lines[separator_index + 2 : price_index]
                        data['name'] = ' '.join([p for p in name_parts if not p.isdigit() and p.lower() != 'sol']).strip() or data['symbol']
                except Exception: data['name'] = data['symbol']
                dollar_values = [l for l in lines if l.startswith('$')]
                if dollar_values: data['price'], data['volume'], data['liquidity'], data['market_cap'] = (dollar_values + ['N/A']*4)[:4]
                percentages = [l for l in lines if l.endswith('%')]
                if percentages: data['change_24h'] = percentages[-1]
                
                scraped_data.append(data)
        except Exception as e:
            print(f"A critical error occurred: {e}")
        finally:
            await browser.close()
            return scraped_data

async def main_scraper_loop():
    DEXSCREENER_URL = "https://dexscreener.com/?rankBy=trendingScoreH6&order=desc&chainIds=solana&minLiq=50000&maxLiq=1000000&minMarketCap=65000&maxMarketCap=10000000&min24HVol=70000&max24HVol=15000000&min24HChg=0.01&max24HChg=10000&min6HChg=0.01&max6HChg=10000"
    token_history = json.load(open(HISTORY_FILE, "r", encoding="utf-8")) if os.path.exists(HISTORY_FILE) else {}
    update_cycle_count = 0
    while True:
        print(f"\n{'='*50}\nStarting scrape cycle #{update_cycle_count + 1} at: {datetime.now().strftime('%H:%M:%S')}")
        results = await scrape_single_page(DEXSCREENER_URL)
        if results:
            update_cycle_count += 1
            for token in results:
                symbol = token.get('symbol')
                if symbol:
                    token_history[symbol] = token_history.get(symbol, 0) + 1
                    token['count'] = token_history[symbol]
            output = { "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "token_count": len(results), "update_cycle": update_cycle_count, "tokens": results }
            with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(output, f, ensure_ascii=False, indent=4)
            print(f"Success: {len(results)} tokens saved to {DATA_FILE}.")
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(token_history, f, ensure_ascii=False, indent=4)
            print(f"History updated.")
        else: print("No data was scraped in this cycle.")
        print(f"Cycle finished. Waiting 10 minutes...\n{'='*50}")
        time.sleep(600)

def run_server():
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Local server running at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Suppress InsecureRequestWarning
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1)
    webbrowser.open_new_tab(f'http://localhost:{PORT}')
    if not get_access_token():
        print("\nCould not get initial access token. Please check your API keys and network connection.")
        print("The most likely cause is a major time difference between your PC and the API server.")
        print("Exiting.")
        sys.exit()
    else:
        asyncio.run(main_scraper_loop())

