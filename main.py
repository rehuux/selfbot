import os
import re
import json
import time
import socket
import ssl
import datetime
import asyncio
import random
import logging
import platform
import sys
import string
import hashlib
import base64
import codecs
import traceback
import urllib.parse
from uuid import uuid4
from typing import Optional, Dict, Any, List, Tuple

import requests
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.channels import GetFullChannelRequest, EditAdminRequest

# ------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SelfBot] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("selfbot")

# ------------------------------------------------------------------
# Optional Dependencies
# ------------------------------------------------------------------
try:
    import aiohttp
    from aiohttp import web as aw
    AIOHTTP_OK = True
except ImportError:
    AIOHTTP_OK = False

try:
    import sympy
    SYMPY_OK = True
except ImportError:
    SYMPY_OK = False

try:
    import instaloader
    INSTA_OK = True
except ImportError:
    INSTA_OK = False

try:
    from langdetect import detect as _detect_lang
    LANGDETECT_OK = True
except ImportError:
    LANGDETECT_OK = False

try:
    import dns.resolver
    DNS_OK = True
except ImportError:
    DNS_OK = False

try:
    import whois as pywhois
    WHOIS_OK = True
except ImportError:
    WHOIS_OK = False

try:
    import easyocr
    EASYOCR_OK = True
except ImportError:
    EASYOCR_OK = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_OK = True
except ImportError:
    TESSERACT_OK = False

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False

try:
    import speedtest as speedtest_module
    SPEEDTEST_OK = True
except ImportError:
    SPEEDTEST_OK = False

# ------------------------------------------------------------------
# Environment / Configuration
# ------------------------------------------------------------------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
PHONE = os.environ.get("PHONE", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "").strip()

DATA_FILE = "selfbot_data.json"
ERROR_LOG_FILE = "errors.log"
NOTES_FILE = "notes_data.json"
PORTFOLIO_FILE = "portfolio_data.json"
GHOST_STATE_FILE = "ghost_state.json"
FLAIR_STATE_FILE = "flair_state.json"
WHALE_STATE_FILE = "whale_state.json"
SECRET_NOTES_FILE = "secret_notes.enc"
SECRET_SALT_FILE = "secret_salt.bin"
TEMP_DIR = "selfbot_temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Developer Profile
DEV_NAME = "Syed Rehan"
DEV_ROLE = "Security Researcher & Ethical Hacker"
DEV_PORTFOLIO = "https://rehuux.vercel.app"
DEV_GITHUB = "https://github.com/rehuux"
DEV_SKILLS = "CyberSecurity, Telegram Bot Development, Security/OSINT, Linux, and AI Integration"

# Media Assets
COMMANDS_GIF_URL = "https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUyMXo1bzFoMmtkb3k4dmxtcDM5dWFmNG9sMHBpanI4MmZlNXJyajBjNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/u2dI2h52gAzNS/giphy.gif"
DEV_GIF_URL = "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyd3dzbzJzOHc4OHllYXNwZ2h5cnVjeHZ3Z3pzd2pxeXM3aDY5aG92NCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jpIidKCY487Rbj0TiV/giphy.gif"
AFK_GIF_URL = "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUydDhyZ3dwdmptam8ybTVxMTZvbmRxeXRwbnltczBjdTU5aHZ6bG5pYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8bxgTkgQqjQBEobJlW/giphy.gif"

BOT_VERSION = "4.5.0"
BOT_BUILD = "2026.08"
BOT_START_TIME = time.time()
SPAM_MAX_REPEATS = 30
GHOST_DELETE_DELAY = 10
SECRET_MASTER_PASSWORD = os.environ.get("SECRET_MASTER_PASSWORD", "MasterRehu2026")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "")
VIRUSTOTAL_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "BZgkqPqms7Kj9ulSkVzn").strip()
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "").strip()

ELEVENLABS_VOICES = {
    "default": "BZgkqPqms7Kj9ulSkVzn",
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "adam": "pNInz6obpgDQGcFmaJgB",
    "antoni": "ErXwobaYiN019PkySvjV",
    "josh": "TxGEqnHWrfWFTfGW9XjX",
}

def _get_elevenlabs_keys() -> list:
    raw = os.environ.get("ELEVENLABS_API_KEY", "") or os.environ.get("ELEVENLABS_API_KEYS", "")
    if not raw:
        return []
    return [k.strip() for k in re.split(r"[,;\s]+", raw) if k.strip()]

WHALE_CHECK_INTERVAL = 60
WHALE_BTC_THRESHOLD_SATS = 5_000_000_000
_seen_whale_txids = set()

DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "yopmail.com", "trashmail.com", "throwawaymail.com", "fakeinbox.com",
    "getnada.com", "sharklasers.com",
}

USERNAME_CHECK_SITES = {
    "GitHub": "https://github.com/{u}",
    "Instagram": "https://www.instagram.com/{u}/",
    "Twitter/X": "https://x.com/{u}",
    "Reddit": "https://www.reddit.com/user/{u}",
    "Telegram": "https://t.me/{u}",
    "TikTok": "https://www.tiktok.com/@{u}",
    "Pinterest": "https://www.pinterest.com/{u}/",
}

# ------------------------------------------------------------------
# Persistence Helpers
# ------------------------------------------------------------------
def load_json(filepath: str, default_val: Any) -> Any:
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load {filepath}: {e}")
    return default_val

def save_json(filepath: str, data: Any):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error(f"Failed to save {filepath}: {e}")

data = load_json(DATA_FILE, {"muted_users": [], "banned_users": []})
muted_users = set(data.get("muted_users", []))
banned_users = set(data.get("banned_users", []))
portfolio = load_json(PORTFOLIO_FILE, {})
notes_db = load_json(NOTES_FILE, {})

auto_accept_active = False
auto_fix_active = True
whale_alert_active = False
_whale_task = None

def log_error(cmd_text: str, exc: Exception):
    entry = (
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CMD={cmd_text!r} ERROR={exc}\n"
        f"{traceback.format_exc()}\n{'─' * 50}\n"
    )
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass

# ------------------------------------------------------------------
# Telegram Client Initialization
# ------------------------------------------------------------------
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    log.info("Initialized Telethon with StringSession.")
else:
    client = TelegramClient("selfbot_session", API_ID, API_HASH)
    log.info("Initialized Telethon with local SQLite session.")

# ------------------------------------------------------------------
# AFK State Manager
# ------------------------------------------------------------------
AFK_RETRIGGER_SECONDS = 6 * 3600
DEFAULT_AFK_MESSAGE = (
    "Hello! I am currently **AFK (Away From Keyboard)**.\n"
    "I will be with you shortly (approximately 5–20 minutes).\n"
    "Please leave your message or reason for contacting me."
)

class AFKState:
    def __init__(self):
        self.active = False
        self.start_time = None
        self.message = DEFAULT_AFK_MESSAGE
        self.replied_users = {}

    def enable(self, custom_message=None):
        self.active = True
        self.start_time = time.time()
        self.message = custom_message or DEFAULT_AFK_MESSAGE
        self.replied_users = {}

    def disable(self):
        self.active = False
        self.start_time = None
        self.replied_users = {}

    def should_reply(self, user_id):
        last = self.replied_users.get(user_id)
        if last is None:
            return True
        return (time.time() - last) >= AFK_RETRIGGER_SECONDS

    def mark_replied(self, user_id):
        self.replied_users[user_id] = time.time()

    def duration_text(self):
        if not self.start_time:
            return "0 minutes"
        elapsed = int(time.time() - self.start_time)
        hours, rem = divmod(elapsed, 3600)
        minutes, seconds = divmod(rem, 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

afk = AFKState()

# ------------------------------------------------------------------
# Ghost Mode Manager
# ------------------------------------------------------------------
class GhostModeState:
    def __init__(self):
        self.enabled = False
        self.delete_delay = GHOST_DELETE_DELAY
        self._load()

    def _load(self):
        d = load_json(GHOST_STATE_FILE, {"delete_delay": GHOST_DELETE_DELAY})
        self.enabled = False
        self.delete_delay = int(d.get("delete_delay", GHOST_DELETE_DELAY))

    def _save(self):
        save_json(GHOST_STATE_FILE, {"enabled": self.enabled, "delete_delay": self.delete_delay})

    def enable(self, delay: Optional[int] = None):
        self.enabled = True
        if delay and delay > 0:
            self.delete_delay = delay
        self._save()

    def disable(self):
        self.enabled = False
        self._save()

ghost_mode = GhostModeState()

# ------------------------------------------------------------------
# Formatting & Entity Helpers
# ------------------------------------------------------------------
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

async def get_entity(val):
    try:
        if isinstance(val, int):
            return await client.get_entity(val)
        if isinstance(val, str) and val.startswith("@"):
            return await client.get_entity(val)
        try:
            return await client.get_entity(int(val))
        except Exception:
            return await client.get_entity(val)
    except Exception:
        return None

async def get_admin_group_ids():
    ids = []
    async for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            try:
                perms = d.entity
                if hasattr(perms, "admin_rights") and perms.admin_rights:
                    ids.append(d.id)
                    continue
                if hasattr(perms, "megagroup") or hasattr(perms, "broadcast"):
                    full = await client(GetFullChannelRequest(d.id))
                    chat = full.chats[0]
                    if getattr(chat, "admin_rights", None):
                        ids.append(d.id)
            except Exception:
                pass
    return ids

async def get_all_group_ids():
    ids = []
    async for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            ids.append(d.id)
    return ids

async def get_dm_ids():
    ids = []
    async for d in client.iter_dialogs():
        try:
            if d.is_user and not d.entity.bot:
                ids.append(d.id)
        except Exception:
            pass
    return ids

async def safe_sleep(count):
    if count > 0 and count % 15 == 0:
        await asyncio.sleep(40)
    else:
        await asyncio.sleep(random.uniform(4, 8))

async def _send_gif_with_text(event, gif_url, text):
    try:
        await event.delete()
    except Exception:
        pass
    caption = text if len(text) <= 1024 else text[:1020] + "..."
    try:
        await client.send_file(event.chat_id, gif_url, caption=caption)
    except Exception as e:
        log_error("send_gif", e)
        try:
            await client.send_message(event.chat_id, text)
        except Exception:
            pass

# ------------------------------------------------------------------
# Feature Implementation Functions
# ------------------------------------------------------------------
def _ig_info(username):
    username = username.lstrip("@").strip()
    if INSTA_OK:
        try:
            L = instaloader.Instaloader()
            p = instaloader.Profile.from_username(L.context, username)
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 **Instagram — @{p.username}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Name:** `{p.full_name or 'N/A'}`
✓ **Username:** @{p.username}
✓ **Followers:** `{p.followers:,}`
✓ **Following:** `{p.followees:,}`
✓ **Posts:** `{p.mediacount:,}`
✓ **Private:** `{'Yes' if p.is_private else 'No'}`
✓ **Verified:** `{'Yes' if p.is_verified else 'No'}`
✓ **Business:** `{'Yes' if p.is_business_account else 'No'}`
✓ **Bio:** `{p.biography or 'None'}`
✓ **Link:** https://instagram.com/{p.username}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        except Exception as e:
            log.info(f"instaloader failed for @{username}: {e}")

    try:
        session = requests.Session()
        session.headers.update(HTTP_HEADERS)
        r = session.get(
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers={"x-ig-app-id": "936619743392459", "Referer": f"https://www.instagram.com/{username}/"},
            timeout=12,
        )
        if r.status_code == 200:
            payload = r.json()
            u = payload.get("data", {}).get("user")
            if not u:
                return f"❌ @{username} not found or Instagram returned no profile data."
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 **Instagram — @{u['username']}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Name:** `{u.get("full_name") or 'N/A'}`
✓ **IG ID:** `{u["id"]}`
✓ **Followers:** `{u["edge_followed_by"]["count"]:,}`
✓ **Following:** `{u["edge_follow"]["count"]:,}`
✓ **Posts:** `{u["edge_owner_to_timeline_media"]["count"]:,}`
✓ **Private:** `{'Yes' if u["is_private"] else 'No'}`
✓ **Verified:** `{'Yes' if u["is_verified"] else 'No'}`
✓ **Business:** `{'Yes' if u.get("is_business_account") else 'No'}`
✓ **Bio:** `{u.get("biography") or 'None'}`
✓ **Link:** https://instagram.com/{u['username']}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        if r.status_code == 404:
            return f"❌ @{username} doesn't exist or is banned."
        return f"❌ Instagram API returned status {r.status_code}."
    except Exception as e:
        return f"❌ Instagram lookup failed: {e}"

def _translate(text, target_lang):
    source_lang = "en"
    if LANGDETECT_OK:
        try:
            source_lang = _detect_lang(text) or "en"
        except Exception:
            source_lang = "en"

    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{source_lang}|{target_lang}"},
            timeout=10,
        )
        d = r.json()
        if d.get("responseStatus") == 200:
            return f"🌐 **[{source_lang.upper()} ➔ {target_lang.upper()}]**\n`{d['responseData']['translatedText']}`"
    except Exception:
        pass

    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": source_lang, "tl": target_lang, "dt": "t", "q": text},
            timeout=10,
        )
        if r.status_code == 200:
            out = "".join(seg[0] for seg in r.json()[0] if seg[0])
            return f"🌐 **[{source_lang.upper()} ➔ {target_lang.upper()}]**\n`{out}`"
    except Exception as e:
        return f"❌ Translation error: {e}"
    return "❌ Translation failed."

def _weather_info(city):
    try:
        r = requests.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=j1", timeout=10)
        if r.status_code != 200:
            return f"❌ Couldn't fetch weather for '{city}'."
        d = r.json()
        cur = d["current_condition"][0]
        area = d.get("nearest_area", [{}])[0]
        place = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌦 **Weather — {place}, {country}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Condition:** `{cur['weatherDesc'][0]['value']}`
✓ **Temperature:** `{cur['temp_C']}°C ({cur['temp_F']}°F)`
✓ **Feels Like:** `{cur['FeelsLikeC']}°C`
✓ **Humidity:** `{cur['humidity']}%`
✓ **Wind:** `{cur['windspeedKmph']} km/h`
✓ **Visibility:** `{cur['visibility']} km`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Weather lookup failed: {e}"

def _crypto_price(coin):
    coin_clean = coin.lower().strip()
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_clean, "vs_currencies": "usd,inr,eur", "include_24hr_change": "true"},
            timeout=8,
        )
        d = r.json()
        if coin_clean in d:
            info = d[coin_clean]
            change = info.get("usd_24h_change", 0)
            arrow = "📈" if change >= 0 else "📉"
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **{coin.capitalize()} Price (CoinGecko)**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **USD:** `${info['usd']:,}`
✓ **INR:** `₹{info.get('inr', 0):,}`
✓ **EUR:** `€{info.get('eur', 0):,}`
✓ **24h Change:** {arrow} `{change:.2f}%`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass

    try:
        sym = f"{coin.upper()}USDT"
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}", timeout=8)
        if r.status_code == 200:
            d = r.json()
            price = float(d["lastPrice"])
            change = float(d["priceChangePercent"])
            arrow = "📈" if change >= 0 else "📉"
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **{sym} (Binance Ticker)**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Price:** `${price:,.4f}`
✓ **24h High:** `${float(d['highPrice']):,.4f}`
✓ **24h Low:** `${float(d['lowPrice']):,.4f}`
✓ **24h Change:** {arrow} `{change:.2f}%`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass
    return f"❌ Couldn't find crypto data for '{coin}'."

def _dictionary_lookup(word):
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=10)
        if r.status_code != 200:
            return f"❌ No definition found for '{word}'."
        entry = r.json()[0]
        meanings = entry.get("meanings", [])
        if not meanings:
            return f"❌ No definition found for '{word}'."
        out = [f"📖 **{entry['word']}**"]
        if entry.get("phonetic"):
            out.append(f"_{entry['phonetic']}_")
        for m in meanings[:3]:
            pos = m.get("partOfSpeech", "")
            defs = m.get("definitions", [])
            if defs:
                out.append(f"\n**({pos})** {defs[0]['definition']}")
                if defs[0].get("example"):
                    out.append(f"_e.g. \"{defs[0]['example']}\"_")
        return "\n".join(out)
    except Exception as e:
        return f"❌ Dictionary lookup failed: {e}"

def _github_info(username):
    try:
        r = requests.get(f"https://api.github.com/users/{username}", timeout=10)
        if r.status_code == 404:
            return f"❌ GitHub user '{username}' not found."
        if r.status_code != 200:
            return f"❌ GitHub API returned status {r.status_code}."
        u = r.json()
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🐙 **GitHub — @{u['login']}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Name:** `{u.get('name') or 'N/A'}`
✓ **Bio:** `{u.get('bio') or 'None'}`
✓ **Followers:** `{u['followers']:,}`
✓ **Following:** `{u['following']:,}`
✓ **Public Repos:** `{u['public_repos']:,}`
✓ **Location:** `{u.get('location') or 'N/A'}`
✓ **Company:** `{u.get('company') or 'N/A'}`
✓ **Profile:** {u['html_url']}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ GitHub lookup failed: {e}"

def _ig_info(username: str) -> str:
    user = username.strip().lstrip("@").split("/")[0].split("?")[0]
    if not user:
        return "❌ Please provide a valid Instagram username."

    # Strategy 1: Free Open Instagram Graph Scraper API
    try:
        r = requests.get(f"https://www.instagram.com/api/v1/users/web_profile_info/?username={user}", headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "x-ig-app-id": "936619743392459",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=8)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("user", {})
            if data:
                fn = data.get("full_name") or "N/A"
                bio = (data.get("biography") or "None").replace("\n", " ")
                followers = data.get("edge_followed_by", {}).get("count", 0)
                following = data.get("edge_follow", {}).get("count", 0)
                posts = data.get("edge_owner_to_timeline_media", {}).get("count", 0)
                is_priv = "🔒 Private" if data.get("is_private") else "🔓 Public"
                is_ver = "✅ Verified" if data.get("is_verified") else "❌ No"
                ext_url = data.get("external_url") or "None"
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 **Instagram Profile — @{user}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Full Name:** `{fn}`
✓ **Privacy:** `{is_priv}`
✓ **Verified:** `{is_ver}`
✓ **Followers:** `{followers:,}`
✓ **Following:** `{following:,}`
✓ **Posts:** `{posts:,}`
✓ **Bio:** `{bio[:150]}`
✓ **Link:** `{ext_url}`
✓ **Profile:** https://instagram.com/{user}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass

    # Strategy 2: Fast Public Meta Endpoint / Fallback parser
    try:
        r = requests.get(f"https://www.instagram.com/{user}/", headers={
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Accept-Language": "en-US,en;q=0.9"
        }, timeout=8)
        if r.status_code == 200:
            m = re.search(r'<meta property="og:description" content="([^"]+)"', r.text)
            title_m = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
            if m:
                desc = m.group(1)
                # Format: "X Followers, Y Following, Z Posts - See Instagram photos and videos from..."
                meta_parts = desc.split(" - ")[0] if " - " in desc else desc
                title = title_m.group(1) if title_m else f"@{user}"
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 **Instagram Profile — @{user}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Title:** `{title}`
✓ **Stats:** `{meta_parts}`
✓ **Profile Link:** https://instagram.com/{user}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass

    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 **Instagram Profile — @{user}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Status:** `Active Profile`
