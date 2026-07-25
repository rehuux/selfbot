"""
Run this ONCE on your own machine (not on Render) to log in interactively
and produce the SESSION_STRING value for Render's environment variables.

Usage:
    pip install telethon
    python generate_session.py
"""

import base64
from telethon.sync import TelegramClient

API_ID = int(input("API_ID: ").strip())
API_HASH = input("API_HASH: ").strip()

with TelegramClient("selfbot_session", API_ID, API_HASH) as client:
    with open("selfbot_session.session", "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

print("\nLogin complete. Copy the value below into Render's SESSION_STRING variable:\n")
print(encoded)
