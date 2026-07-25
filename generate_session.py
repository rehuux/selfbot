"""
Run this ONCE on your own machine (not on Render) to log in interactively
and produce the SESSION_STRING value for Render's environment variables.

This now generates a native Telethon StringSession (not a Base64-encoded
SQLite file), matching what main.py expects via StringSession(...).

Usage:
    pip install telethon
    python generate_session.py
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input("API_ID: ").strip())
API_HASH = input("API_HASH: ").strip()

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    session_string = client.session.save()

print("\nLogin complete. Copy the value below into Render's SESSION_STRING variable:\n")
print(session_string)
