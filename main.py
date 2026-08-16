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
    if len(text) <= 1024:
        await client.send_file(event.chat_id, gif_url, caption=text)
    else:
        await client.send_file(event.chat_id, gif_url)
        await client.send_message(event.chat_id, text)

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
    }
    if style not in styles:
        return "❌ Available styles: `bubble`, `gothic`, `bold`, `italic`, `mono`, `square`\n\nUsage: `.font gothic your text here`"
    target = styles[style]
    trans_map = str.maketrans(norm[:len(target)], target)
    return text.translate(trans_map)

def _download_tts(text: str, lang: str = "en") -> Optional[str]:
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(text[:200])}&tl={lang}&client=tw-ob"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200 and len(r.content) > 100:
            out_file = os.path.join(TEMP_DIR, f"tts_{uuid4().hex}.mp3")
            with open(out_file, "wb") as f:
                f.write(r.content)
            return out_file
    except Exception as e:
        log_error("tts", e)
    return None

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
# Help & Developer Matrix
# ------------------------------------------------------------------
HELP_CATEGORIES = {
    "🤖 Info & Telegram": [".info", ".tinfo", ".chatinfo", ".id", ".unread", ".ocr", ".repo", ".time"],
    "🛠 Productivity": [".paste", ".tts", ".remind", ".unit", ".json", ".note", ".calc", ".weather", ".tr", ".qr", ".crypto", ".define", ".github", ".short", ".schedule", ".portfolio", ".currency", ".wiki"],
    "🛡 Security & OSINT": [".bin", ".whois", ".dns", ".scan", ".osint", ".secret", ".net", ".ip", ".genpass", ".b64", ".hash"],
    "👤 User & Stealth": [".afk", ".back", ".ghost", ".analytics", ".mood", ".flair", ".speed"],
    "🎉 Fun & Social": [".react", ".font", ".meme", ".korn", ".cat", ".trivia", ".fact", ".horoscope", ".country", ".anime", ".quote", ".joke", ".8ball", ".roll", ".flip", ".reverse"],
    "🧩 Moderation": [".mute", ".unmute", ".unmuteall", ".ban", ".unban", ".unbanall", ".block", ".unblock", ".kick", ".admin", ".demote"],
    "📡 Broadcast": [".dm", ".frwd", ".gc", ".broad", ".frwdall", ".spm", ".mm", ".tag", ".del", ".purge", ".close", ".count", ".say"],
    "💰 Crypto Tracker": [".whale", ".portfolio", ".crypto"],
    "⚙️ System": [".fix", ".fixlog", ".ping", ".alive", ".uptime", ".dev", ".owner"],
}

