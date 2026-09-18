import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("GENESYS_CLIENT_ID")
client_secret = os.getenv("GENESYS_CLIENT_SECRET")
region = os.getenv("GENESYS_REGION", "mypurecloud.com")

auth_url = f"https://login.{region}/oauth/token"
api_url = f"https://api.{region}/api/v2/tokens/me"

auth_string = f"{client_id}:{client_secret}"
b64_auth = base64.b64encode(auth_string.encode()).decode()

resp = requests.post(
    auth_url,
    headers={
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    },
    data={"grant_type": "client_credentials"}
)

if resp.status_code != 200:
    print("Failed to authenticate:", resp.text)
    exit(1)

token = resp.json().get("access_token")

me_resp = requests.get(
    api_url,
    headers={"Authorization": f"Bearer {token}"}
)

if me_resp.status_code != 200:
    print("Failed to fetch /api/v2/tokens/me:", me_resp.text)
    exit(1)

permissions = me_resp.json().get("authorization", {}).get("permissions", [])
print("\n".join(sorted(permissions)))

