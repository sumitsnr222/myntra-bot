import asyncio
import sys
import os
import json
import logging

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Set up logging to file
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("data/live_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

from backend import browser
from backend.config import generate_device
from backend.myntra_client import MyntraClient

async def run_live_test():
    phone = "9992443292"
    device = generate_device()
    
    print("\n" + "="*60)
    print("🔥 LIVE E2E TEST: BROWSER LOGIN -> DIRECT API")
    print("="*60)
    print(f"Device Identity: {device['brand']} {device['model']} (Android {device.get('android', '14')})")
    
    print("\n[1/4] Spawning Visible Browser & Simulating Human...")
    ok, msg, cookies, ctx, page = await browser.send_otp(phone, device)
    
    if not ok:
        print(f"\n❌ Failed to send OTP: {msg}")
        return
        
    print("\n[2/4] OTP Sent Successfully!")
    print("Please check your phone for the 4-digit OTP from Myntra.")
    
    # Wait for OTP from stdin
    otp = input("\n👉 ENTER 4-DIGIT OTP (or type 'cancel'): ").strip()
    
    if otp.lower() == 'cancel' or not otp:
        print("\nTest cancelled.")
        await ctx.close()
        return
        
    print(f"\n[3/4] Verifying OTP: {otp} ...")
    v_ok, v_msg, final_cookies = await browser.verify_otp(phone, otp, ctx, page)
    
    if not v_ok:
        print(f"\n❌ OTP Verification Failed: {v_msg}")
        return
        
    print(f"\n✅ Verification Success! Extracted {len(final_cookies)} cookies.")
    print("Browser closed. Switching to Direct API Client...")
    
    print("\n[4/4] Testing Direct API Access (Bypassing Akamai)...")
    client = MyntraClient(phone, device, final_cookies)
    
    try:
        profile = await client.get_profile()
        print(f"\n👤 Profile API Result:")
        print(json.dumps(profile, indent=2))
        
        cart = await client.get_cart()
        print(f"\n🛒 Cart API Result: {cart.get('count', 0)} items found.")
        print(json.dumps(cart, indent=2))
        
    except Exception as e:
        print(f"\n❌ API Test Failed: {e}")
    finally:
        await client.close()
        print("\n" + "="*60)
        print("✅ LIVE E2E TEST COMPLETE!")
        print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_live_test())
