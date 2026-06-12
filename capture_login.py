"""
Real Myntra Login - Visible Browser + Human Simulation
Uses Real Chrome, captures ALL network requests
Browser will open ON SCREEN so user can see the login happening
"""
import asyncio
import json
import time
import os
import random
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright

PHONE = "9992443292"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

captured_requests = []
captured_responses = []


async def human_delay(min_ms=300, max_ms=800):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


async def human_mouse_move(page, x, y):
    cx = x + random.randint(-5, 5)
    cy = y + random.randint(-5, 5)
    await page.mouse.move(cx, cy, steps=random.randint(5, 15))
    await human_delay(100, 300)


async def main():
    print("=" * 60)
    print("  MYNTRA REAL LOGIN - Visible Browser + Human Mode")
    print("  A Chrome window will open - you can watch it!")
    print("=" * 60)

    pw = await async_playwright().start()

    print("\n[1/7] Launching Chrome (VISIBLE on screen)...")
    browser = await pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
        slow_mo=30,
    )

    ctx = await browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/AP2A.240805.005) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
        ),
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        ignore_https_errors=True,
        permissions=["geolocation"],
        geolocation={"latitude": 28.6139, "longitude": 77.2090},
    )

    # Deep stealth patches
    await ctx.add_init_script("""
        () => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const arr = [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
                    ];
                    arr.length = 3;
                    return arr;
                }
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en', 'hi'] });
            Object.defineProperty(navigator, 'language', { get: () => 'en-IN' });
            window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            const origQuery = window.navigator.permissions?.query;
            if (origQuery) {
                window.navigator.permissions.query = (params) => {
                    if (params.name === 'notifications') return Promise.resolve({ state: 'prompt', onchange: null });
                    return origQuery(params);
                };
            }
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Google Inc. (NVIDIA)';
                if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter.call(this, param);
            };
        }
    """)

    page = await ctx.new_page()

    # Capture network requests (API calls only, silently)
    def on_request(req):
        entry = {
            "url": req.url,
            "method": req.method,
            "headers": dict(req.headers),
            "post_data": req.post_data,
            "ts": time.time(),
        }
        captured_requests.append(entry)
        if any(kw in req.url for kw in ["/gateway/", "/auth/", "/getotp", "/verifyotp"]):
            body_info = ""
            if req.post_data and len(req.post_data) < 500:
                body_info = f" | BODY: {req.post_data[:150]}"
            print(f"  -> {req.method} {req.url.split('?')[0][-80:]}{body_info}")

    async def on_response(resp):
        entry = {
            "url": resp.url,
            "status": resp.status,
            "headers": dict(resp.headers),
            "ts": time.time(),
        }
        if any(kw in resp.url for kw in ["/gateway/", "/auth/", "/getotp", "/verifyotp"]):
            try:
                body = await resp.text()
                entry["body"] = body[:3000]
                print(f"  <- {resp.status} {resp.url.split('?')[0][-80:]}")
                if len(body) < 500:
                    print(f"     BODY: {body[:300]}")
            except:
                pass
        captured_responses.append(entry)

    page.on("request", on_request)
    page.on("response", on_response)

    # Step 2: Homepage
    print(f"\n[2/7] Loading Myntra homepage...")
    try:
        await page.goto("https://www.myntra.com/", wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        print(f"  [OK] Homepage loaded: {title}")
    except Exception as e:
        print(f"  [WARN] Homepage: {str(e)[:100]}")

    # CRITICAL: Wait for Akamai sensor to init + generate human interactions
    print(f"  Waiting 8s for Akamai sensor to initialize...")
    await page.wait_for_timeout(3000)

    print(f"  Generating human-like mouse movements on homepage...")
    for _ in range(6):
        x = random.randint(50, 340)
        y = random.randint(100, 700)
        await human_mouse_move(page, x, y)
        await human_delay(200, 600)

    # Scroll like a human
    await page.evaluate("window.scrollBy(0, 350)")
    await human_delay(800, 1500)
    await page.evaluate("window.scrollBy(0, -200)")
    await human_delay(500, 1000)

    await page.wait_for_timeout(3000)

    # Step 3: Login page
    print(f"\n[3/7] Loading login page...")
    try:
        await page.goto(
            "https://www.myntra.com/login?referer=https%3A%2F%2Fwww.myntra.com%2F",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        print(f"  [OK] Login page loaded")
    except Exception as e:
        print(f"  [WARN] Login: {str(e)[:100]}")

    # More human interactions on login page
    print(f"  Waiting 6s + mouse movements on login page...")
    await page.wait_for_timeout(3000)
    for _ in range(4):
        x = random.randint(50, 340)
        y = random.randint(200, 600)
        await human_mouse_move(page, x, y)
        await human_delay(300, 700)
    await page.wait_for_timeout(3000)

    await page.screenshot(path=os.path.join(DATA_DIR, "capture_01_login.png"))
    print(f"  Screenshot: capture_01_login.png")

    # Step 4: Enter phone
    print(f"\n[4/7] Finding phone input and typing {PHONE}...")
    try:
        inp = page.locator("input.mobileNumberInput").first
        await inp.wait_for(timeout=10000)
        box = await inp.bounding_box()
        if box:
            await human_mouse_move(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
        await inp.click()
        await human_delay(500, 1000)
        for ch in PHONE:
            await page.keyboard.press(ch)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        print(f"  [OK] Phone entered: {PHONE}")
    except Exception as e:
        print(f"  [FAIL] Phone input error: {e}")
        await browser.close()
        await pw.stop()
        return

    await human_delay(500, 1000)

    # Step 5: Terms checkbox
    print(f"\n[5/7] Clicking terms checkbox...")
    try:
        cb = page.locator("input.consentCheckbox").first
        if await cb.is_visible(timeout=3000):
            box = await cb.bounding_box()
            if box:
                await human_mouse_move(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            if not await cb.is_checked():
                await cb.click()
                print(f"  [OK] Checkbox checked")
            else:
                print(f"  [OK] Checkbox already checked")
    except Exception as e:
        print(f"  [WARN] Checkbox: {e}")

    await human_delay(500, 1000)
    await page.screenshot(path=os.path.join(DATA_DIR, "capture_02_filled.png"))

    # Step 6: Click CONTINUE
    print(f"\n[6/7] Clicking CONTINUE button...")
    print(f"  Watching for getotp API call...\n")

    try:
        btn = page.locator("div.submitButton").first
        box = await btn.bounding_box()
        if box:
            await human_mouse_move(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await human_delay(200, 500)
        await btn.click()
        print(f"  [OK] CONTINUE clicked!")
    except Exception as e:
        print(f"  [FAIL] Button error: {e}")

    # Wait for response
    print(f"\n  Waiting 10s for Myntra response...")
    await page.wait_for_timeout(10000)
    await page.screenshot(path=os.path.join(DATA_DIR, "capture_03_after_continue.png"))
    print(f"  Screenshot: capture_03_after_continue.png")
    print(f"  URL: {page.url}")

    content = await page.content()
    is_akamai = "akamai" in content.lower() or "processing your request" in content.lower()
    is_otp_page = "otpinput" in content.lower() or "verify" in content.lower()

    if is_akamai:
        print(f"\n  [!] AKAMAI CHALLENGE - waiting 35s for it to resolve...")
        await page.wait_for_timeout(35000)
        await page.screenshot(path=os.path.join(DATA_DIR, "capture_03b_after_akamai.png"))
        print(f"  URL after wait: {page.url}")
        content = await page.content()
        is_otp_page = "otpinput" in content.lower() or "verify" in content.lower()

    if is_otp_page:
        print(f"\n  [OK] OTP PAGE DETECTED - OTP was sent to {PHONE}!")

    # Cookies
    cookies = await ctx.cookies()
    cookie_dict = {c["name"]: c["value"] for c in cookies}
    print(f"\n  Cookies: {len(cookie_dict)}")

    # Step 7: Wait for OTP input from user
    print(f"\n{'='*60}")
    print(f"  CHECK YOUR PHONE: {PHONE}")
    print(f"  Enter the 4-digit OTP you received from Myntra.")
    print(f"  Type 'skip' to just save data.")
    print(f"  Type 'retry' to try again.")
    print(f"{'='*60}")

    while True:
        user_input = input("\n  > Enter OTP / skip / retry: ").strip()

        if user_input == "skip":
            break
        elif user_input == "retry":
            print(f"  Retrying login flow...")
            await page.goto("https://www.myntra.com/login", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            for _ in range(3):
                await human_mouse_move(page, random.randint(50,340), random.randint(200,600))
            await page.wait_for_timeout(3000)
            inp = page.locator("input.mobileNumberInput").first
            await inp.click()
            await human_delay(500, 1000)
            for ch in PHONE:
                await page.keyboard.press(ch)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            cb = page.locator("input.consentCheckbox").first
            try:
                if not await cb.is_checked():
                    await cb.click()
            except:
                pass
            await human_delay(500, 1000)
            btn = page.locator("div.submitButton").first
            bx = await btn.bounding_box()
            if bx:
                await human_mouse_move(page, bx["x"]+bx["width"]/2, bx["y"]+bx["height"]/2)
            await btn.click()
            await page.wait_for_timeout(10000)
            await page.screenshot(path=os.path.join(DATA_DIR, "capture_retry.png"))
            print(f"  Screenshot: capture_retry.png | URL: {page.url}")
            continue

        elif user_input.isdigit() and len(user_input) == 4:
            otp = user_input
            print(f"\n  Entering OTP: {otp}...")

            entered = False
            for sel in ["input.otpInput", "input[class*='otp']", ".otpContainer input"]:
                try:
                    boxes = page.locator(sel)
                    count = await boxes.count()
                    if count >= 4:
                        for i in range(4):
                            await boxes.nth(i).click()
                            await boxes.nth(i).fill(otp[i])
                            await human_delay(100, 200)
                        entered = True
                        print(f"  [OK] OTP entered in boxes ({sel})")
                        break
                except:
                    continue

            if not entered:
                for sel in ["input[maxlength='4']", "input[type='tel']:not(.mobileNumberInput)"]:
                    try:
                        inp2 = page.locator(sel).first
                        if await inp2.is_visible(timeout=2000):
                            await inp2.fill(otp)
                            entered = True
                            print(f"  [OK] OTP entered ({sel})")
                            break
                    except:
                        continue

            if not entered:
                print(f"  Using in-page API call for verify...")
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch('https://www.myntra.com/gateway/v1/auth/verifyotp', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json', 'x-myntraweb': 'Yes', 'x-requested-with': 'browser' }},
                                body: JSON.stringify({{ phoneNumber: '{PHONE}', otp: '{otp}', consentInfo: {{ language: 'en' }} }})
                            }});
                            return {{ status: r.status, body: await r.text() }};
                        }} catch(e) {{ return {{ error: e.message }}; }}
                    }}
                """)
                print(f"  API result: {json.dumps(result, indent=2)}")
            else:
                try:
                    btn2 = page.locator("div.submitButton, button:has-text('VERIFY')").first
                    bx2 = await btn2.bounding_box()
                    if bx2:
                        await human_mouse_move(page, bx2["x"]+bx2["width"]/2, bx2["y"]+bx2["height"]/2)
                    await btn2.click()
                    print(f"  [OK] VERIFY clicked")
                except Exception as e:
                    print(f"  [WARN] Verify button: {e}")

            await page.wait_for_timeout(5000)
            await page.screenshot(path=os.path.join(DATA_DIR, "capture_04_verified.png"))
            cookies = await ctx.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            print(f"  Cookies after verify: {len(cookie_dict)}")
            break
        else:
            print(f"  Enter a 4-digit OTP, 'skip', or 'retry'")

    # Save all data
    capture = {
        "phone": PHONE,
        "timestamp": time.time(),
        "cookies": cookie_dict,
        "final_url": page.url,
        "api_requests": [r for r in captured_requests
                         if any(kw in r["url"] for kw in ["/gateway/", "/auth/", "/getotp", "/verifyotp"])],
        "api_responses": [r for r in captured_responses
                          if any(kw in r["url"] for kw in ["/gateway/", "/auth/", "/getotp", "/verifyotp"])],
        "all_request_count": len(captured_requests),
    }

    outfile = os.path.join(DATA_DIR, "captured_apis.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(capture, f, indent=2, default=str)
    print(f"\n  Saved to: {outfile}")
    print(f"  Total requests: {len(captured_requests)}")
    print(f"  API requests: {len(capture['api_requests'])}")
    print(f"  Cookies: {len(cookie_dict)}")

    for k in ["at", "ut", "mynt-ulc", "_abck", "ak_bmsc", "bm_sv"]:
        v = cookie_dict.get(k, "-")
        if v != "-" and len(v) > 50:
            v = v[:50] + "..."
        print(f"    {k} = {v}")

    await page.screenshot(path=os.path.join(DATA_DIR, "capture_final.png"))
    await browser.close()
    await pw.stop()

    print(f"\n{'='*60}")
    print(f"  DONE! All data in: {DATA_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
