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
    api_url = f"https://api.{region}/api/v2/authorization/roles?pageSize=1"

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

        # Test an actual endpoint that requires permissions
        roles_resp = await client.get(
            api_url,
            headers={"Authorization": f"Bearer {token}"}
        )

        if roles_resp.status_code == 200:
            print("SUCCESS: Was able to fetch roles. Perms are working!")
            data = roles_resp.json()
            print("Entities:", len(data.get("entities", [])))
        else:
            print(f"FAILED to fetch roles (Status: {roles_resp.status_code}): {roles_resp.text}")

        # Let's test telephony station
        station_url = f"https://api.{region}/api/v2/stations"
        station_resp = await client.get(
            station_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        if station_resp.status_code == 200:
            print("SUCCESS: Was able to fetch stations.")
        else:
            print(f"FAILED to fetch stations (Status: {station_resp.status_code}): {station_resp.text}")

if __name__ == "__main__":
    asyncio.run(main())
