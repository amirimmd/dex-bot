# برای اجرای این کد، ابتدا باید Playwright و نسخه سازگار Stealth را نصب کنید:
# pip install --upgrade playwright
# pip install playwright-stealth==1.0.6
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

# --- بخش وب سرور ---
PORT = 8000

def run_server():
    """یک وب سرور ساده برای ارائه فایل‌های محلی (index.html, data.json) اجرا می‌کند."""
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"سرور محلی در آدرس http://localhost:{PORT} در حال اجراست")
        httpd.serve_forever()

# --- بخش استخراج داده ---
def is_number_with_comma(s):
    """بررسی می‌کند که آیا رشته یک عدد (احتمالا با کاما) است یا خیر."""
    return bool(re.match(r'^[0-9,]+$', s))

async def scrape_single_page(url: str):
    """
    داده‌ها را از یک صفحه استخراج می‌کند و در صورت نیاز به کاربر اجازه حل کپچا می‌دهد.
    """
    scraped_data = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await stealth_async(page)
        
        try:
            print(f"در حال پردازش آدرس: {url}...")
            await page.goto(url, wait_until="networkidle", timeout=90000)

            captcha_locator = page.locator("text=/Cloudflare|Verifying you are human/i")
            first_row_selector = "a[href^='/solana/']"

            if await captcha_locator.count() > 0:
                print("\n!!! کپچا شناسایی شد. لطفاً آن را به صورت دستی در پنجره مرورگر حل کنید...")
                await page.wait_for_selector(first_row_selector, timeout=120000)
                print("کپچا با موفقیت حل شد. ادامه می‌دهیم...")
            else:
                await page.wait_for_selector(first_row_selector, timeout=30000)
            
            rows = await page.query_selector_all(first_row_selector)
            if not rows:
                 print("هیچ ردیفی در صفحه پیدا نشد.")
                 return []

            print(f"تعداد {len(rows)} ردیف پیدا شد. در حال تجزیه اطلاعات...")
            
            for row_element in rows:
                texts = await row_element.inner_text()
                lines = [line.strip() for line in texts.split('\n') if line.strip()]
                if len(lines) < 8: continue
                
                data = {
                    'rank': lines[0] if lines[0].startswith('#') else 'N/A', 'symbol': lines[1], 'name': 'N/A', 'price': 'N/A',
                    'volume': 'N/A', 'change_6h': 'N/A', 'change_24h': 'N/A', 'liquidity': 'N/A',
                    'market_cap': 'N/A', 'href': "https://dexscreener.com" + await row_element.get_attribute('href')
                }
                
                dollar_values = [l for l in lines if l.startswith('$')]
                if dollar_values:
                    data['price'] = dollar_values[0]
                    if len(dollar_values) > 1: data['volume'] = dollar_values[1]
                    if len(dollar_values) > 2: data['liquidity'] = dollar_values[-2]
                    if len(dollar_values) > 3: data['market_cap'] = dollar_values[-1]

                percentages = [l for l in lines if l.endswith('%')]
                if len(percentages) >= 2:
                    data['change_6h'] = percentages[-2]
                    data['change_24h'] = percentages[-1]
                elif len(percentages) == 1:
                    data['change_24h'] = percentages[0]


                scraped_data.append(data)
        except Exception as e:
            print(f"یک خطای جدی در حین استخراج رخ داد: {e}")
        finally:
            await browser.close()
            return scraped_data

async def main_scraper_loop():
    """حلقه اصلی که به صورت دوره‌ای داده‌ها را استخراج و ذخیره می‌کند."""
    DEXSCREENER_URL = "https://dexscreener.com/?rankBy=trendingScoreH6&order=desc&chainIds=solana&minLiq=50000&maxLiq=1000000&minMarketCap=65000&maxMarketCap=10000000&min24HVol=70000&max24HVol=15000000&min24HChg=0.01&max24HChg=10000&min6HChg=0.01&max6HChg=10000"
    
    while True:
        print("\n" + "="*50)
        print(f"شروع دور جدید استخراج در ساعت: {datetime.now().strftime('%H:%M:%S')}")
        results = await scrape_single_page(DEXSCREENER_URL)
        
        if results:
            output = {
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "token_count": len(results),
                "tokens": results
            }
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=4)
            print(f"{len(results)} توکن با موفقیت در data.json ذخیره شد.")
        else:
            print("هیچ داده‌ای برای ذخیره وجود نداشت.")
        
        print(f"استخراج این دور به پایان رسید. انتظار به مدت ۱۰ دقیقه تا دور بعدی...")
        print("="*50)
        time.sleep(600) # انتظار به مدت ۱۰ دقیقه (۶۰۰ ثانیه)

if __name__ == "__main__":
    # اجرای وب سرور در یک ترد (Thread) جداگانه
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # باز کردن داشبورد در مرورگر پس از یک تاخیر کوتاه
    webbrowser.open_new_tab(f'http://localhost:{PORT}')
    
    # شروع حلقه اصلی استخراج داده
    asyncio.run(main_scraper_loop())

