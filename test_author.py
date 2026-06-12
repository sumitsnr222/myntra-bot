import aiohttp
import asyncio

async def main():
    async with aiohttp.ClientSession() as s:
        h = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14) Chrome/133.0.0.0 Mobile Safari/537.36'}
        async with s.get('https://www.myntra.com/studio/influencer?id=KiEAashbJ4', headers=h) as r:
            html = await r.text()
            with open('author_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'Fetched {len(html)} bytes')

asyncio.run(main())
