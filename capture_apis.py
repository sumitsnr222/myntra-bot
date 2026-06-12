"""
API Capture Script - Opens Chrome in mobile mode with network logging.
User will login, follow someone, and tap a product.
All API calls will be captured and saved.
"""
import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

DATA = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA, exist_ok=True)

captured_apis = []

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        slow_mo=30,
    )
    
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        is_mobile=False,
    )
    
    async def on_request(request):
        url = request.url
        if "myntra.com/gateway" in url or "mynsta" in url:
            entry = {
                "timestamp": time.strftime("%H:%M:%S"),
                "method": request.method,
                "url": url,
                "headers": dict(request.headers),
            }
            try:
                body = request.post_data
                if body:
                    try:
                        entry["body"] = json.loads(body)
                    except:
                        entry["body"] = body
            except:
                pass
            captured_apis.append(entry)
            print(f"\n{'='*60}")
            print(f"[{entry['timestamp']}] {request.method} {url}")
            if entry.get("body"):
                print(f"BODY: {json.dumps(entry['body'], indent=2)[:500]}")
    
    async def on_response(response):
        url = response.url
        if "myntra.com/gateway" in url or "mynsta" in url:
            status = response.status
            ct = response.headers.get("content-type", "")
            print(f"  -> {status} {ct[:40]}")
            if status == 200 and "json" in ct:
                try:
                    data = await response.json()
                    # Find the matching request entry and add response
                    for entry in reversed(captured_apis):
                        if entry["url"] == url and "response" not in entry:
                            entry["response_status"] = status
                            entry["response"] = data
                            break
                except:
                    pass
    
    ctx.on("request", on_request)
    ctx.on("response", on_response)
    
    page = await ctx.new_page()
    
    # Navigate to Myntra login
    print("\n" + "="*60)
    print("OPENING MYNTRA LOGIN PAGE...")
    print("Please login with 9992443292 and enter OTP.")
    print("Then navigate to the influencer profile and do:")
    print("  1. Follow the author")
    print("  2. Tap on a product link under a post")
    print("="*60 + "\n")
    
    await page.goto("https://www.myntra.com/login", wait_until="domcontentloaded")
    
    # Keep running until user presses Ctrl+C
    try:
        while True:
            await asyncio.sleep(5)
            # Auto-save captured APIs every 5 seconds
            if captured_apis:
                with open(os.path.join(DATA, "captured_apis_live.json"), "w") as f:
                    json.dump(captured_apis, f, indent=2)
    except KeyboardInterrupt:
        pass
    finally:
        # Save final capture
        out_file = os.path.join(DATA, "captured_apis_live.json")
        with open(out_file, "w") as f:
            json.dump(captured_apis, f, indent=2)
        print(f"\n\nSaved {len(captured_apis)} API calls to {out_file}")
        await browser.close()
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
