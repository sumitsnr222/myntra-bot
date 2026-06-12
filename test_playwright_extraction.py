import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    try:
        with open('data/accounts.json') as f: data = json.load(f)
        if not data:
            print("No accounts in db")
            return
            
        acc = list(data.values())[0]
        cookies = acc['cookies']
        pw_cookies = [{'name': k, 'value': v, 'domain': '.myntra.com', 'path': '/'} for k,v in cookies.items()]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent='Mozilla/5.0 (Linux; Android 14) Chrome/133.0.0.0 Mobile Safari/537.36')
            await context.add_cookies(pw_cookies)
            page = await context.new_page()
            
            # Navigate directly to the provided URL
            url = 'https://www.myntra.com/studio/influencer?id=KiEAashbJ4&affiliateId=KiEAashbJ4'
            print('Going to URL:', url)
            
            # Using wait_until='domcontentloaded' because 'networkidle' might timeout on Myntra
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            # Wait a few seconds for Myntra React app to hydrate and render posts
            await page.wait_for_timeout(3000)
            print('Page loaded.')
            
            html = await page.content()
            print('HTML len:', len(html))
            
            # Extract links
            js = "Array.from(document.querySelectorAll('a[href*=\"/studio/studiopost/\"]')).map(a => a.href)"
            posts = await page.evaluate(js)
            print('Found posts via DOM:', len(posts))
            
            # Extract from __myx window variable
            myx = await page.evaluate("window.__myx || {}")
            print("myx keys:", list(myx.keys()))
            
            await browser.close()
    except Exception as e:
        print('Error:', e)

if __name__ == "__main__":
    asyncio.run(main())