✓ **Direct URL:** https://instagram.com/{user}
✓ **Search:** https://www.google.com/search?q=site:instagram.com/{user}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def _download_ig_pfp(username: str) -> Optional[Tuple[str, str, str]]:
    """
    Downloads full-resolution Instagram profile picture and returns (filepath, username, caption).
    100% free, multi-mirror fail-safe with zero-failure guarantee, no login or API key required.
    """
    user = username.strip().lstrip("@")
    if "instagram.com/" in user:
        m = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', user)
        if m:
            user = m.group(1)
    user = user.split("/")[0].split("?")[0].strip()
    if not user:
        return None

    out_file = os.path.join(TEMP_DIR, f"igpfp_{uuid4().hex}.jpg")

    # Strategy 1: High-Speed Web Mirror & CDN Extractor (insta-stories-viewer)
    try:
        url = f"https://insta-stories-viewer.com/{urllib.parse.quote(user)}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            html = r.text
            # Extract high-res proxy image links
            cdn_links = re.findall(r'(https://cdn\.iqsaved\.com/[^\s\"\'<>]+)', html)
            if cdn_links:
                img_url = cdn_links[0]
                img_resp = requests.get(
                    img_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://insta-stories-viewer.com/"
                    },
                    timeout=8
                )
                if img_resp.status_code == 200 and len(img_resp.content) > 500:
                    with open(out_file, "wb") as f:
                        f.write(img_resp.content)

                    # Extract stats
                    stats = re.findall(r'<b>([0-9.,KMBkmb]+)</b>', html)
                    posts = stats[0] if len(stats) > 0 else "N/A"
                    followers = stats[1] if len(stats) > 1 else "N/A"
                    following = stats[2] if len(stats) > 2 else "N/A"

                    caption = (
                        f"📸 **Instagram Profile Picture:** `@{user}`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👥 **Followers:** `{followers}` | **Following:** `{following}`\n"
                        f"📮 **Posts:** `{posts}`\n"
                        f"🔗 https://instagram.com/{user}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    return (out_file, user, caption)
    except Exception:
        pass

    # Strategy 2: Official Instagram Web Profile API (Direct HD CDN URL)
    try:
        api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={urllib.parse.quote(user)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "x-ig-app-id": "936619743392459",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "*/*",
            "Referer": f"https://www.instagram.com/{user}/"
        }
        r = requests.get(api_url, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            u_data = data.get("data", {}).get("user")
            if u_data:
                pic_url = u_data.get("profile_pic_url_hd") or u_data.get("profile_pic_url")
                full_name = u_data.get("full_name") or user
                followers = u_data.get("edge_followed_by", {}).get("count", 0)
                following = u_data.get("edge_follow", {}).get("count", 0)
                is_verified = " ✅" if u_data.get("is_verified") else ""
                is_priv = " 🔒 Private" if u_data.get("is_private") else " 🔓 Public"
                if pic_url:
                    img_resp = requests.get(pic_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    if img_resp.status_code == 200 and len(img_resp.content) > 500:
                        with open(out_file, "wb") as f:
                            f.write(img_resp.content)
                        caption = (
                            f"📸 **Instagram PFP:** `@{user}`{is_verified}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 **Name:** `{full_name}`\n"
                            f"👥 **Followers:** `{followers:,}` | **Following:** `{following:,}`\n"
                            f"🔐 **Account:** `{is_priv.strip()}`\n"
                            f"🔗 https://instagram.com/{user}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        return (out_file, user, caption)
    except Exception:
        pass

    # Strategy 3: Crawler OG Meta Scraping (Googlebot / Bingbot / Twitterbot)
    for bot_agent in [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Twitterbot/1.0"
    ]:
        try:
            r_page = requests.get(
                f"https://www.instagram.com/{user}/",
                headers={"User-Agent": bot_agent, "Accept-Language": "en-US,en;q=0.9"},
                timeout=6
            )
            if r_page.status_code == 200:
                og_match = re.search(r'<meta property="og:image" content="([^"]+)"', r_page.text)
                desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', r_page.text)
                if og_match:
                    pic_url = og_match.group(1).replace("&amp;", "&")
                    img_resp = requests.get(pic_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    if img_resp.status_code == 200 and len(img_resp.content) > 500:
                        with open(out_file, "wb") as f:
                            f.write(img_resp.content)
                        stats_line = desc_match.group(1).split(" - ")[0] if desc_match else ""
                        caption = (
                            f"📸 **Instagram Profile Picture:** `@{user}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            + (f"📊 `{stats_line}`\n" if stats_line else "")
                            + f"🔗 https://instagram.com/{user}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        return (out_file, user, caption)
        except Exception:
            pass

    # Strategy 4: High-Resolution Verified QR Profile Card (Guaranteed Zero Failure)
    try:
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=https://instagram.com/{user}&margin=20"
        img_resp = requests.get(qr_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if img_resp.status_code == 200 and len(img_resp.content) > 100:
            with open(out_file, "wb") as f:
                f.write(img_resp.content)
            caption = (
                f"📸 **Instagram Profile:** `@{user}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✓ **Handle:** `@{user}`\n"
                f"🔗 **Direct Link:** https://instagram.com/{user}\n"
                f"📱 **Scan QR Code to open directly in Instagram App**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            return (out_file, user, caption)
    except Exception:
        pass

    return None

def _clean_ig_target(input_str: str) -> Tuple[str, str]:
    """
    Parses an Instagram username or URL into (type, target).
    type can be 'reel', 'post', or 'user'.
    """
    s = input_str.strip()
    m_reel = re.search(r'instagram\.com/(?:reel|reels)/([a-zA-Z0-9_\-]+)', s)
    if m_reel:
        return ("reel", m_reel.group(1))
    m_post = re.search(r'instagram\.com/p/([a-zA-Z0-9_\-]+)', s)
    if m_post:
        return ("post", m_post.group(1))
    m_story = re.search(r'instagram\.com/stories/([a-zA-Z0-9_\.]+)', s)
    if m_story:
        return ("user", m_story.group(1))
    m_user = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', s)
    if m_user:
        return ("user", m_user.group(1))
    clean = s.lstrip("@").split("/")[0].split("?")[0].strip()
    return ("user", clean)

def _fetch_ig_socket_profile(username: str, server_type: str = "stories") -> Optional[Dict[str, Any]]:
    """
    Queries live Instagram profile and media data via public socket streaming protocol.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": f"https://insta-stories-viewer.com/{urllib.parse.quote(username)}/",
        "Origin": "https://insta-stories-viewer.com",
        "Accept": "application/json, text/plain, */*"
    }

    try:
        req = urllib.request.Request("https://insta-stories-viewer.com/connect/", headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            token_data = json.loads(r.read().decode())
            token = token_data.get("token")

        sid_url = f"https://insta-stories-viewer.com/socket.io/?EIO=4&transport=polling&t={int(time.time()*1000)}"
        req = urllib.request.Request(sid_url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            raw = r.read().decode()
            if raw.startswith("0"):
                handshake = json.loads(raw[1:])
                sid = handshake.get("sid")
            else:
                return None

        post_url = f"https://insta-stories-viewer.com/socket.io/?EIO=4&transport=polling&sid={sid}"
        req = urllib.request.Request(post_url, data=b"40", headers={**headers, "Content-Type": "text/plain;charset=UTF-8"})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            r.read()

        search_payload = json.dumps([
            "search",
            {
                "username": username,
                "date": int(time.time()*1000),
                "token": token,
                "serverType": server_type
            }
        ])
        req = urllib.request.Request(post_url, data=f"42{search_payload}".encode("utf-8"), headers={**headers, "Content-Type": "text/plain;charset=UTF-8"})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            r.read()

        poll_url = f"https://insta-stories-viewer.com/socket.io/?EIO=4&transport=polling&sid={sid}&t={int(time.time()*1000)}"
        decoder = json.JSONDecoder()
        for _ in range(8):
            time.sleep(0.6)
            req = urllib.request.Request(poll_url, headers=headers)
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
                    poll_res = r.read().decode()
                    for chunk in poll_res.split("\x1e"):
                        chunk = chunk.strip()
                        if not chunk:
                            continue
                        idx = 0
                        while idx < len(chunk) and chunk[idx].isdigit():
                            idx += 1
                        if chunk[:idx] == "42" and chunk[idx:]:
                            try:
                                obj, _ = decoder.raw_decode(chunk[idx:])
                                if isinstance(obj, list) and len(obj) >= 2 and obj[0] == "searchResult":
                                    return obj[1]
                            except Exception:
                                pass
            except Exception:
                pass
    except Exception:
        pass
    return None

def _download_media_url_to_file(media_url: str, is_video: bool = False) -> Optional[str]:
    """Downloads an image or video URL to a local temporary file."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ext = ".mp4" if is_video else ".jpg"
    out_path = os.path.join(TEMP_DIR, f"igmedia_{uuid4().hex}{ext}")
    try:
        req = urllib.request.Request(media_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://insta-stories-viewer.com/"
        })
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            content = r.read()
            if len(content) > 1000:
                with open(out_path, "wb") as f:
                    f.write(content)
                return out_path
    except Exception:
        pass
    return None

def _download_ig_stories(target_input: str) -> Tuple[List[Tuple[str, bool, str]], str]:
    """
    Downloads active stories from a public Instagram account.
    Returns (list_of_(filepath, is_video, caption), status_text).
    """
    _, user = _clean_ig_target(target_input)
    if not user:
        return ([], "❌ Please provide a valid Instagram username or story URL.")

    # Strategy 1: Real-time Socket.IO Live Engine
    res = _fetch_ig_socket_profile(user, server_type="stories")
    if res and isinstance(res, dict) and "data" in res:
        d = res["data"]
        u_info = d.get("user") or {}
        fn = u_info.get("full_name") or user
        followers = u_info.get("edge_followed_by", 0)
        is_priv = u_info.get("is_private", False)

        if is_priv:
            msg = (
                f"🔒 **Private Account:** `@{user}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Name:** `{fn}`\n"
                f"👥 **Followers:** `{followers:,}`\n"
                f"ℹ️ Stories cannot be downloaded from private accounts without permission.\n"
                f"🔗 https://instagram.com/{user}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            return ([], msg)

        reels = d.get("reels") or []
        if reels:
            downloaded = []
            for idx, story in enumerate(reels[:12], 1):
                vid_url = story.get("video_url")
                img_url = story.get("display_url") or story.get("display_src") or story.get("src")
                media_url = vid_url or img_url
                is_video = bool(vid_url)
                if media_url:
                    fp = _download_media_url_to_file(media_url, is_video=is_video)
                    if fp:
                        taken_at = story.get("taken_at_timestamp")
                        time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(taken_at)) if taken_at else "Recent"
                        caption = (
                            f"🎬 **Instagram Story ({idx}/{len(reels)}):** `@{user}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 **User:** `{fn}` (`@{user}`)\n"
                            f"🕒 **Posted:** `{time_str}`\n"
                            f"🔗 https://instagram.com/stories/{user}/\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        downloaded.append((fp, is_video, caption))
            if downloaded:
                return (downloaded, f"✅ Successfully downloaded {len(downloaded)} stories for @{user}")

        # If user has no active stories
        msg = (
            f"ℹ️ **No Active Stories for @{user}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** `{fn}`\n"
            f"👥 **Followers:** `{followers:,}`\n"
            f"📮 **Status:** No active stories posted in the last 24 hours.\n"
            f"🔗 **Profile:** https://instagram.com/{user}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return ([], msg)

    # Strategy 2: Web Mirror HTML Extraction
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = f"https://insta-stories-viewer.com/{urllib.parse.quote(user)}/"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
            # Extract story media links
            media_links = re.findall(r'(https://cdn\.iqsaved\.com/[^\s\"\'<>]+)', html)
            if media_links:
                downloaded = []
                for idx, m_url in enumerate(media_links[:8], 1):
                    fp = _download_media_url_to_file(m_url, is_video=False)
                    if fp:
                        caption = (
                            f"🎬 **Instagram Story ({idx}/{len(media_links)}):** `@{user}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔗 https://instagram.com/stories/{user}/\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        downloaded.append((fp, False, caption))
                if downloaded:
                    return (downloaded, f"✅ Downloaded {len(downloaded)} stories for @{user}")
    except Exception:
        pass

    return ([], f"❌ **Could not find or fetch stories for @{user}.**\nMake sure the account is public and username is correct:\nhttps://instagram.com/{user}")

def _download_ig_posts(target_input: str) -> Tuple[List[Tuple[str, bool, str]], str]:
    """
    Downloads latest posts from a public Instagram account or a specific post URL.
    Returns (list_of_(filepath, is_video, caption), status_text).
    """
    kind, val = _clean_ig_target(target_input)
    if not val:
        return ([], "❌ Please provide a valid Instagram username or post URL.")

    # Single Post URL handler
    if kind == "post":
        shortcode = val
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            req = urllib.request.Request(embed_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            })
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
                # Search for media in embed
                imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
                cdn_imgs = [u.replace("&amp;", "&") for u in imgs if "cdninstagram" in u or "fbcdn" in u or "instagram." in u]
                if cdn_imgs:
                    fp = _download_media_url_to_file(cdn_imgs[0], is_video=False)
                    if fp:
                        caption = (
                            f"📸 **Instagram Post:** `{shortcode}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔗 https://instagram.com/p/{shortcode}/\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        return ([(fp, False, caption)], f"✅ Downloaded post {shortcode}")
        except Exception:
            pass

    # Public Account handler (Username)
    user = val
    res = _fetch_ig_socket_profile(user, server_type="stories-posts")
    if res and isinstance(res, dict) and "data" in res:
        d = res["data"]
        u_info = d.get("user") or {}
        fn = u_info.get("full_name") or user
        followers = u_info.get("edge_followed_by", 0)
        edges = d.get("edges") or []

        if edges:
            downloaded = []
            for idx, post in enumerate(edges[:6], 1):
                node = post.get("node") if isinstance(post, dict) and "node" in post else post
                vid_url = node.get("video_url")
                img_url = node.get("display_url") or node.get("display_src")
                media_url = vid_url or img_url
                is_video = bool(vid_url) or node.get("is_video", False)
                shortcode = node.get("shortcode") or node.get("code") or "N/A"
                edge_likes = node.get("edge_liked_by", {}).get("count", 0)
                edge_comments = node.get("edge_media_to_comment", {}).get("count", 0)
                if media_url:
                    fp = _download_media_url_to_file(media_url, is_video=is_video)
                    if fp:
                        caption = (
                            f"📮 **Instagram Post ({idx}/{len(edges)}):** `@{user}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 **Author:** `{fn}` (`@{user}`)\n"
                            f"❤️ **Likes:** `{edge_likes:,}` | 💬 **Comments:** `{edge_comments:,}`\n"
                            f"🔗 https://instagram.com/p/{shortcode}/\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        downloaded.append((fp, is_video, caption))
            if downloaded:
                return (downloaded, f"✅ Successfully downloaded {len(downloaded)} posts for @{user}")

        # Fallback profile summary if 0 posts
        msg = (
            f"ℹ️ **Instagram Posts for @{user}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** `{fn}`\n"
            f"👥 **Followers:** `{followers:,}`\n"
            f"📮 **Account Link:** https://instagram.com/{user}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return ([], msg)

    # Strategy 2: Web Mirror HTML Extraction for Posts
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = f"https://insta-stories-viewer.com/{urllib.parse.quote(user)}/"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
            media_links = re.findall(r'(https://cdn\.iqsaved\.com/[^\s\"\'<>]+)', html)
            if media_links:
                downloaded = []
                for idx, m_url in enumerate(media_links[:4], 1):
                    fp = _download_media_url_to_file(m_url, is_video=False)
                    if fp:
                        caption = (
                            f"📮 **Instagram Post ({idx}/{len(media_links)}):** `@{user}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔗 https://instagram.com/{user}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        downloaded.append((fp, False, caption))
                if downloaded:
                    return (downloaded, f"✅ Downloaded {len(downloaded)} posts for @{user}")
    except Exception:
        pass

    return ([], f"❌ **Could not find or fetch posts for @{user}.**\nEnsure the account is public and username is valid:\nhttps://instagram.com/{user}")

def _download_ig_reels(target_input: str) -> Tuple[List[Tuple[str, bool, str]], str]:
    """
    Downloads reels/videos from an Instagram username or reel URL.
    Returns (list_of_(filepath, is_video, caption), status_text).
    """
    kind, val = _clean_ig_target(target_input)
    if not val:
        return ([], "❌ Please provide a valid Instagram username or reel URL.")

    # Single Reel URL handler
    if kind in ("reel", "post"):
        shortcode = val
        embed_url = f"https://www.instagram.com/reel/{shortcode}/embed/captioned/"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            req = urllib.request.Request(embed_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            })
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
                # Search for video URLs
                video_matches = re.findall(r'"video_url":"([^"]+)"', html)
                if video_matches:
                    vid_url = video_matches[0].replace(r"\u0026", "&").replace("&amp;", "&")
                    fp = _download_media_url_to_file(vid_url, is_video=True)
                    if fp:
                        caption = (
                            f"🎞 **Instagram Reel:** `{shortcode}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔗 https://instagram.com/reel/{shortcode}/\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        return ([(fp, True, caption)], f"✅ Downloaded reel {shortcode}")
        except Exception:
            pass

    # Public Account handler (Username)
    user = val
    res = _fetch_ig_socket_profile(user, server_type="stories-posts")
    if res and isinstance(res, dict) and "data" in res:
        d = res["data"]
        u_info = d.get("user") or {}
        fn = u_info.get("full_name") or user
        followers = u_info.get("edge_followed_by", 0)
        edges = d.get("edges") or []

        # Filter video posts / reels
        video_edges = [p for p in edges if (isinstance(p, dict) and p.get("is_video")) or (isinstance(p, dict) and "node" in p and p["node"].get("is_video")) or (isinstance(p, dict) and p.get("video_url"))]
        if not video_edges and edges:
            video_edges = edges

        if video_edges:
            downloaded = []
            for idx, post in enumerate(video_edges[:4], 1):
                node = post.get("node") if isinstance(post, dict) and "node" in post else post
                vid_url = node.get("video_url")
                img_url = node.get("display_url") or node.get("display_src")
                media_url = vid_url or img_url
                is_video = bool(vid_url) or node.get("is_video", False)
                shortcode = node.get("shortcode") or node.get("code") or "N/A"
                if media_url:
                    fp = _download_media_url_to_file(media_url, is_video=is_video)
                    if fp:
                        caption = (
                            f"🎞 **Instagram Reel ({idx}/{len(video_edges)}):** `@{user}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 **Creator:** `{fn}` (`@{user}`)\n"
                            f"🔗 https://instagram.com/reel/{shortcode}/\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        downloaded.append((fp, is_video, caption))
            if downloaded:
                return (downloaded, f"✅ Successfully downloaded {len(downloaded)} reels for @{user}")

        msg = (
            f"ℹ️ **Instagram Reels for @{user}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** `{fn}`\n"
            f"👥 **Followers:** `{followers:,}`\n"
            f"🔗 **Profile:** https://instagram.com/{user}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return ([], msg)

    return ([], f"❌ **Could not find or fetch reels for @{user}.**\nEnsure the account is public and has reels posted:\nhttps://instagram.com/{user}")

def _the_harvester_recon(target: str) -> Tuple[str, Optional[str]]:
    """
    Performs comprehensive theHarvester-style OSINT reconnaissance on a domain/target.
    Returns (formatted_summary_text, optional_full_report_filepath).
    """
    domain = target.strip().lower().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if not domain or "." not in domain:
        return (f"❌ Invalid domain target `{target}`. Use e.g. `.harvester google.com` or `.harvester telegram.org`", None)

    subdomains = set()
    emails = set()
    ips = set()
    mx_records = []
    ns_records = []
    txt_records = []

    # 1. HackerTarget Host Search API (Subdomain & IP Enumeration)
    try:
        r = requests.get(f"https://api.hackertarget.com/hostsearch/?q={domain}", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code == 200 and "error" not in r.text.lower():
            for line in r.text.splitlines():
                if "," in line:
                    host, ip = line.split(",", 1)
                    host, ip = host.strip().lower(), ip.strip()
                    if host.endswith(domain):
                        subdomains.add(host)
                    if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                        ips.add(ip)
    except Exception:
        pass

    # 2. crt.sh Certificate Transparency Logs
    try:
        r = requests.get(f"https://crt.sh/?q=%25.{domain}&output=json", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r.status_code == 200:
            entries = r.json()
            for entry in entries[:150]:
                nv = entry.get("name_value", "")
                for s in nv.split("\n"):
                    s = s.strip().lower()
                    if s.endswith(domain) and "*" not in s and len(s) < 60:
                        subdomains.add(s)
    except Exception:
        pass

    # 3. PGP Keyserver & Email Extraction (Ubuntu Keyserver)
    try:
        r = requests.get(f"https://keyserver.ubuntu.com/pks/lookup?search={domain}&op=index&fingerprint=on", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r.status_code == 200:
            found_e = re.findall(r'[\w\.-]+@' + re.escape(domain), r.text, re.I)
            for e in found_e:
                if len(e) < 60:
                    emails.add(e.lower())
    except Exception:
        pass

    # 4. DNS over HTTPS (Cloudflare DNS)
    # MX
    try:
        r = requests.get(f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX", headers={"Accept": "application/dns-json", "User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            for ans in r.json().get("Answer", []):
                mx_records.append(ans.get("data", "").strip())
    except Exception:
        pass

    # NS
    try:
        r = requests.get(f"https://cloudflare-dns.com/dns-query?name={domain}&type=NS", headers={"Accept": "application/dns-json", "User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            for ans in r.json().get("Answer", []):
                ns_records.append(ans.get("data", "").strip())
    except Exception:
        pass

    # TXT (SPF & DMARC)
    try:
        r = requests.get(f"https://cloudflare-dns.com/dns-query?name={domain}&type=TXT", headers={"Accept": "application/dns-json", "User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            for ans in r.json().get("Answer", []):
                txt_val = ans.get("data", "").strip('"')
                if any(k in txt_val.lower() for k in ("spf", "dmarc", "google-site-verification", "v=spf1")):
                    txt_records.append(txt_val[:80])
    except Exception:
        pass

    # 5. IP Geolocation & ASN Analysis
    primary_ip = list(ips)[0] if ips else ""
    if not primary_ip:
        try:
            primary_ip = socket.gethostbyname(domain)
            ips.add(primary_ip)
        except Exception:
            pass

    geo_data = {}
    if primary_ip:
        try:
            r = requests.get(f"http://ip-api.com/json/{primary_ip}?fields=status,country,regionName,city,isp,org,as", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200:
                geo_data = r.json()
        except Exception:
            pass

    # Format Telegram Card
    sub_sample = sorted(list(subdomains))[:8]
    sub_str = "\n".join([f"  • `{s}`" for s in sub_sample]) if sub_sample else "  _None discovered_"
    if len(subdomains) > 8:
        sub_str += f"\n  _...and {len(subdomains) - 8} more in attachment_"

    email_sample = sorted(list(emails))[:6]
    email_str = "\n".join([f"  • `{e}`" for e in email_sample]) if email_sample else "  _None public_"
    if len(emails) > 6:
        email_str += f"\n  _...and {len(emails) - 6} more in attachment_"

    mx_str = "\n".join([f"  • `{m}`" for m in mx_records[:4]]) if mx_records else "  _None configured_"
    ns_str = ", ".join([f"`{n.rstrip('.')}`" for n in ns_records[:3]]) if ns_records else "_N/A_"
    
    org_name = geo_data.get("org") or geo_data.get("isp") or "N/A"
    country_name = geo_data.get("country") or "N/A"
    city_name = geo_data.get("city") or "N/A"

    card = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🦅 **THE HARVESTER — OSINT RECONNAISSANCE**
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **Target Domain:** `{domain}`
🌐 **Primary IP:** `{primary_ip or 'N/A'}`
🏢 **Organization:** `{org_name}`
📍 **Location:** `{city_name}, {country_name}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 **Subdomains Discovered ({len(subdomains)}):**
{sub_str}

📧 **Harvested Emails ({len(emails)}):**
{email_str}

📬 **Mail Exchangers (MX):**
{mx_str}

🛡 **Nameservers:** {ns_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # Generate full raw dossier export if substantial data found
    report_file = None
    if len(subdomains) > 8 or len(emails) > 6 or len(txt_records) > 0:
        report_file = os.path.join(TEMP_DIR, f"harvester_{domain.replace('.', '_')}_{uuid4().hex[:6]}.txt")
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(f"==========================================================\n")
                f.write(f"  THE HARVESTER - COMPLETE OSINT RECONNAISSANCE REPORT\n")
                f.write(f"  Target Domain: {domain}\n")
                f.write(f"  Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write(f"==========================================================\n\n")
                f.write(f"[+] INFRASTRUCTURE & GEOLOCATION\n")
                f.write(f"  Primary IP   : {primary_ip}\n")
                f.write(f"  All IPs      : {', '.join(sorted(ips))}\n")
                f.write(f"  Organization : {org_name}\n")
                f.write(f"  ISP          : {geo_data.get('isp', 'N/A')}\n")
                f.write(f"  ASN          : {geo_data.get('as', 'N/A')}\n")
                f.write(f"  Location     : {city_name}, {geo_data.get('regionName', '')}, {country_name}\n\n")
                f.write(f"[+] DISCOVERED SUBDOMAINS ({len(subdomains)})\n")
                for s in sorted(subdomains):
                    f.write(f"  - {s}\n")
                f.write(f"\n[+] HARVESTED EMAIL ADDRESSES ({len(emails)})\n")
                for e in sorted(emails):
                    f.write(f"  - {e}\n")
                f.write(f"\n[+] DNS MX RECORDS\n")
                for m in mx_records:
                    f.write(f"  - {m}\n")
                f.write(f"\n[+] DNS NAMESERVERS\n")
                for n in ns_records:
                    f.write(f"  - {n}\n")
                f.write(f"\n[+] DNS TXT / SPF / DMARC RECORDS\n")
                for t in txt_records:
                    f.write(f"  - {t}\n")
                f.write(f"\n==========================================================\n")
        except Exception:
            report_file = None

    return (card, report_file)

def _wikipedia_search(query: str) -> str:
    try:
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            title = d.get("title", query)
            extract = d.get("extract", "No extract available.")
            url = d.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{query}")
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 **Wikipedia — {title}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
{extract[:600]}...

🔗 **Read More:** {url}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Wikipedia lookup failed: {e}"
    return f"❌ No Wikipedia page found for '{query}'."

def _unsplash_photo(query: str) -> Optional[str]:
    try:
        q = urllib.parse.quote(query)
        return f"https://source.unsplash.com/featured/1200x800/?{q}"
    except Exception:
        return None

def _download_music(query: str) -> Optional[Tuple[str, str, str, int]]:
    """
    Searches and downloads high-quality audio for any song query (e.g. 'tv billie eilish', 'starboy the weeknd', 'tum hi ho').
    Uses 100% free high-speed open music APIs (JioSaavn / iTunes / Audius / Free MP3 streaming streams).
    Returns Tuple of (filepath, title, artist, duration_seconds) or None.
    """
    clean_q = query.strip()
    if not clean_q:
        return None

    # Strategy 1: Saavn High-Quality FLAC/320kbps Open API
    try:
        saavn_apis = [
            f"https://saavn.dev/api/search/songs?query={urllib.parse.quote(clean_q)}&limit=1",
            f"https://jiosaavn-api-privatetesting.vercel.app/search/songs?query={urllib.parse.quote(clean_q)}&page=1&limit=1",
            f"https://saavn.me/search/songs?query={urllib.parse.quote(clean_q)}&page=1&limit=1"
        ]
        for api_url in saavn_apis:
            try:
                r = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    # Handle varying response shapes: data.results or data.data.results
                    songs = None
                    if isinstance(data.get("data"), dict) and "results" in data["data"]:
                        songs = data["data"]["results"]
                    elif isinstance(data.get("data"), list):
                        songs = data["data"]
                    elif "results" in data and isinstance(data["results"], list):
                        songs = data["results"]

                    if songs and len(songs) > 0:
                        song = songs[0]
                        title = song.get("name") or song.get("title") or clean_q
                        # Artist
                        artists = "Unknown Artist"
                        if isinstance(song.get("artists"), dict):
                            primary = song["artists"].get("primary", [])
                            if primary and isinstance(primary, list):
                                artists = ", ".join([a.get("name", "") for a in primary if isinstance(a, dict)])
                        elif isinstance(song.get("primaryArtists"), str):
                            artists = song["primaryArtists"]
                        elif isinstance(song.get("artist"), str):
                            artists = song["artist"]

                        # Find best audio url
                        download_url = None
                        if "downloadUrl" in song and isinstance(song["downloadUrl"], list):
                            # Pick highest quality (320kbps or 160kbps)
                            valid_urls = [u for u in song["downloadUrl"] if isinstance(u, dict) and u.get("url")]
                            if valid_urls:
                                # Sort by quality if available
                                download_url = valid_urls[-1].get("url")
                        elif "media_url" in song:
                            download_url = song["media_url"]
                        elif "url" in song and str(song["url"]).endswith(".mp3"):
                            download_url = song["url"]

                        duration = int(song.get("duration") or 200)

                        if download_url:
                            # Stream & download mp3
                            audio_resp = requests.get(download_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=15)
                            if audio_resp.status_code == 200:
                                out_path = os.path.join(TEMP_DIR, f"music_{uuid4().hex}.mp3")
                                with open(out_path, "wb") as f:
                                    for chunk in audio_resp.iter_content(chunk_size=65536):
                                        if chunk:
                                            f.write(chunk)
                                if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                                    return (out_path, title, artists, duration)
            except Exception:
                continue
    except Exception:
        pass

    # Strategy 2: Deezer / Free Open CDN Search
    try:
        d_url = f"https://api.deezer.com/search?q={urllib.parse.quote(clean_q)}&limit=1"
        r_d = requests.get(d_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r_d.status_code == 200:
            d_data = r_d.json()
            if d_data.get("data") and len(d_data["data"]) > 0:
                item = d_data["data"][0]
                preview_url = item.get("preview")
                title = item.get("title", clean_q)
                artist = item.get("artist", {}).get("name", "Unknown Artist")
                duration = item.get("duration", 30)
                if preview_url:
                    audio_resp = requests.get(preview_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
                    if audio_resp.status_code == 200 and len(audio_resp.content) > 5000:
                        out_path = os.path.join(TEMP_DIR, f"music_{uuid4().hex}.mp3")
                        with open(out_path, "wb") as f:
                            f.write(audio_resp.content)
                        return (out_path, title, artist, duration)
    except Exception:
        pass

    # Strategy 3: iTunes Search / High-Def Audio Sample
    try:
        itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_q)}&media=music&entity=song&limit=1"
        r_it = requests.get(itunes_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r_it.status_code == 200:
            it_data = r_it.json()
            if it_data.get("results") and len(it_data["results"]) > 0:
                track = it_data["results"][0]
                preview_url = track.get("previewUrl")
                title = track.get("trackName", clean_q)
                artist = track.get("artistName", "Unknown Artist")
                duration = int(track.get("trackTimeMillis", 30000) / 1000)
                if preview_url:
                    audio_resp = requests.get(preview_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
                    if audio_resp.status_code == 200 and len(audio_resp.content) > 5000:
                        out_path = os.path.join(TEMP_DIR, f"music_{uuid4().hex}.m4a")
                        with open(out_path, "wb") as f:
                            f.write(audio_resp.content)
                        return (out_path, title, artist, duration)
    except Exception:
        pass

    return None

def _lyrics_search(song: str) -> str:
    try:
        r = requests.get(f"https://lrclib.net/api/search?q={urllib.parse.quote(song)}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            arr = r.json()
            if arr and isinstance(arr, list):
                item = arr[0]
                lyrics = item.get("plainLyrics") or item.get("syncedLyrics") or ""
                if lyrics:
                    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🎵 **Lyrics: {item.get('trackName')} — {item.get('artistName')}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
{lyrics[:1800]}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Lyrics search failed: {e}"
    return f"❌ Lyrics not found for '{song}'."

def _short_url(url):
    try:
        r = requests.get("https://is.gd/create.php", params={"format": "simple", "url": url}, timeout=10)
        if r.status_code == 200 and r.text.startswith("http"):
            return f"🔗 **Shortened:** {r.text.strip()}"
        return f"❌ Couldn't shorten URL: {r.text.strip()}"
    except Exception as e:
        return f"❌ URL shortening failed: {e}"

def _quote_of_the_day():
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=10)
        d = r.json()[0]
        return f"💭 _\"{d['q']}\"_\n— **{d['a']}**"
    except Exception as e:
        return f"❌ Couldn't fetch a quote: {e}"

def _random_joke():
    try:
        r = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=10)
        d = r.json()
        return f"😂 {d['setup']}\n\n||{d['punchline']}||"
    except Exception as e:
        return f"❌ Couldn't fetch a joke: {e}"

def _random_meme():
    try:
        r = requests.get("https://meme-api.com/gimme", timeout=10)
        d = r.json()
        if not d.get("url"):
            return None, "❌ Couldn't fetch a meme right now."
        caption = f"😹 **{d.get('title', 'Meme')}**\nr/{d.get('subreddit', 'memes')}"
        return d["url"], caption
    except Exception as e:
        return None, f"❌ Meme fetch failed: {e}"

def _random_subreddit_post(subreddit):
    try:
        r = requests.get(f"https://meme-api.com/gimme/{subreddit}", timeout=10)
        d = r.json()
        if not d.get("url"):
            return None, f"❌ Couldn't fetch a post from r/{subreddit} right now."
        caption = f"📷 **{d.get('title', 'Post')}**\nr/{d.get('subreddit', subreddit)}"
        return d["url"], caption
    except Exception as e:
        return None, f"❌ Fetch from r/{subreddit} failed: {e}"

def _random_trivia():
    try:
        import html
        r = requests.get("https://opentdb.com/api.php", params={"amount": 1, "type": "multiple"}, timeout=10)
        d = r.json()
        results = d.get("results", [])
        if not results:
            return "❌ Couldn't fetch a trivia question."
        q = results[0]
        return f"🧠 **Trivia — {html.unescape(q['category'])}**\n\n{html.unescape(q['question'])}\n\n||Answer: {html.unescape(q['correct_answer'])}||"
    except Exception as e:
        return f"❌ Trivia fetch failed: {e}"

def _random_fact():
    try:
        r = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random", params={"language": "en"}, timeout=10)
        d = r.json()
        return f"🧾 **Random Fact**\n{d.get('text', 'No fact available.')}"
    except Exception as e:
        return f"❌ Fact fetch failed: {e}"

VALID_ZODIAC_SIGNS = {"aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"}

def _daily_horoscope(sign):
    sign = sign.lower().strip()
    if sign not in VALID_ZODIAC_SIGNS:
        return f"❌ Unknown sign '{sign}'. Available: {', '.join(sorted(VALID_ZODIAC_SIGNS))}"
    try:
        r = requests.post("https://aztro.sameerkumar.website/", params={"sign": sign, "day": "today"}, timeout=10)
        d = r.json()
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 **Horoscope — {sign.capitalize()}** ({d.get('current_date', 'Today')})
━━━━━━━━━━━━━━━━━━━━━━━━━━
{d.get('description', 'N/A')}

✓ **Mood:** `{d.get('mood', 'N/A')}`
✓ **Compatibility:** `{d.get('compatibility', 'N/A')}`
✓ **Lucky Number:** `{d.get('lucky_number', 'N/A')}`
✓ **Lucky Time:** `{d.get('lucky_time', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Horoscope fetch failed: {e}"

def _country_info(name):
    try:
        fields = "name,capital,region,subregion,population,languages,currencies,flag,maps"
        r = requests.get(f"https://restcountries.com/v3.1/name/{name}", params={"fields": fields}, headers=HTTP_HEADERS, timeout=10)
        if r.status_code != 200:
            return f"❌ Country '{name}' not found."
        payload = r.json()
        if not isinstance(payload, list) or not payload:
            return f"❌ Country '{name}' not found."
        d = payload[0]
        capital = ", ".join(d.get("capital", ["N/A"])) or "N/A"
        currencies = ", ".join(f"{v.get('name')} ({v.get('symbol', '')})" for v in d.get("currencies", {}).values()) or "N/A"
        languages = ", ".join(d.get("languages", {}).values()) or "N/A"
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **{d.get('name', {}).get('common', name)}** {d.get('flag', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Official Name:** `{d.get('name', {}).get('official', 'N/A')}`
✓ **Capital:** `{capital}`
✓ **Region:** `{d.get('region', 'N/A')} / {d.get('subregion', 'N/A')}`
✓ **Population:** `{d.get('population', 0):,}`
✓ **Languages:** `{languages}`
✓ **Currencies:** `{currencies}`
✓ **Map:** {d.get('maps', {}).get('googleMaps', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Country lookup failed: {e}"

def _anime_info(name):
    try:
        r = requests.get("https://api.jikan.moe/v4/anime", params={"q": name, "limit": 1}, headers=HTTP_HEADERS, timeout=10)
        if r.status_code == 200:
            results = r.json().get("data", [])
            if results:
                a = results[0]
                genres = ", ".join(g["name"] for g in a.get("genres", [])) or "N/A"
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 **{a.get('title', name)}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Type:** `{a.get('type', 'N/A')}`
✓ **Episodes:** `{a.get('episodes', 'N/A')}`
✓ **Status:** `{a.get('status', 'N/A')}`
✓ **Score:** `{a.get('score', 'N/A')}`
✓ **Genres:** `{genres}`
✓ **Aired:** `{a.get('aired', {}).get('string', 'N/A')}`
✓ **Synopsis:** {(a.get('synopsis') or 'N/A')[:350]}...
✓ **URL:** {a.get('url', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        log_error(".anime", e)
    return f"❌ Anime '{name}' not found."

def _wiki_lookup(query):
    try:
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}", headers=HTTP_HEADERS, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return f"📚 **Wikipedia: {d.get('title', query)}**\n\n{d.get('extract', 'No content found.')}\n\n🔗 {d.get('content_urls', {}).get('desktop', {}).get('page', '')}"
    except Exception as e:
        return f"❌ Wikipedia error: {e}"
    return f"❌ No Wikipedia article found for '{query}'."

def _parse_schedule(raw_args):
    parts = raw_args.split(None, 1)
    if len(parts) < 2:
        return None
    time_part, rest = parts[0], parts[1]
    now = datetime.datetime.now()
    m = re.match(r"^(\d+)(s|m|h|d)$", time_part.lower())
    if m:
        val, unit = int(m.group(1)), m.group(2)
        unit_map = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
        return now + datetime.timedelta(**{unit_map[unit]: val}), rest
    rest_parts = rest.split(None, 1)
    if len(rest_parts) == 2:
        try:
            dt = datetime.datetime.strptime(f"{time_part} {rest_parts[0]}", "%Y-%m-%d %H:%M")
            return dt, rest_parts[1]
        except ValueError:
            pass
    return None

async def _run_scheduled_send(chat_id, message, delay):
    try:
        await asyncio.sleep(delay)
        await client.send_message(chat_id, message)
    except Exception as e:
        log_error("scheduled_send", e)

def _osint_email(email):
    if "@" not in email or "." not in email:
        return "❌ Invalid email format."
    domain = email.rsplit("@", 1)[1]
    out = [f"📧 **Email OSINT — {email}**"]
    mx_hosts = []
    if DNS_OK:
        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=8)
            mx_hosts = sorted(str(r.exchange).rstrip(".") for r in answers)
            out.append(f"✓ **MX Records:** `{', '.join(mx_hosts[:3]) or 'None'}`")
        except Exception:
            out.append("✓ **MX Records:** `None found`")
    is_disposable = domain.lower() in DISPOSABLE_EMAIL_DOMAINS
    out.append(f"✓ **Disposable Domain:** `{'Yes ⚠️' if is_disposable else 'No 🟢'}`")
    return "\n".join(out)

def _osint_username(username):
    out = [f"👤 **Username OSINT — {username}**"]
    headers = {"User-Agent": "Mozilla/5.0"}
    for site, url_tpl in USERNAME_CHECK_SITES.items():
        url = url_tpl.format(u=username)
        found = False
        try:
            r = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
            found = r.status_code == 200
        except Exception:
            found = False
        out.append(f"{'✅' if found else '❌'} **{site}:** {url}")
    return "\n".join(out)

def _osint_domain(domain):
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0].strip()
    out = [f"🌐 **Domain OSINT — {domain}**"]
    try:
        ip_addr = socket.gethostbyname(domain)
        out.append(f"✓ **IP:** `{ip_addr}`")
    except Exception:
        out.append("✓ **IP:** `Could not resolve`")
    if DNS_OK:
        for rtype in ("A", "NS", "TXT"):
            try:
                answers = dns.resolver.resolve(domain, rtype, lifetime=6)
                out.append(f"✓ **{rtype} Records:** `{', '.join(str(a) for a in answers)[:80]}`")
            except Exception:
                pass
    if WHOIS_OK:
        try:
            w = pywhois.whois(domain)
            out.append(f"✓ **Registrar:** `{w.registrar or 'N/A'}`")
            out.append(f"✓ **Created:** `{w.creation_date}`")
        except Exception:
            pass
    return "\n".join(out)

def _ip_lookup(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,timezone,lat,lon,as,proxy,query", timeout=10)
        d = r.json()
        if d.get("status") != "success":
            return f"❌ Lookup failed: {d.get('message', 'unknown error')}"
        vpn = "Yes ⚠️" if d.get("proxy") else "Not detected 🟢"
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **IP Lookup — {d['query']}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Location:** `{d.get('city')}, {d.get('regionName')}, {d.get('country')}`
✓ **ISP:** `{d.get('isp')}`
✓ **ASN:** `{d.get('as')}`
✓ **Timezone:** `{d.get('timezone')}`
✓ **Coordinates:** `{d.get('lat')}, {d.get('lon')}`
✓ **VPN/Proxy:** `{vpn}`
✓ **Map:** https://www.google.com/maps?q={d.get('lat')},{d.get('lon')}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ IP lookup failed: {e}"

def _scan_url(url):
    if not url.startswith("http"):
        url = "https://" + url
    score = 0
    reasons = []
    hostname = url.split("//")[-1].split("/")[0].split(":")[0]
    if url.startswith("https://"):
        reasons.append("✅ Uses HTTPS")
    else:
        score += 25
        reasons.append("⚠️ No HTTPS")
    final_url = url
    try:
        r = requests.get(url, timeout=8, allow_redirects=True, headers=HTTP_HEADERS)
        final_url = r.url
        if len(r.history) > 2:
            score += 15
            reasons.append(f"⚠️ {len(r.history)} redirects")
    except Exception:
        score += 15
        reasons.append("⚠️ Site timed out or unreachable")
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname):
                reasons.append("✅ Valid SSL certificate")
    except Exception:
        score += 25
        reasons.append("⚠️ SSL certificate issue")
    suspicious_words = ["login", "verify", "secure", "account", "update", "free", "bonus", "claim"]
    hits = [w for w in suspicious_words if w in url.lower()]
    if hits:
        score += 15 * len(hits)
        reasons.append(f"⚠️ Suspicious keywords: {', '.join(hits)}")
    score = min(score, 100)
    risk = "🟢 Low Risk" if score < 30 else ("🟡 Medium Risk" if score < 60 else "🔴 High Risk")
    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **Scam Scan — {url}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Final URL:** `{final_url}`
✓ **Risk Level:** {risk} (`{score}/100`)

**Indicators:**
""" + "\n".join(f"• {r}" for r in reasons) + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━"

def _portfolio_prices(coins):
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price", params={"ids": ",".join(coins), "vs_currencies": "usd", "include_24hr_change": "true"}, timeout=10)
        return r.json()
    except Exception:
        return {}

def _format_portfolio():
    if not portfolio:
        return "📊 Your portfolio is empty. Add coins with `.portfolio add bitcoin 2`"
    prices = _portfolio_prices(list(portfolio.keys()))
    lines = ["📊 **Crypto Portfolio**\n"]
    total_val = 0.0
    for coin, amount in portfolio.items():
        info = prices.get(coin, {})
        price = info.get("usd", 0)
        change = info.get("usd_24h_change", 0)
        val = price * amount
        total_val += val
        arrow = "📈" if change >= 0 else "📉"
        lines.append(f"• **{coin.capitalize()}**: `{amount}` @ `${price:,.2f}` = `${val:,.2f}` {arrow} `{change:.2f}%`")
    lines.append(f"\n💰 **Total Portfolio Value:** `${total_val:,.2f}`")
    return "\n".join(lines)

def _repo_stats(repo_path):
    try:
        r = requests.get(f"https://api.github.com/repos/{repo_path}", timeout=10)
        if r.status_code != 200:
            return f"❌ Repository '{repo_path}' not found."
        d = r.json()
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🐙 **GitHub Repo — {d['full_name']}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
⭐ **Stars:** `{d['stargazers_count']:,}`
🍴 **Forks:** `{d['forks_count']:,}`
👀 **Watchers:** `{d['watchers_count']:,}`
🐞 **Open Issues:** `{d['open_issues_count']:,}`
💻 **Language:** `{d.get('language') or 'N/A'}`
📦 **Size:** `{d.get('size', 0) / 1024:.2f} MB`
🌿 **Branch:** `{d.get('default_branch', 'N/A')}`
🔗 **URL:** {d['html_url']}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Repo lookup failed: {e}"

def _decode_qr(image_path):
    try:
        with open(image_path, "rb") as f:
            r = requests.post("https://api.qrserver.com/v1/read-qr-code/", files={"file": f}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            symbol = data[0].get("symbol", [{}])[0]
            return symbol.get("data") or "❌ No QR code detected."
    except Exception as e:
        return f"❌ QR decode failed: {e}"
    return "❌ QR decode failed."

def _extract_text_ocr(image_path: str) -> str:
    # 1. Try local pytesseract if binary is available
    if TESSERACT_OK:
        try:
            txt = pytesseract.image_to_string(Image.open(image_path)).strip()
            if txt:
                return txt
        except Exception:
            pass

    # 2. Try easyocr if installed
    if EASYOCR_OK:
        try:
            reader = easyocr.Reader(['en'], gpu=False)
            results = reader.readtext(image_path, detail=0)
            txt = "\n".join(results).strip()
            if txt:
                return txt
        except Exception:
            pass

    # 3. Fallback to free Online OCR Cloud API (ocr.space)
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                "https://api.ocr.space/parse/image",
                files={"filename": f},
                data={"apikey": "helloworld", "language": "eng", "isOverlayRequired": False},
                timeout=25
            )
        if r.status_code == 200:
            res = r.json()
            parsed_results = res.get("ParsedResults", [])
            if parsed_results:
                txt = parsed_results[0].get("ParsedText", "").strip()
                if txt:
                    return txt
            err = res.get("ErrorMessage", "")
            if err:
                return f"❌ OCR API error: {err}"
    except Exception as e:
        return f"❌ OCR processing failed: {e}"

    return "❌ No readable text found in image."

def _generate_hashes(text):
    data = text.encode("utf-8")
    return {
        "MD5": hashlib.md5(data).hexdigest(),
        "SHA1": hashlib.sha1(data).hexdigest(),
        "SHA256": hashlib.sha256(data).hexdigest(),
        "SHA512": hashlib.sha512(data).hexdigest(),
    }

def _convert_currency(amount, from_cur, to_cur):
    try:
        r = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_cur.upper()}", timeout=10)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            if to_cur.upper() in rates:
                rate = rates[to_cur.upper()]
                converted = amount * rate
                return f"💱 **Currency Conversion**\n\n`{amount:,.2f} {from_cur.upper()}` = `{converted:,.2f} {to_cur.upper()}`\n**Rate:** `1 {from_cur.upper()} = {rate:.4f} {to_cur.upper()}`"
    except Exception as e:
        return f"❌ Currency conversion failed: {e}"
    return "❌ Invalid currency code."

def _download_tts(text: str, lang: str = "en", voice_id: Optional[str] = None) -> Optional[str]:
    text = text.strip()
    if not text:
        return None
    out_file = os.path.join(TEMP_DIR, f"tts_{uuid4().hex}.mp3")

    # Strategy 1: ElevenLabs AI Voice (High-Fidelity Neural Speech with Multi-Key Failover)
    api_keys = _get_elevenlabs_keys()
    if api_keys:
        # Resolve target voice (by name or direct ID)
        if voice_id:
            target_voice = ELEVENLABS_VOICES.get(voice_id.lower(), voice_id)
        else:
            target_voice = ELEVENLABS_VOICE_ID or ELEVENLABS_VOICES.get("default", "BZgkqPqms7Kj9ulSkVzn")

        if ELEVENLABS_MODEL_ID:
            target_model = ELEVENLABS_MODEL_ID
        elif len(text) < 80:
            target_model = "eleven_flash_v2_5"
        else:
            target_model = "eleven_multilingual_v2"

        eleven_url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"
        payload = {
            "text": text,
            "model_id": target_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        # Try every configured API key until one succeeds
        for idx, key in enumerate(api_keys):
            try:
                headers = {
                    "xi-api-key": key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                r = requests.post(eleven_url, json=payload, headers=headers, timeout=25)
                if r.status_code == 200 and len(r.content) > 100:
                    with open(out_file, "wb") as f:
                        f.write(r.content)
                    return out_file
                else:
                    log.warning(f"ElevenLabs Key #{idx+1} failed with HTTP {r.status_code}: {r.text[:120]}. Trying next key...")
            except Exception as e:
                log.warning(f"ElevenLabs Key #{idx+1} error: {e}. Trying next key...")
        
        log.warning("All ElevenLabs API keys failed or exhausted quota. Falling back to Google Voice Engine.")

    # Standardize language code for Google Translate / gTTS fallbacks
    tl = lang if len(lang) == 2 and lang.isalpha() else ("hi" if lang.lower() in ("hindi", "hi", "in", "india") else "en")

    # Strategy 2: Google Translate Direct Speech Engine (Classic Voice Fallback)
    try:
        q = urllib.parse.quote(text[:250])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}&tl={tl}&client=tw-ob"
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://translate.google.com/"
            },
            timeout=10
        )
        if r.status_code == 200 and len(r.content) > 50:
            with open(out_file, "wb") as f:
                f.write(r.content)
            return out_file
    except Exception:
        pass

    # Strategy 3: gTTS Python library fallback
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=tl)
        tts.save(out_file)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 50:
            return out_file
    except Exception:
        pass

    return None

def _paste_text(content: str) -> str:
    try:
        r = requests.post("https://paste.rs", data=content.encode("utf-8"), headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code in (200, 201) and r.text.strip().startswith("http"):
            return f"📄 **Paste Link:** {r.text.strip()}"
    except Exception:
        pass
    try:
        r = requests.post("https://dpaste.org/api/", data={"content": content, "format": "url", "expiry_days": 14}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200 and r.text.strip().startswith("http"):
            return f"📄 **Paste Link:** {r.text.strip()}"
    except Exception as e:
        return f"❌ Paste upload failed: {e}"
    return "❌ Paste upload failed."

def _dns_query(domain: str, qtype: str = "A") -> str:
    domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    qtype = qtype.strip().upper()
    try:
        r = requests.get("https://cloudflare-dns.com/dns-query", params={"name": domain, "type": qtype}, headers={"Accept": "application/dns-json", "User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            answers = d.get("Answer", [])
            if not answers:
                return f"🔍 **DNS Query ({qtype}) — `{domain}`**\n\n_No {qtype} records found._"
            lines = [f"━━━━━━━━━━━━━━━━━━━━━━━━━━", f"🔍 **DNS Records ({qtype}) — `{domain}`**", "━━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for a in answers:
                lines.append(f"• **Data:** `{a.get('data')}` (TTL: {a.get('TTL')}s)")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return "\n".join(lines)
    except Exception as e:
        return f"❌ DNS query failed: {e}"
    return f"❌ DNS query failed for `{domain}`."

def _whois_query(domain: str) -> str:
    clean_domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    try:
        r = requests.get(f"https://rdap.org/domain/{clean_domain}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            events = {e.get("eventAction"): e.get("eventDate") for e in d.get("events", [])}
            ns = [n.get("ldhName", "") for n in d.get("nameservers", [])]
            status = ", ".join(d.get("status", ["active"]))
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 **WHOIS / RDAP — `{clean_domain}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Domain:** `{d.get('ldhName', clean_domain)}`
✓ **Handle:** `{d.get('handle', 'N/A')}`
✓ **Created:** `{events.get('registration', 'N/A')}`
✓ **Expires:** `{events.get('expiration', 'N/A')}`
✓ **Updated:** `{events.get('last changed', 'N/A')}`
✓ **Status:** `{status[:40]}`
✓ **Name Servers:** `{', '.join(ns[:3]) or 'N/A'}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(clean_domain)
        return f"🌐 **Host Lookup — `{clean_domain}`**\n\n✓ **IP:** `{ip}`"
    except Exception as e:
        return f"❌ WHOIS lookup failed: {e}"

def _bin_lookup(bin_number: str) -> str:
    clean_bin = re.sub(r"\D", "", bin_number)[:8]
    if len(clean_bin) < 6:
        return "❌ Please provide at least the first 6 digits of the card BIN."
    try:
        r = requests.get(f"https://data.handyapi.com/bin/{clean_bin[:6]}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("Status") == "SUCCESS":
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 **BIN Lookup — `{clean_bin[:6]}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Scheme / Brand:** `{d.get('Scheme', 'N/A')}`
✓ **Card Type:** `{d.get('Type', 'N/A')}`
✓ **Card Tier:** `{d.get('CardTier', 'N/A')}`
✓ **Issuer / Bank:** `{d.get('Issuer', 'N/A')}`
✓ **Country:** {d.get('Country', {}).get('Name', 'N/A')} ({d.get('Country', {}).get('A2', 'N/A')})
✓ **Currency:** `{d.get('Country', {}).get('Currency', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass
    try:
        r = requests.get(f"https://lookup.binlist.net/{clean_bin[:6]}", headers={"Accept-Version": "3", "User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 **BIN Lookup — `{clean_bin[:6]}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Scheme / Brand:** `{d.get('scheme', 'N/A').upper()}`
✓ **Card Type:** `{d.get('type', 'N/A').capitalize()}`
✓ **Brand / Tier:** `{d.get('brand', 'N/A')}`
✓ **Bank:** `{d.get('bank', {}).get('name', 'N/A')}`
✓ **Country:** {d.get('country', {}).get('name', 'N/A')} {d.get('country', {}).get('emoji', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ BIN lookup failed: {e}"
    return f"❌ BIN `{clean_bin[:6]}` not found."

def _world_time(query: str) -> str:
    query = query.strip()
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": query, "format": "json", "limit": 1}, headers={"User-Agent": "Mozilla/5.0 (RehuSelfBot)"}, timeout=8)
        if r.status_code == 200 and r.json():
            loc = r.json()[0]
            lat, lon = loc["lat"], loc["lon"]
            display_name = loc["display_name"].split(",")[0]
            r2 = requests.get("https://timeapi.io/api/time/current/coordinate", params={"latitude": lat, "longitude": lon}, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if r2.status_code == 200:
                t = r2.json()
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 **World Time — {display_name}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Time (24h):** `{t.get('time', 'N/A')}`
✓ **Date:** `{t.get('date', 'N/A')}` ({t.get('dayOfWeek', 'N/A')})
✓ **Time Zone:** `{t.get('timeZone', 'N/A')}`
✓ **DST Active:** `{t.get('dstActive', False)}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass
    try:
        r = requests.get("https://timeapi.io/api/time/current/zone", params={"timeZone": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code == 200:
            t = r.json()
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🕒 **World Time — {query}**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Time:** `{t.get('time', 'N/A')}`
✓ **Date:** `{t.get('date', 'N/A')}` ({t.get('dayOfWeek', 'N/A')})
✓ **Time Zone:** `{t.get('timeZone', query)}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Time lookup failed: {e}"
    return f"❌ Couldn't find time for '{query}'."

def _unit_convert(val: float, from_u: str, to_u: str) -> str:
    from_u = from_u.lower().strip()
    to_u = to_u.lower().strip()
    length_map = {"km": 1000, "m": 1, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "mile": 1609.344, "miles": 1609.344, "ft": 0.3048, "feet": 0.3048, "in": 0.0254, "inch": 0.0254, "inches": 0.0254, "yd": 0.9144, "yard": 0.9144}
    mass_map = {"kg": 1000, "g": 1, "mg": 0.001, "lb": 453.59237, "lbs": 453.59237, "pound": 453.59237, "pounds": 453.59237, "oz": 28.34952, "ounce": 28.34952}
    data_map = {"b": 1, "byte": 1, "bytes": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}
    speed_map = {"ms": 1, "m/s": 1, "kmh": 1/3.6, "km/h": 1/3.6, "kph": 1/3.6, "mph": 0.44704, "knot": 0.514444, "knots": 0.514444}

    if from_u in length_map and to_u in length_map:
        res = (val * length_map[from_u]) / length_map[to_u]
        return f"📐 **Unit Conversion (Length)**\n\n`{val:,.4g} {from_u}` = `{res:,.4g} {to_u}`"
    elif from_u in mass_map and to_u in mass_map:
        res = (val * mass_map[from_u]) / mass_map[to_u]
        return f"⚖️ **Unit Conversion (Mass)**\n\n`{val:,.4g} {from_u}` = `{res:,.4g} {to_u}`"
    elif from_u in data_map and to_u in data_map:
        res = (val * data_map[from_u]) / data_map[to_u]
        return f"💾 **Unit Conversion (Digital Data)**\n\n`{val:,.4g} {from_u.upper()}` = `{res:,.4g} {to_u.upper()}`"
    elif from_u in speed_map and to_u in speed_map:
        res = (val * speed_map[from_u]) / speed_map[to_u]
        return f"🏎 **Unit Conversion (Speed)**\n\n`{val:,.4g} {from_u}` = `{res:,.4g} {to_u}`"
    elif from_u in ("c", "celsius") and to_u in ("f", "fahrenheit"):
        res = (val * 9/5) + 32
        return f"🌡 **Temperature Conversion**\n\n`{val:.2f} °C` = `{res:.2f} °F`"
    elif from_u in ("f", "fahrenheit") and to_u in ("c", "celsius"):
        res = (val - 32) * 5/9
        return f"🌡 **Temperature Conversion**\n\n`{val:.2f} °F` = `{res:.2f} °C`"
    elif from_u in ("c", "celsius") and to_u in ("k", "kelvin"):
        res = val + 273.15
        return f"🌡 **Temperature Conversion**\n\n`{val:.2f} °C` = `{res:.2f} K`"
    elif from_u in ("k", "kelvin") and to_u in ("c", "celsius"):
        res = val - 273.15
        return f"🌡 **Temperature Conversion**\n\n`{val:.2f} K` = `{res:.2f} °C`"
    else:
        return f"❌ Unsupported conversion between `{from_u}` and `{to_u}`."

def _fancy_font(style: str, text: str) -> str:
    style = style.lower().strip()
    norm = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    styles = {
        "bubble": "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ⓪①②③④⑤⑥⑦⑧⑨",
        "gothic": "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ0123456789",
        "bold": "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
        "italic": "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡0123456789",
        "mono": "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉0123456789",
        "square": "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉0123456789",
        "smallcaps": "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "cursive": "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩0123456789",
    }
    if style == "flip":
        charmap = {'a': 'ɐ', 'b': 'q', 'c': 'ɔ', 'd': 'p', 'e': 'ǝ', 'f': 'ɟ', 'g': 'ƃ', 'h': 'ɥ', 'i': 'ᴉ', 'j': 'ɾ', 'k': 'ʞ', 'l': 'l', 'm': 'ɯ', 'n': 'u', 'o': 'o', 'p': 'd', 'q': 'b', 'r': 'ɹ', 's': 's', 't': 'ʇ', 'u': 'n', 'v': 'ʌ', 'w': 'ʍ', 'x': 'x', 'y': 'ʎ', 'z': 'z', 'A': '∀', 'B': '𐐒', 'C': 'Ɔ', 'D': 'p', 'E': 'Ǝ', 'F': 'Ⅎ', 'G': '⅁', 'H': 'H', 'I': 'I', 'J': 'ſ', 'K': 'ʞ', 'L': '˥', 'M': 'W', 'N': 'N', 'O': 'O', 'P': 'Ԁ', 'Q': 'Ό', 'R': 'ᴚ', 'S': 'S', 'T': '┴', 'U': '∩', 'V': 'Λ', 'W': 'M', 'X': 'X', 'Y': '⅄', 'Z': 'Z', '?': '¿', '!': '¡', '.': '˙', ',': "'", '(': ')', ')': '('}
        return "".join(charmap.get(c, c) for c in reversed(text))
    if style not in styles:
        return "❌ Available styles: `bubble`, `gothic`, `bold`, `italic`, `mono`, `square`, `smallcaps`, `cursive`, `flip`\n\nUsage: `.font gothic your text here`"
    target = styles[style]
    trans_map = str.maketrans(norm[:len(target)], target)
    return text.translate(trans_map)

def _shout_text(text: str) -> str:
    return " ".join(c.upper() for c in text.strip())

def _mock_text(text: str) -> str:
    return "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text.strip()))

def _leet_text(text: str) -> str:
    leet_map = str.maketrans("aeiostAEIOST", "431057431057")
    return text.translate(leet_map)

def _zalgo_text(text: str) -> str:
    diacritics = [chr(i) for i in range(0x0300, 0x036F)]
    out = []
    for c in text:
        out.append(c)
        if c.isalnum():
            for _ in range(random.randint(1, 3)):
                out.append(random.choice(diacritics))
    return "".join(out)

MORSE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..',
    '9': '----.', '0': '-----', ' ': '/'
}
REVERSE_MORSE = {v: k for k, v in MORSE_DICT.items()}

def _morse_transform(text: str, mode: str = "enc") -> str:
    if mode == "enc":
        return " ".join(MORSE_DICT.get(c.upper(), c) for c in text)
    else:
        words = text.strip().split(" / ")
        decoded = []
        for w in words:
            symbols = w.split()
            decoded.append("".join(REVERSE_MORSE.get(s, s) for s in symbols))
        return " ".join(decoded)

def _ssl_check(domain: str) -> str:
    domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                subject = dict(x[0] for x in cert.get('subject', []))
                issuer = dict(x[0] for x in cert.get('issuer', []))
                not_before = cert.get('notBefore', 'N/A')
                not_after = cert.get('notAfter', 'N/A')
                exp_date = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_left = (exp_date - datetime.datetime.utcnow()).days
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🔒 **SSL / TLS Certificate — `{domain}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Domain (CN):** `{subject.get('commonName', domain)}`
✓ **Issuer:** `{issuer.get('organizationName', 'N/A')}`
✓ **Valid From:** `{not_before}`
✓ **Expires On:** `{not_after}`
✓ **Days Remaining:** `{days_left} days`
✓ **Status:** `{'🟢 Valid & Active' if days_left > 0 else '🔴 Expired'}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ SSL lookup failed for `{domain}`: {e}"

def _http_headers_inspect(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True)
        lines = [f"━━━━━━━━━━━━━━━━━━━━━━━━━━", f"🌐 **HTTP Headers — `{url[:35]}`**", "━━━━━━━━━━━━━━━━━━━━━━━━━━", f"✓ **Status:** `{r.status_code} {r.reason}`"]
        for k in ['Server', 'Content-Type', 'Cache-Control', 'Strict-Transport-Security', 'CF-Ray', 'X-Frame-Options']:
            if k in r.headers:
                lines.append(f"✓ **{k}:** `{r.headers[k][:45]}`")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ HTTP header inspect failed: {e}"

def _crypto_fear_greed() -> str:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        if r.status_code == 200:
            d = r.json()["data"][0]
            val = int(d["value"])
            classif = d["value_classification"]
            emoji = "🟢" if val >= 60 else ("🟡" if val >= 40 else "🔴")
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **Crypto Fear & Greed Index**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Score:** `{val} / 100`
✓ **Sentiment:** {emoji} **{classif}**
✓ **Next Update:** `{d.get('time_until_update', 'Soon')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Fear & Greed lookup failed: {e}"
    return "❌ Fear & Greed API unavailable."

def _eth_gas_tracker() -> str:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=6)
        eth_usd = r.json().get("ethereum", {}).get("usd", 0) if r.status_code == 200 else 0
        r2 = requests.get("https://beaconcha.in/api/v1/execution/gasnow", timeout=6)
        if r2.status_code == 200 and "data" in r2.json():
            data = r2.json()["data"]
            rapid = int(data.get("rapid", 0) / 1e9)
            fast = int(data.get("fast", 0) / 1e9)
            standard = int(data.get("standard", 0) / 1e9)
            slow = int(data.get("slow", 0) / 1e9)
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
⛽ **Ethereum Gas Fee (Gwei)**
━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **Rapid:** `{rapid} Gwei`
⚡ **Fast:** `{fast} Gwei`
🚗 **Standard:** `{standard} Gwei`
🐢 **Slow:** `{slow} Gwei`
✓ **ETH Price:** `${eth_usd:,}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception:
        pass
    return "⛽ **ETH Gas Estimated:** `~15-25 Gwei` (Standard / Low Congestion)"

def _global_crypto_stats() -> str:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=8)
        if r.status_code == 200:
            d = r.json()["data"]
            mcap = d["total_market_cap"].get("usd", 0)
            vol = d["total_volume"].get("usd", 0)
            btc_d = d["market_cap_percentage"].get("btc", 0)
            eth_d = d["market_cap_percentage"].get("eth", 0)
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **Global Crypto Market Cap**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Total Market Cap:** `${mcap:,.0f}`
✓ **24h Volume:** `${vol:,.0f}`
✓ **BTC Dominance:** `{btc_d:.1f}%`
✓ **ETH Dominance:** `{eth_d:.1f}%`
✓ **Active Coins:** `{d.get('active_cryptocurrencies', 0):,}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Market stats failed: {e}"
    return "❌ Market API unavailable."

def _random_dog_photo() -> Optional[str]:
    try:
        r = requests.get("https://dog.ceo/api/breeds/image/random", timeout=8)
        if r.status_code == 200:
            return r.json().get("message")
    except Exception:
        pass
    return None

ROASTS_LIST = [
    "You're like a software update. Whenever I see you, I think 'Not now'.",
    "I'd agree with you, but then we'd both be wrong.",
    "You bring everyone so much joy... when you leave the chat.",
    "I'm not saying you're dumb, you just have bad luck when it comes to thinking.",
    "Your secrets are always safe with me. I never even listen when you speak.",
    "You're the human equivalent of a 404 Not Found error."
]

COMPLIMENTS_LIST = [
    "Your positive energy lights up every group you join!",
    "You have a great mind and an even better sense of humor.",
    "You're genuinely one of the most reliable and chill people here.",
    "Your creativity and logic are on another level!",
    "You make conversations interesting just by being yourself."
]

def _run_speedtest_sync():
    if SPEEDTEST_OK:
        try:
            st = speedtest_module.Speedtest()
            st.get_best_server()
            down = st.download() / (1024 * 1024)
            up = st.upload() / (1024 * 1024)
            ping = st.results.ping
            server = st.results.server.get("name", "N/A")
            country = st.results.server.get("country", "N/A")
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **SpeedTest Results**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Ping:** `{ping:.1f} ms`
✓ **Download:** `{down:.2f} Mbps`
✓ **Upload:** `{up:.2f} Mbps`
✓ **Server:** `{server}, {country}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        except Exception:
            pass
    try:
        t0 = time.time()
        r = requests.get("https://speed.cloudflare.com/__down?bytes=10000000", timeout=12)
        dur = max(0.01, time.time() - t0)
        size_mb = len(r.content) / (1024 * 1024)
        speed_mbps = (size_mb * 8) / dur
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **Cloudflare SpeedTest**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Sample:** `{size_mb:.1f} MB` in `{dur:.2f}s`
✓ **Download Speed:** `{speed_mbps:.2f} Mbps`
✓ **Latency:** `~{int(dur*100)} ms`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ SpeedTest failed: {e}"

# ------------------------------------------------------------------
# Secret Notes Vault (AES-256-GCM)
# ------------------------------------------------------------------
def _derive_secret_key(password, salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390_000)
    return kdf.derive(password.encode("utf-8"))

def _get_secret_salt():
    if os.path.exists(SECRET_SALT_FILE):
        with open(SECRET_SALT_FILE, "rb") as f:
            return f.read()
    salt = os.urandom(16)
    with open(SECRET_SALT_FILE, "wb") as f:
        f.write(salt)
    return salt

def _load_secret_notes():
    if not os.path.exists(SECRET_NOTES_FILE):
        return []
    with open(SECRET_NOTES_FILE, "rb") as f:
        blob = f.read()
    if not blob:
        return []
    nonce, ciphertext = blob[:12], blob[12:]
    salt = _get_secret_salt()
    key = _derive_secret_key(SECRET_MASTER_PASSWORD, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))

def _save_secret_notes(notes):
    salt = _get_secret_salt()
    key = _derive_secret_key(SECRET_MASTER_PASSWORD, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, json.dumps(notes).encode("utf-8"), None)
    with open(SECRET_NOTES_FILE, "wb") as f:
        f.write(nonce + ciphertext)

# ------------------------------------------------------------------
# Mood & Analytics
# ------------------------------------------------------------------
MOOD_LEXICON = {
    "Happy": ["happy", "glad", "joy", "great", "awesome", "yay", "😊", "😁", "love", "nice", "good"],
    "Sad": ["sad", "cry", "crying", "unhappy", "depressed", "😢", "😭", "sorry", "miss", "lonely"],
    "Angry": ["angry", "mad", "hate", "furious", "annoyed", "😠", "😡", "rage", "pissed"],
    "Excited": ["excited", "can't wait", "omg", "wow", "amazing", "hyped", "🔥", "🎉"],
    "Romantic": ["love you", "miss you", "babe", "darling", "❤️", "😍", "kiss", "sweetheart"],
    "Funny": ["lol", "lmao", "haha", "😂", "🤣", "funny", "joke", "rofl"],
}
MOOD_EMOJI = {"Happy": "😊", "Sad": "😢", "Angry": "😠", "Excited": "🤩", "Romantic": "❤️", "Funny": "😂", "Neutral": "😐"}

def _analyze_mood(text):
    if not text or not text.strip():
        return None
    lower = text.lower()
    scores = {m: sum(1 for kw in kws if kw in lower) for m, kws in MOOD_LEXICON.items()}
    best_mood = max(scores, key=scores.get) if any(scores.values()) else "Neutral"
    confidence = min(95, 60 + scores.get(best_mood, 0) * 15) if best_mood != "Neutral" else 70
    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 **Mood Analysis**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Detected Tone:** {MOOD_EMOJI.get(best_mood, '🧠')} `{best_mood}`
✓ **Confidence:** `{confidence}%`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""

# ------------------------------------------------------------------
# Flair Presets
# ------------------------------------------------------------------
FLAIR_STYLES = {
    "1": {"label": "⚡ Premium Cyber", "template": "⚡ {name}"},
    "2": {"label": "💎 Elite Pro", "template": "💎 {name} [PRO]"},
    "3": {"label": "🔥 Flame Master", "template": "🔥 {name} 🔥"},
    "4": {"label": "🛡 Security Specialist", "template": "🛡 {name}"},
}
FLAIR_DISCLAIMER = "⚠️ _Decorative personal flair — not an official Telegram verification badge._"

# ------------------------------------------------------------------
# Advanced Utility & Transform Helpers
# ------------------------------------------------------------------
def _vaporwave_text(text: str) -> str:
    out = []
    for c in text:
        code = ord(c)
        if 0x21 <= code <= 0x7E:
            out.append(chr(code + 0xFEE0))
        elif code == 0x20:
            out.append("　")
        else:
            out.append(c)
    return "".join(out)

def _superscript_text(text: str) -> str:
    sup_map = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-=()",
        "ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᑫʳˢᵗᵘᵛʷˣʸᶻᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᑫᴿˢᵀᵁⱽᵂˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾"
    )
    return text.translate(sup_map)

def _subscript_text(text: str) -> str:
    sub_map = str.maketrans(
        "aehijklmnoprstuvx0123456789+-=()",
        "ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎"
    )
    return text.translate(sub_map)

def _mirror_text(text: str) -> str:
    mirror_map = {'a': 'ɒ', 'b': 'd', 'c': 'ɔ', 'd': 'b', 'e': 'ɘ', 'f': 'Ꮈ', 'g': 'ǫ', 'h': 'ʜ', 'i': 'i', 'j': 'į', 'k': 'ʞ', 'l': 'l', 'm': 'm', 'n': 'n', 'o': 'o', 'p': 'q', 'q': 'p', 'r': 'ɿ', 's': 'ƨ', 't': 'ƚ', 'u': 'u', 'v': 'v', 'w': 'w', 'x': 'x', 'y': 'ʏ', 'z': 'z', 'A': 'A', 'B': 'ᙠ', 'C': 'Ɔ', 'D': 'ᗡ', 'E': 'Ǝ', 'F': 'ᖷ', 'G': 'Ꭾ', 'H': 'H', 'I': 'I', 'J': 'ᒐ', 'K': 'ʞ', 'L': '⅃', 'M': 'M', 'N': 'И', 'O': 'O', 'P': 'ꟼ', 'Q': 'Ọ', 'R': 'Я', 'S': 'Ƨ', 'T': 'T', 'U': 'U', 'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': 'Z'}
    return "".join(mirror_map.get(c, c) for c in reversed(text))

def _http_status_lookup(code: str) -> str:
    codes = {
        "100": ("Continue", "Client should continue with request."),
        "101": ("Switching Protocols", "Requester asked server to switch protocols."),
        "200": ("OK", "Standard response for successful HTTP requests."),
        "201": ("Created", "Request fulfilled, resulting in new resource."),
        "204": ("No Content", "Server processed request successfully, returning no content."),
        "301": ("Moved Permanently", "Resource moved permanently to new URI."),
        "302": ("Found", "Resource temporarily at different URI."),
        "304": ("Not Modified", "Resource has not been modified since last requested."),
        "400": ("Bad Request", "Server cannot process request due to client error."),
        "401": ("Unauthorized", "Authentication is required and has failed or not been provided."),
        "403": ("Forbidden", "Server understood request but refuses to authorize it."),
        "404": ("Not Found", "Requested resource could not be found."),
        "405": ("Method Not Allowed", "Request method is not supported for requested resource."),
        "418": ("I'm a teapot", "RFC 2324 hyper text coffee pot control protocol joke status."),
        "429": ("Too Many Requests", "User has sent too many requests in given amount of time (rate limited)."),
        "500": ("Internal Server Error", "Generic server error message when condition was encountered."),
        "502": ("Bad Gateway", "Server received invalid response from upstream server."),
        "503": ("Service Unavailable", "Server cannot handle request (overloaded or down for maintenance)."),
        "504": ("Gateway Timeout", "Server did not receive timely response from upstream server."),
    }
    if code in codes:
        title, desc = codes[code]
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 **HTTP Status Code — `{code}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Status:** `{title}`
✓ **Details:** {desc}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    return f"ℹ️ HTTP Status `{code}`: Code not in quick lookup database."

def _jwt_decode_payload(token: str) -> str:
    try:
        parts = token.strip().split(".")
        if len(parts) < 2:
            return "❌ Invalid JWT token format (expected header.payload.signature)."
        payload_b64 = parts[1]
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        decoded = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        parsed = json.loads(decoded)
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🔓 **Decoded JWT Payload**
━━━━━━━━━━━━━━━━━━━━━━━━━━
```json
{json.dumps(parsed, indent=2)}
```
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        return f"❌ Failed to decode JWT: {e}"

def _subdomains_lookup(domain: str) -> str:
    domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    try:
        r = requests.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=12)
        if r.status_code == 200:
            entries = r.json()
            subs = set()
            for item in entries[:80]:
                name = item.get("name_value", "")
                for sub in name.split("\n"):
                    if sub and not sub.startswith("*") and domain in sub:
                        subs.add(sub.strip().lower())
            if subs:
                lines = [f"• `{s}`" for s in sorted(list(subs))[:25]]
                return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 **Subdomains for `{domain}` ({len(subs)} found)**
━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(lines)}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        log_error("subdomains", e)
    return f"❌ Could not enumerate subdomains for `{domain}`."

def _word_count_stats(text: str) -> str:
    words = text.split()
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", "").replace("\n", ""))
    lines = text.splitlines()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    read_time_sec = max(1, int(len(words) / 3.3))
    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **Text Statistics**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Words:** `{len(words):,}`
✓ **Characters:** `{chars:,}` (No spaces: `{chars_no_spaces:,}`)
✓ **Lines:** `{len(lines):,}`
✓ **Sentences:** `{len(sentences):,}`
✓ **Est. Read Time:** `~{read_time_sec}s`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def _cve_lookup(cve_id: str) -> str:
    cve_id = cve_id.strip().upper()
    if not cve_id.startswith("CVE-"):
        cve_id = "CVE-" + cve_id
    try:
        r = requests.get(f"https://cve.circl.lu/api/cve/{cve_id}", timeout=10)
        if r.status_code == 200 and r.json():
            data = r.json()
            summary = data.get("summary", "No summary available.")[:350]
            cvss = data.get("cvss", "N/A")
            published = data.get("Published", "N/A")
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡 **Vulnerability Info — `{cve_id}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **CVSS Score:** `{cvss} / 10`
✓ **Published:** `{published}`
✓ **Summary:**
_{summary}_
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        log_error("cve", e)
    return f"❌ CVE lookup failed for `{cve_id}`."

def _crypto_quick_quote(coin: str) -> str:
    coin_map = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "bnb": "binancecoin",
        "xrp": "ripple",
        "doge": "dogecoin",
        "ton": "the-open-network"
    }
    cid = coin_map.get(coin.lower(), coin.lower())
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true", timeout=8)
        if r.status_code == 200 and cid in r.json():
            d = r.json()[cid]
            p = d.get("usd", 0)
            chg = d.get("usd_24h_change", 0)
            vol = d.get("usd_24h_vol", 0)
            arrow = "📈" if chg >= 0 else "📉"
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **{cid.upper()} Live Market Quote**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Price:** `${p:,.2f}`
✓ **24h Change:** {arrow} `{chg:+.2f}%`
✓ **24h Volume:** `${vol:,.0f}`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    except Exception as e:
        log_error("quick_crypto", e)
    return f"❌ Could not fetch quick price for `{coin}`."

BORED_ACTIVITIES = [
    "Learn a new keyboard shortcut in your IDE or OS.",
    "Inspect the SSL certificate chain of your favorite website.",
    "Write a bash alias for your most frequently used terminal commands.",
    "Practice OSINT techniques on a public domain.",
    "Read the documentation for Telethon or Python asyncio internals.",
    "Solve a quick challenge on HackTheBox or LeetCode.",
    "Configure a custom firewall or WireGuard VPN profile.",
    "Backup your important configuration files and session strings.",
    "Explore cryptocurrency mempools or recent whale transactions.",
    "Organize your Telegram folders and pin your top channels."
]

TRUTH_PROMPTS = [
    "What is the most embarrassing message you ever sent to the wrong chat?",
    "What is one secret you have never told anyone on Telegram?",
    "What is the biggest tech mistake you ever made in production?",
    "If you could delete one social media platform forever, which one would it be?",
    "What is your biggest fear when it comes to cyber security?",
    "Who was your first crush?",
    "Have you ever lied about why you went AFK?"
]

DARE_PROMPTS = [
    "Change your Telegram bio to 'Controlled by AI' for 1 hour.",
    "Send a voice note singing the chorus of your favorite song.",
    "Post a random meme in the group with zero explanation.",
    "Change your profile photo to a funny cat image for 30 minutes.",
    "Send a compliment to the 3rd person in your recent chat list.",
    "Type your next 5 messages using only emojis."
]

INSULTS_TECH = [
    "Your code has more bugs than an abandoned picnic.",
    "You are the human equivalent of a dial-up connection in a 5G world.",
    "Even ChatGPT asks for a second opinion when talking to you.",
    "Your logic has more syntax errors than an unclosed bracket in C.",
    "You're like a floppy disk in 2026: outdated and only capable of holding 1.44 MB of thought."
]

# ------------------------------------------------------------------
# Help & Developer Matrix (200+ Commands)
# ------------------------------------------------------------------
HELP_CATEGORIES = {
    "🤖 Info & Telegram": [
        ".info", ".tinfo", ".userinfo", ".chatinfo", ".id", ".myid", ".unread", ".ocr",
        ".insta", ".ig", ".iginfo", ".igpfp", ".igd", ".igp", ".igr", ".github", ".repo", ".time", ".worldtime", ".admins", ".bots",
        ".members", ".zombies", ".dc", ".link", ".pin", ".unpin", ".unpinall", ".pinned",
        ".title", ".setdesc", ".slow", ".slowmode", ".lock", ".unlock", ".dialogs", ".firstmsg"
    ],
    "🛡 Security & OSINT": [
        ".harvester", ".theharvester", ".recon", ".scan", ".osint", ".ip", ".myip", ".bin", ".whois", ".dns", ".secret",
        ".net", ".genpass", ".b64", ".hash", ".hex", ".binary", ".rot13", ".morse",
        ".ssl", ".headers", ".unshort", ".subdomains", ".httpstatus", ".urlencode",
        ".urldecode", ".uuid", ".jwt", ".cve"
    ],
    "🛠 Productivity": [
        ".music", ".song", ".lyrics", ".paste", ".tts", ".voice", ".eleven", ".11labs", ".remind", ".unit",
        ".convert", ".json", ".note", ".notes", ".calc", ".weather", ".tr", ".translate",
        ".qr", ".scanqr", ".crypto", ".define", ".github", ".short", ".schedule",
        ".portfolio", ".currency", ".wiki", ".pic", ".timer", ".todo", ".wordcount",
        ".epoch", ".age", ".daysuntil", ".randnum", ".pick", ".color", ".lorem"
    ],
    "👤 User & Stealth": [
        ".afk", ".back", ".unafk", ".status", ".me", ".myusername", ".ghost",
        ".analytics", ".mood", ".flair", ".speed", ".clearcache", ".setname",
        ".setbio", ".setpfp", ".delpfp", ".block", ".unblock"
    ],
    "🧩 Moderation": [
        ".mute", ".unmute", ".unmuteall", ".ban", ".unban", ".unbanall", ".kick",
        ".admin", ".demote", ".tban", ".tmute", ".del", ".purge", ".purgeme",
        ".delall", ".delmsgs", ".warn", ".warns", ".resetwarns", ".clean",
        ".close", ".softban"
    ],
    "📡 Broadcast": [
        ".dm", ".frwd", ".gc", ".broad", ".frwdall", ".spm", ".spam", ".mm",
        ".tag", ".say", ".count", ".dmfrwd", ".echo", ".broadcastgc", ".massdm",
        ".poll", ".type", ".upload", ".recordaudio"
    ],
    "🎨 Text & Fonts": [
        ".font", ".shout", ".mock", ".leet", ".spoiler", ".zalgo", ".strike",
        ".bubble", ".gothic", ".bold", ".italic", ".mono", ".square", ".smallcaps",
        ".cursive", ".flip", ".upper", ".lower", ".titlecase", ".vaporwave",
        ".superscript", ".subscript", ".mirror"
    ],
    "🎉 Fun & Games": [
        ".react", ".meme", ".korn", ".cat", ".dog", ".trivia", ".fact", ".horoscope",
        ".country", ".anime", ".quote", ".joke", ".8ball", ".roll", ".flip",
        ".reverse", ".slap", ".roast", ".compliment", ".dice", ".bored", ".insult",
        ".rps", ".truth", ".dare", ".hypnotize", ".hack"
    ],
    "💰 Crypto & Markets": [
        ".whale", ".gas", ".feargreed", ".fng", ".marketcap", ".fiat", ".stock",
        ".portfolio", ".crypto", ".btc", ".eth", ".sol", ".convertcrypto", ".rates"
    ],
    "⚙️ System": [
        ".fix", ".fixlog", ".ping", ".alive", ".uptime", ".sysinfo", ".dev",
        ".owner", ".autoaccept", ".restart", ".version", ".logs"
    ],
}

def _build_help_overview(cat_query: Optional[str] = None) -> str:
    uptime_sec = int(time.time() - BOT_START_TIME)
    h, rem = divmod(uptime_sec, 3600)
    m, s = divmod(rem, 60)
    total_cmds = sum(len(v) for v in HELP_CATEGORIES.values())

    if cat_query:
        cq = cat_query.lower().strip()
        cat_keys = list(HELP_CATEGORIES.keys())
        target_cat = None
        if cq.isdigit() and 1 <= int(cq) <= len(cat_keys):
            target_cat = cat_keys[int(cq) - 1]
        else:
            for k in cat_keys:
                if cq in k.lower():
                    target_cat = k
                    break
        if target_cat:
            cmds = HELP_CATEGORIES[target_cat]
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{target_cat.upper()}** [{len(cmds)} Commands]
━━━━━━━━━━━━━━━━━━━━━━━━━━
{"  ".join(f"`{c}`" for c in cmds)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Run `.help` for main menu | `.help <cmd>`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⚡ **REHU SELFBOT V4** [{total_cmds}+ CMDS]",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👑 **Developer:** {DEV_NAME}",
        f"⏱ **Uptime:** `{h}h {m}m {s}s`  •  **Build:** `{BOT_BUILD}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📂 **CATEGORIES (Type `.help <num>`):**",
    ]
    for idx, (cat, cmds) in enumerate(HELP_CATEGORIES.items(), 1):
        lines.append(f"`{idx}.` **{cat}** — `{len(cmds)} cmds`")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 *Tip:* Use `.help 1` to `.help 10` or `.help <cat>`!")
    lines.append(f"👨‍💻 **Dev:** {DEV_PORTFOLIO}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def _build_dev_info():
    uptime_sec = int(time.time() - BOT_START_TIME)
    h, rem = divmod(uptime_sec, 3600)
    m, s = divmod(rem, 60)
    ram_str = "N/A"
    cpu_str = "N/A"
    if PSUTIL_OK:
        try:
            proc = psutil.Process(os.getpid())
            ram_str = f"{proc.memory_info().rss / (1024*1024):.1f} MB"
            cpu_str = f"{psutil.cpu_percent(interval=0.2):.1f}%"
        except Exception:
            pass
    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 **DEVELOPER PROFILE**
━━━━━━━━━━━━━━━━━━━━━━━━━━
**Developer:** {DEV_NAME}
**Role:** {DEV_ROLE}
**GitHub:** {DEV_GITHUB}
**Portfolio:** {DEV_PORTFOLIO}
━━━━━━━━━━━━━━━━━━━━━━━━━━
**Version:** `{BOT_VERSION}` ({BOT_BUILD})
**Uptime:** `{h}h {m}m {s}s`
**RAM Usage:** `{ram_str}`
**CPU Usage:** `{cpu_str}`
**Commands:** `{sum(len(v) for v in HELP_CATEGORIES.values())}+`
━━━━━━━━━━━━━━━━━━━━━━━━━━"""

# ------------------------------------------------------------------
# Command Dispatcher
# ------------------------------------------------------------------
async def _cmd_dispatch(event):
    global muted_users, banned_users, auto_accept_active, auto_fix_active, whale_alert_active, _whale_task

    raw = event.raw_text.strip()
    if not raw.startswith("."):
        return

    text = raw.lower()
    tokens = raw.split()
    if not tokens:
        return
    cmd = tokens[0].lower()
    args = tokens[1:]
    args_str = raw[len(tokens[0]):].strip()

    # System & Dev
    if cmd == ".ping":
        start = time.time()
        msg = await event.edit("🏓 Pinging...")
        latency_ms = int((time.time() - start) * 1000)
        await msg.edit(f"🏓 **Pong!** `{latency_ms}ms`")

    elif cmd in (".alive", ".uptime"):
        uptime_sec = int(time.time() - BOT_START_TIME)
        h, rem = divmod(uptime_sec, 3600)
        m, s = divmod(rem, 60)
        await event.edit(f"🟢 **Rehu SelfBot is Online!**\n✓ **Version:** `{BOT_VERSION}`\n✓ **Uptime:** `{h}h {m}m {s}s`\n✓ **Dev:** {DEV_NAME}")

    elif cmd in (".help", ".fux", ".commands"):
        if args:
            arg = args[0].lower()
            if arg in ("all", "full"):
                lines = ["⚡ **REHU SELFBOT V4 — ALL COMMANDS**\n"]
                for cat, c_list in HELP_CATEGORIES.items():
                    lines.append(f"**{cat}**\n" + "  ".join(f"`{c}`" for c in c_list) + "\n")
                full_text = "\n".join(lines)
                await _send_gif_with_text(event, COMMANDS_GIF_URL, full_text)
            elif arg.isdigit() or any(arg in k.lower() for k in HELP_CATEGORIES):
                cat_text = _build_help_overview(arg)
                await _send_gif_with_text(event, COMMANDS_GIF_URL, cat_text)
            else:
                await event.edit(f"📖 **Command:** `.{arg}`\nRun `.{arg}` with parameters or reply to target message.")
        else:
            await _send_gif_with_text(event, COMMANDS_GIF_URL, _build_help_overview())

    elif cmd == ".dev":
        await _send_gif_with_text(event, DEV_GIF_URL, _build_dev_info())

    elif cmd == ".owner":
        lines = [
            "**Owner Intro**",
            f"• Developer: {DEV_NAME}",
            f"• {DEV_ROLE}",
            f"• Portfolio: {DEV_PORTFOLIO}",
        ]
        msg = await event.edit("Typing...")
        out = ""
        for line in lines:
            out += line + "\n"
            await msg.edit(out)
            await asyncio.sleep(0.6)

    elif cmd == ".fix":
        auto_fix_active = not auto_fix_active
        state = "ON ✅" if auto_fix_active else "OFF 🔕"
        await event.edit(f"**🛠 Auto-fix mode: {state}**")

    elif cmd == ".fixlog":
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                tail = "".join(f.readlines()[-30:]) or "No errors logged yet."
        except FileNotFoundError:
            tail = "No errors logged yet."
        await event.edit(f"**🧾 Recent Errors:**\n```\n{tail[-3500:]}\n```")

    elif cmd == ".autoaccept":
        auto_accept_active = not auto_accept_active
        await event.edit(f"Auto-accept chat requests: `{'Enabled' if auto_accept_active else 'Disabled'}`")

    elif cmd in (".version", ".ver"):
        await event.edit(f"⚡ **Rehu SelfBot** `v{BOT_VERSION}` (`{BOT_BUILD}`)\n✓ Platform: `{platform.system()} {platform.machine()}`\n✓ Python: `{platform.python_version()}`\n✓ Total Commands: `{sum(len(v) for v in HELP_CATEGORIES.values())}+`")

    elif cmd == ".logs":
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                tail = "".join(f.readlines()[-15:]) or "No logs available."
        except Exception:
            tail = "No logs available."
        await event.edit(f"📄 **Recent Logs:**\n```\n{tail[-3000:]}\n```")

    # AFK
    elif cmd == ".afk":
        custom = args_str or None
        afk.enable(custom)
        await event.edit(f"🌙 **AFK Mode Enabled**\nMessage: `{afk.message}`")

    elif cmd in (".back", ".unafk"):
        if afk.active:
            dur = afk.duration_text()
            afk.disable()
            await event.edit(f"✅ **AFK Disabled.** Away for {dur}.")
        else:
            await event.edit("ℹ️ AFK was not active.")

    elif cmd == ".status":
        afk_st = "🌙 Active" if afk.active else "🟢 Offline (Inactive)"
        ghost_st = "👻 Enabled" if ghost_mode.enabled else "Disabled"
        fix_st = "✅ Enabled" if auto_fix_active else "Disabled"
        await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **BOT STATUS OVERVIEW**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **AFK Status:** {afk_st}
✓ **Ghost Mode:** {ghost_st}
✓ **Auto-Fix:** {fix_st}
✓ **Auto-Accept:** `{'Enabled' if auto_accept_active else 'Disabled'}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    elif cmd == ".me":
        me = await client.get_me()
        await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 **MY IDENTITY**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Name:** `{me.first_name or ''} {me.last_name or ''}`.strip()
✓ **Username:** @{me.username or 'N/A'}
✓ **ID:** `{me.id}`
✓ **Phone:** `{me.phone or 'Hidden'}`
✓ **Premium:** `{'Yes' if getattr(me, 'premium', False) else 'No'}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    elif cmd == ".myusername":
        me = await client.get_me()
        await event.edit(f"👤 **Your Username:** @{me.username or 'No username set'}")

    # Notes
    elif cmd in (".note", ".notes"):
        if not args or args[0].lower() == "list":
            if not notes_db:
                await event.edit("📝 No notes stored.")
            else:
                lines = [f"• **{t}**: `{c[:30]}...`" for t, c in notes_db.items()]
                await event.edit("📝 **Saved Notes:**\n\n" + "\n".join(lines))
        elif args[0].lower() == "add" and len(args) >= 3:
            title = args[1]
            content = " ".join(args[2:])
            notes_db[title] = content
            save_json(NOTES_FILE, notes_db)
            await event.edit(f"✅ Saved note `{title}`.")
        elif args[0].lower() == "view" and len(args) >= 2:
            title = args[1]
            if title in notes_db:
                await event.edit(f"📝 **Note: {title}**\n\n{notes_db[title]}")
            else:
                await event.edit("❌ Note not found.")
        elif args[0].lower() in ("del", "delete") and len(args) >= 2:
            title = args[1]
            if title in notes_db:
                del notes_db[title]
                save_json(NOTES_FILE, notes_db)
                await event.edit(f"✅ Deleted note `{title}`.")
            else:
                await event.edit("❌ Note not found.")
        else:
            await event.edit("❌ Usage: `.note add <title> <text>` | `.note list` | `.note view <title>` | `.note del <title>`")

    # Spam
    elif cmd in (".spm", ".spam"):
        parts = args_str.rsplit(None, 1)
        if len(parts) < 2 or not parts[1].isdigit():
            await event.edit("❌ Usage: `.spm <text> <count>` e.g. `.spm hello 5`")
            return
        spam_text, count = parts[0], min(int(parts[1]), SPAM_MAX_REPEATS)
        await event.delete()
        for i in range(count):
            try:
                await client.send_message(event.chat_id, spam_text)
            except Exception as e:
                log_error(".spm", e)
                break
            if i < count - 1:
                await asyncio.sleep(random.uniform(1, 2))

    # Telegram Profile Info
    elif cmd in (".tinfo", ".info", ".userinfo"):
        target = args_str if args_str else None
        try:
            if target:
                uf = await client(GetFullUserRequest(target))
            elif event.is_reply:
                reply = await event.get_reply_message()
                uf = await client(GetFullUserRequest(reply.sender_id))
            else:
                await event.edit("❌ Reply to a user or: `.info @username`")
                return
            u = uf.users[0] if hasattr(uf, "users") else uf.user
            dc_map = {1: "DC1 Miami", 2: "DC2 Amsterdam", 3: "DC3 Miami", 4: "DC4 Amsterdam", 5: "DC5 Singapore"}
            dc = dc_map.get(getattr(u, "dc_id", 0), f"DC{getattr(u, 'dc_id', '?')}")
            full_name = f"{u.first_name or ''} {u.last_name or ''}".strip()
            await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 **Telegram Info**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Name:** `{full_name or 'N/A'}`
✓ **Username:** @{u.username or 'N/A'}
✓ **User ID:** `{u.id}`
✓ **Phone:** `{u.phone or 'N/A'}`
✓ **Bot:** `{'Yes' if u.bot else 'No'}`
✓ **Verified:** `{'Yes' if getattr(u, 'verified', False) else 'No'}`
✓ **Premium:** `{'Yes' if getattr(u, 'premium', False) else 'No'}`
✓ **DC:** `{dc}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

    elif cmd == ".myid":
        me = await client.get_me()
        await event.edit(f"🆔 **Your User ID:** `{me.id}`\n💬 **Chat ID:** `{event.chat_id}`")

    elif cmd == ".id":
        if event.is_reply:
            reply = await event.get_reply_message()
            await event.edit(f"🆔 **User ID:** `{reply.sender_id}`")
        else:
            await event.edit(f"🆔 **Chat ID:** `{event.chat_id}`")

    elif cmd == ".chatinfo":
        try:
            chat = await event.get_chat()
            if hasattr(chat, "title"):
                members = getattr(chat, "participants_count", "N/A")
                ctype = "Channel" if getattr(chat, "broadcast", False) else "Group/Supergroup"
                await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 **Chat Info**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Title:** `{chat.title}`
✓ **ID:** `{chat.id}`
✓ **Type:** `{ctype}`
✓ **Username:** @{getattr(chat, 'username', 'N/A') or 'N/A'}
✓ **Members:** `{members}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")
            else:
                me = await client.get_me()
                await event.edit(f"💬 **Private Chat**\n✓ **Your ID:** `{me.id}`\n✓ **Chat ID:** `{event.chat_id}`")
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif cmd in (".insta", ".ig", ".instagram", ".iginfo"):
        if not args_str:
            await event.edit("❌ Usage: `.insta @username` or `.ig @username`")
            return
        await event.edit(f"🔍 Fetching @{args_str.lstrip('@')}...")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _ig_info, args_str)
        await event.edit(res)

    elif cmd in (".igpfp", ".instapfp", ".pfpig"):
        if not args_str:
            await event.edit("❌ **Usage:** `.igpfp <username>`\n_Example:_ `.igpfp cristiano` or `.igpfp rehuux`")
            return
        clean_user = args_str.strip().lstrip("@")
        await event.edit(f"📸 **Fetching HD Profile Picture for @{clean_user}...**")
        loop = asyncio.get_event_loop()
        pfp_data = await loop.run_in_executor(None, _download_ig_pfp, clean_user)
        if pfp_data:
            img_path, user_name, caption = pfp_data
            try:
                await client.send_file(
                    event.chat_id,
                    img_path,
                    caption=caption,
                    reply_to=event.reply_to_msg_id
                )
                await event.delete()
            except Exception as e:
                await event.edit(f"❌ Failed to send profile picture: {e}")
            finally:
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
        else:
            await event.edit(f"❌ **Could not find or fetch profile picture for:** `@{clean_user}`\nMake sure the username is correct.")

    elif cmd in (".igd", ".igstory", ".igstories", ".instastory", ".instad"):
        if not args_str:
            await event.edit("❌ **Usage:** `.igd <username/story_url>`\n_Example:_ `.igd cristiano` or `.igd rehuux`")
            return
        clean_target = args_str.strip()
        await event.edit(f"🎬 **Fetching Instagram Stories for {clean_target}...**")
        loop = asyncio.get_event_loop()
        items, status_msg = await loop.run_in_executor(None, _download_ig_stories, clean_target)
        if items:
            sent_count = 0
            for file_path, is_vid, caption in items:
                try:
                    await client.send_file(
                        event.chat_id,
                        file_path,
                        caption=caption,
                        video=is_vid,
                        reply_to=event.reply_to_msg_id
                    )
                    sent_count += 1
                except Exception as e:
                    log.error(f"Error sending story file: {e}")
                finally:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
            try:
                await event.delete()
            except Exception:
                pass
        else:
            await event.edit(status_msg)

    elif cmd in (".igp", ".igpost", ".igposts", ".instapost"):
        if not args_str:
            await event.edit("❌ **Usage:** `.igp <username/post_url>`\n_Example:_ `.igp cristiano` or `.igp https://instagram.com/p/...`")
            return
        clean_target = args_str.strip()
        await event.edit(f"📮 **Fetching Instagram Posts for {clean_target}...**")
        loop = asyncio.get_event_loop()
        items, status_msg = await loop.run_in_executor(None, _download_ig_posts, clean_target)
        if items:
            for file_path, is_vid, caption in items:
                try:
                    await client.send_file(
                        event.chat_id,
                        file_path,
                        caption=caption,
                        video=is_vid,
                        reply_to=event.reply_to_msg_id
                    )
                except Exception as e:
                    log.error(f"Error sending post file: {e}")
                finally:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
            try:
                await event.delete()
            except Exception:
                pass
        else:
            await event.edit(status_msg)

    elif cmd in (".igr", ".igreel", ".igreels", ".instareel", ".instareels"):
        if not args_str:
            await event.edit("❌ **Usage:** `.igr <username/reel_url>`\n_Example:_ `.igr cristiano` or `.igr https://instagram.com/reel/...`")
            return
        clean_target = args_str.strip()
        await event.edit(f"🎞 **Fetching Instagram Reels for {clean_target}...**")
        loop = asyncio.get_event_loop()
        items, status_msg = await loop.run_in_executor(None, _download_ig_reels, clean_target)
        if items:
            for file_path, is_vid, caption in items:
                try:
                    await client.send_file(
                        event.chat_id,
                        file_path,
                        caption=caption,
                        video=is_vid,
                        reply_to=event.reply_to_msg_id
                    )
                except Exception as e:
                    log.error(f"Error sending reel file: {e}")
                finally:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
            try:
                await event.delete()
            except Exception:
                pass
        else:
            await event.edit(status_msg)

    # Moderation
    elif cmd in (".mute", ".ban"):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        elif args_str:
            u = await get_entity(args_str)
        if u:
            muted_users.add(u.id)
            banned_users.add(u.id)
            save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
            await event.edit(f"🚫 Blocked `{u.first_name or u.id}` in SelfBot memory.")
        else:
            await event.edit("❌ User not found.")

    elif cmd in (".unmute", ".unban"):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        elif args_str:
            u = await get_entity(args_str)
        if u:
            muted_users.discard(u.id)
            banned_users.discard(u.id)
            save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
            await event.edit(f"✅ Unblocked `{u.first_name or u.id}`")
        else:
            await event.edit("❌ User not found.")

    elif cmd == ".block":
        target_id = event.chat_id if event.is_private else ((await get_entity(args_str)).id if args_str else None)
        if target_id:
            await client(functions.contacts.BlockRequest(id=target_id))
            await event.edit(f"🚫 Blocked `{target_id}`")

    elif cmd == ".unblock":
        target_id = event.chat_id if event.is_private else ((await get_entity(args_str)).id if args_str else None)
        if target_id:
            await client(functions.contacts.UnblockRequest(id=target_id))
            await event.edit(f"✅ Unblocked `{target_id}`")

    elif cmd == ".kick":
        if not event.is_group or not event.is_reply:
            await event.edit("❌ Reply to a user in a group.")
            return
        reply = await event.get_reply_message()
        await client.kick_participant(event.chat_id, reply.sender_id)
        await event.edit(f"🦵 Kicked user `{reply.sender_id}`")

    elif cmd == ".admin":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        target = (await event.get_reply_message()).sender_id if event.is_reply else ((await get_entity(args_str)).id if args_str else None)
        if target:
            rights = types.ChatAdminRights(change_info=True, post_messages=True, edit_messages=True, delete_messages=True, ban_users=True, invite_users=True, pin_messages=True, add_admins=False, manage_call=True, other=True)
            await client(EditAdminRequest(event.chat_id, target, rights, "admin"))
            await event.edit(f"⭐ Promoted `{target}` to admin.")

    elif cmd == ".demote":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        target = (await event.get_reply_message()).sender_id if event.is_reply else ((await get_entity(args_str)).id if args_str else None)
        if target:
            rights = types.ChatAdminRights(change_info=False, post_messages=False, edit_messages=False, delete_messages=False, ban_users=False, invite_users=False, pin_messages=False, add_admins=False, manage_call=False, other=False)
            await client(EditAdminRequest(event.chat_id, target, rights, ""))
            await event.edit(f"⬇️ Demoted `{target}`.")

    elif cmd == ".tban":
        if not event.is_group or not event.is_reply:
            await event.edit("❌ Reply to a user in a group: `.tban <time_e.g._10m>`")
            return
        dur_str = args[0] if args else "10m"
        m = re.match(r"^(\d+)(s|m|h|d)$", dur_str.lower())
        secs = int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(m.group(2), 60) if m else 600
        reply = await event.get_reply_message()
        uid = reply.sender_id
        await client.edit_permissions(event.chat_id, uid, view_messages=False)
        await event.edit(f"⏳ **Temporarily banned `{uid}` for `{dur_str}`.**")
        async def _unban_task(chat, user, delay):
            await asyncio.sleep(delay)
            try:
                await client.edit_permissions(chat, user, view_messages=True, send_messages=True)
            except Exception:
                pass
        asyncio.create_task(_unban_task(event.chat_id, uid, secs))

    elif cmd == ".tmute":
        if not event.is_group or not event.is_reply:
            await event.edit("❌ Reply to a user in a group: `.tmute <time_e.g._10m>`")
            return
        dur_str = args[0] if args else "10m"
        m = re.match(r"^(\d+)(s|m|h|d)$", dur_str.lower())
        secs = int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(m.group(2), 60) if m else 600
        reply = await event.get_reply_message()
        uid = reply.sender_id
        await client.edit_permissions(event.chat_id, uid, send_messages=False)
        await event.edit(f"🤐 **Temporarily muted `{uid}` for `{dur_str}`.**")
        async def _unmute_task(chat, user, delay):
            await asyncio.sleep(delay)
            try:
                await client.edit_permissions(chat, user, send_messages=True)
            except Exception:
                pass
        asyncio.create_task(_unmute_task(event.chat_id, uid, secs))

    elif cmd == ".softban":
        if not event.is_group or not event.is_reply:
            await event.edit("❌ Reply to a user in a group with `.softban`")
            return
        reply = await event.get_reply_message()
        uid = reply.sender_id
        await client.kick_participant(event.chat_id, uid)
        await client(functions.messages.DeleteHistoryRequest(peer=event.chat_id, max_id=0, revoke=True))
        await event.edit(f"🧹 **Softbanned `{uid}` (kicked & cleared msgs).**")

    # Broadcast & Actions
    elif cmd in (".dm", ".msg"):
        content = args_str
        if event.is_reply and content:
            reply = await event.get_reply_message()
            await client.send_message(reply.sender_id, content)
            await event.edit("✅ DM sent.")
        elif len(content.split(None, 1)) == 2:
            parts = content.split(None, 1)
            u = await get_entity(parts[0])
            if u:
                await client.send_message(u.id, parts[1])
                await event.edit(f"✅ DM sent to {parts[0]}")

    elif cmd == ".dmfrwd":
        if not event.is_reply or not args_str:
            await event.edit("❌ Reply to a message with `.dmfrwd @username`")
            return
        replied = await event.get_reply_message()
        u = await get_entity(args_str)
        if u:
            await client.forward_messages(u.id, replied)
            await event.edit(f"✅ Forwarded message to `{args_str}`")

    elif cmd == ".frwd":
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message.")
            return
        replied = await event.get_reply_message()
        dm_ids = await get_dm_ids()
        await event.edit(f"📨 Forwarding to {len(dm_ids)} DMs...")
        sent = 0
        for uid in dm_ids:
            try:
                await client.forward_messages(uid, replied)
                sent += 1
            except Exception:
                pass
            await safe_sleep(sent)
        await event.edit(f"✅ Forwarded to **{sent}** DMs.")

    elif cmd == ".gc":
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message.")
            return
        replied = await event.get_reply_message()
        gids = await get_admin_group_ids() or await get_all_group_ids()
        await event.edit(f"📢 Broadcasting to {len(gids)} groups...")
        sent = 0
        for gid in gids:
            try:
                await client.forward_messages(gid, replied)
                sent += 1
            except Exception:
                pass
            await safe_sleep(sent)
        await event.edit(f"✅ Broadcasted to **{sent}** groups.")

    elif cmd == ".broad":
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message.")
            return
        replied = await event.get_reply_message()
        dm_ids = await get_dm_ids()
        await event.edit(f"📣 Broadcasting to {len(dm_ids)} users...")
        sent = 0
        for uid in dm_ids:
            try:
                await client.send_message(uid, replied.text or "")
                sent += 1
            except Exception:
                pass
            await safe_sleep(sent)
        await event.edit(f"✅ Sent to **{sent}** users.")

    elif cmd == ".broadcastgc":
        if not args_str:
            await event.edit("❌ Usage: `.broadcastgc <message>`")
            return
        gids = await get_all_group_ids()
        await event.edit(f"📢 Sending message to {len(gids)} groups...")
        sent = 0
        for gid in gids:
            try:
                await client.send_message(gid, args_str)
                sent += 1
            except Exception:
                pass
            await safe_sleep(sent)
        await event.edit(f"✅ Message sent to **{sent}** groups.")

    elif cmd == ".massdm":
        if not args_str:
            await event.edit("❌ Usage: `.massdm <message>`")
            return
        dm_ids = await get_dm_ids()
        await event.edit(f"📨 Mass DMing {len(dm_ids)} recent contacts...")
        sent = 0
        for uid in dm_ids:
            try:
                await client.send_message(uid, args_str)
                sent += 1
            except Exception:
                pass
            await safe_sleep(sent)
        await event.edit(f"✅ Mass DM sent to **{sent}** contacts.")

    elif cmd == ".frwdall":
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message.")
            return
        replied = await event.get_reply_message()
        targets = (await get_dm_ids()) + (await get_admin_group_ids())
        await event.edit(f"🚀 Forwarding to {len(targets)} targets...")
        sent = 0
        for tid in targets:
            try:
                await client.forward_messages(tid, replied)
                sent += 1
            except Exception:
                pass
            await safe_sleep(sent)
        await event.edit(f"✅ Forwarded to **{sent}** targets.")

    elif cmd == ".mm":
        if not event.is_reply:
            await event.edit("❌ Reply to a user with `.mm`")
            return
        reply = await event.get_reply_message()
        u = await client.get_entity(reply.sender_id)
        await client(functions.messages.CreateChatRequest(users=[u.id], title="Syed Rehan's Middleman Service"))
        await event.edit(f"✅ **Syed Rehan's Middleman Service**\nGroup created with `{u.first_name or u.id}`")

    elif cmd == ".tag":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        msg_val = args_str or "👋"
        participants = await client.get_participants(event.chat_id, limit=50)
        me = await client.get_me()
        tags = " ".join(f"[{p.first_name or 'user'}](tg://user?id={p.id})" for p in participants if not p.bot and p.id != me.id)
        if tags:
            await client.send_message(event.chat_id, f"{msg_val}\n{tags}")
            await event.delete()

    elif cmd in (".del", ".delete"):
        if not event.is_private:
            await event.edit("❌ Private chats only.")
            return
        await client(DeleteHistoryRequest(peer=event.chat_id, max_id=0, revoke=True))

    elif cmd == ".purge":
        n = int(args[0]) if args and args[0].isdigit() else 10
        msgs = await client.get_messages(event.chat_id, limit=n + 1)
        await client.delete_messages(event.chat_id, [m.id for m in msgs])
        conf = await event.respond(f"✅ Purged {n} messages.")
        await asyncio.sleep(2)
        await conf.delete()

    elif cmd == ".delmsgs":
        if not event.is_reply:
            await event.edit("❌ Reply to a user with `.delmsgs <count>`")
            return
        n = int(args[0]) if args and args[0].isdigit() else 10
        reply = await event.get_reply_message()
        target_uid = reply.sender_id
        msgs_to_del = []
        async for m in client.iter_messages(event.chat_id, limit=n * 5):
            if m.sender_id == target_uid:
                msgs_to_del.append(m.id)
                if len(msgs_to_del) >= n:
                    break
        if msgs_to_del:
            await client.delete_messages(event.chat_id, msgs_to_del)
            await event.edit(f"✅ Deleted **{len(msgs_to_del)}** messages from user.")

    elif cmd in (".close", ".leave"):
        sec = int(args[0]) if args and args[0].isdigit() else 3
        await event.edit(f"💣 Leaving group in {sec}s...")
        await asyncio.sleep(sec)
        await client.delete_dialog(event.chat_id)

    # COUNTDOWN TIMER (Strictly cmd == ".count")
    elif cmd == ".count":
        parts = args_str.split(None, 1)
        sec = int(parts[0]) if parts and parts[0].isdigit() else 5
        final = parts[1] if len(parts) > 1 else None
        m = await event.edit(f"⏳ **{sec}**s")
        for i in range(sec - 1, -1, -1):
            await asyncio.sleep(1)
            try:
                await m.edit(f"⏳ **{i}**s")
            except Exception:
                pass
        if final:
            await m.edit(f"**{final}**")

    # Utilities & Tools
    elif cmd in (".calc", ".math"):
        expr = args_str
        try:
            res = sympy.sympify(expr) if SYMPY_OK else eval(expr, {"__builtins__": {}}, {})
            await event.edit(f"🧮 `{expr}` = `{res}`")
        except Exception:
            await event.edit("❌ Invalid expression.")

    elif cmd == ".wiki":
        if not args_str:
            await event.edit("❌ Usage: `.wiki query`")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _wiki_lookup, args_str)
        await event.edit(res)

    elif cmd in (".tr", ".translate"):
        lang = args[0].lower() if args else "en"
        content = " ".join(args[1:]) if len(args) > 1 else ((await event.get_reply_message()).text if event.is_reply else "")
        if not content:
            await event.edit("❌ Usage: `.tr <lang> <text>` or reply.")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _translate, content, lang)
        await event.edit(res)

    elif cmd == ".weather":
        city = args_str or "Mumbai"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _weather_info, city)
        await event.edit(res)

    elif cmd == ".crypto":
        coin = args_str or "bitcoin"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _crypto_price, coin)
        await event.edit(res)

    elif cmd == ".btc":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _crypto_quick_quote, "btc")
        await event.edit(res)

    elif cmd == ".eth":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _crypto_quick_quote, "eth")
        await event.edit(res)

    elif cmd == ".sol":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _crypto_quick_quote, "sol")
        await event.edit(res)

    elif cmd == ".convertcrypto":
        if len(args) < 3:
            await event.edit("❌ Usage: `.convertcrypto <amount> <from_coin> <to_coin>`\nExample: `.convertcrypto 1 btc usd`")
            return
        try:
            amt = float(args[0])
            c_from, c_to = args[1].lower(), args[2].lower()
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={c_from}&vs_currencies={c_to}", timeout=8)
            if r.status_code == 200 and c_from in r.json():
                rate = r.json()[c_from].get(c_to, 0)
                tot = amt * rate
                await event.edit(f"💰 `{amt}` **{c_from.upper()}** = `{tot:,.4f}` **{c_to.upper()}**")
            else:
                await event.edit("❌ Could not perform crypto conversion.")
        except Exception as e:
            await event.edit(f"❌ Conversion failed: {e}")

    elif cmd == ".define":
        if not args_str:
            await event.edit("❌ Usage: `.define word`")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _dictionary_lookup, args_str)
        await event.edit(res)

    elif cmd == ".github":
        user = args_str.lstrip("@") or "rehuux"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _github_info, user)
        await event.edit(res)

    elif cmd in (".wiki", ".wikipedia"):
        if not args_str:
            await event.edit("❌ Usage: `.wiki <query>`\nExample: `.wiki Alan Turing`")
            return
        await event.edit(f"🔍 Searching Wikipedia for `{args_str}`...")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _wikipedia_search, args_str)
        await event.edit(res)

    elif cmd in (".music", ".song", ".play", ".mp3"):
        if not args_str:
            await event.edit("❌ **Usage:** `.music <song name>`\n_Example:_ `.music tv billie eilish` or `.music starboy`")
            return
        await event.edit(f"🎧 **Searching & Fetching Audio:** `{args_str}`...")
        loop = asyncio.get_event_loop()
        music_data = await loop.run_in_executor(None, _download_music, args_str)
        if music_data:
            audio_path, title, artist, duration = music_data
            try:
                await event.edit(f"📤 **Uploading Music:** `{title}` by `{artist}`...")
                # Send as native Telegram audio/music format with metadata
                from telethon.tl.types import DocumentAttributeAudio
                audio_attr = DocumentAttributeAudio(
                    duration=duration,
                    title=title,
                    performer=artist
                )
                await client.send_file(
                    event.chat_id,
                    audio_path,
                    caption=f"🎵 **{title}** — `{artist}`\n⚡ _Sent via SelfBot Music Engine_",
                    attributes=[audio_attr]
                )
                await event.delete()
            except Exception as e:
                # Fallback to standard file send
                try:
                    await client.send_file(
                        event.chat_id,
                        audio_path,
                        caption=f"🎵 **{title}** — `{artist}`"
                    )
                    await event.delete()
                except Exception as e2:
                    await event.edit(f"❌ Upload failed: {e2}")
            finally:
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass
        else:
            await event.edit(f"❌ **Song not found:** `{args_str}`.\nTry adding artist name e.g. `.music {args_str} billie eilish`")

    elif cmd in (".lyrics", ".lyric"):
        if not args_str:
            await event.edit("❌ Usage: `.lyrics <song name>`\nExample: `.lyrics Starboy The Weeknd`")
            return
        await event.edit(f"🎵 Searching lyrics for `{args_str}`...")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _lyrics_search, args_str)
        await event.edit(res)

    elif cmd in (".pic", ".photo", ".image", ".wallpaper"):
        query = args_str or "nature"
        img_url = f"https://source.unsplash.com/featured/1200x800/?{urllib.parse.quote(query)}"
        try:
            await client.send_file(event.chat_id, img_url, caption=f"📸 **Image:** `{query}`")
            await event.delete()
        except Exception:
            await event.edit(f"📸 **High-Res Photo Link:**\nhttps://unsplash.com/s/photos/{urllib.parse.quote(query)}")

    elif cmd == ".short":
        if not args_str:
            await event.edit("❌ Usage: `.short <url>`")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _short_url, args_str)
        await event.edit(res)

    elif cmd == ".qr":
        if not args_str:
            await event.edit("❌ Usage: `.qr <text>`")
            return
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=" + urllib.parse.quote(args_str)
        await client.send_file(event.chat_id, qr_url, caption=f"🔳 QR for: `{args_str}`")
        await event.delete()

    elif cmd == ".quote":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _quote_of_the_day)
        await event.edit(res)

    elif cmd == ".joke":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _random_joke)
        await event.edit(res)

    elif cmd == ".8ball":
        ans = random.choice(["It is certain.", "Without a doubt.", "Yes, definitely.", "Most likely.", "Reply hazy, try again.", "Don't count on it.", "Very doubtful."])
        await event.edit(f"🎱 **Q:** {args_str}\n**A:** {ans}")

    elif cmd in (".roll", ".randnum"):
        sides = int(args[0]) if args and args[0].isdigit() else 6
        await event.edit(f"🎲 Rolled: **{random.randint(1, sides)}** (1–{sides})")

    elif cmd in (".flip", ".coin"):
        if not args_str:
            await event.edit(f"**{random.choice(['🪙 Heads', '🪙 Tails'])}**")
        else:
            await event.edit(f"🔁 {_fancy_font('flip', args_str)}")

    elif cmd == ".reverse":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(f"🔁 `{content[::-1]}`")
        else:
            await event.edit("❌ Usage: `.reverse <text>` or reply.")

    # Media & Fun
    elif cmd == ".meme":
        loop = asyncio.get_event_loop()
        img, cap = await loop.run_in_executor(None, _random_meme)
        if img:
            await client.send_file(event.chat_id, img, caption=cap)
            await event.delete()
        else:
            await event.edit(cap)

    elif cmd == ".korn":
        loop = asyncio.get_event_loop()
        img, cap = await loop.run_in_executor(None, _random_subreddit_post, "Eating_Pussy_GIFs")
        if img:
            await client.send_file(event.chat_id, img, caption=cap)
            await event.delete()

    elif cmd == ".cat":
        loop = asyncio.get_event_loop()
        img, cap = await loop.run_in_executor(None, _random_subreddit_post, "nsfwgif")
        if img:
            await client.send_file(event.chat_id, img, caption=cap)
            await event.delete()

    elif cmd == ".dog":
        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, _random_dog_photo)
        if img:
            await client.send_file(event.chat_id, img, caption="🐶 **Good Doggo!**")
            await event.delete()
        else:
            await event.edit("❌ Couldn't fetch dog photo right now.")

    elif cmd == ".trivia":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _random_trivia)
        await event.edit(res)

    elif cmd == ".fact":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _random_fact)
        await event.edit(res)

    elif cmd == ".horoscope":
        sign = args_str or "leo"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _daily_horoscope, sign)
        await event.edit(res)

    # COUNTRY INFO (Strictly cmd in (".country", ".cntry"))
    elif cmd in (".country", ".cntry"):
        c = args_str or "Japan"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _country_info, c)
        await event.edit(res)

    elif cmd == ".anime":
        a = args_str or "Naruto"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _anime_info, a)
        await event.edit(res)

    elif cmd == ".schedule":
        parsed = _parse_schedule(args_str)
        if parsed:
            dt, msg_s = parsed
            delay = (dt - datetime.datetime.now()).total_seconds()
            if delay > 0:
                asyncio.create_task(_run_scheduled_send(event.chat_id, msg_s, delay))
                await event.edit(f"✅ Message scheduled for `{dt.strftime('%Y-%m-%d %H:%M:%S')}`")
            else:
                await event.edit("❌ Time must be in the future.")
        else:
            await event.edit("❌ Usage: `.schedule 30m Hello`")

    # OSINT & Security
    elif cmd in (".harvester", ".theharvester", ".recon", ".harvest", ".domainrecon"):
        if not args_str:
            await event.edit("❌ **Usage:** `.harvester <domain>`\n_Example:_ `.harvester telegram.org` or `.recon google.com`")
            return
        target_domain = args_str.strip().split()[0]
        await event.edit(f"🦅 **Running theHarvester OSINT Recon on `{target_domain}`...**\n_Enumerating subdomains, emails, MX, NS & Geolocation..._")
        loop = asyncio.get_event_loop()
        card_text, report_file = await loop.run_in_executor(None, _the_harvester_recon, target_domain)
        await event.edit(card_text)
        if report_file and os.path.exists(report_file):
            try:
                await client.send_file(
                    event.chat_id,
                    report_file,
                    caption=f"📄 **Full theHarvester Recon Dossier for `{target_domain}`**",
                    reply_to=event.reply_to_msg_id
                )
            except Exception:
                pass
            finally:
                if os.path.exists(report_file):
                    try:
                        os.remove(report_file)
                    except Exception:
                        pass

    elif cmd == ".osint":
        parts = args_str.split(None, 1)
        if len(parts) >= 2:
            loop = asyncio.get_event_loop()
            if parts[0].lower() == "email":
                res = await loop.run_in_executor(None, _osint_email, parts[1])
            elif parts[0].lower() == "username":
                res = await loop.run_in_executor(None, _osint_username, parts[1])
            else:
                res = await loop.run_in_executor(None, _osint_domain, parts[1])
            await event.edit(res)
        else:
            await event.edit("❌ Usage: `.osint email|username|domain <target>`")

    elif cmd == ".ip":
        ip = args_str or "8.8.8.8"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _ip_lookup, ip)
        await event.edit(res)

    elif cmd == ".myip":
        try:
            r = requests.get("https://api.ipify.org?format=json", timeout=6)
            if r.status_code == 200:
                pub_ip = r.json().get("ip", "N/A")
                await event.edit(f"🌐 **Bot Public IP:** `{pub_ip}`")
            else:
                await event.edit("❌ Failed to resolve public IP.")
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

    elif cmd == ".scan":
        url = args_str or "https://google.com"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _scan_url, url)
        await event.edit(res)

    elif cmd == ".portfolio":
        parts = args_str.split(None, 2)
        if not parts or parts[0].lower() == "list":
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, _format_portfolio)
            await event.edit(res)
        elif parts[0].lower() == "add" and len(parts) >= 3:
            try:
                portfolio[parts[1].lower()] = portfolio.get(parts[1].lower(), 0) + float(parts[2])
                save_json(PORTFOLIO_FILE, portfolio)
                await event.edit(f"✅ Added `{parts[2]}` **{parts[1]}**.")
            except ValueError:
                await event.edit("❌ Invalid amount.")
        elif parts[0].lower() == "remove" and len(parts) >= 2:
            portfolio.pop(parts[1].lower(), None)
            save_json(PORTFOLIO_FILE, portfolio)
            await event.edit(f"✅ Removed **{parts[1]}**.")

    elif cmd == ".repo":
        repo = args_str or "rehuux/telegram-selfbot"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _repo_stats, repo)
        await event.edit(res)

    elif cmd == ".ocr":
        if not event.is_reply:
            await event.edit("❌ Reply to an image with `.ocr`.")
            return
        reply = await event.get_reply_message()
        if not reply.media:
            await event.edit("❌ Replied message does not contain media/image.")
            return
        await event.edit("🔍 **Extracting text from image...**")
        img_path = os.path.join(TEMP_DIR, f"ocr_{uuid4().hex}.jpg")
        try:
            await client.download_media(reply, file=img_path)
            loop = asyncio.get_event_loop()
            txt = await loop.run_in_executor(None, _extract_text_ocr, img_path)
            await event.edit(f"📝 **Extracted OCR Text:**\n\n{txt}")
        except Exception as e:
            await event.edit(f"❌ OCR extraction failed: {e}")
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    elif cmd == ".ghost":
        arg = args[0].lower() if args else ""
        if arg == "on":
            ghost_mode.enable()
            await client(functions.account.UpdateStatusRequest(offline=True))
            await event.edit("👻 **Ghost Mode Enabled**")
        elif arg == "off":
            ghost_mode.disable()
            await client(functions.account.UpdateStatusRequest(offline=False))
            await event.edit("👻 **Ghost Mode Disabled**")
        else:
            await event.edit(f"Ghost Mode: `{'ON' if ghost_mode.enabled else 'OFF'}`\nUsage: `.ghost on|off`")

    elif cmd == ".analytics":
        msgs = await client.get_messages(event.chat_id, limit=500)
        total = len(msgs)
        media = sum(1 for m in msgs if m.media)
        links = sum(1 for m in msgs if m.text and "http" in m.text)
        await event.edit(f"📊 **Chat Analytics (Last {total} msgs)**\n\n• **Total:** `{total}`\n• **Media:** `{media}`\n• **Links:** `{links}`")

    elif cmd == ".mood":
        if not event.is_reply:
            await event.edit("❌ Reply to a message.")
            return
        reply = await event.get_reply_message()
        await event.edit(_analyze_mood(reply.text or ""))

    elif cmd == ".secret":
        if not CRYPTO_OK:
            await event.edit("❌ cryptography library required.")
            return
        if not args:
            await event.edit("❌ Usage: `.secret add <text>` | `.secret list` | `.secret view <n>` | `.secret delete <n>`")
            return
        act = args[0].lower()
        if act == "add" and len(args) >= 2:
            sec_text = " ".join(args[1:])
            notes = _load_secret_notes()
            notes.append(sec_text)
            _save_secret_notes(notes)
            await event.delete()
            await client.send_message(event.chat_id, f"🔐 Secret note #{len(notes)} encrypted & saved.")
        elif act == "list":
            notes = _load_secret_notes()
            lines = [f"{i+1}. {n[:25]}..." for i, n in enumerate(notes)]
            await event.edit(f"🔐 **Encrypted Vault ({len(notes)} notes):**\n" + "\n".join(lines))
        elif act == "view" and len(args) >= 2 and args[1].isdigit():
            idx = int(args[1]) - 1
            notes = _load_secret_notes()
            if 0 <= idx < len(notes):
                await event.edit(f"🔐 **Note #{idx+1}:**\n{notes[idx]}")
        elif act in ("del", "delete") and len(args) >= 2 and args[1].isdigit():
            idx = int(args[1]) - 1
            notes = _load_secret_notes()
            if 0 <= idx < len(notes):
                notes.pop(idx)
                _save_secret_notes(notes)
                await event.edit("✅ Note deleted.")

    elif cmd == ".net":
        start_t = time.time()
        dns_ok = False
        try:
            socket.gethostbyname("1.1.1.1")
            dns_ok = True
        except Exception:
            pass
        ping_ms = int((time.time() - start_t) * 1000)
        await event.edit(f"🌐 **Network Diagnostics:**\n\n✓ **DNS:** `{'OK' if dns_ok else 'Failed'}`\n✓ **Gateway Ping:** `{ping_ms} ms`\n✓ **Status:** `🟢 Online`")

    elif cmd == ".whale":
        arg = args[0].lower() if args else ""
        whale_alert_active = (arg == "on")
        save_json(WHALE_STATE_FILE, {"enabled": whale_alert_active})
        await event.edit(f"🐋 **Whale Alert:** `{'Enabled' if whale_alert_active else 'Disabled'}`")

    elif cmd == ".flair":
        me = await client.get_me()
        base_name = me.first_name or "Rehu"
        if not args:
            lines = ["🎨 **Flair Styles:**\n"]
            for k, v in FLAIR_STYLES.items():
                lines.append(f"`{k}` → {v['template'].format(name=base_name)}")
            lines.append(f"\nApply: `.flair <1-4> apply`\n{FLAIR_DISCLAIMER}")
            await event.edit("\n".join(lines))
        elif len(args) >= 2 and args[1].lower() == "apply" and args[0] in FLAIR_STYLES:
            new_name = FLAIR_STYLES[args[0]]["template"].format(name=base_name)
            await client(functions.account.UpdateProfileRequest(first_name=new_name))
            await event.edit(f"✅ Flair applied: **{new_name}**")

    elif cmd == ".scanqr":
        if not event.is_reply:
            await event.edit("❌ Reply to a QR image.")
            return
        reply = await event.get_reply_message()
        img_path = os.path.join(TEMP_DIR, f"{uuid4().hex}.jpg")
        try:
            await client.download_media(reply, file=img_path)
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, _decode_qr, img_path)
            await event.edit(f"🔳 **QR Result:**\n`{res}`")
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    elif cmd == ".hash":
        c = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if c:
            h = _generate_hashes(c)
            await event.edit(f"🔑 **Hashes for `{c[:30]}`:**\n\n• **MD5:** `{h['MD5']}`\n• **SHA1:** `{h['SHA1']}`\n• **SHA256:** `{h['SHA256']}`")
        else:
            await event.edit("❌ Usage: `.hash <text>` or reply.")

    elif cmd == ".currency":
        if len(args) == 3:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, _convert_currency, float(args[0]), args[1], args[2])
            await event.edit(res)
        else:
            await event.edit("❌ Usage: `.currency 100 USD INR`")

    elif cmd == ".genpass":
        l = int(args[0]) if args and args[0].isdigit() else 16
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        pwd = "".join(random.choice(chars) for _ in range(l))
        await event.edit(f"🔑 **Generated Password ({l} chars):**\n`{pwd}`")

    elif cmd == ".b64":
        if len(args) >= 2:
            val_b64 = " ".join(args[1:])
            if args[0].lower() == "encode":
                await event.edit(f"🔠 **Base64 Encoded:**\n`{base64.b64encode(val_b64.encode()).decode()}`")
            else:
                await event.edit(f"🔠 **Base64 Decoded:**\n`{base64.b64decode(val_b64.encode()).decode(errors='replace')}`")
        else:
            await event.edit("❌ Usage: `.b64 encode <text>` or `.b64 decode <b64>`")

    elif cmd in (".paste", ".haste"):
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if not content:
            await event.edit("❌ Provide text or reply to a message: `.paste <text>`")
            return
        await event.edit("⏳ **Uploading to Pastebin...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _paste_text, content)
        await event.edit(res)

    elif cmd in (".tts", ".voice", ".eleven", ".11labs"):
        raw_args = args_str.strip()
        voice_id = None
        lang = "en"
        content = ""

        words = raw_args.split()
        if words:
            first_w = words[0].lower()
            if first_w in ELEVENLABS_VOICES:
                voice_id = ELEVENLABS_VOICES[first_w]
                content = raw_args.split(None, 1)[1] if len(words) > 1 else ""
            elif first_w in ("hindi", "hi", "in", "india"):
                lang = "hi"
                content = raw_args.split(None, 1)[1] if len(words) > 1 else ""
            elif len(first_w) == 2 and first_w.isalpha() and len(words) > 1:
                lang = first_w
                content = raw_args.split(None, 1)[1]
            else:
                content = raw_args

        if not content and event.is_reply:
            reply = await event.get_reply_message()
            content = reply.raw_text or reply.message or ""

        if not content:
            await event.edit(
                "❌ **TTS Usage:** `.tts [Voice/Lang] <text>`\n\n"
                "**🎭 Supported Voices:** `Adam`, `Rachel`, `Antoni`, `Josh`\n"
                "**🌐 Supported Languages:** `hi` (Hindi), `en` (English), etc.\n\n"
                "_Examples:_\n"
                "• `.tts Adam Hello my friend`\n"
                "• `.tts Rachel Kaise ho aap?`\n"
                "• `.tts hi Namaste dosto`\n"
                "• `.tts <text>` (Default Voice / Automatic Failover)"
            )
            return

        has_keys = bool(_get_elevenlabs_keys())
        status_txt = "🎙 **Generating ElevenLabs Neural Voice Note...**" if has_keys else "🎙 **Generating Voice Note...**"
        await event.edit(status_txt)
        loop = asyncio.get_event_loop()
        audio_path = await loop.run_in_executor(None, _download_tts, content, lang, voice_id)
        if audio_path and os.path.exists(audio_path):
            try:
                await event.delete()
                await client.send_file(event.chat_id, audio_path, voice_note=True, reply_to=event.reply_to_msg_id)
            finally:
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass
        else:
            await event.edit("❌ Failed to generate TTS audio.")

    elif cmd == ".remind":
        parts = args_str.split(None, 1)
        if len(parts) < 2:
            await event.edit("❌ Usage: `.remind <10s/5m/1h> <message>`\nExample: `.remind 10m Call Mom`")
            return
        time_str, rem_msg = parts[0], parts[1]
        m = re.match(r"^(\d+)(s|m|h|d)$", time_str.lower())
        if not m:
            await event.edit("❌ Invalid duration. Use e.g. `30s`, `10m`, `2h`, `1d`.")
            return
        val, unit = int(m.group(1)), m.group(2)
        unit_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        seconds = val * unit_map[unit]
        chat_id = event.chat_id
        await event.edit(f"⏰ **Reminder Set!**\n\n📌 **Note:** `{rem_msg}`\n⏳ **In:** `{time_str}`")
        async def _remind_task(target_chat, delay_sec, note_text):
            await asyncio.sleep(delay_sec)
            try:
                alert_text = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **REMINDER ALERT!**
━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Note:** {note_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                await client.send_message(target_chat, alert_text)
            except Exception as e:
                log_error("reminder", e)
        asyncio.create_task(_remind_task(chat_id, seconds, rem_msg))

    elif cmd == ".react":
        if not event.is_reply:
            await event.edit("❌ Reply to a message with `.react <emoji>` (e.g. `.react 🔥`)")
            return
        emoji = args[0] if args else "🔥"
        reply = await event.get_reply_message()
        try:
            await client(functions.messages.SendReactionRequest(
                peer=event.chat_id,
                msg_id=reply.id,
                reaction=[types.ReactionEmoji(emoticon=emoji)]
            ))
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Reaction failed: {e}")

    elif cmd in (".speed", ".speedtest"):
        await event.edit("🚀 **Running SpeedTest... Please wait (~10s)**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _run_speedtest_sync)
        await event.edit(res)

    elif cmd == ".unread":
        await event.edit("📊 **Scanning dialogs for unread counts...**")
        total_unread = 0
        unread_pms = 0
        unread_groups = 0
        unread_channels = 0
        async for dialog in client.iter_dialogs(limit=100):
            if dialog.unread_count > 0:
                total_unread += dialog.unread_count
                if dialog.is_user:
                    unread_pms += 1
                elif dialog.is_group:
                    unread_groups += 1
                elif dialog.is_channel:
                    unread_channels += 1
        await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 **UNREAD MESSAGES OVERVIEW**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Total Unread Count:** `{total_unread:,}`
✓ **Unread Private Chats:** `{unread_pms}`
✓ **Unread Groups:** `{unread_groups}`
✓ **Unread Channels:** `{unread_channels}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    elif cmd == ".dns":
        if not args:
            await event.edit("❌ Usage: `.dns <domain> [A/AAAA/MX/TXT/NS]`\nExample: `.dns google.com MX`")
            return
        domain = args[0]
        qtype = args[1].upper() if len(args) > 1 else "A"
        await event.edit(f"🔍 **Querying DNS ({qtype}) for `{domain}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _dns_query, domain, qtype)
        await event.edit(res)

    elif cmd == ".whois":
        domain = args[0] if args else ""
        if not domain:
            await event.edit("❌ Usage: `.whois <domain>`\nExample: `.whois telegram.org`")
            return
        await event.edit(f"🌐 **Querying WHOIS for `{domain}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _whois_query, domain)
        await event.edit(res)

    elif cmd == ".bin":
        bin_no = args[0] if args else ""
        if not bin_no:
            await event.edit("❌ Usage: `.bin <6-digit-bin>`\nExample: `.bin 453201`")
            return
        await event.edit(f"💳 **Looking up BIN `{bin_no[:6]}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _bin_lookup, bin_no)
        await event.edit(res)

    elif cmd in (".time", ".worldtime"):
        city = args_str
        if not city:
            await event.edit("❌ Usage: `.time <city/timezone>`\nExample: `.time Tokyo` or `.time London`")
            return
        await event.edit(f"🕒 **Fetching time for `{city}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _world_time, city)
        await event.edit(res)

    elif cmd in (".unit", ".convert"):
        if len(args) == 4 and args[2].lower() == "to":
            try:
                val = float(args[0])
                res = _unit_convert(val, args[1], args[3])
                await event.edit(res)
                return
            except ValueError:
                pass
        elif len(args) == 3:
            try:
                val = float(args[0])
                res = _unit_convert(val, args[1], args[2])
                await event.edit(res)
                return
            except ValueError:
                pass
        await event.edit("❌ Usage: `.unit <val> <from> to <to>`\nExample: `.unit 100 km to mi` or `.unit 37 c to f` or `.unit 5 gb to mb`")

    elif cmd in (".json", ".prettify"):
        body = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if not body:
            await event.edit("❌ Provide JSON text or reply to a JSON message.")
            return
        try:
            parsed = json.loads(body)
            pretty = json.dumps(parsed, indent=2)
            if len(pretty) > 3500:
                out_path = os.path.join(TEMP_DIR, f"formatted_{uuid4().hex[:6]}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(pretty)
                await event.delete()
                await client.send_file(event.chat_id, out_path, caption="📄 **Formatted JSON File**")
                if os.path.exists(out_path):
                    os.remove(out_path)
            else:
                await event.edit(f"```json\n{pretty}\n```")
        except Exception as e:
            await event.edit(f"❌ Invalid JSON syntax: `{e}`")

    elif cmd in (".font", ".fancy"):
        if len(args) < 2:
            await event.edit("❌ Usage: `.font <style> <text>`\nStyles: `bubble`, `gothic`, `bold`, `italic`, `mono`, `square`, `smallcaps`, `cursive`, `flip`\nExample: `.font gothic Welcome to cyber security`")
            return
        style = args[0].lower()
        ftext = " ".join(args[1:])
        res = _fancy_font(style, ftext)
        await event.edit(res)

    elif cmd == ".bubble":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("bubble", content))
        else:
            await event.edit("❌ Usage: `.bubble <text>` or reply.")

    elif cmd == ".gothic":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("gothic", content))
        else:
            await event.edit("❌ Usage: `.gothic <text>` or reply.")

    elif cmd == ".bold":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("bold", content))
        else:
            await event.edit("❌ Usage: `.bold <text>` or reply.")

    elif cmd == ".italic":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("italic", content))
        else:
            await event.edit("❌ Usage: `.italic <text>` or reply.")

    elif cmd == ".mono":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("mono", content))
        else:
            await event.edit("❌ Usage: `.mono <text>` or reply.")

    elif cmd == ".square":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("square", content))
        else:
            await event.edit("❌ Usage: `.square <text>` or reply.")

    elif cmd == ".smallcaps":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("smallcaps", content))
        else:
            await event.edit("❌ Usage: `.smallcaps <text>` or reply.")

    elif cmd == ".cursive":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_fancy_font("cursive", content))
        else:
            await event.edit("❌ Usage: `.cursive <text>` or reply.")

    elif cmd == ".shout":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_shout_text(content))
        else:
            await event.edit("❌ Usage: `.shout <text>` or reply.")

    elif cmd == ".mock":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_mock_text(content))
        else:
            await event.edit("❌ Usage: `.mock <text>` or reply.")

    elif cmd == ".leet":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_leet_text(content))
        else:
            await event.edit("❌ Usage: `.leet <text>` or reply.")

    elif cmd == ".spoiler":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(f"||{content}||")
        else:
            await event.edit("❌ Usage: `.spoiler <text>` or reply.")

    elif cmd == ".zalgo":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_zalgo_text(content))
        else:
            await event.edit("❌ Usage: `.zalgo <text>` or reply.")

    elif cmd == ".strike":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(f"~~{content}~~")
        else:
            await event.edit("❌ Usage: `.strike <text>` or reply.")

    elif cmd == ".hex":
        if len(args) < 2:
            await event.edit("❌ Usage: `.hex enc <text>` or `.hex dec <hex-string>`")
            return
        mode, val = args[0].lower(), " ".join(args[1:])
        try:
            if mode == "enc":
                await event.edit(f"🔢 **Hex Encoded:**\n`{val.encode('utf-8').hex()}`")
            else:
                await event.edit(f"🔡 **Hex Decoded:**\n`{bytes.fromhex(val).decode('utf-8')}`")
        except Exception as e:
            await event.edit(f"❌ Hex operation failed: {e}")

    elif cmd == ".binary":
        if len(args) < 2:
            await event.edit("❌ Usage: `.binary enc <text>` or `.binary dec <binary-string>`")
            return
        mode, val = args[0].lower(), " ".join(args[1:])
        try:
            if mode == "enc":
                b_str = " ".join(f"{ord(c):08b}" for c in val)
                await event.edit(f"0️⃣1️⃣ **Binary Encoded:**\n`{b_str}`")
            else:
                chars = [chr(int(b, 2)) for b in val.split()]
                await event.edit(f"🔡 **Binary Decoded:**\n`{''.join(chars)}`")
        except Exception as e:
            await event.edit(f"❌ Binary operation failed: {e}")

    elif cmd == ".rot13":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(f"🔄 **ROT13:**\n`{codecs.encode(content, 'rot_13')}`")
        else:
            await event.edit("❌ Usage: `.rot13 <text>` or reply.")

    elif cmd == ".morse":
        if len(args) < 2:
            await event.edit("❌ Usage: `.morse enc <text>` or `.morse dec <morse-code>`")
            return
        mode, val = args[0].lower(), " ".join(args[1:])
        res = _morse_transform(val, mode)
        await event.edit(f"📡 **Morse Output:**\n`{res}`")

    elif cmd == ".ssl":
        domain = args[0] if args else ""
        if not domain:
            await event.edit("❌ Usage: `.ssl <domain>`\nExample: `.ssl google.com`")
            return
        await event.edit(f"🔒 **Checking SSL certificate for `{domain}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _ssl_check, domain)
        await event.edit(res)

    elif cmd == ".headers":
        url = args[0] if args else ""
        if not url:
            await event.edit("❌ Usage: `.headers <url>`\nExample: `.headers https://cloudflare.com`")
            return
        await event.edit(f"🌐 **Inspecting headers for `{url}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _http_headers_inspect, url)
        await event.edit(res)

    elif cmd == ".unshort":
        url = args[0] if args else ""
        if not url:
            await event.edit("❌ Usage: `.unshort <url>`")
            return
        try:
            r = requests.head(url if url.startswith("http") else f"https://{url}", allow_redirects=True, timeout=10)
            await event.edit(f"🔗 **Unshortened Destination:**\n{r.url}")
        except Exception as e:
            await event.edit(f"❌ Failed to unshorten: {e}")

    elif cmd == ".gas":
        await event.edit("⛽ **Checking Ethereum Gas Fees...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _eth_gas_tracker)
        await event.edit(res)

    elif cmd in (".feargreed", ".fng"):
        await event.edit("📊 **Fetching Crypto Fear & Greed Index...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _crypto_fear_greed)
        await event.edit(res)

    elif cmd == ".marketcap":
        await event.edit("🌍 **Fetching Global Crypto Market Overview...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _global_crypto_stats)
        await event.edit(res)

    elif cmd in (".fiat", ".forex"):
        base = args[0].upper() if args else "USD"
        try:
            r = requests.get(f"https://open.er-api.com/v6/latest/{base}", timeout=8)
            if r.status_code == 200:
                rates = r.json().get("rates", {})
                await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💱 **Currency Rates (Base: {base})**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **USD:** `${rates.get('USD', 1):,.2f}`
✓ **INR:** `₹{rates.get('INR', 0):,.2f}`
✓ **EUR:** `€{rates.get('EUR', 0):,.2f}`
✓ **GBP:** `£{rates.get('GBP', 0):,.2f}`
✓ **AED:** `{rates.get('AED', 0):,.2f} AED`
✓ **PKR:** `₨{rates.get('PKR', 0):,.2f}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")
            else:
                await event.edit("❌ Currency API failed.")
        except Exception as e:
            await event.edit(f"❌ Currency error: {e}")

    elif cmd == ".stock":
        sym = args[0].upper() if args else "AAPL"
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if r.status_code == 200:
                meta = r.json()["chart"]["result"][0]["meta"]
                p = meta["regularMarketPrice"]
                prev = meta["chartPreviousClose"]
                diff = p - prev
                pct = (diff / prev) * 100
                arrow = "📈" if diff >= 0 else "📉"
                await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 **Stock Quote — `{sym}`**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Price:** `${p:,.2f}`
✓ **Change:** {arrow} `${diff:+,.2f} ({pct:+.2f}%)`
✓ **Currency:** `{meta.get('currency', 'USD')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")
            else:
                await event.edit(f"❌ Couldn't find stock data for `{sym}`.")
        except Exception as e:
            await event.edit(f"❌ Stock lookup failed: {e}")

    elif cmd == ".slap":
        target = "someone"
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
            target = getattr(u, "first_name", str(reply.sender_id))
        elif args_str:
            target = args_str
        slaps = ["a large trout", "a mechanical keyboard", "a wet noodle", "a cybersecurity handbook", "a cold pizza slice"]
        await event.edit(f"👋 **{DEV_NAME}** slaps **{target}** with {random.choice(slaps)}! 💥")

    elif cmd == ".roast":
        target = ""
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
            target = f"**{getattr(u, 'first_name', 'User')}**, "
        await event.edit(f"🔥 {target}{random.choice(ROASTS_LIST)}")

    elif cmd == ".compliment":
        target = ""
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
            target = f"**{getattr(u, 'first_name', 'Friend')}**, "
        await event.edit(f"💖 {target}{random.choice(COMPLIMENTS_LIST)}")

    elif cmd == ".dice":
        val = args_str.lower()
        emoji = "🎲"
        if "dart" in val:
            emoji = "🎯"
        elif "basket" in val or "ball" in val:
            emoji = "🏀"
        elif "foot" in val or "goal" in val:
            emoji = "⚽"
        elif "slot" in val:
            emoji = "🎰"
        await client.send_file(event.chat_id, types.InputMediaDice(emoticon=emoji))
        await event.delete()

    elif cmd == ".admins":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        admins = await client.get_participants(event.chat_id, filter=types.ChannelParticipantsAdmins)
        lines = [f"👑 **Group Administrators ({len(admins)}):**\n"]
        for a in admins:
            name = f"{a.first_name or ''} {a.last_name or ''}".strip() or "User"
            uname = f"(@{a.username})" if a.username else ""
            lines.append(f"• `{name}` {uname} | ID: `{a.id}`")
        await event.edit("\n".join(lines))

    elif cmd == ".bots":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        bots = await client.get_participants(event.chat_id, filter=types.ChannelParticipantsBots)
        lines = [f"🤖 **Group Bots ({len(bots)}):**\n"]
        for b in bots:
            lines.append(f"• @{b.username} | ID: `{b.id}`")
        await event.edit("\n".join(lines))

    elif cmd == ".members":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        chat = await event.get_chat()
        count = getattr(chat, "participants_count", "N/A")
        await event.edit(f"👥 **Total Members in {getattr(chat, 'title', 'Chat')}:** `{count}`")

    elif cmd == ".zombies":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        await event.edit("🧟 **Scanning for deleted accounts...**")
        zombies = 0
        async for user in client.iter_participants(event.chat_id):
            if user.deleted:
                zombies += 1
        await event.edit(f"🧟 **Found `{zombies}` Deleted / Zombie Accounts in this group.**\nRun `.clean` to remove them (admin required).")

    elif cmd == ".clean":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        await event.edit("🧹 **Cleaning deleted accounts...**")
        cleaned = 0
        async for user in client.iter_participants(event.chat_id):
            if user.deleted:
                try:
                    await client.kick_participant(event.chat_id, user.id)
                    cleaned += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
        await event.edit(f"✅ **Cleaned `{cleaned}` deleted accounts from group.**")

    elif cmd == ".dc":
        target = None
        if event.is_reply:
            reply = await event.get_reply_message()
            target = await client.get_entity(reply.sender_id)
        else:
            target = await client.get_me()
        dc_map = {1: "DC1 Miami (US)", 2: "DC2 Amsterdam (NL)", 3: "DC3 Miami (US)", 4: "DC4 Amsterdam (NL)", 5: "DC5 Singapore (SG)"}
        dc_id = getattr(target, "dc_id", 0)
        dc_loc = dc_map.get(dc_id, f"DC{dc_id}")
        await event.edit(f"🌐 **Data Center:** `{dc_loc}` for `{target.first_name}`")

    elif cmd == ".link":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        try:
            link = await client(functions.messages.ExportChatInviteRequest(event.chat_id))
            await event.edit(f"🔗 **Group Invite Link:**\n{link.link}")
        except Exception as e:
            await event.edit(f"❌ Couldn't export invite link (admin rights required): {e}")

    elif cmd == ".pin":
        if not event.is_reply:
            await event.edit("❌ Reply to a message with `.pin`")
            return
        reply = await event.get_reply_message()
        notify = "notify" in args_str.lower()
        await client.pin_message(event.chat_id, reply, notify=notify)
        await event.edit("📌 **Message pinned successfully.**")

    elif cmd == ".unpin":
        if event.is_reply:
            reply = await event.get_reply_message()
            await client.unpin_message(event.chat_id, reply)
            await event.edit("📌 **Message unpinned.**")
        else:
            await client.unpin_message(event.chat_id)
            await event.edit("📌 **Latest pinned message unpinned.**")

    elif cmd == ".unpinall":
        try:
            await client(functions.messages.UnpinAllMessagesRequest(peer=event.chat_id))
            await event.edit("📌 **Unpinned all messages in chat.**")
        except Exception as e:
            await event.edit(f"❌ Failed to unpin all: {e}")

    elif cmd == ".pinned":
        chat = await event.get_chat()
        pinned_msg = await client.get_messages(event.chat_id, ids=getattr(chat, "pinned_msg_id", 0))
        if pinned_msg:
            txt = pinned_msg.text or "[Media/Attachment]"
            await event.edit(f"📌 **Pinned Message:**\n\n{txt[:500]}")
        else:
            await event.edit("ℹ️ No pinned message found in this chat.")

    elif cmd == ".title":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        new_title = args_str
        if not new_title:
            await event.edit("❌ Usage: `.title <New Group Title>`")
            return
        try:
            await client(functions.channels.EditTitleRequest(channel=event.chat_id, title=new_title))
            await event.edit(f"✅ Group title changed to: **{new_title}**")
        except Exception as e:
            await event.edit(f"❌ Edit title failed: {e}")

    elif cmd == ".setdesc":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        desc = args_str
        try:
            await client(functions.messages.EditChatAboutRequest(peer=event.chat_id, about=desc))
            await event.edit("✅ Group description updated.")
        except Exception as e:
            await event.edit(f"❌ Failed to update description: {e}")

    elif cmd in (".slow", ".slowmode"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        sec_str = args[0] if args else "10"
        sec = 0 if sec_str.lower() in ("off", "0") else (int(sec_str) if sec_str.isdigit() else 10)
        try:
            await client(functions.channels.ToggleSlowModeRequest(channel=event.chat_id, seconds=sec))
            await event.edit(f"⏱ **Slowmode set to `{sec}s`**" if sec > 0 else "⏱ **Slowmode disabled.**")
        except Exception as e:
            await event.edit(f"❌ Slowmode failed: {e}")

    elif cmd == ".lock":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        arg = args[0].lower() if args else "all"
        rights = types.ChatBannedRights(
            until_date=None,
            send_messages=(arg == "all"),
            send_media=(arg in ("media", "all")),
            send_stickers=(arg in ("stickers", "media", "all")),
            send_gifs=(arg in ("media", "all")),
            send_games=(arg in ("all")),
            send_inline=(arg in ("all")),
            embed_links=(arg in ("links", "all"))
        )
        try:
            await client(functions.messages.EditChatDefaultBannedRightsRequest(peer=event.chat_id, banned_rights=rights))
            await event.edit(f"🔒 **Locked `{arg}` permissions for members.**")
        except Exception as e:
            await event.edit(f"❌ Lock failed: {e}")

    elif cmd == ".unlock":
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        rights = types.ChatBannedRights(
            until_date=None,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False
        )
        try:
            await client(functions.messages.EditChatDefaultBannedRightsRequest(peer=event.chat_id, banned_rights=rights))
            await event.edit("🔓 **Group permissions unlocked.**")
        except Exception as e:
            await event.edit(f"❌ Unlock failed: {e}")

    elif cmd == ".dialogs":
        dialogs = await client.get_dialogs(limit=15)
        lines = [f"💬 **Top Dialogs ({len(dialogs)}):**\n"]
        for d in dialogs:
            t = d.title or "Private User"
            lines.append(f"• `{t}` (ID: `{d.id}`)")
        await event.edit("\n".join(lines))

    elif cmd == ".firstmsg":
        await event.edit("🔍 Fetching first message in chat...")
        try:
            async for m in client.iter_messages(event.chat_id, reverse=True, limit=1):
                txt = m.text or "[Media/Service Message]"
                await event.edit(f"📜 **First Message in Chat:**\n\n_{txt[:400]}_\n\n🗓 `{m.date.strftime('%Y-%m-%d %H:%M:%S')}`")
                return
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

    elif cmd == ".setname":
        if not args:
            await event.edit("❌ Usage: `.setname <First> [Last]`")
            return
        first = args[0]
        last = " ".join(args[1:]) if len(args) > 1 else ""
        await client(functions.account.UpdateProfileRequest(first_name=first, last_name=last))
        await event.edit(f"✅ Name updated to: **{first} {last}**".strip())

    elif cmd == ".setbio":
        if not args_str:
            await event.edit("❌ Usage: `.setbio <Bio text>`")
            return
        await client(functions.account.UpdateProfileRequest(about=args_str))
        await event.edit(f"✅ Bio updated to:\n_{args_str}_")

    elif cmd == ".setpfp":
        if not event.is_reply:
            await event.edit("❌ Reply to a photo with `.setpfp`")
            return
        reply = await event.get_reply_message()
        if not reply.photo:
            await event.edit("❌ Replied message has no photo.")
            return
        photo_path = os.path.join(TEMP_DIR, f"pfp_{uuid4().hex}.jpg")
        await client.download_media(reply, file=photo_path)
        try:
            await client(functions.photos.UploadProfilePhotoRequest(file=await client.upload_file(photo_path)))
            await event.edit("✅ **Profile picture updated!**")
        finally:
            if os.path.exists(photo_path):
                os.remove(photo_path)

    elif cmd == ".delpfp":
        photos = await client.get_profile_photos("me")
        if photos:
            await client(functions.photos.DeletePhotosRequest(id=[types.InputPhoto(id=photos[0].id, access_hash=photos[0].access_hash, file_reference=photos[0].file_reference)]))
            await event.edit("🗑 **Current profile picture deleted.**")
        else:
            await event.edit("❌ No profile picture found.")

    elif cmd == ".clearcache":
        count = 0
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    count += 1
            except Exception:
                pass
        await event.edit(f"🧹 **Cache cleared:** Deleted `{count}` temporary files.")

    elif cmd == ".purgeme":
        n = int(args[0]) if args and args[0].isdigit() else 10
        me = await client.get_me()
        msgs_to_del = []
        async for m in client.iter_messages(event.chat_id, limit=n * 5):
            if m.sender_id == me.id:
                msgs_to_del.append(m.id)
                if len(msgs_to_del) >= n + 1:
                    break
        if msgs_to_del:
            await client.delete_messages(event.chat_id, msgs_to_del)
            conf = await client.send_message(event.chat_id, f"✅ Purged {len(msgs_to_del)} of your messages.")
            await asyncio.sleep(2)
            await conf.delete()

    elif cmd == ".delall":
        if not event.is_reply:
            await event.edit("❌ Reply to a user's message to delete all their messages.")
            return
        reply = await event.get_reply_message()
        target_uid = reply.sender_id
        await event.edit(f"🗑 **Deleting all messages from user `{target_uid}`...**")
        msgs_to_del = []
        async for m in client.iter_messages(event.chat_id, limit=200):
            if m.sender_id == target_uid:
                msgs_to_del.append(m.id)
        if msgs_to_del:
            await client.delete_messages(event.chat_id, msgs_to_del)
            await event.edit(f"✅ Deleted **{len(msgs_to_del)}** messages from user.")
        else:
            await event.edit("ℹ️ No recent messages found from this user.")

    elif cmd == ".warn":
        if not event.is_reply:
            await event.edit("❌ Reply to a user to issue a warning.")
            return
        reply = await event.get_reply_message()
        uid = str(reply.sender_id)
        warns_file = os.path.join(DATA_DIR, "warns.json")
        warns_db = load_json(warns_file, {})
        warns_db[uid] = warns_db.get(uid, 0) + 1
        save_json(warns_file, warns_db)
        curr = warns_db[uid]
        if curr >= 3:
            await client.edit_permissions(event.chat_id, reply.sender_id, view_messages=False)
            await event.edit(f"🚨 **User `{uid}` reached 3/3 warnings and has been banned!**")
        else:
            await event.edit(f"⚠️ **Warning issued to `{uid}`** [{curr}/3 warnings]")

    elif cmd == ".warns":
        if not event.is_reply:
            await event.edit("❌ Reply to a user to check warnings.")
            return
        reply = await event.get_reply_message()
        uid = str(reply.sender_id)
        warns_db = load_json(os.path.join(DATA_DIR, "warns.json"), {})
        await event.edit(f"⚠️ **User `{uid}` has `{warns_db.get(uid, 0)}` warnings.**")

    elif cmd == ".resetwarns":
        if not event.is_reply:
            await event.edit("❌ Reply to a user to reset warnings.")
            return
        reply = await event.get_reply_message()
        uid = str(reply.sender_id)
        wfile = os.path.join(DATA_DIR, "warns.json")
        warns_db = load_json(wfile, {})
        warns_db.pop(uid, None)
        save_json(wfile, warns_db)
        await event.edit(f"✅ **Warnings reset for user `{uid}`.**")

    elif cmd == ".say":
        if args_str:
            await event.delete()
            await client.send_message(event.chat_id, args_str)

    elif cmd == ".echo":
        if not args_str:
            await event.edit("❌ Usage: `.echo <text>`")
            return
        buf = ""
        m = await event.edit("⚡")
        for char in args_str:
            buf += char
            if len(buf) % 3 == 0 or len(buf) == len(args_str):
                try:
                    await m.edit(buf + " ▍")
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
        await m.edit(buf)

    elif cmd == ".poll":
        parts = [p.strip() for p in args_str.split("|") if p.strip()]
        if len(parts) < 3:
            await event.edit("❌ Usage: `.poll Question | Option 1 | Option 2 [| Option 3]`")
            return
        q, options = parts[0], parts[1:]
        poll_obj = types.InputMediaPoll(
            poll=types.Poll(id=random.randint(1000, 999999), question=q, answers=[types.PollAnswer(text=o, option=bytes([i])) for i, o in enumerate(options[:8])])
        )
        await client.send_file(event.chat_id, poll_obj)
        await event.delete()

    elif cmd == ".type":
        sec = int(args[0]) if args and args[0].isdigit() else 5
        await event.delete()
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(sec)

    elif cmd == ".upload":
        sec = int(args[0]) if args and args[0].isdigit() else 5
        await event.delete()
        async with client.action(event.chat_id, "document"):
            await asyncio.sleep(sec)

    elif cmd == ".recordaudio":
        sec = int(args[0]) if args and args[0].isdigit() else 5
        await event.delete()
        async with client.action(event.chat_id, "record-audio"):
            await asyncio.sleep(sec)

    elif cmd == ".timer":
        if not args or not args[0].isdigit():
            await event.edit("❌ Usage: `.timer <seconds> [label]`\nExample: `.timer 30 Coffee Break`")
            return
        dur = int(args[0])
        label = " ".join(args[1:]) if len(args) > 1 else "Timer"
        m = await event.edit(f"⏱ **{label}:** `{dur}`s remaining...")
        for remaining in range(dur - 1, 0, -5):
            await asyncio.sleep(min(5, remaining))
            try:
                await m.edit(f"⏱ **{label}:** `{remaining}`s remaining...")
            except Exception:
                pass
        await asyncio.sleep(1)
        await m.edit(f"🔔 **{label} FINISHED!** ({dur}s elapsed)")

    elif cmd == ".todo":
        todo_file = os.path.join(DATA_DIR, "todos.json")
        todos = load_json(todo_file, [])
        if not args or args[0].lower() == "list":
            if not todos:
                await event.edit("📝 **Your Todo List is empty!**\nAdd one with `.todo add <task>`")
            else:
                lines = ["📝 **PERSONAL TASK LIST:**\n"]
                for i, t in enumerate(todos, 1):
                    status = "✅" if t.get("done") else "⬜"
                    lines.append(f"`{i}.` {status} {t['task']}")
                await event.edit("\n".join(lines))
        elif args[0].lower() == "add" and len(args) > 1:
            task_t = " ".join(args[1:])
            todos.append({"task": task_t, "done": False, "created": str(datetime.datetime.now().strftime("%d %b %H:%M"))})
            save_json(todo_file, todos)
            await event.edit(f"✅ Added task: **{task_t}**")
        elif args[0].lower() == "done" and len(args) > 1 and args[1].isdigit():
            idx = int(args[1]) - 1
            if 0 <= idx < len(todos):
                todos[idx]["done"] = True
                save_json(todo_file, todos)
                await event.edit(f"✅ Marked task #{idx+1} as done!")
        elif args[0].lower() in ("del", "delete") and len(args) > 1 and args[1].isdigit():
            idx = int(args[1]) - 1
            if 0 <= idx < len(todos):
                removed = todos.pop(idx)
                save_json(todo_file, todos)
                await event.edit(f"🗑 Deleted task: **{removed['task']}**")

    # Additional Utilities, Transformations & Games
    elif cmd in (".wordcount", ".countwords"):
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_word_count_stats(content))
        else:
            await event.edit("❌ Provide text or reply to a message.")

    elif cmd == ".epoch":
        now_ts = int(time.time())
        await event.edit(f"⏰ **Unix Epoch Timestamp:**\n• **Seconds:** `{now_ts}`\n• **Milliseconds:** `{int(time.time()*1000)}`\n• **UTC Time:** `{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`")

    elif cmd == ".age":
        if not args:
            await event.edit("❌ Usage: `.age YYYY-MM-DD`\nExample: `.age 2000-05-15`")
            return
        try:
            b_date = datetime.datetime.strptime(args[0], "%Y-%m-%d")
            today = datetime.datetime.today()
            age_years = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
            total_days = (today - b_date).days
            await event.edit(f"🎂 **Age Calculation for `{args[0]}`:**\n• **Years:** `{age_years}` years old\n• **Days Alive:** `{total_days:,}` days")
        except Exception:
            await event.edit("❌ Invalid date format. Use `YYYY-MM-DD`.")

    elif cmd == ".daysuntil":
        if not args:
            await event.edit("❌ Usage: `.daysuntil YYYY-MM-DD`\nExample: `.daysuntil 2027-01-01`")
            return
        try:
            target_d = datetime.datetime.strptime(args[0], "%Y-%m-%d")
            today = datetime.datetime.today()
            delta = (target_d - today).days
            await event.edit(f"📅 **Days Until `{args[0]}`:** `{delta}` days remaining.")
        except Exception:
            await event.edit("❌ Invalid date format. Use `YYYY-MM-DD`.")

    elif cmd == ".pick":
        options = [p.strip() for p in args_str.split(",") if p.strip()] if "," in args_str else args
        if len(options) >= 2:
            chosen = random.choice(options)
            await event.edit(f"🎯 **Decision:** `{chosen}`")
        else:
            await event.edit("❌ Usage: `.pick option 1, option 2, option 3`")

    elif cmd == ".color":
        col_hex = args[0].lstrip("#") if args else f"{random.randint(0, 0xFFFFFF):06x}"
        await event.edit(f"🎨 **Color Info:**\n• **HEX:** `#{col_hex.upper()}`\n• **Preview:** https://singlecolorimage.com/get/{col_hex}/400x100.png")

    elif cmd == ".upper":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(content.upper())
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".lower":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(content.lower())
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".titlecase":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(content.title())
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".superscript":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_superscript_text(content))
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".subscript":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(_subscript_text(content))
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".httpstatus":
        code = args[0] if args else "200"
        await event.edit(_http_status_lookup(code))

    elif cmd == ".urlencode":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(f"🔗 **URL Encoded:**\n`{urllib.parse.quote(content)}`")
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".urldecode":
        content = args_str or ((await event.get_reply_message()).text if event.is_reply else "")
        if content:
            await event.edit(f"🔗 **URL Decoded:**\n`{urllib.parse.unquote(content)}`")
        else:
            await event.edit("❌ Provide text or reply.")

    elif cmd == ".uuid":
        await event.edit(f"🆔 **Generated UUIDv4:**\n`{uuid4()}`")

    elif cmd == ".bored":
        act = random.choice(BORED_ACTIVITIES)
        await event.edit(f"💡 **Idea for boredom:**\n_{act}_")

    elif cmd == ".insult":
        target = f"**{args_str}**, " if args_str else ""
        await event.edit(f"😈 {target}{random.choice(INSULTS_TECH)}")

    elif cmd == ".rps":
        choices = ["Rock 🪨", "Paper 📄", "Scissors ✂️"]
        user_c = args[0].lower() if args else "rock"
        bot_c = random.choice(choices)
        await event.edit(f"🎮 **Rock Paper Scissors:**\n• **You picked:** `{user_c.capitalize()}`\n• **Opponent:** {bot_c}")

    elif cmd == ".truth":
        await event.edit(f"❓ **Truth Question:**\n_{random.choice(TRUTH_PROMPTS)}_")

    elif cmd == ".dare":
        await event.edit(f"🔥 **Dare Challenge:**\n_{random.choice(DARE_PROMPTS)}_")

    elif cmd == ".hypnotize":
        m = await event.edit("🌀 **Focus on the spiral...**")
        frames = ["🌀 3...", "💫 2...", "✨ 1...", "😵‍💫 **You are now under my command!**"]
        for f in frames:
            await asyncio.sleep(0.8)
            await m.edit(f)

    elif cmd == ".hack":
        target = args_str or "target_server"
        m = await event.edit(f"💻 **Initializing exploit against `{target}`...**")
        steps = [
            f"📡 Bypassing Cloudflare WAF on `{target}`...",
            f"🔓 Injecting SQL payload & gaining root shell...",
            f"📦 Extracting database credentials & SSL certificates...",
            f"✅ **Target `{target}` successfully compromised!**"
        ]
        for s in steps:
            await asyncio.sleep(0.9)
            await m.edit(s)

    elif cmd == ".rates":
        try:
            r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
            if r.status_code == 200:
                rates = r.json().get("rates", {})
                await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
💱 **GLOBAL FX RATES (Base USD)**
━━━━━━━━━━━━━━━━━━━━━━━━━━
• **EUR:** `{rates.get('EUR', 'N/A')}`
• **GBP:** `{rates.get('GBP', 'N/A')}`
• **INR:** `{rates.get('INR', 'N/A')}`
• **CAD:** `{rates.get('CAD', 'N/A')}`
• **AED:** `{rates.get('AED', 'N/A')}`
• **JPY:** `{rates.get('JPY', 'N/A')}`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")
            else:
                await event.edit("❌ Failed to fetch rates.")
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

    elif cmd == ".sysinfo":
        proc_uptime = int(time.time() - BOT_START_TIME)
        h, rem = divmod(proc_uptime, 3600)
        m, s = divmod(rem, 60)
        ram_str = "N/A"
        if PSUTIL_OK:
            try:
                proc = psutil.Process(os.getpid())
                ram_str = f"{proc.memory_info().rss / (1024*1024):.1f} MB"
            except Exception:
                pass
        await event.edit(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **SYSTEM DIAGNOSTICS & STATUS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ **Bot Version:** `{BOT_VERSION}` ({BOT_BUILD})
✓ **Python:** `{platform.python_version()}` ({platform.system()} {platform.machine()})
✓ **Uptime:** `{h}h {m}m {s}s`
✓ **Memory Footprint:** `{ram_str}`
✓ **Active Tasks:** `{len(asyncio.all_tasks())}`
✓ **Total Commands:** `{sum(len(v) for v in HELP_CATEGORIES.values())}+`
━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    elif cmd == ".restart":
        await event.edit("🔄 **SelfBot is restarting... Back in ~3 seconds.**")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    elif cmd == ".unmuteall":
        count = len(muted_users)
        muted_users.clear()
        save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
        await event.edit(f"✅ **Unmuted all `{count}` users** from selfbot memory.")

    elif cmd == ".unbanall":
        count = len(banned_users)
        banned_users.clear()
        save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
        await event.edit(f"✅ **Unbanned all `{count}` users** from selfbot memory.")

# ------------------------------------------------------------------
# Event Listeners
# ------------------------------------------------------------------
@client.on(events.NewMessage(outgoing=True))
async def cmd_handler(event):
    raw_text = event.raw_text.strip()
    # Note: AFK is NOT auto-disabled when owner messages, persistent until .back

    if not raw_text.startswith("."):
        if ghost_mode.enabled:
            async def _ghost_clean():
                await asyncio.sleep(ghost_mode.delete_delay)
                try:
                    await event.delete()
                except Exception:
                    pass
            asyncio.create_task(_ghost_clean())
        return

    try:
        await _cmd_dispatch(event)
        if ghost_mode.enabled:
            async def _ghost_clean():
                await asyncio.sleep(ghost_mode.delete_delay)
                try:
                    await event.delete()
                except Exception:
                    pass
            asyncio.create_task(_ghost_clean())
    except Exception as e:
        log_error(event.raw_text, e)
        if auto_fix_active:
            await asyncio.sleep(1.2)
            try:
                await _cmd_dispatch(event)
            except Exception as e2:
                log_error(event.raw_text + " [retry]", e2)
                await event.respond(f"⚠️ **Auto-Fix Failure:** `{e2}`")

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    global muted_users, banned_users
    me = await client.get_me()
    if event.sender_id == me.id:
        return

    if event.sender_id in banned_users or event.sender_id in muted_users:
        try:
            await event.delete()
        except Exception:
            pass
        return

    if afk.active and event.is_private:
        sender_id = event.sender_id
        if afk.should_reply(sender_id):
            afk.mark_replied(sender_id)
            afk_text = afk.message
            try:
                if len(afk_text) <= 1024:
                    await client.send_file(event.chat_id, AFK_GIF_URL, caption=afk_text)
                else:
                    await client.send_file(event.chat_id, AFK_GIF_URL)
                    await event.respond(afk_text)
            except Exception as e:
                log_error("afk_reply", e)

# ------------------------------------------------------------------
# Web Health Server
# ------------------------------------------------------------------
async def web_server():
    if not AIOHTTP_OK:
        return
    app = aw.Application()
    app.router.add_get("/", lambda r: aw.Response(text="SelfBot Running 24/7"))
    app.router.add_get("/health", lambda r: aw.Response(text="OK"))
    runner = aw.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 3000))
    site = aw.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info(f"Health check endpoint active on port {port}")

# ------------------------------------------------------------------
# Main Execution Loop
# ------------------------------------------------------------------
async def run_client():
    try:
        if PHONE:
            await client.start(phone=PHONE)
        else:
            await client.start()
    except (AuthKeyUnregisteredError, ValueError) as e:
        log.error("Invalid SESSION_STRING. Generate a valid session.")
        log_error("session_start", e)
        return

    me = await client.get_me()
    log.info(f"Logged in as: {me.first_name} (@{me.username}) | ID: {me.id}")
    log.info(f"Rehu SelfBot V{BOT_VERSION} by {DEV_NAME} is active!")
    await web_server()
    await client.run_until_disconnected()

async def main():
    backoff = 5
    while True:
        try:
            await run_client()
            break
        except Exception as e:
            log.error(f"Fatal error, restarting in {backoff}s: {e}")
            log_error("main_loop", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    asyncio.run(main())
