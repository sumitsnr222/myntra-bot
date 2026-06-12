"""
Myntra Suite v4 -- REST API
Full-featured API: login, profile, cart, wishlist, studio actions.
Each account acts as a different mobile device.
"""
import json
import logging
import os
import time
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from . import browser
from .config import generate_device
from .myntra_client import MyntraClient
from .database import load_db, save_db
from .proxy_manager import init_proxy_manager, get_proxy_manager

log = logging.getLogger(__name__)

app = FastAPI(title="Myntra Suite v4")

# ── State ──
accounts: dict[str, MyntraClient] = {}
pending_logins: dict[str, dict] = {}  # phone -> {device, ctx, page, cookies}
ws_clients: list[WebSocket] = []

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_FILE = os.path.join(DATA, "accounts.json")


# ── Models ──
class AuthRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    phone: str
    owner: str = ""


class VerifyRequest(BaseModel):
    phone: str
    otp: str

class WishlistRequest(BaseModel):
    phone: str
    style_id: int

class StudioRequest(BaseModel):
    phone: str
    post_id: str = ""
    user_id: str = ""

class TaskRequest(BaseModel):
    mode: str
    author_id: Optional[str] = None
    post_id: str = ""
    product_id: Optional[str] = None
    product_ids: Optional[list] = None
    
class ExtractRequest(BaseModel):
    url: str

# ── WebSocket broadcast ──
async def broadcast(event: str, data: dict):
    msg = json.dumps({"type": event, **data})
    dead = []
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


# ── Load saved accounts on startup ──
async def load_accounts():
    os.makedirs(DATA, exist_ok=True)
    init_proxy_manager(os.path.join(DATA, "proxies.txt"))
    db = await load_db(DB_FILE)
    for phone, info in db.items():
        device = info.get("device", generate_device())
        cookies = info.get("cookies", {})
        proxy = info.get("proxy")
        owner = info.get("owner", "")
        if not proxy:
            pm = get_proxy_manager()
            if pm:
                proxy = pm.get_random_proxy()
        client = MyntraClient(phone, device, cookies, proxy=proxy, owner=owner)
        accounts[phone] = client
        log.info(f"[Load] Account {phone} ({device['model']}) proxy={proxy}")
    log.info(f"[Load] {len(accounts)} accounts loaded")


async def save_accounts():
    db = {}
    for phone, client in accounts.items():
        if owner and users_db.get(owner, {}).get("role") != "admin" and getattr(client, 'owner', '') != owner:
            continue
        db[phone] = client.to_dict()
    await save_db(DB_FILE, db)


