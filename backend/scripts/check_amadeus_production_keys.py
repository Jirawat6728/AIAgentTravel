"""
ตรวจสอบว่า Amadeus Production API keys ใช้ได้หรือไม่
เรียก OAuth2 token ที่ api.amadeus.com (production)
"""
import asyncio
import sys
from pathlib import Path

# โหลด .env ผ่าน app config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import settings

try:
    import httpx
except ImportError:
    print("ติดตั้ง httpx: pip install httpx")
    sys.exit(1)


async def check_production_keys():
    client_id = settings.amadeus_search_api_key or settings.amadeus_api_key
    client_secret = settings.amadeus_search_api_secret or settings.amadeus_api_secret
    url = "https://api.amadeus.com/v1/security/oauth2/token"

    if not client_id or not client_secret:
        print("[FAIL] Not found AMADEUS_SEARCH_API_KEY or AMADEUS_SEARCH_API_SECRET in .env")
        return False

    print("Checking Production keys (api.amadeus.com)...")
    print("  Client ID: {}...{}".format(client_id[:8], client_id[-4:] if len(client_id) > 12 else "***"))

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                data = resp.json()
                exp = data.get("expires_in", 0)
                print("[OK] Production keys valid - got access_token (expires in {} sec)".format(exp))
                return True
            else:
                body = resp.text
                print("[FAIL] Production keys invalid - HTTP {}".format(resp.status_code))
                if resp.status_code == 401:
                    print("  Reason: Keys are likely Test keys (only work with test.api.amadeus.com)")
                    print("  Fix: Use Production API keys from Amadeus, or set AMADEUS_SEARCH_ENV=test")
                try:
                    err = resp.json()
                    for e in err.get("errors", [err]):
                        if isinstance(e, dict):
                            print("  ", e.get("detail") or e.get("title") or e)
                except Exception:
                    print("  ", body[:300] if len(body) > 300 else body)
                return False
        except Exception as e:
            print("[FAIL] Error: {}".format(e))
            return False


if __name__ == "__main__":
    ok = asyncio.run(check_production_keys())
    sys.exit(0 if ok else 1)
