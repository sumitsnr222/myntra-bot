import asyncio
from backend.api import accounts, load_accounts
from backend.myntra_client import MyntraClient

async def main():
    await load_accounts()
    if not accounts:
        print("No accounts available")
        return
    client = list(accounts.values())[0]
    session = await client._get_session()
    headers = client._headers({"source": "mweb"})
    
    # Try different endpoints to get an author's posts
    author_id = "KiEAashbJ4"
    
    # 1. Try search/feed by author ID
    feed_url = "https://www.myntra.com/gateway/v1/layout/mynsta/feed"
    body = {
        "pageNumber": 1,
        "idsPerPage": 100,
        "feedType": "AUTHOR",
        "authorId": author_id
    }
    async with session.post(feed_url, headers=headers, json=body) as r:
        print(f"POST {feed_url}: {r.status}")
        data = await r.json()
        if r.status == 200:
            posts = data.get("response", {}).get("screen", {}).get("list", [])
            print(f"Feed posts: {len(posts)}")
            if posts:
                print(f"First post ID: {posts[0].get('post', {}).get('id')}")

    # 2. Try influencer profile endpoint
    url2 = f"https://www.myntra.com/gateway/v2/mynsta/user/{author_id}/profile"
    async with session.get(url2, headers=headers) as r:
        print(f"GET {url2}: {r.status}")
        if r.status == 200:
            data = await r.json()
            print(f"Profile: {data.keys()}")
        
    # 3. Try studio layout endpoint
    url3 = "https://www.myntra.com/gateway/v3/layout/influencer"
    body3 = {
        "pageUri": f"/studio/influencer?id={author_id}",
        "pageContext": {}
    }
    async with session.post(url3, headers=headers, json=body3) as r:
        print(f"POST {url3}: {r.status}")
        if r.status == 200:
            data = await r.json()
            print("Layout response:", data.get("response", {}).get("screen", {}).keys())

if __name__ == "__main__":
    asyncio.run(main())
