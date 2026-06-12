"""
Myntra Suite v4 — Config
Mobile device fingerprints + API endpoints from captured traffic.
"""
import uuid
import random

# ═══════════════════════════════════════════════════════════════════
#  API ENDPOINTS (from real captured traffic)
# ═══════════════════════════════════════════════════════════════════
BASE = "https://www.myntra.com"

API = {
    "getotp":           f"{BASE}/gateway/v1/auth/getotp",
    "verifyotp":        f"{BASE}/gateway/v1/auth/verifyotp",
    "profile":          f"{BASE}/gateway/v1/profile/default",
    "cart":             f"{BASE}/gateway/v1/cart/default/summary",
    "location":         f"{BASE}/gateway/v1/user/locationContext",
    "context":          f"{BASE}/gateway/v1/getContextAttrs",
    "abtests":          f"{BASE}/gateway/v1/abtests",
    "user_attrs":       f"{BASE}/gateway/v1/user/attributes",
    "feed":             f"{BASE}/gateway/v3/layout/feed/fashion",
    # Studio actions (mynsta)
    "studio_like":      f"{BASE}/gateway/v1/mynsta/react",
    "studio_unlike":    f"{BASE}/gateway/v1/mynsta/unlike",
    "studio_follow":    f"{BASE}/gateway/v1/mynsta/follow",
    "studio_unfollow":  f"{BASE}/gateway/v1/mynsta/unfollow",
    "studio_view":      f"{BASE}/gateway/v1/mynsta/markPostsAsSeen",
    "wishlist_add":     f"{BASE}/gateway/v1/wishlist",
    "wishlist_del":     f"{BASE}/gateway/v1/wishlist",
}

# ═══════════════════════════════════════════════════════════════════
#  MOBILE DEVICE POOL — each account uses a different "phone"
# ═══════════════════════════════════════════════════════════════════
DEVICES = [
    {"model": "Pixel 8 Pro",   "brand": "Google",  "build": "AP2A.240805.005",   "android": "14"},
    {"model": "Pixel 7",       "brand": "Google",  "build": "TQ3A.230901.001",   "android": "13"},
    {"model": "SM-S928B",      "brand": "Samsung", "build": "UP1A.231005.007",   "android": "14"},
    {"model": "SM-A546E",      "brand": "Samsung", "build": "TP1A.220624.014",   "android": "13"},
    {"model": "2201117TG",     "brand": "Xiaomi",  "build": "SKQ1.211006.001",   "android": "12"},
    {"model": "V2227",         "brand": "vivo",    "build": "TP1A.220624.014",   "android": "13"},
    {"model": "CPH2493",       "brand": "OPPO",    "build": "TP1A.220905.001",   "android": "13"},
    {"model": "22041219PI",    "brand": "Redmi",   "build": "SP1A.210812.016",   "android": "12"},
    {"model": "RMX3630",       "brand": "realme",  "build": "TP1A.220905.001",   "android": "13"},
    {"model": "OnePlus 11",    "brand": "OnePlus", "build": "TP1A.220905.001",   "android": "14"},
]

CHROME_VERSIONS = ["129.0.0.0", "130.0.0.0", "131.0.0.0", "132.0.0.0", "133.0.0.0"]


def generate_device():
    """Generate a unique mobile device fingerprint."""
    dev = random.choice(DEVICES)
    chrome = random.choice(CHROME_VERSIONS)
    device_id = str(uuid.uuid4())
    ua = (
        f"Mozilla/5.0 (Linux; Android {dev['android']}; {dev['model']} "
        f"Build/{dev['build']}) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome} Mobile Safari/537.36"
    )
    return {
        "device_id": device_id,
        "user_agent": ua,
        "model": dev["model"],
        "brand": dev["brand"],
    }


def build_headers(device, extra=None):
    """Build standard Myntra API headers for a device."""
    h = {
        "user-agent":         device["user_agent"],
        "x-myntraweb":        "Yes",
        "x-requested-with":   "browser",
        "content-type":       "application/json",
        "accept-language":    "en-IN",
        "x-location-context": "pincode=122001;source=IP",
        "deviceid":           device["device_id"],
        "x-meta-app": (
            f"deviceId={device['device_id']};"
            f"appFamily=MyntraRetailMweb;"
            f"channel=web;appVersion=4.2602.10"
        ),
        "x-myntra-app": (
            f"deviceID={device['device_id']}; "
            f"appFamily=MyntraRetailMweb;"
        ),
        "x-device-state": f"model={device['model']}; brand={device['brand']};",
        "referer": "https://www.myntra.com/",
        "origin":  "https://www.myntra.com",
    }
    if extra:
        h.update(extra)
    return h