# ── Auth Routes ──
USERS_FILE = os.path.join(DATA, "users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        return json.load(open(USERS_FILE, encoding='utf-8'))
    admin = {"s09698840@gmail.com": {"password": "870881@Qwer", "role": "admin"}}
    save_users(admin)
    return admin

def save_users(users):
    json.dump(users, open(USERS_FILE, "w", encoding='utf-8'))

users_db = load_users()

@app.post("/api/auth/signup")
async def auth_signup(req: AuthRequest):
    if req.email in users_db:
        return {"success": False, "message": "User already exists"}
    users_db[req.email] = {"password": req.password, "role": "user"}
    save_users(users_db)
    return {"success": True, "message": "Signup successful", "role": "user", "token": req.email}

@app.post("/api/auth/login")
async def auth_login(req: AuthRequest):
    user = users_db.get(req.email)
    if not user or user["password"] != req.password:
        return {"success": False, "message": "Invalid credentials"}
    return {"success": True, "role": user["role"], "token": req.email}


# ── API Routes ──

@app.get("/api/stats")
async def get_stats(owner: str = None):
    accs = []
    for phone, client in accounts.items():
        if owner and users_db.get(owner, {}).get("role") != "admin" and getattr(client, 'owner', '') != owner:
            continue
        accs.append({
            "phone": phone,
            "device": f"{client.device.get('brand', '')} {client.device.get('model', '')}",
            "device_id": client.device.get("device_id", "")[:12] + "...",
            "logged_in": client.logged_in,
            "uidx": client.uidx[:20] + "..." if client.uidx else "",
            "added_at": client.last_used,
            "has_cookies": client.logged_in
        })
    return {
        "accounts": accs,
        "total_accounts": len(accounts),
        "active_sessions": sum(1 for c in accounts.values() if c.logged_in),
        "tasks_run": 0,
        "actions_ok": 0
    }


@app.get("/api/accounts")
async def list_accounts(owner: str = None):
    return await get_stats(owner)


@app.post("/api/accounts/login")
async def login_send_otp(req: LoginRequest):
    phone = req.phone.strip().replace("+91", "").replace(" ", "")
    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(400, "Invalid phone number")

    if phone in accounts:
        return {"success": False, "message": f"Account {phone} already exists in the system!"}

    device = generate_device()
    log.info(f"[Login] {phone} -> device: {device['brand']} {device['model']}")

    await broadcast("log", {"message": f"Sending OTP to {phone} as {device['brand']} {device['model']}..."})

    ok, msg, cookies, ctx, page = await browser.send_otp(phone, device)

    if ok and ctx and page:
        pending_logins[phone] = {"device": device, "ctx": ctx, "page": page, "cookies": cookies, "owner": req.owner}
        await broadcast("otp_sent", {"phone": phone, "device": f"{device['brand']} {device['model']}"})
    else:
        await broadcast("log", {"message": f"OTP failed for {phone}: {msg}"})

    return {"success": ok, "message": msg}


@app.post("/api/accounts/verify")
async def login_verify_otp(req: VerifyRequest):
    phone = req.phone.strip().replace("+91", "").replace(" ", "")
    otp = req.otp.strip()

    if not otp.isdigit() or len(otp) != 4:
        raise HTTPException(400, "OTP must be 4 digits")

    pending = pending_logins.get(phone)
    if not pending:
        raise HTTPException(400, f"No pending login for {phone}. Send OTP first.")

    ctx = pending["ctx"]
    page = pending["page"]
    device = pending["device"]

    await broadcast("log", {"message": f"Verifying OTP for {phone}..."})

    ok, msg, cookies = await browser.verify_otp(phone, otp, ctx, page)

    if ok:
        proxy = None
        pm = get_proxy_manager()
        if pm:
            proxy = pm.get_random_proxy()
        client = MyntraClient(phone, device, cookies, proxy=proxy, owner=owner)
        accounts[phone] = client
        await save_accounts()
        await broadcast("account_added", {
            "phone": phone,
            "device": f"{device['brand']} {device['model']}",
            "uidx": client.uidx[:20] + "...",
        })
        log.info(f"[Login] {phone} SUCCESS - uidx: {client.uidx[:30]}")
    else:
        await broadcast("log", {"message": f"Verify failed: {msg}"})

    pending_logins.pop(phone, None)
    return {"success": ok, "message": msg, "cookies_count": len(cookies)}


@app.get("/api/accounts/{phone}")
async def get_account_detail(phone: str):
    client = accounts.get(phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return {
        "phone": phone,
        "cookie_count": len(client.cookies),
        "cookie_keys": list(client.cookies.keys()),
        "manual": False,
        "cookie_string": "; ".join(f"{k}={v}" for k, v in client.cookies.items())
    }


@app.delete("/api/accounts/{phone}")
async def delete_account(phone: str):
    if phone in accounts:
        client = accounts.pop(phone)
        await client.close()
        await save_accounts()
    return {"success": True}


@app.get("/api/account/{phone}/profile")
async def get_profile(phone: str):
    client = accounts.get(phone)
    if not client:
        raise HTTPException(404, "Account not found")
    if not client.logged_in:
        raise HTTPException(400, "Account not logged in")
    try:
        return await client.get_profile()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/account/{phone}/cart")
async def get_cart(phone: str):
    client = accounts.get(phone)
    if not client:
        raise HTTPException(404, "Account not found")
    try:
        return await client.get_cart()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/account/wishlist/add")
async def wishlist_add(req: WishlistRequest):
    client = accounts.get(req.phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return await client.add_to_wishlist(req.style_id)


@app.post("/api/account/wishlist/remove")
async def wishlist_remove(req: WishlistRequest):
    client = accounts.get(req.phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return await client.remove_from_wishlist(req.style_id)


@app.post("/api/account/studio/like")
async def studio_like(req: StudioRequest):
    client = accounts.get(req.phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return await client.studio_like(req.post_id)


@app.post("/api/account/studio/follow")
async def studio_follow(req: StudioRequest):
    client = accounts.get(req.phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return await client.studio_follow(req.user_id)


@app.post("/api/account/studio/view")
async def studio_view(req: StudioRequest):
    client = accounts.get(req.phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return await client.studio_view(req.post_id)


@app.get("/api/account/{phone}/feed")
async def get_feed(phone: str):
    client = accounts.get(phone)
    if not client:
        raise HTTPException(404, "Account not found")
    return await client.get_feed()


@app.post("/api/tasks/extract")
async def extract_url(req: ExtractRequest):
    import re
    
    url = req.url.strip()
    post_id = ""
    author_id = ""
    product_id = ""
    product_ids = []
    
    # ── URL Patterns ──
    # Pattern: /studio/studiopost/12459426?...  (UGC share link)
    m = re.search(r'/studiopost/(\d+)', url)
    if m:
        post_id = m.group(1)
    
    # Pattern: /studio/post/12459426
    if not post_id:
        m2 = re.search(r'/post/(\d+)', url)
        if m2:
            post_id = m2.group(1)
    
    # Pattern: postId=12459426 in query
    if not post_id:
        m3 = re.search(r'postId[=:](\d+)', url)
        if m3:
            post_id = m3.group(1)

    # Pattern: /influencer/AUTHOR_ID or /studio/influencer?id=AUTHOR_ID
    m4 = re.search(r'/influencer/([A-Za-z0-9._-]+)', url)
    if m4:
        author_id = m4.group(1)
    if not author_id:
        m5 = re.search(r'id=([A-Za-z0-9._-]+)', url)
        if m5 and "influencer" in url:
            author_id = m5.group(1)
            
    is_author_profile = bool(author_id and not post_id and "influencer" in url)

    # If we have a post_id and a logged-in account, use the Myntra API to get full details
    if post_id and accounts and (not author_id or not product_id):
        # Use the first available logged-in account
        client = next((c for c in accounts.values() if c.logged_in), None)
        if client:
            try:
                details = await client.get_post_details(post_id)
                if details.get("author_id"):
                    author_id = details["author_id"]
                if details.get("product_ids"):
                    product_ids = details["product_ids"]
                    product_id = product_ids[0] if product_ids else ""
                log.info(f"[Extract] Post {post_id}: author={author_id}, products={product_ids}")
            except Exception as e:
                log.error(f"[Extract] API fetch error: {e}")
                
    if is_author_profile:
        log.info(f"[Extract] Detected Author Profile URL, extracting via Playwright...")
        # Get cookies from first logged-in account
        client = next((c for c in accounts.values() if c.logged_in), None)
        if client:
            extracted = await browser.extract_influencer_posts(url, client.cookies, proxy=client.proxy)
            if extracted:
                # extracted is a list of {post_id, author_id, product_ids}
                product_ids = extracted  # store the full list of post dicts
                if not author_id and extracted[0].get("author_id"):
                    author_id = extracted[0]["author_id"]
                log.info(f"[Extract] Found {len(extracted)} posts via Playwright.")
        else:
            log.warning("[Extract] No logged-in accounts to extract influencer posts.")
            
    return {
        "success": True, 
        "post_id": post_id, 
        "author_id": author_id, 
        "product_id": product_id,
        "product_ids": product_ids,
        "is_author_profile": is_author_profile,
    }

@app.get("/api/debug/influencer/{author_id}")
async def debug_influencer(author_id: str):
    if not accounts:
        return {"error": "no accounts"}
    client = list(accounts.values())[0]
    session = await client._get_session()
    headers = client._headers({"source": "mweb"})
    
    feed_url = "https://www.myntra.com/gateway/v1/layout/mynsta/feed"
    body = {"pageNumber": 1, "idsPerPage": 100, "feedType": "AUTHOR", "authorId": author_id}
    try:
        async with session.post(feed_url, headers=headers, json=body) as r:
            feed_status = r.status
            feed_data = await r.json() if r.status == 200 else {}
    except Exception as e:
        feed_status = str(e)
        feed_data = {}

    layout_url = "https://www.myntra.com/gateway/v3/layout/influencer"
    body2 = {"pageUri": f"/studio/influencer?id={author_id}", "pageContext": {}}
    try:
        async with session.post(layout_url, headers=headers, json=body2) as r:
            layout_status = r.status
            layout_data = await r.json() if r.status == 200 else {}
    except Exception as e:
        layout_status = str(e)
        layout_data = {}

    return {
        "feed": {"status": feed_status, "data": feed_data},
        "layout": {"status": layout_status, "data": layout_data}
    }


@app.post("/api/tasks/run")
async def run_tasks_api(req: TaskRequest):
    if not accounts:
        return {"success": False, "message": "No accounts available"}

    async def _run_task():
        await broadcast("task_start", {"label": req.mode.upper(), "total": len(accounts)})
        
        # --- AUTHOR ALL MODE ---
        if req.mode == "author_all":
            # req.product_ids contains either:
            #   a) list of dicts: [{post_id, author_id, product_ids}, ...] from Playwright extraction
            #   b) list of strings: ["12345", "67890", ...] as post IDs
            raw_posts = req.product_ids or []
            if not raw_posts:
                await broadcast("task_progress", {"info": True, "message": "❌ No posts found. Make sure you have a logged-in account."})
                return

            # Normalize to list of dicts
            posts_data = []
            for item in raw_posts:
                if isinstance(item, dict):
                    posts_data.append(item)
                else:
                    posts_data.append({"post_id": str(item), "author_id": req.author_id or "", "product_ids": []})
            
            await broadcast("task_progress", {"info": True, "message": f"Found {len(posts_data)} posts. Starting processing..."})
            
            for p_idx, post_data in enumerate(posts_data):
                pid = str(post_data.get("post_id", ""))
                pids = post_data.get("product_ids", [])
                post_author = post_data.get("author_id") or req.author_id or ""
                
                if not pid:
                    continue
                
                await broadcast("task_progress", {"info": True, "message": f"Processing Post {p_idx+1}/{len(posts_data)} (ID: {pid}) — {len(pids)} products"})
                
                for i, (phone, acc_client) in enumerate(accounts.items()):
                    try:
                        import random
                        
                        # 1. View post
                        await acc_client.studio_view(pid)
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                        
                        # 2. Follow author
                        follow_ok = False
                        if post_author:
                            r_follow = await acc_client.studio_follow(post_author)
                            follow_ok = r_follow.get("error") is None
                            await asyncio.sleep(random.uniform(1.5, 3.0))
                        
                        # 3. Product Taps
                        tap_ok = 0
                        for pdid in pids:
                            if pdid:
                                r_tap = await acc_client.product_tap(str(pdid))
                                if r_tap.get("error") is None:
                                    tap_ok += 1
                                await asyncio.sleep(random.uniform(1.0, 2.5))
                                
                        # 4. Like post
                        r_like = await acc_client.studio_like(pid)
                        like_ok = r_like.get("error") is None
                        
                        await broadcast("task_progress", {
                            "phone": phone,
                            "index": i + 1,
                            "total": len(accounts),
                            "status": "success" if like_ok else "error",
                            "results": {"View": True, "Follow": follow_ok, "ProductTap": tap_ok, "Like": like_ok},
                            "post_idx": p_idx + 1,
                            "total_posts": len(posts_data)
                        })
                    except Exception as e:
                        log.error(f"[AuthorAll] Error on post {pid} for {phone}: {e}")
                        await broadcast("task_progress", {
                            "phone": phone,
                            "index": i + 1,
                            "total": len(accounts),
                            "status": "error",
                            "detail": str(e),
                            "post_idx": p_idx + 1,
                            "total_posts": len(posts_data)
                        })
                
                # Random delay between posts
                import random
                await asyncio.sleep(random.uniform(2.0, 5.0))
            
            await broadcast("task_progress", {"info": True, "message": f"✅ Completed all {len(posts_data)} posts!"})
            return

        # --- NORMAL MODES ---
        ok = 0
        fail = 0

        for i, (phone, client) in enumerate(accounts.items()):
            try:
                import random
                results = {}
                if "like" in req.mode:
                    r = await client.studio_like(req.post_id)
                    results["Like"] = r.get("error") is None
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                if "follow" in req.mode and req.author_id:
                    r = await client.studio_follow(req.author_id)
                    results["Follow"] = r.get("error") is None
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                if "view" in req.mode:
                    r = await client.studio_view(req.post_id)
                    results["View"] = r.get("error") is None
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                if "wishlist" in req.mode and req.product_id:
                    r = await client.add_to_wishlist(int(req.product_id))
                    results["Wishlist"] = r.get("error") is None
                    await asyncio.sleep(random.uniform(1.0, 3.0))

                if "full" in req.mode:
                    # Step 1: View post (markPostsAsSeen)
                    if req.post_id:
                        r1 = await client.studio_view(req.post_id)
                        results["View"] = r1.get("error") is None
                        await asyncio.sleep(random.uniform(2.5, 4.5))
                    
                    # Step 2: Follow the creator
                    if req.author_id:
                        r4 = await client.studio_follow(req.author_id)
                        results["Follow"] = r4.get("error") is None
                        await asyncio.sleep(random.uniform(1.5, 3.5))
                    
                    # Step 3: Product Tap — tap ALL products from the post
                    all_pids = req.product_ids or ([req.product_id] if req.product_id else [])
                    tap_ok = 0
                    for pid in all_pids:
                        if pid:
                            r5 = await client.product_tap(str(pid))
                            if r5.get("error") is None:
                                tap_ok += 1
                            await asyncio.sleep(random.uniform(1.5, 3.0))
                    if all_pids:
                        results["ProductTap"] = tap_ok > 0
                    
                    # Step 4: Like the post
                    if req.post_id:
                        r2 = await client.studio_like(req.post_id)
                        results["Like"] = r2.get("error") is None
                        await asyncio.sleep(random.uniform(1.5, 3.0))

                is_success = all(results.values()) if results else False
                if is_success:
                    ok += 1
                else:
                    fail += 1

                await broadcast("task_progress", {
                    "phone": phone,
                    "index": i + 1,
                    "total": len(accounts),
                    "status": "success" if is_success else "error",
                    "results": results
                })

            except Exception as e:
                fail += 1
                await broadcast("task_progress", {
                    "phone": phone,
                    "index": i + 1,
                    "total": len(accounts),
                    "status": "error",
                    "detail": str(e)
                })

            await asyncio.sleep(1)

        await broadcast("task_done", {"label": req.mode.upper(), "ok": ok, "fail": fail, "total": len(accounts)})

    asyncio.create_task(_run_task())
    return {"success": True, "message": "Task started in background"}


@app.get("/api/browser-info")
async def browser_info():
    return {
        "engine": "Mobile Client + aiohttp",
        "strategy": "Chrome (visible) + Direct API",
        "mode": "Mobile device simulation",
        "akamai_bypass": "Human-like interactions + real Chrome TLS",
    }


# ── WebSocket ──
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)


# ── Frontend ──
FRONTEND = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))

@app.get("/style.css")
async def css():
    return FileResponse(os.path.join(FRONTEND, "style.css"), media_type="text/css")

@app.get("/app.js")
async def js():
    return FileResponse(os.path.join(FRONTEND, "app.js"), media_type="application/javascript")

@app.get("/api/accounts/{phone}/cookies")
async def download_cookies(phone: str, owner: str = None):
    client = accounts.get(phone)
    if not client:
        raise HTTPException(404, "Account not found")
    if owner and users_db.get(owner, {}).get("role") != "admin" and getattr(client, 'owner', '') != owner:
        raise HTTPException(403, "Not authorized")
    content = json.dumps(client.cookies, indent=2)
    with open(f"{phone}_cookies.json", "w") as f:
        f.write(content)
    return FileResponse(f"{phone}_cookies.json", filename=f"{phone}_cookies.txt")
