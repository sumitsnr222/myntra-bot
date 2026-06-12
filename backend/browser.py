"""
Myntra Suite v4 -- Browser Module (Login Only)
Uses real Chrome with human simulation to bypass Akamai during login.
After login, the browser captures cookies and the MyntraClient takes over.
"""
import asyncio
import logging
import os
import random
import time

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .config import generate_device, build_headers

log = logging.getLogger(__name__)

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA, exist_ok=True)

_pw = None
_browser: Browser = None


async def _ensure_browser():
    global _pw, _browser
    if _browser and _browser.is_connected():
        return
    log.info("[Browser] Launching Chrome (visible)...")
    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--window-position=-3000,-3000",
        ],
        slow_mo=30,
    )
    log.info("[Browser] Chrome ready")


async def _human_delay(min_ms=200, max_ms=600):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


async def _human_mouse_move(page: Page, x, y):
    cx = x + random.randint(-5, 5)
    cy = y + random.randint(-5, 5)
    await page.mouse.move(cx, cy, steps=random.randint(5, 15))
    await _human_delay(100, 250)


async def send_otp(phone: str, device: dict, proxy: str = None) -> tuple:
    """
    Open Myntra login in real Chrome, enter phone, click CONTINUE.
    Returns: (success, message, cookies_dict)
    """
    await _ensure_browser()

    ctx_args = {
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": device["user_agent"],
        "locale": "en-IN",
        "timezone_id": "Asia/Kolkata",
        "ignore_https_errors": True,
        "permissions": ["geolocation"],
        "geolocation": {"latitude": 28.6139, "longitude": 77.2090},
    }
    if proxy:
        ctx_args["proxy"] = {"server": proxy}

    ctx = await _browser.new_context(**ctx_args)
    await ctx.add_init_script("""
        () => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en', 'hi'] });
            window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            const gp = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Google Inc. (NVIDIA)';
                if (p === 37446) return 'ANGLE (NVIDIA GeForce RTX 3060)';
                return gp.call(this, p);
            };
        }
    """)

    page = await ctx.new_page()

    try:
        # Step 1: Homepage with human interactions
        log.info(f"[OTP] {phone} Step 1: Homepage")
        await page.goto("https://www.myntra.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Human mouse movements
        for _ in range(5):
            await _human_mouse_move(page, random.randint(50, 340), random.randint(100, 700))
            await _human_delay(200, 500)
        await page.evaluate("window.scrollBy(0, 300)")
        await _human_delay(600, 1200)
        await page.evaluate("window.scrollBy(0, -200)")
        await page.wait_for_timeout(3000)

        # Step 2: Login page
        log.info(f"[OTP] {phone} Step 2: Login page")
        await page.goto("https://www.myntra.com/login?referer=https%3A%2F%2Fwww.myntra.com%2F",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        for _ in range(3):
            await _human_mouse_move(page, random.randint(50, 340), random.randint(200, 600))
        await page.wait_for_timeout(3000)

        # Step 3: Enter phone
        log.info(f"[OTP] {phone} Step 3: Entering phone")
        inp = page.locator("input.mobileNumberInput").first
        await inp.wait_for(timeout=10000)
        box = await inp.bounding_box()
        if box:
            await _human_mouse_move(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        await inp.click()
        await _human_delay(400, 800)
        for ch in phone:
            await page.keyboard.press(ch)
            await asyncio.sleep(random.uniform(0.08, 0.25))

        # Step 4: Checkbox
        log.info(f"[OTP] {phone} Step 4: Checkbox")
        cb = page.locator("input.consentCheckbox").first
        try:
            if await cb.is_visible(timeout=3000) and not await cb.is_checked():
                bx = await cb.bounding_box()
                if bx:
                    await _human_mouse_move(page, bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
                await cb.click()
        except:
            pass
        await _human_delay(400, 800)

        # Step 5: CONTINUE
        log.info(f"[OTP] {phone} Step 5: CONTINUE")
        
        async def _click_continue():
            """Try to find and click the continue/submit button."""
            for selector in [".submitBottomOption", "div.submitButton", "button.submitBottomOption", 
                           "[class*='submit']", "button:has-text('CONTINUE')", "div:has-text('CONTINUE')>>nth=0"]:
                try:
                    el = page.locator(selector).first
                    if await el.is_visible(timeout=2000):
                        bx = await el.bounding_box()
                        if bx:
                            await _human_mouse_move(page, bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
                            await _human_delay(200, 400)
                        await el.click()
                        log.info(f"[OTP] {phone} Clicked continue via {selector}")
                        return True
                except:
                    continue
            return False
        
        await _click_continue()
        
        # Wait for Akamai challenge + OTP API
        log.info(f"[OTP] {phone} Step 6: Waiting for response...")
        await page.wait_for_timeout(10000)

        content = await page.content()
        if "akamai" in content.lower() or "processing your request" in content.lower():
            log.info(f"[OTP] {phone} Akamai challenge detected - waiting 35s...")
            await page.wait_for_timeout(35000)
            
            # After Akamai clears, the CONTINUE button re-appears — click it again
            log.info(f"[OTP] {phone} Step 6b: Retrying CONTINUE after Akamai...")
            for _ in range(3):
                await _human_delay(1000, 2000)
                clicked = await _click_continue()
                if clicked:
                    await page.wait_for_timeout(8000)
                    break

        # Save screenshot
        ts = int(time.time())
        await page.screenshot(path=os.path.join(DATA, f"otp_{phone}_{ts}.png"))

        # Get cookies
        cookies = await ctx.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        log.info(f"[OTP] {phone} Done - {len(cookie_dict)} cookies, URL: {page.url}")

        # Store the page reference so verify_otp can use it
        return True, "OTP sent", cookie_dict, ctx, page

    except Exception as e:
        log.error(f"[OTP] {phone} Error: {e}")
        await ctx.close()
        return False, str(e), {}, None, None


async def verify_otp(phone: str, otp: str, ctx: BrowserContext, page: Page) -> tuple:
    """
    Enter OTP on the open Myntra page.
    Returns: (success, message, cookies_dict)
    """
    try:
        entered = False

        # Method 1: OTP input boxes
        for sel in ["input.otpInput", "input[class*='otp']", ".otpContainer input"]:
            try:
                boxes = page.locator(sel)
                count = await boxes.count()
                if count >= 4:
                    for i in range(min(4, len(otp))):
                        await boxes.nth(i).click()
                        await boxes.nth(i).fill(otp[i])
                        await _human_delay(80, 180)
                    entered = True
                    log.info(f"[VERIFY] {phone} OTP entered via {sel}")
                    break
            except:
                continue

        # Method 2: Single input
        if not entered:
            for sel in ["input[maxlength='4']", "input[type='tel']:not(.mobileNumberInput)"]:
                try:
                    inp = page.locator(sel).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(otp)
                        entered = True
                        break
                except:
                    continue

        # Method 3: In-page API call
        if not entered:
            log.info(f"[VERIFY] {phone} Using in-page API call")
            result = await page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('https://www.myntra.com/gateway/v1/auth/verifyotp', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json', 'x-myntraweb': 'Yes' }},
                            body: JSON.stringify({{ phoneNumber: '{phone}', otp: '{otp}', consentInfo: {{ language: 'en' }} }})
                        }});
                        return {{ status: r.status, body: await r.text() }};
                    }} catch(e) {{ return {{ error: e.message }}; }}
                }}
            """)
            log.info(f"[VERIFY] {phone} API result: {result}")
        else:
            # Click verify/submit
            try:
                btn = page.locator("div.submitButton, button:has-text('VERIFY')").first
                await btn.click()
            except:
                pass

        await page.wait_for_timeout(5000)

        # Capture final cookies
        cookies = await ctx.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        at = cookie_dict.get("at", "")
        success = bool(at)
        msg = "Login successful" if success else "Verify failed - no auth token"

        log.info(f"[VERIFY] {phone} {'OK' if success else 'FAIL'} - {len(cookie_dict)} cookies")

        # Close context
        await ctx.close()
        return success, msg, cookie_dict

    except Exception as e:
        log.error(f"[VERIFY] {phone} Error: {e}")
        try:
            await ctx.close()
        except:
            pass
        return False, str(e), {}


async def extract_influencer_posts(url: str, cookies: dict) -> list[dict]:
    """
    Open the influencer URL in the EXISTING real Chrome browser (same one used for login,
    which already passed Akamai). Intercept network responses to capture post data.
    Returns list of {post_id, author_id, product_ids}.
    """
    import re as _re

    await _ensure_browser()

    posts_found = {}  # post_id -> {author_id, product_ids}
    author_id_found = ""

    def _extract_posts_from_json(obj, depth=0):
        nonlocal author_id_found
        if depth > 15 or obj is None:
            return
        if isinstance(obj, dict):
            pid = obj.get("id") or obj.get("postId")
            
            # Extract author uidx if available anywhere in the object (usually under "author")
            author = obj.get("author", {})
            if isinstance(author, dict):
                uidx = author.get("uidx") or author.get("id") or ""
                if uidx and isinstance(uidx, str) and len(uidx) > 10:  # uidx is usually long
                    author_id_found = uidx
            
            # If it's a valid post object
            if pid and str(pid).isdigit() and ("author" in obj or "styles" in obj or "products" in obj or "media" in obj):
                pid = str(pid)
                
                # Extract products (can be under 'styles' as list of dicts, or 'products' as list of ints)
                styles = obj.get("styles") or obj.get("products") or []
                style_ids = []
                if isinstance(styles, list):
                    for s in styles:
                        sid = s.get("id") if isinstance(s, dict) else s
                        if sid and str(sid).isdigit():
                            style_ids.append(str(sid))
                
                # Update post entry. If author_id_found is already known, use it.
                if pid not in posts_found:
                    posts_found[pid] = {"post_id": pid, "author_id": author_id_found, "product_ids": style_ids}
                else:
                    # Merge product IDs if already exists
                    existing = set(posts_found[pid]["product_ids"])
                    existing.update(style_ids)
                    posts_found[pid]["product_ids"] = list(existing)
                    if author_id_found and not posts_found[pid]["author_id"]:
                        posts_found[pid]["author_id"] = author_id_found
            
            for v in obj.values():
                _extract_posts_from_json(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _extract_posts_from_json(item, depth + 1)

    async def _on_response(response):
        try:
            resp_url = response.url
            if response.status == 200 and ("/mynsta/" in resp_url or "/layout/" in resp_url or "/feed/" in resp_url):
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    data = await response.json()
                    _extract_posts_from_json(data)
        except Exception:
            pass

    ctx = None
    try:
        # Build Playwright cookies
        pw_cookies = []
        for name, value in cookies.items():
            pw_cookies.append({
                "name": name,
                "value": value,
                "domain": ".myntra.com",
                "path": "/",
            })

        # Create a new context in the EXISTING real Chrome browser
        ctx_args = {
            "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/AP2A.240805.005) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
            "viewport": {"width": 412, "height": 915},
            "is_mobile": True,
        }
        if proxy:
            ctx_args["proxy"] = {"server": proxy}

        ctx = await _browser.new_context(**ctx_args)
        await ctx.add_cookies(pw_cookies)

        page = await ctx.new_page()
        page.on("response", _on_response)

        log.info(f"[Extract] Navigating to {url} in real Chrome...")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)

        # Scroll to load more posts
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(1500)

        # DOM fallback: extract post links
        try:
            dom_links = await page.evaluate(
                """Array.from(document.querySelectorAll('a[href*="/studiopost/"]')).map(a => a.href)"""
            )
            for link in dom_links:
                m = _re.search(r'/studiopost/(\d+)', link)
                if m:
                    pid = m.group(1)
                    if pid not in posts_found:
                        posts_found[pid] = {"post_id": pid, "author_id": author_id_found, "product_ids": []}
        except Exception:
            pass

        # Also try to get post IDs from data attributes or scripts
        try:
            extra_ids = await page.evaluate("""
                (() => {
                    const ids = new Set();
                    // Look for post IDs in any data attribute
                    document.querySelectorAll('[data-postid], [data-post-id]').forEach(el => {
                        const id = el.getAttribute('data-postid') || el.getAttribute('data-post-id');
                        if (id) ids.add(id);
                    });
                    // Look in any img/video with studio URLs
                    document.querySelectorAll('img[src*="studio"], video[src*="studio"]').forEach(el => {
                        const m = el.src.match(/\\/studio\\/(\\d+)/);
                        if (m) ids.add(m[1]);
                    });
                    return Array.from(ids);
                })()
            """)
            for pid in extra_ids:
                if pid not in posts_found:
                    posts_found[pid] = {"post_id": pid, "author_id": author_id_found, "product_ids": []}
        except Exception:
            pass

        await ctx.close()

        # Backfill any posts that missed the author_id (e.g. parsed out of order)
        for p in posts_found.values():
            if not p["author_id"] and author_id_found:
                p["author_id"] = author_id_found

        result = list(posts_found.values())
        log.info(f"[Extract] Extracted {len(result)} posts from influencer page.")
        return result

    except Exception as e:
        log.error(f"[Extract] Influencer extraction error: {e}")
        if ctx:
            try:
                await ctx.close()
            except:
                pass
        return []


async def shutdown():
    global _browser, _pw
    if _browser:
        try:
            await _browser.close()
        except:
            pass
    if _pw:
        try:
            await _pw.stop()
        except:
            pass
