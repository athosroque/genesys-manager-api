import os
import httpx
import base64
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    client_id = os.getenv("GENESYS_CLIENT_ID")
    client_secret = os.getenv("GENESYS_CLIENT_SECRET")
    region = os.getenv("GENESYS_REGION", "mypurecloud.com")

    auth_url = f"https://login.{region}/oauth/token"
    api_url = f"https://api.{region}/api/v2/tokens/me"

    auth_string = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_string.encode()).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            auth_url,
            headers={
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials"}
        )

        if resp.status_code != 200:
            print("Failed to authenticate:", resp.text)
            return

        token = resp.json().get("access_token")

        me_resp = await client.get(
            api_url,
            headers={"Authorization": f"Bearer {token}"}
        )

        if me_resp.status_code != 200:
            print("Failed to fetch /api/v2/tokens/me:", me_resp.text)
            return
        
        data = me_resp.json()
        print("Raw response from /tokens/me:", data)
        permissions = data.get("authorization", {}).get("permissions", [])
        if not permissions:
            print("NO PERMISSIONS FOUND!")
        else:
            print("--- PERMISSIONS ---")
            for p in sorted(permissions):
                print(p)

if __name__ == "__main__":
    asyncio.run(main())
