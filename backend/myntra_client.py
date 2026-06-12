"""
Myntra Suite v4 -- Direct API Client
Uses aiohttp to call Myntra APIs directly, acting as a mobile device.
Browser is ONLY used for the login flow (Akamai bypass).
After login, all operations use pure HTTP with the auth token.
"""
import aiohttp
import json
import logging
import time
from typing import Optional

from .config import API, build_headers

log = logging.getLogger(__name__)


class MyntraClient:
    """Represents a logged-in Myntra account."""

    def __init__(self, phone: str, device: dict, cookies: dict, auth_headers: dict = None, proxy: str = None, owner: str = ""):
        self.phone = phone
        self.device = device
        self.cookies = cookies
        self.auth_headers = auth_headers or {}
        self.proxy = proxy
        self.owner = owner
        self.uidx = cookies.get("uidx", "")
        self.at_token = cookies.get("at", "")
        self.rt_token = cookies.get("rt", "")
        self.logged_in = bool(self.at_token)
        self.last_used = time.time()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(
                cookie_jar=cookie_jar,
                connector=aiohttp.TCPConnector(ssl=False, limit=10),
            )
            # Load saved cookies
            for name, value in self.cookies.items():
                self._session.cookie_jar.update_cookies(
                    {name: value},
                    response_url=aiohttp.client.URL("https://www.myntra.com/"),
                )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _headers(self, extra=None):
        h = build_headers(self.device, extra)
        return h

    # ---- Profile ----
    async def get_profile(self) -> dict:
        session = await self._get_session()
        headers = self._headers({"source": "mweb", "user-state": "NEW_USER"})
        async with session.get(API["profile"], headers=headers, proxy=self.proxy) as r:
            data = await r.json()
            log.info(f"[{self.phone}] Profile: {data}")
            return data

    # ---- Cart ----
    async def get_cart(self) -> dict:
        session = await self._get_session()
        headers = self._headers()
        async with session.get(API["cart"], headers=headers, proxy=self.proxy) as r:
            data = await r.json()
            log.info(f"[{self.phone}] Cart: {data.get('count', 0)} items")
            return data

    # ---- Wishlist ----
    async def add_to_wishlist(self, style_id: int) -> dict:
        session = await self._get_session()
        headers = self._headers()
        body = {"styleId": style_id}
        async with session.post(API["wishlist_add"], headers=headers, json=body, proxy=self.proxy) as r:
            data = await r.json() if r.status == 200 else {"error": r.status}
            log.info(f"[{self.phone}] Wishlist add {style_id}: {r.status}")
            return data

    async def remove_from_wishlist(self, style_id: int) -> dict:
        session = await self._get_session()
        headers = self._headers()
        async with session.delete(f"{API['wishlist_del']}/{style_id}", headers=headers, proxy=self.proxy) as r:
            data = await r.json() if r.status == 200 else {"error": r.status}
            log.info(f"[{self.phone}] Wishlist remove {style_id}: {r.status}")
            return data

    # ---- Studio ----
    async def studio_like(self, post_id: str) -> dict:
        session = await self._get_session()
        headers = self._headers()
        body = {"postId": int(post_id), "reaction": "LIKE"}
        async with session.post(API["studio_like"], headers=headers, json=body, proxy=self.proxy) as r:
            data = await r.json() if r.status == 200 else {"error": r.status}
            log.info(f"[{self.phone}] Studio like {post_id}: {r.status}")
            return data

    async def studio_follow(self, user_id: str) -> dict:
        session = await self._get_session()
        headers = self._headers()
        body = {"option": "FOLLOW_AUTHOR", "ids": [user_id]}
        async with session.post(API["studio_follow"], headers=headers, json=body, proxy=self.proxy) as r:
            data = await r.json() if r.status == 200 else {"error": r.status}
            log.info(f"[{self.phone}] Studio follow {user_id}: {r.status}")
            return data

    async def studio_view(self, post_id: str) -> dict:
        session = await self._get_session()
        headers = self._headers()
        body = {"postIds": [post_id]}
        async with session.post(API["studio_view"], headers=headers, json=body, proxy=self.proxy) as r:
            data = await r.json() if r.status == 200 else {"error": r.status}
            log.info(f"[{self.phone}] Studio view {post_id}: {r.status}")
            return data

    async def product_tap(self, product_id: str) -> dict:
        """Simulate tapping on a product in the Studio post (PDP view)."""
        session = await self._get_session()
        headers = self._headers()
        url = f"https://www.myntra.com/gateway/v3/layout/{product_id}"
        body = {
            "pageUri": f"/v3/layout/{product_id}",
            "pageContext": {
                "RequestPayloadData": {
                    "customerCohorts": [],
                    "nonWorkingDays": [],
                    "pincode": "",
                    "isMiniPdpEnabled": False,
                    "selectedImage": "",
                    "pidx": self.device.get("device_id", ""),
                    "store": "myntra",
                    "immersiveFwdEnabled": False,
                    "isOpenedFromDeeplink": False,
                }
            }
        }
        async with session.post(url, headers=headers, json=body, proxy=self.proxy) as r:
            data = await r.json() if r.status == 200 else {"error": r.status}
            log.info(f"[{self.phone}] Product tap {product_id}: {r.status}")
            return data

    async def get_post_details(self, post_id: str) -> dict:
        """Fetch full post details (author, styles/products) from Myntra feed."""
        session = await self._get_session()
        headers = self._headers()
        # Use the mynsta feed to get post info
        feed_url = "https://www.myntra.com/gateway/v1/layout/mynsta/feed"
        body = {"pageNumber": 1, "idsPerPage": 100, "feedType": "USER"}
        try:
            async with session.post(feed_url, headers=headers, json=body, proxy=self.proxy) as r:
                if r.status != 200:
                    log.error(f"[{self.phone}] Feed fetch failed: {r.status}")
                    return {"error": r.status}
                data = await r.json()
                # Search through feed posts for our post_id
                resp = data.get("response", {})
                screen = resp.get("screen", {})
                posts = screen.get("list", [])
                for item in posts:
                    post = item.get("post", {})
                    if str(post.get("id", "")) == str(post_id):
                        author = post.get("author", {})
                        styles = post.get("styles", [])
                        style_ids = [str(s.get("id", "")) for s in styles if s.get("id")]
                        result = {
                            "post_id": str(post.get("id", "")),
                            "author_id": author.get("id", ""),
                            "author_name": author.get("name", ""),
                            "product_ids": style_ids,
                        }
                        log.info(f"[{self.phone}] Post details: {result}")
                        return result
                log.info(f"[{self.phone}] Post {post_id} not found in feed")
                return {"error": "not_found"}
        except Exception as e:
            log.error(f"[{self.phone}] get_post_details error: {e}")
            return {"error": str(e)}

    async def get_influencer_posts(self, author_id: str) -> list[dict]:
        """Fetch all posts and their products for a given author ID."""
        session = await self._get_session()
        headers = self._headers()
        
        # 1. Try AUTHOR feed API
        feed_url = "https://www.myntra.com/gateway/v1/layout/mynsta/feed"
        body = {"pageNumber": 1, "idsPerPage": 100, "feedType": "AUTHOR", "authorId": author_id}
        posts_data = []
        try:
            async with session.post(feed_url, headers=headers, json=body, proxy=self.proxy) as r:
                if r.status == 200:
                    data = await r.json()
                    posts = data.get("response", {}).get("screen", {}).get("list", [])
                    for item in posts:
                        post = item.get("post", {})
                        pid = str(post.get("id", ""))
                        if pid:
                            styles = post.get("styles", [])
                            style_ids = [str(s.get("id", "")) for s in styles if s.get("id")]
                            posts_data.append({"post_id": pid, "product_ids": style_ids})
            
            # 2. If Feed API returns 0, try Layout API as fallback
            if not posts_data:
                layout_url = "https://www.myntra.com/gateway/v3/layout/influencer"
                body2 = {"pageUri": f"/studio/influencer?id={author_id}", "pageContext": {}}
                async with session.post(layout_url, headers=headers, json=body2, proxy=self.proxy) as r:
                    if r.status == 200:
                        data = await r.json()
                        widgets = data.get("response", {}).get("screen", {}).get("widgets", [])
                        for w in widgets:
                            if "data" in w and "posts" in w["data"]:
                                for post in w["data"]["posts"]:
                                    pid = str(post.get("id", ""))
                                    if pid:
                                        styles = post.get("styles", [])
                                        style_ids = [str(s.get("id", "")) for s in styles if s.get("id")]
                                        posts_data.append({"post_id": pid, "product_ids": style_ids})
            
            log.info(f"[{self.phone}] Fetched {len(posts_data)} posts for influencer {author_id}")
            return posts_data
        except Exception as e:
            log.error(f"[{self.phone}] get_influencer_posts error: {e}")
            return []

    # ---- Location ----
    async def get_location(self) -> dict:
        session = await self._get_session()
        headers = self._headers()
        body = {"previousContext": {"pincode": "", "source": ""}, "currentContext": None}
        async with session.post(API["location"], headers=headers, json=body, proxy=self.proxy) as r:
            return await r.json()

    # ---- Feed ----
    async def get_feed(self) -> dict:
        session = await self._get_session()
        headers = self._headers({"source": "mweb"})
        body = {
            "pageUri": "/v3/layout/feed/fashion?context=myntra",
            "pageContext": {"RequestPayloadData": {}, "widgetHash": {}},
        }
        async with session.post(f"{API['feed']}?context=myntra", headers=headers, json=body, proxy=self.proxy) as r:
            if r.status == 200:
                data = await r.json()
                log.info(f"[{self.phone}] Feed loaded")
                return data
            return {"error": r.status}

    # ---- Utility ----
    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "device": self.device,
            "cookies": self.cookies,
            "uidx": self.uidx,
            "proxy": getattr(self, "proxy", None),
            "owner": getattr(self, "owner", ""),
            "logged_in": self.logged_in,
            "last_used": self.last_used,
        }
