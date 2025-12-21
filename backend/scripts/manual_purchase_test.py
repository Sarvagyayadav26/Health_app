"""Small script to call the running backend /purchase/verify endpoint.

Usage:
    python manual_purchase_test.py

It expects the backend to be running on http://localhost:8000
"""
import requests
import time

URL = "http://localhost:8000/purchase/verify"


def run():
    email = f"manual_test_{int(time.time()*1000)}@example.com"
    payload = {
        "email": email,
        "purchase_token": "manual-token-" + str(int(time.time())),
        "product_id": "mental_health_5_chats_v1"
    }
    print("Posting:", payload)
    r = requests.post(URL, json=payload)
    print(r.status_code, r.text)


if __name__ == "__main__":
    run()