def _build_help_overview():
    uptime_sec = int(time.time() - BOT_START_TIME)
    h, rem = divmod(uptime_sec, 3600)
    m, s = divmod(rem, 60)
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ **REHU SELFBOT V4**",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"**Version:** `{BOT_VERSION}`  •  **Build:** `{BOT_BUILD}`",
        f"**Developer:** {DEV_NAME}",
        f"**Uptime:** `{h}h {m}m {s}s`",
        f"**Python:** `{platform.python_version()}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for category, cmds in HELP_CATEGORIES.items():
        lines.append(f"\n**{category}**")
        lines.append("  " + "  ".join(f"`{c}`" for c in cmds))
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
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
    text = raw.lower()
    if not text.startswith("."):
        return

    # System & Dev
    if text == ".ping":
        start = time.time()
        msg = await event.edit("🏓 Pinging...")
        latency_ms = int((time.time() - start) * 1000)
        await msg.edit(f"🏓 **Pong!** `{latency_ms}ms`")

    elif text in (".alive", ".uptime"):
        uptime_sec = int(time.time() - BOT_START_TIME)
        h, rem = divmod(uptime_sec, 3600)
        m, s = divmod(rem, 60)
        await event.edit(f"🟢 **Rehu SelfBot is Online!**\n✓ **Version:** `{BOT_VERSION}`\n✓ **Uptime:** `{h}h {m}m {s}s`\n✓ **Dev:** {DEV_NAME}")

    elif text in (".help", ".fux", ".commands"):
        await _send_gif_with_text(event, COMMANDS_GIF_URL, _build_help_overview())

    elif text.startswith(".help "):
        cmd_query = raw[6:].strip().lower()
        await event.edit(f"📖 **Command:** `.{cmd_query}`\nRun `.{cmd_query}` with appropriate parameters or reply to target.")

    elif text == ".dev":
        await _send_gif_with_text(event, DEV_GIF_URL, _build_dev_info())

    elif text == ".owner":
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

    elif text == ".fix":
        auto_fix_active = not auto_fix_active
        state = "ON ✅" if auto_fix_active else "OFF 🔕"
        await event.edit(f"**🛠 Auto-fix mode: {state}**")

    elif text == ".fixlog":
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                tail = "".join(f.readlines()[-30:]) or "No errors logged yet."
        except FileNotFoundError:
            tail = "No errors logged yet."
        await event.edit(f"**🧾 Recent Errors:**\n```\n{tail[-3500:]}\n```")

    elif text == ".autoaccept":
        auto_accept_active = not auto_accept_active
        await event.edit(f"Auto-accept chat requests: `{'Enabled' if auto_accept_active else 'Disabled'}`")

    # AFK
    elif text == ".afk" or text.startswith(".afk "):
        custom = raw[4:].strip() or None
        afk.enable(custom)
        await event.edit(f"🌙 **AFK Mode Enabled**\nMessage: `{afk.message}`")

    elif text == ".back":
        if afk.active:
            dur = afk.duration_text()
            afk.disable()
            await event.edit(f"✅ **AFK Disabled.** Away for {dur}.")
        else:
            await event.edit("ℹ️ AFK was not active.")

    # Notes
    elif text.startswith(".note"):
        parts = raw[5:].strip().split(None, 2)
        if not parts:
            await event.edit("❌ Usage: `.note add <title> <text>` | `.note list` | `.note view <title>` | `.note del <title>`")
            return
        act = parts[0].lower()
        if act == "list":
            if not notes_db:
                await event.edit("📝 No notes stored.")
            else:
                lines = [f"• **{t}**: `{c[:30]}...`" for t, c in notes_db.items()]
                await event.edit("📝 **Saved Notes:**\n\n" + "\n".join(lines))
        elif act == "add" and len(parts) >= 3:
            notes_db[parts[1]] = parts[2]
            save_json(NOTES_FILE, notes_db)
            await event.edit(f"✅ Saved note `{parts[1]}`.")
        elif act == "view" and len(parts) >= 2:
            if parts[1] in notes_db:
                await event.edit(f"📝 **Note: {parts[1]}**\n\n{notes_db[parts[1]]}")
            else:
                await event.edit("❌ Note not found.")
        elif act == "del" and len(parts) >= 2:
            if parts[1] in notes_db:
                del notes_db[parts[1]]
                save_json(NOTES_FILE, notes_db)
                await event.edit(f"✅ Deleted note `{parts[1]}`.")
            else:
                await event.edit("❌ Note not found.")

    # Spam
    elif text.startswith(".spm") or text.startswith(".spam"):
        cmd_len = 4 if text.startswith(".spm") else 5
        parts = raw[cmd_len:].strip().rsplit(None, 1)
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
    elif text.startswith(".tinfo") or text.startswith(".info"):
        cmd_len = 5 if text.startswith(".info") else 7
        target = raw[cmd_len:].strip() if len(raw) > cmd_len else None
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

    elif text == ".id":
        if event.is_reply:
            reply = await event.get_reply_message()
            await event.edit(f"🆔 **User ID:** `{reply.sender_id}`")
        else:
            await event.edit(f"🆔 **Chat ID:** `{event.chat_id}`")

    elif text.startswith(".chatinfo"):
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

    elif text.startswith(".insta") or text.startswith(".iginfo"):
        parts = raw.split(None, 1)
        if len(parts) < 2:
            await event.edit("❌ Usage: `.insta @username`")
            return
        await event.edit(f"🔍 Fetching @{parts[1].strip().lstrip('@')}...")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _ig_info, parts[1].strip())
        await event.edit(res)

    # Moderation
    elif (text.startswith(".mute") and not text.startswith(".unmute")) or (text.startswith(".ban") and not text.startswith(".unban")):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        elif len(raw.split()) > 1:
            u = await get_entity(raw.split(None, 1)[1].strip())
        if u:
            muted_users.add(u.id)
            banned_users.add(u.id)
            save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
            await event.edit(f"🚫 Blocked `{u.first_name or u.id}` — messages will be deleted.")
        else:
            await event.edit("❌ User not found.")

    elif text.startswith(".unmute") or text.startswith(".unban"):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        elif len(raw.split()) > 1:
            u = await get_entity(raw.split(None, 1)[1].strip())
        if u:
            muted_users.discard(u.id)
            banned_users.discard(u.id)
            save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
            await event.edit(f"✅ Unblocked `{u.first_name or u.id}`")
        else:
            await event.edit("❌ User not found.")

    elif text.startswith(".block") and not text.startswith(".unblock"):
        target_id = event.chat_id if event.is_private else ((await get_entity(raw.split(None, 1)[1].strip())).id if len(raw.split()) > 1 else None)
        if target_id:
            await client(functions.contacts.BlockRequest(id=target_id))
            await event.edit(f"🚫 Blocked `{target_id}`")

    elif text.startswith(".unblock"):
        target_id = event.chat_id if event.is_private else ((await get_entity(raw.split(None, 1)[1].strip())).id if len(raw.split()) > 1 else None)
        if target_id:
            await client(functions.contacts.UnblockRequest(id=target_id))
            await event.edit(f"✅ Unblocked `{target_id}`")

    elif text.startswith(".kick"):
        if not event.is_group or not event.is_reply:
            await event.edit("❌ Reply to a user in a group.")
            return
        reply = await event.get_reply_message()
        await client.kick_participant(event.chat_id, reply.sender_id)
        await event.edit(f"🦵 Kicked user `{reply.sender_id}`")

    elif text.startswith(".admin"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        target = (await event.get_reply_message()).sender_id if event.is_reply else ((await get_entity(raw.split(None, 1)[1].strip())).id if len(raw.split()) > 1 else None)
        if target:
            rights = types.ChatAdminRights(change_info=True, post_messages=True, edit_messages=True, delete_messages=True, ban_users=True, invite_users=True, pin_messages=True, add_admins=False, manage_call=True, other=True)
            await client(EditAdminRequest(event.chat_id, target, rights, "admin"))
            await event.edit(f"⭐ Promoted `{target}` to admin.")

    elif text.startswith(".demote"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        target = (await event.get_reply_message()).sender_id if event.is_reply else ((await get_entity(raw.split(None, 1)[1].strip())).id if len(raw.split()) > 1 else None)
        if target:
            rights = types.ChatAdminRights(change_info=False, post_messages=False, edit_messages=False, delete_messages=False, ban_users=False, invite_users=False, pin_messages=False, add_admins=False, manage_call=False, other=False)
            await client(EditAdminRequest(event.chat_id, target, rights, ""))
            await event.edit(f"⬇️ Demoted `{target}`.")

    # Broadcast & Actions
    elif text.startswith(".dm") and not text.startswith(".dmfrwd"):
        content = raw[3:].strip()
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

    elif text.startswith(".frwd") and not text.startswith(".frwdall"):
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

    elif text.startswith(".gc"):
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

    elif text.startswith(".broad"):
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

    elif text.startswith(".frwdall"):
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

    elif text.startswith(".mm"):
        if not event.is_reply:
            await event.edit("❌ Reply to a user with `.mm`")
            return
        reply = await event.get_reply_message()
        u = await client.get_entity(reply.sender_id)
        await client(functions.messages.CreateChatRequest(users=[u.id], title="Syed Rehan's Middleman Service"))
        await event.edit(f"✅ **Syed Rehan's Middleman Service**\nGroup created with `{u.first_name or u.id}`")

    elif text.startswith(".tag"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        msg_val = raw[4:].strip() or "👋"
        participants = await client.get_participants(event.chat_id, limit=50)
        me = await client.get_me()
        tags = " ".join(f"[{p.first_name or 'user'}](tg://user?id={p.id})" for p in participants if not p.bot and p.id != me.id)
        if tags:
            await client.send_message(event.chat_id, f"{msg_val}\n{tags}")
            await event.delete()

    elif text == ".del":
        if not event.is_private:
            await event.edit("❌ Private chats only.")
            return
        await client(DeleteHistoryRequest(peer=event.chat_id, max_id=0, revoke=True))

    elif text.startswith(".purge"):
        n = int(raw.split()[1]) if len(raw.split()) > 1 and raw.split()[1].isdigit() else 10
        msgs = await client.get_messages(event.chat_id, limit=n + 1)
        await client.delete_messages(event.chat_id, [m.id for m in msgs])
        conf = await event.respond(f"✅ Purged {n} messages.")
        await asyncio.sleep(2)
        await conf.delete()

    elif text.startswith(".close"):
        sec = int(raw.split()[1]) if len(raw.split()) > 1 and raw.split()[1].isdigit() else 3
        await event.edit(f"💣 Leaving group in {sec}s...")
        await asyncio.sleep(sec)
        await client.delete_dialog(event.chat_id)

    elif text.startswith(".count"):
        parts = raw.split(None, 2)
        sec = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
        final = parts[2] if len(parts) > 2 else None
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
    elif text.startswith(".calc"):
        expr = raw[6:].strip()
        try:
            res = sympy.sympify(expr) if SYMPY_OK else eval(expr, {"__builtins__": {}}, {})
            await event.edit(f"🧮 `{expr}` = `{res}`")
        except Exception:
            await event.edit("❌ Invalid expression.")

    elif text.startswith(".wiki"):
        query = raw[6:].strip()
        if not query:
            await event.edit("❌ Usage: `.wiki query`")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _wiki_lookup, query)
        await event.edit(res)

    elif text.startswith(".tr") or text.startswith(".translate"):
        cmd_end = 3 if text.startswith(".tr") else 10
        rest = raw[cmd_end:].strip()
        parts = rest.split(None, 1)
        lang = parts[0].lower() if parts else "en"
        content = parts[1] if len(parts) > 1 else ((await event.get_reply_message()).text if event.is_reply else "")
        if not content:
            await event.edit("❌ Usage: `.tr <lang> <text>` or reply.")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _translate, content, lang)
        await event.edit(res)

    elif text.startswith(".weather"):
        city = raw[8:].strip() or "Mumbai"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _weather_info, city)
        await event.edit(res)

    elif text.startswith(".crypto"):
        coin = raw[7:].strip() or "bitcoin"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _crypto_price, coin)
        await event.edit(res)

    elif text.startswith(".define"):
        word = raw[7:].strip()
        if not word:
            await event.edit("❌ Usage: `.define word`")
            return
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _dictionary_lookup, word)
        await event.edit(res)

    elif text.startswith(".github"):
        user = raw[7:].strip().lstrip("@") or "rehuux"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _github_info, user)
        await event.edit(res)

    elif text.startswith(".short"):
        url = raw[6:].strip()
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _short_url, url)
        await event.edit(res)

    elif text.startswith(".qr"):
        qr_text = raw[3:].strip()
        if not qr_text:
            await event.edit("❌ Usage: `.qr <text>`")
            return
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=" + urllib.parse.quote(qr_text)
        await client.send_file(event.chat_id, qr_url, caption=f"🔳 QR for: `{qr_text}`")
        await event.delete()

    elif text == ".quote":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _quote_of_the_day)
        await event.edit(res)

    elif text == ".joke":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _random_joke)
        await event.edit(res)

    elif text.startswith(".8ball"):
        ans = random.choice(["It is certain.", "Without a doubt.", "Yes, definitely.", "Most likely.", "Reply hazy, try again.", "Don't count on it.", "Very doubtful."])
        await event.edit(f"🎱 **Q:** {raw[6:].strip()}\n**A:** {ans}")

    elif text.startswith(".roll"):
        sides = int(raw.split()[1]) if len(raw.split()) > 1 and raw.split()[1].isdigit() else 6
        await event.edit(f"🎲 Rolled: **{random.randint(1, sides)}** (1–{sides})")

    elif text == ".flip":
        await event.edit(f"**{random.choice(['🪙 Heads', '🪙 Tails'])}**")

    elif text.startswith(".reverse"):
        await event.edit(f"🔁 `{raw[8:].strip()[::-1]}`")

    # Media & Fun
    elif text == ".meme":
        loop = asyncio.get_event_loop()
        img, cap = await loop.run_in_executor(None, _random_meme)
        if img:
            await client.send_file(event.chat_id, img, caption=cap)
            await event.delete()
        else:
            await event.edit(cap)

    elif text == ".korn":
        loop = asyncio.get_event_loop()
        img, cap = await loop.run_in_executor(None, _random_subreddit_post, "randi_khanna")
        if img:
            await client.send_file(event.chat_id, img, caption=cap)
            await event.delete()

    elif text == ".cat":
        loop = asyncio.get_event_loop()
        img, cap = await loop.run_in_executor(None, _random_subreddit_post, "youngpussylips")
        if img:
            await client.send_file(event.chat_id, img, caption=cap)
            await event.delete()

    elif text == ".trivia":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _random_trivia)
        await event.edit(res)

    elif text == ".fact":
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _random_fact)
        await event.edit(res)

    elif text.startswith(".horoscope"):
        sign = raw[10:].strip() or "leo"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _daily_horoscope, sign)
        await event.edit(res)

    elif text.startswith(".country"):
        c = raw[8:].strip() or "Japan"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _country_info, c)
        await event.edit(res)

    elif text.startswith(".anime"):
        a = raw[6:].strip() or "Naruto"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _anime_info, a)
        await event.edit(res)

    elif text.startswith(".schedule"):
        parsed = _parse_schedule(raw[9:].strip())
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
    elif text.startswith(".osint"):
        parts = raw[6:].strip().split(None, 1)
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

    elif text.startswith(".ip"):
        ip = raw[3:].strip() or "8.8.8.8"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _ip_lookup, ip)
        await event.edit(res)

    elif text.startswith(".scan"):
        url = raw[5:].strip() or "https://google.com"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _scan_url, url)
        await event.edit(res)

    elif text.startswith(".portfolio"):
        parts = raw[10:].strip().split(None, 2)
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

    elif text.startswith(".repo"):
        repo = raw[5:].strip() or "rehuux/telegram-selfbot"
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _repo_stats, repo)
        await event.edit(res)

    elif text == ".ocr":
        if not event.is_reply:
            await event.edit("❌ Reply to an image.")
            return
        reply = await event.get_reply_message()
        img_path = os.path.join(TEMP_DIR, f"{uuid4().hex}.jpg")
        try:
            await client.download_media(reply, file=img_path)
            # Simple fallback OCR
            if TESSERACT_OK:
                txt = pytesseract.image_to_string(Image.open(img_path))
                await event.edit(f"📝 **Extracted Text:**\n`{txt}`")
            else:
                await event.edit("❌ Tesseract OCR not installed.")
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    elif text.startswith(".ghost"):
        arg = raw[6:].strip().lower()
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

    elif text == ".analytics":
        msgs = await client.get_messages(event.chat_id, limit=500)
        total = len(msgs)
        media = sum(1 for m in msgs if m.media)
        links = sum(1 for m in msgs if m.text and "http" in m.text)
        await event.edit(f"📊 **Chat Analytics (Last {total} msgs)**\n\n• **Total:** `{total}`\n• **Media:** `{media}`\n• **Links:** `{links}`")

    elif text == ".mood":
        if not event.is_reply:
            await event.edit("❌ Reply to a message.")
            return
        reply = await event.get_reply_message()
        await event.edit(_analyze_mood(reply.text or ""))

    elif text.startswith(".secret"):
        if not CRYPTO_OK:
            await event.edit("❌ cryptography library required.")
            return
        parts = raw[7:].strip().split(None, 1)
        if not parts:
            await event.edit("❌ Usage: `.secret add <text>` | `.secret list` | `.secret view <n>` | `.secret delete <n>`")
            return
        act = parts[0].lower()
        if act == "add" and len(parts) >= 2:
            notes = _load_secret_notes()
            notes.append(parts[1])
            _save_secret_notes(notes)
            await event.delete()
            await client.send_message(event.chat_id, f"🔐 Secret note #{len(notes)} encrypted & saved.")
        elif act == "list":
            notes = _load_secret_notes()
            lines = [f"{i+1}. {n[:25]}..." for i, n in enumerate(notes)]
            await event.edit(f"🔐 **Encrypted Vault ({len(notes)} notes):**\n" + "\n".join(lines))
        elif act == "view" and len(parts) >= 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            notes = _load_secret_notes()
            if 0 <= idx < len(notes):
                await event.edit(f"🔐 **Note #{idx+1}:**\n{notes[idx]}")
        elif act == "delete" and len(parts) >= 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            notes = _load_secret_notes()
            if 0 <= idx < len(notes):
                notes.pop(idx)
                _save_secret_notes(notes)
                await event.edit("✅ Note deleted.")

    elif text == ".net":
        start_t = time.time()
        dns_ok = False
        try:
            socket.gethostbyname("1.1.1.1")
            dns_ok = True
        except Exception:
            pass
        ping_ms = int((time.time() - start_t) * 1000)
        await event.edit(f"🌐 **Network Diagnostics:**\n\n✓ **DNS:** `{'OK' if dns_ok else 'Failed'}`\n✓ **Gateway Ping:** `{ping_ms} ms`\n✓ **Status:** `🟢 Online`")

    elif text.startswith(".whale"):
        arg = raw[6:].strip().lower()
        whale_alert_active = (arg == "on")
        save_json(WHALE_STATE_FILE, {"enabled": whale_alert_active})
        await event.edit(f"🐋 **Whale Alert:** `{'Enabled' if whale_alert_active else 'Disabled'}`")

    elif text.startswith(".flair"):
        args = raw[6:].strip().split()
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

    elif text == ".scanqr":
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

    elif text.startswith(".hash"):
        c = raw[5:].strip()
        if c:
            h = _generate_hashes(c)
            await event.edit(f"🔑 **Hashes for `{c[:30]}`:**\n\n• **MD5:** `{h['MD5']}`\n• **SHA1:** `{h['SHA1']}`\n• **SHA256:** `{h['SHA256']}`")

    elif text.startswith(".currency"):
        parts = raw[9:].strip().split()
        if len(parts) == 3:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, _convert_currency, float(parts[0]), parts[1], parts[2])
            await event.edit(res)

    elif text.startswith(".genpass"):
        l = int(raw.split()[1]) if len(raw.split()) > 1 and raw.split()[1].isdigit() else 16
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        pwd = "".join(random.choice(chars) for _ in range(l))
        await event.edit(f"🔑 **Generated Password ({l} chars):**\n`{pwd}`")

    elif text.startswith(".b64"):
        parts = raw[4:].strip().split(None, 1)
        if len(parts) == 2:
            if parts[0].lower() == "encode":
                await event.edit(f"🔠 **Base64 Encoded:**\n`{base64.b64encode(parts[1].encode()).decode()}`")
            else:
                await event.edit(f"🔠 **Base64 Decoded:**\n`{base64.b64decode(parts[1].encode()).decode(errors='replace')}`")

    elif text.startswith(".say"):
        content = raw[4:].strip()
        if content:
            await event.delete()
            await client.send_message(event.chat_id, content)

    elif text.startswith(".paste") or text.startswith(".haste"):
        content = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
        if not content and event.is_reply:
            reply = await event.get_reply_message()
            content = reply.raw_text or reply.message or ""
        if not content:
            await event.edit("❌ Provide text or reply to a message: `.paste <text>`")
            return
        await event.edit("⏳ **Uploading to Pastebin...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _paste_text, content)
        await event.edit(res)

    elif text.startswith(".tts") or text.startswith(".voice"):
        args = raw.split(None, 1)
        content = args[1] if len(args) > 1 else ""
        lang = "en"
        if not content and event.is_reply:
            reply = await event.get_reply_message()
            content = reply.raw_text or reply.message or ""
        elif content and len(content.split()) > 1 and len(content.split()[0]) == 2 and content.split()[0].isalpha():
            lang = content.split()[0].lower()
            content = content.split(None, 1)[1]
        if not content:
            await event.edit("❌ Provide text or reply to a message: `.tts [lang] <text>`")
            return
        await event.edit("🎙 **Generating Voice Note...**")
        loop = asyncio.get_event_loop()
        audio_path = await loop.run_in_executor(None, _download_tts, content, lang)
        if audio_path and os.path.exists(audio_path):
            try:
                await event.delete()
                await client.send_file(event.chat_id, audio_path, voice_note=True, reply_to=event.reply_to_msg_id)
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
        else:
            await event.edit("❌ Failed to generate TTS audio.")

    elif text.startswith(".remind"):
        parts = raw[7:].strip().split(None, 1)
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

    elif text.startswith(".react"):
        if not event.is_reply:
            await event.edit("❌ Reply to a message with `.react <emoji>` (e.g. `.react 🔥`)")
            return
        parts = raw[6:].strip().split()
        emoji = parts[0] if parts else "🔥"
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

    elif text in (".speed", ".speedtest"):
        await event.edit("🚀 **Running SpeedTest... Please wait (~10s)**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _run_speedtest_sync)
        await event.edit(res)

    elif text == ".unread":
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

    elif text.startswith(".dns"):
        parts = raw[4:].strip().split()
        if not parts:
            await event.edit("❌ Usage: `.dns <domain> [A/AAAA/MX/TXT/NS]`\nExample: `.dns google.com MX`")
            return
        domain = parts[0]
        qtype = parts[1] if len(parts) > 1 else "A"
        await event.edit(f"🔍 **Querying DNS ({qtype}) for `{domain}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _dns_query, domain, qtype)
        await event.edit(res)

    elif text.startswith(".whois"):
        domain = raw[6:].strip()
        if not domain:
            await event.edit("❌ Usage: `.whois <domain>`\nExample: `.whois telegram.org`")
            return
        await event.edit(f"🌐 **Querying WHOIS for `{domain}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _whois_query, domain)
        await event.edit(res)

    elif text.startswith(".bin"):
        bin_no = raw[4:].strip()
        if not bin_no:
            await event.edit("❌ Usage: `.bin <6-digit-bin>`\nExample: `.bin 453201`")
            return
        await event.edit(f"💳 **Looking up BIN `{bin_no[:6]}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _bin_lookup, bin_no)
        await event.edit(res)

    elif text.startswith(".time") or text.startswith(".worldtime"):
        city = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
        if not city:
            await event.edit("❌ Usage: `.time <city/timezone>`\nExample: `.time Tokyo` or `.time London`")
            return
        await event.edit(f"🕒 **Fetching time for `{city}`...**")
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, _world_time, city)
        await event.edit(res)

    elif text.startswith(".unit") or text.startswith(".convert"):
        args = raw.split()[1:]
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

    elif text.startswith(".json") or text.startswith(".prettify"):
        body = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
        if not body and event.is_reply:
            reply = await event.get_reply_message()
            body = reply.raw_text or reply.message or ""
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

    elif text.startswith(".font") or text.startswith(".fancy"):
        parts = raw.split(None, 2)
        if len(parts) < 3:
            await event.edit("❌ Usage: `.font <style> <text>`\nStyles: `bubble`, `gothic`, `bold`, `italic`, `mono`, `square`\nExample: `.font gothic Welcome to cyber security`")
            return
        style, ftext = parts[1], parts[2]
        res = _fancy_font(style, ftext)
        await event.edit(res)

    elif text == ".unmuteall":
        count = len(muted_users)
        muted_users.clear()
        save_json(DATA_FILE, {"muted_users": list(muted_users), "banned_users": list(banned_users)})
        await event.edit(f"✅ **Unmuted all `{count}` users** from selfbot memory.")

    elif text == ".unbanall":
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
    if afk.active and not raw_text.startswith("."):
        afk.disable()
        try:
            await event.respond("✅ **AFK auto-disabled** — welcome back!")
        except Exception:
            pass

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
            afk_text = f"{afk.message}\n\n_I have been away for {afk.duration_text()}._"
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
