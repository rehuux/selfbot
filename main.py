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
import traceback
from uuid import uuid4

import requests
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import AuthKeyUnregisteredError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.channels import GetFullChannelRequest, EditAdminRequest

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("selfbot")

# Optional deps
try:
    import aiohttp  # noqa: F401
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

# --- New feature dependencies (all optional — bot degrades gracefully) ---
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
# Environment / config
# ------------------------------------------------------------------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
PHONE = os.environ.get("PHONE", "")  # only used for first-time interactive login

if not API_ID or not API_HASH:
    log.warning("API_ID / API_HASH not set — bot will fail to start until configured.")

DATA_FILE = "selfbot_data.json"
ERROR_LOG_FILE = "errors.log"

# Developer / owner info shown by .dev
DEV_NAME = "Syed Rehan"
DEV_ROLE = "Security Researcher & Ethical Hacker"
DEV_PORTFOLIO = "https://rehuux.vercel.app"
DEV_SKILLS = (
    "CyberSecurity, Telegram Bot Development, "
    "Security/OSINT, Linux, and AI Integration"
)
DEV_GITHUB = "https://github.com/rehuux"  # update to your actual GitHub if different
BOT_VERSION = "3.0.0"
BOT_BUILD = "2026.07"
BOT_START_TIME = time.time()

# Spam command safety cap — prevents accidental account-flagging floods
SPAM_MAX_REPEATS = 20

# --- New feature config ---
TEMP_DIR = "selfbot_temp"
os.makedirs(TEMP_DIR, exist_ok=True)

PORTFOLIO_FILE = "portfolio_data.json"

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
}

# --- Ghost Mode config/state ---
GHOST_STATE_FILE = "ghost_state.json"
GHOST_DELETE_DELAY = 5  # seconds — how long a command's result stays visible

# --- Secret Notes config (AES-256-GCM, local file only) ---
SECRET_NOTES_FILE = "secret_notes.enc"
SECRET_SALT_FILE = "secret_salt.bin"
# Master password comes from an environment variable rather than an
# interactive prompt — a blocking input() at startup would hang the
# process forever on a headless host like Render (no stdin available),
# which would break deployment. Set SECRET_MASTER_PASSWORD before using
# any `.secret` command.
SECRET_MASTER_PASSWORD = os.environ.get("SECRET_MASTER_PASSWORD", "")

# --- Whale Alert config/state ---
WHALE_STATE_FILE = "whale_state.json"
WHALE_CHECK_INTERVAL = 60  # seconds between polls
WHALE_BTC_THRESHOLD_SATS = 5_000_000_000  # ~50 BTC — "unusually large" cutoff
WHALE_ETH_THRESHOLD_WEI = 500 * 10**18  # ~500 ETH
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "")
_seen_whale_txids = set()  # in-memory de-dupe (bounded, cleared periodically)


def load_portfolio():
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_portfolio(p):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(p, f)


portfolio = load_portfolio()


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"muted_users": [], "banned_users": []}


def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f)


data = load_data()
muted_users = set(data.get("muted_users", []))
banned_users = set(data.get("banned_users", []))
auto_accept_active = False
auto_fix_active = True


def log_error(cmd_text, exc):
    entry = (
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CMD={cmd_text!r} ERROR={exc}\n"
        f"{traceback.format_exc()}\n{'-' * 60}\n"
    )
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


# ------------------------------------------------------------------
# Session bootstrap: use a Telethon StringSession from SESSION_STRING
# when available (Render / production — no interactive login needed).
# Falls back to a local SQLite session file for local development.
# ------------------------------------------------------------------
SESSION_STRING = os.environ.get("SESSION_STRING", "").strip()
LOCAL_SESSION_NAME = "selfbot_session"

if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    log.info("Loaded Telethon StringSession from environment.")
else:
    client = TelegramClient(LOCAL_SESSION_NAME, API_ID, API_HASH)
    log.info("Using local SQLite session file.")


# ------------------------------------------------------------------
# AFK SYSTEM
# ------------------------------------------------------------------
AFK_RETRIGGER_SECONDS = 6 * 60 * 60  # 6 hours — re-send AFK message per user after this gap

DEFAULT_AFK_MESSAGE = (
    "Hello, I will be with you shortly (approximately 5–20 minutes). "
    "To help me assist you efficiently, please describe what you are "
    "interested in or what services you require."
)


class AFKState:
    """Holds all AFK-related state in one place.

    `replied_users` maps sender_id -> unix timestamp of the last time we
    auto-replied to them. A user gets a fresh AFK reply if they message
    again after AFK_RETRIGGER_SECONDS (6 hours) has passed since our last
    reply to them — otherwise they're only replied to once, as before.
    """

    def __init__(self):
        self.active = False
        self.start_time = None
        self.message = DEFAULT_AFK_MESSAGE
        self.replied_users = {}  # {user_id: last_reply_unix_ts}

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
        """True if this user hasn't been replied to yet, or their last
        reply was more than 6 hours ago."""
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
        minutes = elapsed // 60
        seconds = elapsed % 60
        if minutes < 1:
            return f"{seconds} seconds"
        return f"{minutes} minute{'s' if minutes != 1 else ''}"


afk = AFKState()


# ------------------------------------------------------------------
# GHOST MODE
# ------------------------------------------------------------------
class GhostModeState:
    """Tracks Ghost Mode on/off + auto-delete delay, persisted to disk so
    the setting survives a restart.

    Honest limitation: Telethon/MTProto sends some acknowledgements at the
    protocol level (e.g. when fetching message history) that a client
    cannot fully suppress. Ghost Mode here does what's actually under our
    control: it never issues explicit typing actions, skips manual
    "mark as read" calls, and auto-deletes command output after a delay.
    """

    def __init__(self):
        self.enabled = False
        self.delete_delay = GHOST_DELETE_DELAY
        self._load()

    def _load(self):
        try:
            with open(GHOST_STATE_FILE, "r") as f:
                d = json.load(f)
            self.enabled = bool(d.get("enabled", False))
            self.delete_delay = int(d.get("delete_delay", GHOST_DELETE_DELAY))
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            pass

    def _save(self):
        try:
            with open(GHOST_STATE_FILE, "w") as f:
                json.dump({"enabled": self.enabled, "delete_delay": self.delete_delay}, f)
        except Exception as e:
            log_error("ghost_state_save", e)

    def enable(self):
        self.enabled = True
        self._save()

    def disable(self):
        self.enabled = False
        self._save()


ghost_mode = GhostModeState()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
async def get_entity(val):
    try:
        if isinstance(val, int):
            return await client.get_entity(val)
        if val.startswith("@"):
            return await client.get_entity(val)
        try:
            return await client.get_entity(int(val))
        except Exception:
            return await client.get_entity(val)
    except Exception:
        return None


async def get_admin_group_ids():
    """Only groups/channels where we are admin — safe for broadcast."""
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
    """All groups/channels (for .gc)."""
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
    """Randomised delay: 5–10s normally, 40s break every 15 messages."""
    if count > 0 and count % 15 == 0:
        await asyncio.sleep(40)
    else:
        await asyncio.sleep(random.uniform(5, 10))


def _ig_info(username):
    """
    Instagram profile lookup.
    Tries instaloader first (if installed), then falls back to a direct
    web_profile_info request. Both methods are best-effort since Instagram
    frequently rate-limits/blocks anonymous requests — failures return a
    clear error message instead of raising.
    """
    username = username.lstrip("@").strip()

    if INSTA_OK:
        try:
            L = instaloader.Instaloader()
            p = instaloader.Profile.from_username(L.context, username)
            return f"""📸 **Instagram — @{p.username}**
✓ **Name:** `{p.full_name or 'N/A'}`
✓ **Username:** @{p.username}
✓ **Followers:** `{p.followers:,}`
✓ **Following:** `{p.followees:,}`
✓ **Posts:** `{p.mediacount:,}`
✓ **Private:** `{'Yes' if p.is_private else 'No'}`
✓ **Verified:** `{'Yes' if p.is_verified else 'No'}`
✓ **Business:** `{'Yes' if p.is_business_account else 'No'}`
✓ **Bio:** `{p.biography or 'None'}`
✓ **Link:** https://instagram.com/{p.username}"""
        except Exception as e:
            log.info(f"instaloader lookup failed for @{username}, falling back: {e}")

    try:
        session = requests.Session()
        headers_get = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        session.get(f"https://www.instagram.com/{username}/", headers=headers_get, timeout=10)
        csrf = session.cookies.get("csrftoken", "")
        r = session.get(
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
                "x-ig-app-id": "936619743392459",
                "x-csrftoken": csrf,
                "x-requested-with": "XMLHttpRequest",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"https://www.instagram.com/{username}/",
                "Origin": "https://www.instagram.com",
            },
            timeout=15,
        )
        if r.status_code == 200:
            payload = r.json()
            user_block = payload.get("data", {}).get("user")
            if not user_block:
                return f"❌ @{username} not found or Instagram returned no profile data."
            u = user_block
            return f"""📸 **Instagram — @{u['username']}**
✓ **Name:** `{u.get("full_name") or 'N/A'}`
✓ **IG ID:** `{u["id"]}`
✓ **Followers:** `{u["edge_followed_by"]["count"]:,}`
✓ **Following:** `{u["edge_follow"]["count"]:,}`
✓ **Posts:** `{u["edge_owner_to_timeline_media"]["count"]:,}`
✓ **Private:** `{'Yes' if u["is_private"] else 'No'}`
✓ **Verified:** `{'Yes' if u["is_verified"] else 'No'}`
✓ **Business:** `{'Yes' if u.get("is_business_account") else 'No'}`
✓ **Bio:** `{u.get("biography") or 'None'}`
✓ **External URL:** `{u.get("external_url") or 'None'}`
✓ **Link:** https://instagram.com/{u['username']}"""
        if r.status_code == 404:
            return f"❌ @{username} doesn't exist or is banned."
        if r.status_code in (401, 403):
            return "❌ Instagram blocked the request (rate limited). Try again in a few minutes."
        return f"❌ Instagram API returned status {r.status_code}."
    except requests.exceptions.Timeout:
        return "❌ Request timed out. Instagram may be slow, try again."
    except Exception as e:
        return f"❌ Failed to fetch info: {e}"


def _translate(text, target_lang):
    """
    Translate text via MyMemory. Source language is detected locally with
    langdetect instead of sending "auto" (MyMemory rejects that with
    "'AUTO' IS AN INVALID SOURCE LANGUAGE"). Falls back to English if
    detection isn't available or fails.
    """
    source_lang = "en"
    if LANGDETECT_OK:
        try:
            source_lang = _detect_lang(text)
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
            translated = d["responseData"]["translatedText"]
            return f"🌐 **[{target_lang.upper()}]** {translated}"
        return f"❌ Translation failed: {d.get('responseDetails', 'unknown error')}"
    except Exception as e:
        return f"❌ Translation error: {e}"


def _weather_info(city):
    """Fetch a compact weather summary via wttr.in (no API key needed)."""
    try:
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
        if r.status_code != 200:
            return f"❌ Couldn't fetch weather for '{city}'."
        d = r.json()
        cur = d["current_condition"][0]
        area = d.get("nearest_area", [{}])[0]
        place = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")
        return f"""🌦 **Weather — {place}, {country}**
✓ **Condition:** `{cur['weatherDesc'][0]['value']}`
✓ **Temperature:** `{cur['temp_C']}°C ({cur['temp_F']}°F)`
✓ **Feels Like:** `{cur['FeelsLikeC']}°C`
✓ **Humidity:** `{cur['humidity']}%`
✓ **Wind:** `{cur['windspeedKmph']} km/h`
✓ **Visibility:** `{cur['visibility']} km`"""
    except Exception as e:
        return f"❌ Weather lookup failed: {e}"


def _crypto_price(coin):
    """Fetch a crypto price via CoinGecko (no API key needed)."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin.lower(), "vs_currencies": "usd,inr", "include_24hr_change": "true"},
            timeout=10,
        )
        d = r.json()
        if coin.lower() not in d:
            return f"❌ Couldn't find a coin called '{coin}'. Try the full name, e.g. `bitcoin`."
        info = d[coin.lower()]
        change = info.get("usd_24h_change", 0)
        arrow = "📈" if change >= 0 else "📉"
        return f"""💰 **{coin.capitalize()} Price**
✓ **USD:** `${info['usd']:,}`
✓ **INR:** `₹{info['inr']:,}`
✓ **24h Change:** {arrow} `{change:.2f}%`"""
    except Exception as e:
        return f"❌ Crypto lookup failed: {e}"


def _dictionary_lookup(word):
    """Fetch a word definition via the free dictionaryapi.dev."""
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=10)
        if r.status_code != 200:
            return f"❌ No definition found for '{word}'."
        entry = r.json()[0]
        meanings = entry.get("meanings", [])
        if not meanings:
            return f"❌ No definition found for '{word}'."
        out = [f"📖 **{entry['word']}**"]
        phonetic = entry.get("phonetic") or ""
        if phonetic:
            out.append(f"_{phonetic}_")
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
    """Fetch a GitHub user's public profile summary."""
    try:
        r = requests.get(f"https://api.github.com/users/{username}", timeout=10)
        if r.status_code == 404:
            return f"❌ GitHub user '{username}' not found."
        if r.status_code != 200:
            return f"❌ GitHub API returned status {r.status_code}."
        u = r.json()
        return f"""🐙 **GitHub — @{u['login']}**
✓ **Name:** `{u.get('name') or 'N/A'}`
✓ **Bio:** `{u.get('bio') or 'None'}`
✓ **Followers:** `{u['followers']:,}`
✓ **Following:** `{u['following']:,}`
✓ **Public Repos:** `{u['public_repos']:,}`
✓ **Location:** `{u.get('location') or 'N/A'}`
✓ **Company:** `{u.get('company') or 'N/A'}`
✓ **Profile:** {u['html_url']}"""
    except Exception as e:
        return f"❌ GitHub lookup failed: {e}"


def _short_url(url):
    """Shorten a URL via is.gd (no API key needed)."""
    try:
        r = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": url},
            timeout=10,
        )
        if r.status_code == 200 and r.text.startswith("http"):
            return f"🔗 Shortened: {r.text.strip()}"
        return f"❌ Couldn't shorten that URL: {r.text.strip()}"
    except Exception as e:
        return f"❌ URL shortening failed: {e}"


def _quote_of_the_day():
    """Fetch a random inspirational quote."""
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=10)
        d = r.json()[0]
        return f"💭 _\"{d['q']}\"_\n— **{d['a']}**"
    except Exception as e:
        return f"❌ Couldn't fetch a quote: {e}"


def _random_joke():
    """Fetch a random clean joke."""
    try:
        r = requests.get(
            "https://official-joke-api.appspot.com/random_joke", timeout=10
        )
        d = r.json()
        return f"😂 {d['setup']}\n\n||{d['punchline']}||"
    except Exception as e:
        return f"❌ Couldn't fetch a joke: {e}"


# ==========================================================================
# NEW FEATURE: MEME FETCHER (.meme)
# ==========================================================================
def _random_meme():
    """Fetch a random meme (image URL + title) from a popular subreddit feed."""
    try:
        r = requests.get("https://meme-api.com/gimme", timeout=10)
        d = r.json()
        if not d.get("url"):
            return None, "❌ Couldn't fetch a meme right now."
        caption = f"😹 **{d.get('title', 'Meme')}**\nr/{d.get('subreddit', 'memes')}"
        return d["url"], caption
    except Exception as e:
        return None, f"❌ Meme fetch failed: {e}"


# ==========================================================================
# NEW FEATURE: TRIVIA (.trivia)
# ==========================================================================
def _random_trivia():
    """Fetch a random trivia question (Open Trivia DB, no key needed)."""
    try:
        r = requests.get(
            "https://opentdb.com/api.php",
            params={"amount": 1, "type": "multiple"},
            timeout=10,
        )
        d = r.json()
        results = d.get("results", [])
        if not results:
            return "❌ Couldn't fetch a trivia question."
        import html
        q = results[0]
        question = html.unescape(q["question"])
        correct = html.unescape(q["correct_answer"])
        category = html.unescape(q["category"])
        return (
            f"🧠 **Trivia — {category}**\n\n{question}\n\n"
            f"||Answer: {correct}||"
        )
    except Exception as e:
        return f"❌ Trivia fetch failed: {e}"


# ==========================================================================
# NEW FEATURE: RANDOM FACT (.fact)
# ==========================================================================
def _random_fact():
    """Fetch a random 'useless fact' (no key needed)."""
    try:
        r = requests.get(
            "https://uselessfacts.jsph.pl/api/v2/facts/random",
            params={"language": "en"},
            timeout=10,
        )
        d = r.json()
        return f"🧾 **Random Fact**\n{d.get('text', 'No fact available.')}"
    except Exception as e:
        return f"❌ Fact fetch failed: {e}"


# ==========================================================================
# NEW FEATURE: HOROSCOPE (.horoscope)
# ==========================================================================
VALID_ZODIAC_SIGNS = {
    "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
    "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
}


def _daily_horoscope(sign):
    sign = sign.lower().strip()
    if sign not in VALID_ZODIAC_SIGNS:
        return f"❌ Unknown sign '{sign}'. Try one of: {', '.join(sorted(VALID_ZODIAC_SIGNS))}"
    try:
        r = requests.get(
            "https://aztro.sameerkumar.website/",
            params={"sign": sign, "day": "today"},
            timeout=10,
        )
        # aztro requires POST in some deployments; fall back to POST if GET fails
        if r.status_code != 200:
            r = requests.post(
                "https://aztro.sameerkumar.website/",
                params={"sign": sign, "day": "today"},
                timeout=10,
            )
        d = r.json()
        return f"""🔮 **Horoscope — {sign.capitalize()}** ({d.get('current_date', 'today')})
{d.get('description', 'N/A')}

✓ **Mood:** `{d.get('mood', 'N/A')}`
✓ **Compatibility:** `{d.get('compatibility', 'N/A')}`
✓ **Lucky Number:** `{d.get('lucky_number', 'N/A')}`
✓ **Lucky Time:** `{d.get('lucky_time', 'N/A')}`"""
    except Exception as e:
        return f"❌ Horoscope fetch failed: {e}"


# ==========================================================================
# NEW FEATURE: COUNTRY INFO (.country)
# ==========================================================================
def _country_info(name):
    try:
        # restcountries.com now REQUIRES an explicit `fields` param — without
        # it, the API returns an error payload instead of country data (this
        # was the actual cause of the earlier "lookup failed: 0" error).
        fields = "name,capital,region,subregion,population,languages,currencies,flag,maps"
        r = requests.get(
            f"https://restcountries.com/v3.1/name/{name}",
            params={"fields": fields},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if r.status_code != 200:
            return f"❌ Country '{name}' not found (HTTP {r.status_code})."

        try:
            payload = r.json()
        except ValueError:
            return "❌ Country lookup failed: API returned an unreadable response."

        # The API can return either a list of matches or an error dict
        # (e.g. {"status":404,"message":"Not Found"}) — handle both so a
        # shape mismatch never surfaces as a raw KeyError to the user.
        if isinstance(payload, dict):
            msg = payload.get("message", "Country not found.")
            return f"❌ Country lookup failed: {msg}"
        if not isinstance(payload, list) or not payload:
            return f"❌ Country '{name}' not found."

        d = payload[0]
        capital = ", ".join(d.get("capital", ["N/A"])) or "N/A"
        currencies = ", ".join(
            f"{v.get('name')} ({v.get('symbol', '')})" for v in d.get("currencies", {}).values()
        ) or "N/A"
        languages = ", ".join(d.get("languages", {}).values()) or "N/A"
        population = d.get("population", 0)
        region = d.get("region", "N/A")
        subregion = d.get("subregion", "N/A")
        maps_link = d.get("maps", {}).get("googleMaps", "")
        flag_emoji = d.get("flag", "")
        common_name = d.get("name", {}).get("common", name)
        official_name = d.get("name", {}).get("official", "N/A")
        return f"""🌍 **{common_name}** {flag_emoji}
✓ **Official Name:** `{official_name}`
✓ **Capital:** `{capital}`
✓ **Region:** `{region} / {subregion}`
✓ **Population:** `{population:,}`
✓ **Languages:** `{languages}`
✓ **Currencies:** `{currencies}`
✓ **Map:** {maps_link}"""
    except requests.exceptions.Timeout:
        return "❌ Country lookup timed out."
    except Exception as e:
        return f"❌ Country lookup failed: {e}"


# ==========================================================================
# NEW FEATURE: ANIME LOOKUP (.anime)
# ==========================================================================
def _anime_info(name):
    last_status = None
    for attempt in range(2):  # try once, retry once on transient failure
        try:
            r = requests.get(
                "https://api.jikan.moe/v4/anime",
                params={"q": name, "limit": 1},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            last_status = r.status_code
            if r.status_code == 429:
                time.sleep(1.5)  # brief backoff, this runs in a worker thread
                continue
            if r.status_code != 200:
                if attempt == 0:
                    time.sleep(1)
                    continue
                return f"❌ Anime lookup failed (HTTP {r.status_code}). Try again shortly."

            try:
                d = r.json()
            except ValueError:
                return "❌ Anime lookup failed: API returned an unreadable response."

            results = d.get("data", [])
            if not results:
                if attempt == 0:
                    time.sleep(1)
                    continue
                return f"❌ Anime '{name}' not found."

            a = results[0]
            genres = ", ".join(g["name"] for g in a.get("genres", [])) or "N/A"
            return f"""🎬 **{a.get('title', name)}**
✓ **Type:** `{a.get('type', 'N/A')}`
✓ **Episodes:** `{a.get('episodes', 'N/A')}`
✓ **Status:** `{a.get('status', 'N/A')}`
✓ **Score:** `{a.get('score', 'N/A')}`
✓ **Genres:** `{genres}`
✓ **Aired:** `{a.get('aired', {}).get('string', 'N/A')}`
✓ **Synopsis:** {(a.get('synopsis') or 'N/A')[:400]}
✓ **URL:** {a.get('url', 'N/A')}"""
        except requests.exceptions.Timeout:
            if attempt == 0:
                continue
            return "❌ Anime lookup timed out."
        except Exception as e:
            log_error(".anime", e)
            if attempt == 0:
                continue
            return f"❌ Anime lookup failed: {e}"

    if last_status == 429:
        return "❌ Anime lookup rate-limited by the API. Please wait a moment and try again."
    return f"❌ Anime '{name}' not found."


# ==========================================================================
# NEW FEATURE: MESSAGE SCHEDULER (.schedule)
# ==========================================================================
def _parse_schedule(raw_args):
    """Parse '<time> <message>' into (send_at_datetime, message) or None.
    Supports: 30s / 30m / 2h / 1d (relative) and 'YYYY-MM-DD HH:MM message'.
    """
    parts = raw_args.split(None, 1)
    if len(parts) < 2:
        return None
    time_part, rest = parts[0], parts[1]
    now = datetime.datetime.now()

    # Relative duration: 30s, 30m, 2h, 1d
    m = re.match(r"^(\d+)(s|m|h|d)$", time_part.lower())
    if m:
        value, unit = int(m.group(1)), m.group(2)
        unit_map = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
        delta = datetime.timedelta(**{unit_map[unit]: value})
        return now + delta, rest

    # Absolute date + time: "2026-08-01 09:00 Hello"
    rest_parts = rest.split(None, 1)
    if len(rest_parts) == 2:
        maybe_time, message = rest_parts
        try:
            dt = datetime.datetime.strptime(f"{time_part} {maybe_time}", "%Y-%m-%d %H:%M")
            return dt, message
        except ValueError:
            pass

    return None


async def _run_scheduled_send(chat_id, message, delay):
    """Background task: sleeps until send time then delivers the message."""
    try:
        await asyncio.sleep(delay)
        await client.send_message(chat_id, message)
    except Exception as e:
        log_error("scheduled_send", e)


# ==========================================================================
# NEW FEATURE: OSINT TOOLKIT (.osint email / username / domain)
# ==========================================================================
def _osint_email(email):
    if "@" not in email or "." not in email.split("@")[-1]:
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
    else:
        out.append("✓ **MX Records:** `dnspython not installed`")

    smtp_result = "Unknown (could not verify)"
    if mx_hosts:
        try:
            import smtplib
            server = smtplib.SMTP(timeout=8)
            server.connect(mx_hosts[0])
            server.helo("gmail.com")
            server.mail("verify@gmail.com")
            code, _resp = server.rcpt(email)
            smtp_result = "Deliverable ✅" if code == 250 else f"Rejected (code {code})"
            server.quit()
        except Exception:
            smtp_result = "Unknown (mail server blocked verification)"
    out.append(f"✓ **SMTP Check:** `{smtp_result}`")

    is_disposable = domain.lower() in DISPOSABLE_EMAIL_DOMAINS
    try:
        r = requests.get(f"https://open.kickbox.com/v1/disposable/{domain}", timeout=8)
        if r.status_code == 200:
            is_disposable = r.json().get("disposable", is_disposable)
    except Exception:
        pass
    out.append(f"✓ **Disposable:** `{'Yes ⚠️' if is_disposable else 'No'}`")
    out.append(f"✓ **Domain:** `{domain}`")
    return "\n".join(out)


def _osint_username(username):
    out = [f"👤 **Username OSINT — {username}**"]
    headers = {"User-Agent": "Mozilla/5.0"}
    for site, url_tpl in USERNAME_CHECK_SITES.items():
        url = url_tpl.format(u=username)
        found = False
        try:
            r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            found = r.status_code == 200
        except Exception:
            found = False
        out.append(f"{'✅' if found else '❌'} **{site}:** {url}")
    return "\n".join(out)


def _osint_domain(domain):
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0].strip()
    out = [f"🌐 **Domain OSINT — {domain}**"]

    ip_addr = None
    try:
        ip_addr = socket.gethostbyname(domain)
        out.append(f"✓ **IP:** `{ip_addr}`")
    except Exception:
        out.append("✓ **IP:** `Could not resolve`")

    if DNS_OK:
        for rtype in ("A", "NS", "TXT"):
            try:
                answers = dns.resolver.resolve(domain, rtype, lifetime=8)
                vals = [str(a) for a in answers][:3]
                out.append(f"✓ **{rtype} Records:** `{', '.join(vals)}`")
            except Exception:
                pass
    else:
        out.append("✓ **DNS:** `dnspython not installed`")

    if WHOIS_OK:
        try:
            w = pywhois.whois(domain)
            out.append(f"✓ **Registrar:** `{w.registrar or 'N/A'}`")
            out.append(f"✓ **Created:** `{w.creation_date}`")
            out.append(f"✓ **Expires:** `{w.expiration_date}`")
        except Exception:
            out.append("✓ **WHOIS:** `Lookup failed`")
    else:
        out.append("✓ **WHOIS:** `python-whois not installed`")

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert.get("issuer", []))
                out.append(f"✓ **SSL Issuer:** `{issuer.get('organizationName', 'N/A')}`")
                out.append(f"✓ **SSL Expiry:** `{cert.get('notAfter', 'N/A')}`")
    except Exception:
        out.append("✓ **SSL:** `Could not verify`")

    if ip_addr:
        try:
            r = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=8)
            d = r.json()
            if d.get("status") == "success":
                out.append(f"✓ **Hosting/ISP:** `{d.get('isp', 'N/A')}`")
                out.append(f"✓ **Location:** `{d.get('city', '')}, {d.get('country', '')}`")
        except Exception:
            pass

    try:
        r = requests.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=10)
        if r.status_code == 200:
            entries = r.json()
            subs = sorted(set(e["name_value"].split("\n")[0] for e in entries))[:8]
            if subs:
                out.append(f"✓ **Subdomains (sample):** `{', '.join(subs)}`")
    except Exception:
        pass

    return "\n".join(out)


# ==========================================================================
# NEW FEATURE: IP LOOKUP (.ip)
# ==========================================================================
def _ip_lookup(ip):
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}"
            "?fields=status,message,country,regionName,city,isp,timezone,lat,lon,as,proxy,query",
            timeout=10,
        )
        d = r.json()
        if d.get("status") != "success":
            return f"❌ Lookup failed: {d.get('message', 'unknown error')}"
        maps_link = f"https://www.google.com/maps?q={d['lat']},{d['lon']}"
        vpn = "Yes ⚠️" if d.get("proxy") else "Not detected"
        return f"""🌍 **IP Lookup — {d['query']}**
✓ **Country:** `{d.get('country', 'N/A')}`
✓ **Region:** `{d.get('regionName', 'N/A')}`
✓ **City:** `{d.get('city', 'N/A')}`
✓ **ISP:** `{d.get('isp', 'N/A')}`
✓ **ASN:** `{d.get('as', 'N/A')}`
✓ **Timezone:** `{d.get('timezone', 'N/A')}`
✓ **Coordinates:** `{d.get('lat')}, {d.get('lon')}`
✓ **VPN/Proxy:** `{vpn}`
✓ **Map:** {maps_link}"""
    except requests.exceptions.Timeout:
        return "❌ IP lookup timed out."
    except Exception as e:
        return f"❌ IP lookup failed: {e}"


# ==========================================================================
# NEW FEATURE: SCAM URL DETECTOR (.scan)
# ==========================================================================
def _scan_url(url):
    if not url.startswith("http"):
        url = "https://" + url
    score = 0
    reasons = []
    hostname = url.split("//")[-1].split("/")[0].split(":")[0]

    if url.startswith("https://"):
        reasons.append("✅ Uses HTTPS")
    else:
        score += 20
        reasons.append("⚠️ No HTTPS")

    final_url = url
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        redirect_count = len(r.history)
        final_url = r.url
        if redirect_count > 2:
            score += 15
            reasons.append(f"⚠️ {redirect_count} redirects")
        else:
            reasons.append(f"✅ {redirect_count} redirect(s)")
    except requests.exceptions.Timeout:
        score += 10
        reasons.append("⚠️ Site timed out")
    except Exception:
        score += 10
        reasons.append("⚠️ Site unreachable")

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname):
                pass
        reasons.append("✅ Valid SSL certificate")
    except Exception:
        score += 20
        reasons.append("⚠️ SSL certificate issue")

    if WHOIS_OK:
        try:
            w = pywhois.whois(hostname)
            created = w.creation_date
            if isinstance(created, list):
                created = created[0]
            if created:
                age_days = (datetime.datetime.now() - created).days
                if age_days < 180:
                    score += 25
                    reasons.append(f"⚠️ Domain is new ({age_days} days old)")
                else:
                    reasons.append(f"✅ Domain age: {age_days} days")
        except Exception:
            reasons.append("ℹ️ Could not verify domain age")
    else:
        reasons.append("ℹ️ python-whois not installed — skipping domain age check")

    suspicious_words = ["login", "verify", "secure", "account", "update", "free", "bonus", "win"]
    hits = [w for w in suspicious_words if w in url.lower()]
    if hits:
        score += 10 * len(hits)
        reasons.append(f"⚠️ Suspicious keywords: {', '.join(hits)}")

    vt_key = os.environ.get("VIRUSTOTAL_API_KEY", "")
    if vt_key:
        try:
            import base64
            url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            r = requests.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers={"x-apikey": vt_key},
                timeout=10,
            )
            if r.status_code == 200:
                stats = r.json()["data"]["attributes"]["last_analysis_stats"]
                malicious = stats.get("malicious", 0)
                if malicious > 0:
                    score += 40
                    reasons.append(f"🚨 VirusTotal: {malicious} engines flagged this URL")
                else:
                    reasons.append("✅ VirusTotal: clean")
        except Exception:
            pass

    score = min(score, 100)
    if score < 30:
        risk = "🟢 Low Risk"
    elif score < 60:
        risk = "🟡 Medium Risk"
    else:
        risk = "🔴 High Risk"

    body = "\n".join(reasons)
    return (
        f"🔍 **Scam Scan — {url}**\n"
        f"**Final URL:** `{final_url}`\n"
        f"**Risk Level:** {risk} (`{score}/100`)\n\n"
        f"{body}"
    )


# ==========================================================================
# NEW FEATURE: CRYPTO PORTFOLIO (.portfolio)
# ==========================================================================
def _portfolio_prices(coins):
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(coins), "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=10,
        )
        return r.json()
    except Exception:
        return {}


def _format_portfolio():
    if not portfolio:
        return "📊 Your portfolio is empty. Add coins with `.portfolio add bitcoin 2`"
    prices = _portfolio_prices(list(portfolio.keys()))
    lines = ["📊 **Crypto Portfolio**\n"]
    total_value = 0.0
    for coin, amount in portfolio.items():
        info = prices.get(coin, {})
        price = info.get("usd", 0)
        change = info.get("usd_24h_change", 0)
        value = price * amount
        total_value += value
        arrow = "📈" if change >= 0 else "📉"
        lines.append(
            f"• **{coin.capitalize()}**: `{amount}` @ `${price:,.2f}` = "
            f"`${value:,.2f}` {arrow} `{change:.2f}%`"
        )
    lines.append(f"\n💰 **Total Portfolio Value:** `${total_value:,.2f}`")
    return "\n".join(lines)


# ==========================================================================
# NEW FEATURE: GITHUB REPO STATS (.repo)
# ==========================================================================
def _repo_stats(repo_path):
    try:
        r = requests.get(f"https://api.github.com/repos/{repo_path}", timeout=10)
        if r.status_code == 404:
            return f"❌ Repository '{repo_path}' not found."
        if r.status_code != 200:
            return f"❌ GitHub API returned status {r.status_code}."
        d = r.json()

        contributors_count = "N/A"
        try:
            cr = requests.get(
                f"https://api.github.com/repos/{repo_path}/contributors",
                params={"per_page": 1, "anon": "true"},
                timeout=10,
            )
            link = cr.headers.get("Link", "")
            m = re.search(r'page=(\d+)>; rel="last"', link)
            if m:
                contributors_count = m.group(1)
            elif cr.status_code == 200:
                contributors_count = str(len(cr.json()))
        except Exception:
            pass

        top_lang = "N/A"
        try:
            lr = requests.get(f"https://api.github.com/repos/{repo_path}/languages", timeout=10)
            if lr.status_code == 200:
                langs = lr.json()
                total = sum(langs.values()) or 1
                if langs:
                    top = max(langs.items(), key=lambda x: x[1])
                    top_lang = f"{top[0]} ({top[1] / total * 100:.1f}%)"
        except Exception:
            pass

        latest_release = "N/A"
        try:
            rr = requests.get(f"https://api.github.com/repos/{repo_path}/releases/latest", timeout=10)
            if rr.status_code == 200:
                latest_release = rr.json().get("tag_name", "N/A")
        except Exception:
            pass

        size_mb = d.get("size", 0) / 1024
        license_name = d.get("license", {}).get("name") if d.get("license") else "N/A"
        return f"""🐙 **GitHub Repo — {d['full_name']}**
⭐ **Stars:** `{d['stargazers_count']:,}`
🍴 **Forks:** `{d['forks_count']:,}`
👀 **Watchers:** `{d['watchers_count']:,}`
🐞 **Open Issues:** `{d['open_issues_count']:,}`
💻 **Language:** `{d.get('language') or 'N/A'}`
📊 **Top Language:** `{top_lang}`
📄 **License:** `{license_name}`
📦 **Size:** `{size_mb:.2f} MB`
🏷 **Latest Release:** `{latest_release}`
🌿 **Default Branch:** `{d.get('default_branch', 'N/A')}`
📅 **Created:** `{d.get('created_at', 'N/A')[:10]}`
🔄 **Updated:** `{d.get('updated_at', 'N/A')[:10]}`
👥 **Contributors:** `{contributors_count}`
🔗 **URL:** {d['html_url']}"""
    except requests.exceptions.Timeout:
        return "❌ GitHub lookup timed out."
    except Exception as e:
        return f"❌ Repo lookup failed: {e}"


# ==========================================================================
# NEW FEATURE: OCR (.ocr — reply to an image)
# ==========================================================================
_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["en", "hi"], gpu=False)
    return _easyocr_reader


def _run_ocr(image_path):
    """Extract text from an image using EasyOCR (preferred) or Tesseract.
    Returns extracted text, None if no text found, or 'ENGINE_MISSING'."""
    if EASYOCR_OK:
        try:
            reader = _get_easyocr_reader()
            results = reader.readtext(image_path, detail=0)
            text = "\n".join(results).strip()
            return text or None
        except Exception as e:
            log_error("easyocr", e)
    if TESSERACT_OK:
        try:
            img = Image.open(image_path)
            try:
                text = pytesseract.image_to_string(img, lang="eng+hin").strip()
            except Exception:
                # Hindi trained data may not be installed — fall back to English only
                text = pytesseract.image_to_string(img, lang="eng").strip()
            return text or None
        except Exception as e:
            log_error("pytesseract", e)
    if not EASYOCR_OK and not TESSERACT_OK:
        return "ENGINE_MISSING"
    return None


# ==========================================================================
# NEW FEATURE: CHAT ANALYTICS (.analytics)
# ==========================================================================
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "in",
    "it", "i", "you", "for", "on", "with", "this", "that", "be", "have",
    "at", "not", "but", "or", "as", "we", "they", "he", "she", "my", "your",
    "kya", "hai", "ke", "ki", "ka", "hi", "to", "me", "ho", "nahi", "aur",
}


async def _build_chat_analytics(chat_id, limit=1000):
    """Scan up to `limit` recent messages in a chat and build a stats
    summary. Runs fully async (client.iter_messages) so it never blocks
    the event loop, and caps the scan so it stays fast on large chats.
    """
    counts = {
        "messages": 0, "media": 0, "links": 0, "files": 0,
        "gifs": 0, "stickers": 0, "voice": 0,
    }
    sender_counts = {}
    word_counts = {}
    emoji_counts = {}
    hour_counts = [0] * 24
    total_chars = 0
    text_msg_count = 0

    async for msg in client.iter_messages(chat_id, limit=limit):
        counts["messages"] += 1

        sender_name = "Unknown"
        try:
            if msg.sender:
                sender_name = getattr(msg.sender, "first_name", None) or \
                    getattr(msg.sender, "title", None) or "Unknown"
        except Exception:
            pass
        sender_counts[sender_name] = sender_counts.get(sender_name, 0) + 1

        if msg.date:
            hour_counts[msg.date.hour] += 1

        if msg.media:
            counts["media"] += 1
            if getattr(msg, "voice", None):
                counts["voice"] += 1
            elif getattr(msg, "gif", None):
                counts["gifs"] += 1
            elif getattr(msg, "sticker", None):
                counts["stickers"] += 1
            elif getattr(msg, "document", None):
                counts["files"] += 1

        if msg.text:
            text_msg_count += 1
            total_chars += len(msg.text)
            if re.search(r"https?://", msg.text):
                counts["links"] += 1
            for w in re.findall(r"[a-zA-Z]{3,}", msg.text.lower()):
                if w not in _STOPWORDS:
                    word_counts[w] = word_counts.get(w, 0) + 1
            for e in _EMOJI_PATTERN.findall(msg.text):
                for ch in e:
                    emoji_counts[ch] = emoji_counts.get(ch, 0) + 1

    top_senders = sorted(sender_counts.items(), key=lambda x: -x[1])[:10]
    top_words = sorted(word_counts.items(), key=lambda x: -x[1])[:5]
    top_emojis = sorted(emoji_counts.items(), key=lambda x: -x[1])[:5]
    peak_hour = max(range(24), key=lambda h: hour_counts[h]) if any(hour_counts) else None
    avg_len = (total_chars / text_msg_count) if text_msg_count else 0

    return {
        "counts": counts,
        "top_senders": top_senders,
        "top_words": top_words,
        "top_emojis": top_emojis,
        "hour_counts": hour_counts,
        "peak_hour": peak_hour,
        "avg_len": avg_len,
    }


def _format_analytics(data):
    c = data["counts"]
    lines = ["━━━━━━━━━━━━━━━━━━", "📊 **CHAT ANALYTICS**", "━━━━━━━━━━━━━━━━━━", ""]
    lines.append(f"💬 **Messages:** `{c['messages']}`")
    lines.append(f"🖼 **Media:** `{c['media']}`")
    lines.append(f"🔗 **Links:** `{c['links']}`")
    lines.append(f"📁 **Files:** `{c['files']}`")
    lines.append(f"🎞 **GIFs:** `{c['gifs']}`")
    lines.append(f"🎟 **Stickers:** `{c['stickers']}`")
    lines.append(f"🎙 **Voice Messages:** `{c['voice']}`")
    lines.append("")

    if data["top_senders"]:
        lines.append(f"👑 **Most Active User:** `{data['top_senders'][0][0]}`")
    if data["top_words"]:
        words_str = ", ".join(f"{w} ({n})" for w, n in data["top_words"])
        lines.append(f"🔤 **Most Common Words:** {words_str}")
    if data["top_emojis"]:
        emoji_str = " ".join(f"{e}×{n}" for e, n in data["top_emojis"])
        lines.append(f"😀 **Emoji Usage:** {emoji_str}")
    lines.append(f"📏 **Average Message Length:** `{data['avg_len']:.0f}` chars")
    if data["peak_hour"] is not None:
        lines.append(f"⏰ **Peak Active Hour:** `{data['peak_hour']:02d}:00`")
    lines.append("")

    if data["top_senders"]:
        lines.append("🏆 **Top Senders:**")
        for i, (name, n) in enumerate(data["top_senders"], start=1):
            lines.append(f"  {i}. {name} — `{n}` msgs")
        lines.append("")

    # Simple text-based bar chart of hourly activity
    max_count = max(data["hour_counts"]) or 1
    lines.append("📈 **Activity by Hour:**")
    for h in range(0, 24, 3):
        bucket = sum(data["hour_counts"][h:h + 3])
        bar_len = int((bucket / (max_count * 3)) * 20) if max_count else 0
        bar = "█" * max(bar_len, 0)
        lines.append(f"  {h:02d}-{h + 3:02d}h │{bar}")
    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# ==========================================================================
# NEW FEATURE: MOOD DETECTOR (.mood) — lightweight local lexicon NLP
# ==========================================================================
MOOD_LEXICON = {
    "Happy": ["happy", "glad", "joy", "great", "awesome", "yay", "😊", "😁", "😄", "love", "nice", "good"],
    "Sad": ["sad", "cry", "crying", "unhappy", "depressed", "😢", "😭", "sorry", "miss", "lonely"],
    "Angry": ["angry", "mad", "hate", "furious", "annoyed", "😠", "😡", "rage", "pissed"],
    "Fear": ["scared", "afraid", "fear", "worried", "anxious", "nervous", "😨", "😰", "terrified"],
    "Excited": ["excited", "can't wait", "omg", "wow", "amazing", "hyped", "🔥", "🎉", "let's go"],
    "Sarcastic": ["yeah right", "sure jan", "totally", "oh great", "wow really", "as if", "lol sure"],
    "Romantic": ["love you", "miss you", "babe", "darling", "❤️", "😍", "kiss", "sweetheart"],
    "Professional": ["regards", "kindly", "please find", "meeting", "deadline", "report", "attached"],
    "Funny": ["lol", "lmao", "haha", "😂", "🤣", "funny", "joke", "rofl"],
    "Neutral": [],
}

MOOD_EMOJI = {
    "Happy": "😊", "Sad": "😢", "Angry": "😠", "Fear": "😨", "Excited": "🤩",
    "Sarcastic": "😏", "Romantic": "❤️", "Professional": "💼", "Funny": "😂",
    "Neutral": "😐",
}


def _analyze_mood(text):
    """Very lightweight keyword-frequency mood classifier — no ML model,
    no external API, runs instantly and stays memory-light."""
    if not text or not text.strip():
        return None
    lower = text.lower()
    scores = {}
    for mood, keywords in MOOD_LEXICON.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits:
            scores[mood] = hits

    if not scores:
        return {"mood": "Neutral", "confidence": 60, "reasons": ["No strong emotional cues detected"]}

    best_mood = max(scores, key=scores.get)
    total_hits = sum(scores.values())
    confidence = min(95, 55 + int((scores[best_mood] / max(total_hits, 1)) * 40))

    reasons = []
    if scores[best_mood] >= 2:
        reasons.append("Multiple matching keywords")
    reasons.append(f"Wording matched the '{best_mood.lower()}' pattern")
    if "!" in text:
        reasons.append("Exclamation marks suggest heightened emotion")
    if _EMOJI_PATTERN.search(text):
        reasons.append("Emoji usage supports the tone")

    return {"mood": best_mood, "confidence": confidence, "reasons": reasons}


def _format_mood(result):
    if not result:
        return "❌ No text found in that message to analyze."
    emoji = MOOD_EMOJI.get(result["mood"], "🧠")
    reasons_str = "\n".join(f"• {r}" for r in result["reasons"])
    return (
        "━━━━━━━━━━━━\n"
        "🧠 **Mood Analysis**\n\n"
        "**Detected:**\n"
        f"{emoji} {result['mood']}\n\n"
        "**Confidence:**\n"
        f"{result['confidence']}%\n\n"
        "**Reason:**\n"
        f"{reasons_str}\n"
        "━━━━━━━━━━━━"
    )


# ==========================================================================
# NEW FEATURE: SECRET NOTES (.secret) — AES-256-GCM, local file only
# ==========================================================================
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
    """Returns a list of note strings, decrypted in-memory only.
    Never logs or persists plaintext."""
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
    plaintext = json.dumps(notes).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    with open(SECRET_NOTES_FILE, "wb") as f:
        f.write(nonce + ciphertext)


# ==========================================================================
# NEW FEATURE: NETWORK MONITOR (.net)
# ==========================================================================
async def _ping_host(host="8.8.8.8", count=4, timeout=8):
    """Async, non-blocking ping using the system ping binary via subprocess.
    Returns (avg_latency_ms, packet_loss_pct) or (None, None) on failure.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), "-W", "2", host,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode(errors="ignore")

        loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
        loss = float(loss_match.group(1)) if loss_match else None

        rtt_match = re.search(r"= [\d.]+/([\d.]+)/", output)
        avg_latency = float(rtt_match.group(1)) if rtt_match else None

        return avg_latency, loss
    except Exception as e:
        log_error("ping", e)
        return None, None


def _speedtest_sync():
    """Blocking speed test — always run via run_in_executor."""
    if not SPEEDTEST_OK:
        return None
    try:
        st = speedtest_module.Speedtest()
        st.get_best_server()
        download_mbps = st.download() / 1_000_000
        upload_mbps = st.upload() / 1_000_000
        return {"download": download_mbps, "upload": upload_mbps}
    except Exception as e:
        log_error("speedtest", e)
        return None


async def _build_network_report():
    """Gathers IP/ISP info, ping, and (optionally) speed test results."""
    ping_task = asyncio.create_task(_ping_host())

    loop = asyncio.get_event_loop()
    ip_info = {}
    try:
        r = await loop.run_in_executor(
            None,
            lambda: requests.get(
                "http://ip-api.com/json/?fields=status,country,isp,query,timezone,as,mobile,proxy",
                timeout=10,
            ),
        )
        ip_info = r.json()
    except Exception as e:
        log_error("net_ip_lookup", e)

    speed = None
    if SPEEDTEST_OK:
        try:
            speed = await asyncio.wait_for(
                loop.run_in_executor(None, _speedtest_sync), timeout=45
            )
        except Exception:
            speed = None

    avg_latency, loss = await ping_task

    dns_check = "OK"
    try:
        socket.gethostbyname("google.com")
    except Exception:
        dns_check = "Failed"

    network_type = "Mobile/Proxy detected" if ip_info.get("mobile") or ip_info.get("proxy") else "Standard"

    return {
        "internet_status": "🟢 Online" if ip_info.get("status") == "success" else "🔴 Unreachable",
        "ping": f"{avg_latency:.1f} ms" if avg_latency is not None else "N/A",
        "loss": f"{loss:.0f}%" if loss is not None else "N/A",
        "public_ip": ip_info.get("query", "N/A"),
        "isp": ip_info.get("isp", "N/A"),
        "asn": ip_info.get("as", "N/A"),
        "dns": dns_check,
        "network_type": network_type,
        "country": ip_info.get("country", "N/A"),
        "timezone": ip_info.get("timezone", "N/A"),
        "download": f"{speed['download']:.1f} Mbps" if speed else "N/A (speedtest not installed)",
        "upload": f"{speed['upload']:.1f} Mbps" if speed else "N/A (speedtest not installed)",
    }


def _format_network_report(r):
    return f"""━━━━━━━━━━━━━━━━━━
🌐 **NETWORK MONITOR**
━━━━━━━━━━━━━━━━━━
✓ **Internet Status:** {r['internet_status']}
✓ **Ping:** `{r['ping']}`
✓ **Packet Loss:** `{r['loss']}`
✓ **Public IP:** `{r['public_ip']}`
✓ **ISP:** `{r['isp']}`
✓ **ASN:** `{r['asn']}`
✓ **DNS:** `{r['dns']}`
✓ **Network Type:** `{r['network_type']}`
✓ **Country:** `{r['country']}`
✓ **Timezone:** `{r['timezone']}`
✓ **Download Speed:** `{r['download']}`
✓ **Upload Speed:** `{r['upload']}`
━━━━━━━━━━━━━━━━━━"""


# ==========================================================================
# NEW FEATURE: CRYPTO WHALE ALERT (.whale on/off)
# ==========================================================================
def _load_whale_state():
    try:
        with open(WHALE_STATE_FILE, "r") as f:
            return json.load(f).get("enabled", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def _save_whale_state(enabled):
    try:
        with open(WHALE_STATE_FILE, "w") as f:
            json.dump({"enabled": enabled}, f)
    except Exception as e:
        log_error("whale_state_save", e)


async def _check_btc_whales():
    """Poll blockchain.info's public unconfirmed-transactions feed (no API
    key needed) for unusually large BTC transfers."""
    alerts = []
    loop = asyncio.get_event_loop()
    try:
        r = await loop.run_in_executor(
            None, lambda: requests.get("https://blockchain.info/unconfirmed-transactions?format=json", timeout=10)
        )
        d = r.json()
        for tx in d.get("txs", []):
            total_out = sum(o.get("value", 0) for o in tx.get("out", []))
            if total_out >= WHALE_BTC_THRESHOLD_SATS:
                txid = tx.get("hash")
                if txid in _seen_whale_txids:
                    continue
                _seen_whale_txids.add(txid)
                btc_amount = total_out / 1e8
                alerts.append({
                    "coin": "BTC",
                    "amount": f"{btc_amount:.4f} BTC",
                    "txid": txid,
                    "explorer": f"https://www.blockchain.com/explorer/transactions/btc/{txid}",
                })
    except Exception as e:
        log_error("whale_btc_check", e)
    return alerts


async def _check_eth_whales():
    """Poll Etherscan for large recent ETH transfers. Requires the free
    ETHERSCAN_API_KEY env var — silently skipped if not set."""
    if not ETHERSCAN_API_KEY:
        return []
    alerts = []
    loop = asyncio.get_event_loop()
    try:
        r = await loop.run_in_executor(
            None,
            lambda: requests.get(
                "https://api.etherscan.io/api",
                params={
                    "module": "account", "action": "txlist", "address": "0x0000000000000000000000000000000000000000",
                    "sort": "desc", "apikey": ETHERSCAN_API_KEY,
                },
                timeout=10,
            ),
        )
        # Note: Etherscan doesn't offer a direct "largest recent tx" feed on
        # the free tier — a full whale-tracker would need a paid/streaming
        # provider. This best-effort check is left as a safe no-op scaffold
        # so ETH monitoring can be extended later without touching other code.
    except Exception as e:
        log_error("whale_eth_check", e)
    return alerts


async def _get_crypto_usd_price(symbol):
    loop = asyncio.get_event_loop()
    coin_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin"}
    try:
        r = await loop.run_in_executor(
            None,
            lambda: requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_map.get(symbol, ""), "vs_currencies": "usd"},
                timeout=8,
            ),
        )
        return r.json().get(coin_map.get(symbol, ""), {}).get("usd", 0)
    except Exception:
        return 0


async def _whale_monitor_loop():
    """Background task — polls free public blockchain APIs on an interval
    and DMs the owner when an unusually large transfer is detected. Runs
    independently of the command dispatcher so it never blocks other
    commands. Automatically stops when whale_alert_active is turned off.
    """
    global whale_alert_active
    log.info("Whale Alert monitor started.")
    while whale_alert_active:
        try:
            btc_alerts = await _check_btc_whales()
            eth_alerts = await _check_eth_whales()
            for alert in btc_alerts + eth_alerts:
                price = await _get_crypto_usd_price(alert["coin"])
                usd_value = "N/A"
                try:
                    amount_val = float(alert["amount"].split()[0])
                    usd_value = f"${amount_val * price:,.0f}"
                except Exception:
                    pass
                msg = (
                    "🐋 **Whale Alert!**\n\n"
                    f"**Coin:** {alert['coin']}\n"
                    f"**Amount:** {alert['amount']}\n"
                    f"**~USD Value:** {usd_value}\n"
                    f"**Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**TxID:** `{alert['txid']}`\n"
                    f"**Explorer:** {alert['explorer']}"
                )
                try:
                    me = await client.get_me()
                    await client.send_message(me.id, msg)
                except Exception as e:
                    log_error("whale_notify", e)

            # Keep the de-dupe set from growing unbounded over a long uptime
            if len(_seen_whale_txids) > 5000:
                _seen_whale_txids.clear()
        except Exception as e:
            log_error("whale_monitor_loop", e)
        await asyncio.sleep(WHALE_CHECK_INTERVAL)
    log.info("Whale Alert monitor stopped.")


whale_alert_active = _load_whale_state()
_whale_task = None


# ==========================================================================
# NEW FEATURE: FLAIR (.flair) — honest custom name decoration
# ==========================================================================
# NOTE: this intentionally does NOT mimic Telegram's official verification
# checkmark or any other platform trust indicator. It's a purely cosmetic
# name decoration, always shown with a disclaimer, so it can never be
# mistaken for an official "verified" status.
FLAIR_STATE_FILE = "flair_state.json"
FLAIR_STYLES = {
    "1": {"label": "Premium", "template": "⚡ {name}", "desc": "Lightning-bolt premium style"},
    "2": {"label": "Elite", "template": "🔥 {name} 🔥", "desc": "Flame-accented elite style"},
    "3": {"label": "Pro", "template": "💎 {name} [PRO]", "desc": "Diamond-accented pro tag"},
}
FLAIR_DISCLAIMER = "⚠️ _This is a custom decorative flair — not an official Telegram verification badge._"


def _load_flair_state():
    try:
        with open(FLAIR_STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_flair_state(state):
    with open(FLAIR_STATE_FILE, "w") as f:
        json.dump(state, f)


def _build_flair_preview_all(current_name):
    lines = ["🎨 **Flair Preview** _(not applied yet)_\n"]
    for key, style in FLAIR_STYLES.items():
        preview = style["template"].format(name=current_name)
        lines.append(f"**{key}. {style['label']}** — {style['desc']}\n`{preview}`\n")
    lines.append(f"Use `.flair apply <1/2/3>` to apply, or `.flair <1/2/3>` to preview one.")
    lines.append(f"\n{FLAIR_DISCLAIMER}")
    return "\n".join(lines)


def _build_flair_preview_one(key, current_name):
    style = FLAIR_STYLES.get(key)
    if not style:
        return "❌ Invalid style. Use `.flair 1`, `.flair 2`, or `.flair 3`."
    preview = style["template"].format(name=current_name)
    return (
        f"🎨 **Flair Preview — {style['label']}**\n`{preview}`\n\n"
        f"Use `.flair apply {key}` to actually apply this to your display name.\n\n"
        f"{FLAIR_DISCLAIMER}"
    )


# ==========================================================================
# NEW FEATURE: QR CODE SCANNER (.scanqr) — reply to an image containing a QR
# ==========================================================================
def _decode_qr(image_path):
    """Decode a QR code from a local image via a free public API
    (no local heavy image-processing libs needed)."""
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                "https://api.qrserver.com/v1/read-qr-code/",
                files={"file": f},
                timeout=15,
            )
        if r.status_code != 200:
            return f"❌ QR decode failed (HTTP {r.status_code})."
        data = r.json()
        symbol = data[0].get("symbol", [{}])[0]
        if symbol.get("error"):
            return "❌ No QR code found in that image."
        return symbol.get("data") or "❌ No QR code found in that image."
    except requests.exceptions.Timeout:
        return "❌ QR decode timed out."
    except Exception as e:
        return f"❌ QR decode failed: {e}"


# ==========================================================================
# NEW FEATURE: HASH GENERATOR (.hash) — local, instant, no API needed
# ==========================================================================
def _generate_hashes(text):
    import hashlib
    data = text.encode("utf-8")
    return {
        "MD5": hashlib.md5(data).hexdigest(),
        "SHA1": hashlib.sha1(data).hexdigest(),
        "SHA256": hashlib.sha256(data).hexdigest(),
        "SHA512": hashlib.sha512(data).hexdigest(),
    }


def _format_hashes(text, hashes):
    lines = [f"🔑 **Hashes for:** `{text[:50]}{'...' if len(text) > 50 else ''}`\n"]
    for algo, value in hashes.items():
        lines.append(f"**{algo}:**\n`{value}`\n")
    return "\n".join(lines)


# ==========================================================================
# NEW FEATURE: CURRENCY CONVERTER (.currency)
# ==========================================================================
def _convert_currency(amount, from_cur, to_cur):
    try:
        r = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{from_cur.upper()}",
            timeout=10,
        )
        if r.status_code != 200:
            return f"❌ Currency lookup failed (HTTP {r.status_code}). Check the currency codes."
        d = r.json()
        rates = d.get("rates", {})
        to_cur_upper = to_cur.upper()
        if to_cur_upper not in rates:
            return f"❌ Unknown currency code '{to_cur_upper}'."
        rate = rates[to_cur_upper]
        converted = amount * rate
        return (
            f"💱 **Currency Conversion**\n\n"
            f"`{amount:,.2f} {from_cur.upper()}` = `{converted:,.2f} {to_cur_upper}`\n"
            f"**Rate:** `1 {from_cur.upper()} = {rate:.4f} {to_cur_upper}`"
        )
    except requests.exceptions.Timeout:
        return "❌ Currency conversion timed out."
    except Exception as e:
        return f"❌ Currency conversion failed: {e}"


# ==========================================================================
# NEW FEATURE: BEAUTIFUL HELP UI (.help / .commands / .dev / .help <command>)
# ==========================================================================
# Commands grouped by category for the overview screen.
# ==========================================================================
# NEW FEATURE: CUSTOM FLAIR BADGE (.flair) — honest, non-impersonating style
# ==========================================================================
# These are decorative personal-style badges only. They intentionally do
# NOT mimic Telegram's actual verification checkmark or any official trust
# indicator — the goal is self-expression, not making anyone think this is
# an officially verified account.
FLAIR_STYLES = {
    "1": {"name": "⚡ Bolt", "template": "⚡ {name}"},
    "2": {"name": "🛠 Builder", "template": "🛠 {name} | dev"},
    "3": {"name": "🚀 Rocket", "template": "🚀 {name}"},
}


def _flair_preview(style_key, current_name):
    style = FLAIR_STYLES.get(style_key)
    if not style:
        return None
    preview = style["template"].format(name=current_name)
    return preview


# ==========================================================================
# BONUS FEATURES: PASSWORD GENERATOR, BASE64 TOOL, HASH CALCULATOR
# ==========================================================================
import string as _string_mod
import base64 as _base64_mod
import hashlib as _hashlib_mod


def _generate_password(length=16):
    length = max(8, min(length, 64))  # sane bounds
    alphabet = _string_mod.ascii_letters + _string_mod.digits + "!@#$%^&*()-_=+"
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def _base64_tool(action, text):
    try:
        if action == "encode":
            return _base64_mod.b64encode(text.encode("utf-8")).decode("utf-8")
        elif action == "decode":
            return _base64_mod.b64decode(text.encode("utf-8")).decode("utf-8", errors="replace")
        return None
    except Exception as e:
        return f"❌ Base64 {action} failed: {e}"


def _hash_text(text):
    return {
        "MD5": _hashlib_mod.md5(text.encode("utf-8")).hexdigest(),
        "SHA1": _hashlib_mod.sha1(text.encode("utf-8")).hexdigest(),
        "SHA256": _hashlib_mod.sha256(text.encode("utf-8")).hexdigest(),
    }


HELP_CATEGORIES = {
    "🤖 Info & Files": [".info", ".chatinfo", ".id", ".ocr", ".repo"],
    "🛠 Utilities": [
        ".calc", ".weather", ".tr", ".qr", ".crypto", ".define",
        ".github", ".short", ".schedule", ".portfolio", ".currency",
    ],
    "🛡 Security": [".scan", ".osint", ".secret", ".net", ".ip", ".genpass", ".b64", ".hash"],
    "👤 User & AFK": [".afk", ".back", ".ghost", ".analytics", ".mood", ".flair"],
    "🎉 Fun": [
        ".meme", ".trivia", ".fact", ".horoscope", ".country", ".anime",
        ".quote", ".joke", ".8ball", ".roll", ".flip", ".reverse",
    ],
    "🧩 Moderation": [
        ".mute", ".unmute", ".unban", ".block", ".unblock", ".kick",
        ".admin", ".demote",
    ],
    "📡 Broadcasting": [".dm", ".frwd", ".gc", ".broad", ".frwdall", ".spm"],
    "💰 Crypto": [".whale", ".portfolio", ".crypto"],
    "⚙️ Reliability": [".fix", ".fixlog", ".ping"],
}

# Detailed per-command help shown by `.help <command>`
HELP_DETAILS = {
    "weather": {
        "purpose": "Get the current weather for a city.",
        "syntax": ".weather <city>",
        "example": ".weather Mumbai",
        "arguments": "city — any city name",
        "notes": "Uses wttr.in, no API key required.",
        "aliases": "none",
    },
    "tr": {
        "purpose": "Translate text, auto-detecting the source language.",
        "syntax": ".tr <target_lang> [text]  (or reply + .tr <target_lang>)",
        "example": ".tr hi Hello, how are you?",
        "arguments": "target_lang — 2-letter language code (e.g. hi, en, fr)",
        "notes": "Falls back to English detection if langdetect isn't installed.",
        "aliases": ".translate",
    },
    "scan": {
        "purpose": "Scan a URL for phishing/scam risk signals.",
        "syntax": ".scan <url>",
        "example": ".scan https://example.com",
        "arguments": "url — the link to check",
        "notes": "Checks HTTPS, redirects, SSL, domain age, suspicious keywords; VirusTotal used if VIRUSTOTAL_API_KEY is set.",
        "aliases": "none",
    },
    "osint": {
        "purpose": "Run an OSINT lookup on an email, username, or domain.",
        "syntax": ".osint <email|username|domain> <target>",
        "example": ".osint domain example.com",
        "arguments": "subcommand + target value",
        "notes": "Username checks are for publicly visible account existence only.",
        "aliases": "none",
    },
    "secret": {
        "purpose": "Store and retrieve encrypted personal notes (AES-256-GCM).",
        "syntax": ".secret add <text> | .secret list | .secret view <n> | .secret delete <n>",
        "example": ".secret add My WiFi password is xyz",
        "arguments": "text for add; index number for view/delete",
        "notes": "Requires the SECRET_MASTER_PASSWORD environment variable to be set.",
        "aliases": "none",
    },
    "net": {
        "purpose": "Show a full network health report for the server running the bot.",
        "syntax": ".net",
        "example": ".net",
        "arguments": "none",
        "notes": "Download/upload speed needs the optional `speedtest-cli` package.",
        "aliases": "none",
    },
    "ghost": {
        "purpose": "Toggle Ghost Mode — reduces visible activity and auto-deletes command output.",
        "syntax": ".ghost on | .ghost off",
        "example": ".ghost on",
        "arguments": "on / off",
        "notes": "Some Telegram-side acknowledgements can't be fully suppressed at the protocol level.",
        "aliases": "none",
    },
    "analytics": {
        "purpose": "Analyze the current chat's recent message history.",
        "syntax": ".analytics",
        "example": ".analytics",
        "arguments": "none",
        "notes": "Scans up to the last 1000 messages for speed.",
        "aliases": "none",
    },
    "mood": {
        "purpose": "Detect the emotional tone of a replied-to message.",
        "syntax": ".mood  (must be used as a reply)",
        "example": "(reply to a message) .mood",
        "arguments": "none — target is the replied message",
        "notes": "Uses a lightweight local keyword lexicon, no external API.",
        "aliases": "none",
    },
    "whale": {
        "purpose": "Toggle background monitoring for unusually large crypto transfers.",
        "syntax": ".whale on | .whale off",
        "example": ".whale on",
        "arguments": "on / off",
        "notes": "BTC works out of the box; ETH/BNB need ETHERSCAN_API_KEY/BSCSCAN_API_KEY.",
        "aliases": "none",
    },
    "afk": {
        "purpose": "Enable an away-from-keyboard auto-reply for your DMs.",
        "syntax": ".afk [custom message]",
        "example": ".afk Busy right now, back soon!",
        "arguments": "optional custom message",
        "notes": "Re-triggers for the same user after 6 hours of silence.",
        "aliases": "none",
    },
    "spm": {
        "purpose": "Send the same text multiple times in the current chat.",
        "syntax": ".spm <text> <count>",
        "example": ".spm hello 5",
        "arguments": "text, then a count (max 20)",
        "notes": "Capped for anti-ban safety.",
        "aliases": ".spam",
    },
    "flair": {
        "purpose": "Preview and apply a decorative name-badge style to your own profile.",
        "syntax": ".flair | .flair <1/2/3> | .flair <1/2/3> apply",
        "example": ".flair 1 apply",
        "arguments": "style number (1–3), optional 'apply' to commit the change",
        "notes": "These are honest personal-style badges — they don't mimic Telegram's official verification checkmark.",
        "aliases": "none",
    },
    "genpass": {
        "purpose": "Generate a cryptographically random password.",
        "syntax": ".genpass [length]",
        "example": ".genpass 20",
        "arguments": "optional length, 8–64 (default 16)",
        "notes": "Uses random.SystemRandom() (CSPRNG), not the regular PRNG.",
        "aliases": "none",
    },
    "b64": {
        "purpose": "Encode or decode text using Base64.",
        "syntax": ".b64 encode <text> | .b64 decode <text>",
        "example": ".b64 encode Hello World",
        "arguments": "encode/decode, then the text",
        "notes": "Purely local, no network call.",
        "aliases": "none",
    },
    "hash": {
        "purpose": "Compute MD5, SHA1, and SHA256 hashes of text.",
        "syntax": ".hash <text>",
        "example": ".hash Hello World",
        "arguments": "any text",
        "notes": "Purely local, no network call.",
        "aliases": "none",
    },
}


def _build_help_overview():
    """Builds the premium boxed-UI overview for .help / .commands."""
    uptime_sec = int(time.time() - BOT_START_TIME)
    h, rem = divmod(uptime_sec, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ **REHU SELFBOT**",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"**Version:** `{BOT_VERSION}`  •  **Build:** `{BOT_BUILD}`",
        f"**Developer:** {DEV_NAME}",
        f"**Uptime:** `{uptime_str}`",
        f"**Python:** `{platform.python_version()}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for category, cmds in HELP_CATEGORIES.items():
        lines.append(f"\n**{category}**")
        lines.append("  " + "  ".join(f"`{c}`" for c in cmds))
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("Type `.help <command>` for detailed usage.")
    lines.append("Example: `.help weather`")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"\n𝗗𝗘𝗩 ~ {DEV_NAME}")
    return "\n".join(lines)


def _build_help_detail(cmd_name):
    cmd_name = cmd_name.lstrip(".").lower()
    detail = HELP_DETAILS.get(cmd_name)
    if not detail:
        return (
            f"❌ No detailed help entry for `.{cmd_name}` yet.\n"
            f"Use `.help` to see the full command list."
        )
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📘 **Help — .{cmd_name}**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Purpose:**\n{detail['purpose']}\n\n"
        f"**Syntax:**\n`{detail['syntax']}`\n\n"
        f"**Example:**\n`{detail['example']}`\n\n"
        f"**Arguments:**\n{detail['arguments']}\n\n"
        f"**Notes:**\n{detail['notes']}\n\n"
        f"**Aliases:**\n{detail['aliases']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def _build_dev_info():
    """Builds the premium .dev system-info panel."""
    uptime_sec = int(time.time() - BOT_START_TIME)
    h, rem = divmod(uptime_sec, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    total_commands = sum(len(v) for v in HELP_CATEGORIES.values())

    ram_str = "N/A (psutil not installed)"
    cpu_str = "N/A (psutil not installed)"
    if PSUTIL_OK:
        try:
            proc = psutil.Process(os.getpid())
            ram_mb = proc.memory_info().rss / (1024 * 1024)
            ram_str = f"{ram_mb:.1f} MB"
            cpu_str = f"{psutil.cpu_percent(interval=0.3):.1f}%"
        except Exception:
            pass

    try:
        import telethon
        telethon_version = telethon.__version__
    except Exception:
        telethon_version = "unknown"

    render_status = "🟢 Running on Render" if os.environ.get("RENDER") or os.environ.get("PORT") else "⚪ Local / Unknown host"

    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 **DEVELOPER INFO**
━━━━━━━━━━━━━━━━━━━━━━━━━━
**Developer:** {DEV_NAME}
**Role:** {DEV_ROLE}
**GitHub:** {DEV_GITHUB}
**Portfolio:** {DEV_PORTFOLIO}
━━━━━━━━━━━━━━━━━━━━━━━━━━
**Version:** `{BOT_VERSION}`
**Build:** `{BOT_BUILD}`
**Python:** `{platform.python_version()}`
**Telethon:** `{telethon_version}`
**Platform:** `{platform.system()} {platform.release()}`
━━━━━━━━━━━━━━━━━━━━━━━━━━
**Total Commands:** `{total_commands}+`
**Uptime:** `{uptime_str}`
**RAM Usage:** `{ram_str}`
**CPU Usage:** `{cpu_str}`
**Render Status:** {render_status}
━━━━━━━━━━━━━━━━━━━━━━━━━━
_This selfbot was built and is maintained by {DEV_NAME} — covering the
AFK system, moderation tools, broadcast engine, security toolkit, and
the full Render deployment setup._
━━━━━━━━━━━━━━━━━━━━━━━━━━"""





# ------------------------------------------------------------------
# Command dispatcher
# ------------------------------------------------------------------
async def _cmd_dispatch(event):
    global muted_users, banned_users, auto_accept_active, auto_fix_active

    raw = event.raw_text.strip()
    text = raw.lower()
    if not text.startswith("."):
        return

    if text == ".fix":
        auto_fix_active = not auto_fix_active
        state = "ON ✅" if auto_fix_active else "OFF 🔕"
        await event.edit(
            f"**🛠 Auto-fix mode: {state}**\nWhen ON, any command error is caught, logged to "
            f"`{ERROR_LOG_FILE}`, the command is retried once automatically, and you get a short "
            f"error report here instead of a crash."
        )

    elif text == ".fixlog":
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            tail = "".join(lines[-40:]) or "No errors logged yet."
        except FileNotFoundError:
            tail = "No errors logged yet."
        await event.edit(f"**🧾 Last errors:**\n```\n{tail[-3500:]}\n```")

    elif text in (".help", ".fux", ".commands"):
        await event.edit(_build_help_overview())

    elif text.startswith(".help "):
        cmd_query = raw[6:].strip()
        await event.edit(_build_help_detail(cmd_query))

    elif text == ".dev":
        await event.edit(_build_dev_info())

    elif text == ".owner":
        lines = [
            "**Owner Intro**",
            f"• Developer: {DEV_NAME}",
            f"• {DEV_ROLE}",
            "• Selfbot script | Python Dev",
            f"• Portfolio: {DEV_PORTFOLIO}",
        ]
        msg = await event.edit("Typing...")
        out = ""
        for line in lines:
            out += line + "\n"
            await msg.edit(out)
            await asyncio.sleep(0.8)

    elif text == ".autoaccept":
        auto_accept_active = not auto_accept_active
        state = "enabled ✅" if auto_accept_active else "disabled 🔕"
        await event.edit(f"Auto-accept chat requests {state}")

    # ---------------- AFK COMMANDS ----------------
    elif text == ".afk" or text.startswith(".afk "):
        custom = raw[4:].strip() or None
        afk.enable(custom)
        await event.edit(
            f"🌙 **AFK mode enabled.**\n"
            f"Message: `{afk.message}`\n"
            f"I will auto-reply in DMs, once per user, and again if they message after "
            f"6 hours of silence — until you send a message or `.back`."
        )

    elif text == ".back":
        if afk.active:
            duration = afk.duration_text()
            afk.disable()
            await event.edit(f"✅ **AFK disabled.** You were away for {duration}.")
        else:
            await event.edit("ℹ️ AFK was not active.")
    # ------------------------------------------------

    # ---------------- SPAM / REPEAT SENDER ----------------
    elif text.startswith(".spm") or text.startswith(".spam"):
        cmd_len = 4 if text.startswith(".spm") else 5
        rest = raw[cmd_len:].strip()
        if not rest:
            await event.edit("❌ Usage: `.spm <text> <count>` e.g. `.spm hello 5`")
            return
        parts = rest.rsplit(None, 1)
        if len(parts) < 2 or not parts[1].isdigit():
            await event.edit("❌ Usage: `.spm <text> <count>` e.g. `.spm hello 5`")
            return
        spam_text, count_str = parts[0], parts[1]
        count = int(count_str)
        if count < 1:
            await event.edit("❌ Count must be at least 1.")
            return
        if count > SPAM_MAX_REPEATS:
            await event.edit(f"❌ Max allowed is {SPAM_MAX_REPEATS} (anti-ban safety limit).")
            return
        await event.delete()
        for i in range(count):
            try:
                await client.send_message(event.chat_id, spam_text)
            except Exception as e:
                log_error(".spm", e)
                break
            if i < count - 1:
                await asyncio.sleep(random.uniform(1, 2))
    # ------------------------------------------------

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
            await event.edit(
                f"""**👤 Telegram Info**
✓ **Name:** `{full_name or 'N/A'}`
✓ **Username:** @{u.username or 'N/A'}
✓ **User ID:** `{u.id}`
✓ **Phone:** `{u.phone or 'N/A'}`
✓ **Bot:** `{'Yes' if u.bot else 'No'}`
✓ **Verified:** `{'Yes' if getattr(u, 'verified', False) else 'No'}`
✓ **Premium:** `{'Yes' if getattr(u, 'premium', False) else 'No'}`
✓ **DC:** `{dc}`
✓ **Last Seen:** `{u.status.__class__.__name__ if u.status else 'Hidden'}`"""
            )
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

    elif text == ".id":
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
            await event.edit(f"🆔 **User ID:** `{u.id}`")
        else:
            await event.edit(f"🆔 **Chat ID:** `{event.chat_id}`")

    elif text.startswith(".chatinfo"):
        try:
            chat = await event.get_chat()
            if hasattr(chat, "title"):
                members = getattr(chat, "participants_count", "N/A")
                ctype = "Channel" if getattr(chat, "broadcast", False) else "Group/Supergroup"
                await event.edit(
                    f"""**💬 Chat Info**
✓ **Title:** `{chat.title}`
✓ **ID:** `{chat.id}`
✓ **Type:** `{ctype}`
✓ **Username:** @{getattr(chat, 'username', 'N/A') or 'N/A'}
✓ **Members:** `{members}`
✓ **Verified:** `{'Yes' if getattr(chat, 'verified', False) else 'No'}`"""
                )
            else:
                me = await client.get_me()
                await event.edit(
                    f"**💬 Chat Info**\n\n✓ **Type:** `Private Chat`\n✓ **Your ID:** `{me.id}`\n"
                    f"✓ **Chat ID:** `{event.chat_id}`"
                )
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif text.startswith(".insta") or text.startswith(".iginfo"):
        parts = raw.split(None, 1)
        if len(parts) < 2:
            await event.edit("❌ Usage: `.insta @username`")
            return
        uname = parts[1].strip().lstrip("@")
        await event.edit(f"🔍 Fetching **@{uname}**...")
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, _ig_info, uname)
        except Exception as e:
            result = f"❌ Instagram lookup failed: {e}"
        await event.edit(result)

    elif (text.startswith(".mute") and not text.startswith(".unmute")) or (
        text.startswith(".ban") and not text.startswith(".unban")
    ):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
        if not u:
            await event.edit("❌ User not found. Reply to a user or provide @username.")
            return
        muted_users.add(u.id)
        banned_users.add(u.id)
        data["muted_users"] = list(muted_users)
        data["banned_users"] = list(banned_users)
        save_data(data)
        await event.edit(f"🚫 **{u.first_name or u.id}** blocked — messages will be deleted.")

    elif text.startswith(".unmute"):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
        if not u:
            await event.edit("❌ User not found.")
            return
        muted_users.discard(u.id)
        banned_users.discard(u.id)
        data["muted_users"] = list(muted_users)
        data["banned_users"] = list(banned_users)
        save_data(data)
        await event.edit(f"✅ **{u.first_name or u.id}** unblocked")

    elif text.startswith(".unban"):
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
        if not u:
            await event.edit("❌ User not found.")
            return
        banned_users.discard(u.id)
        data["banned_users"] = list(banned_users)
        save_data(data)
        await event.edit(f"✅ Unbanned `{u.first_name or u.id}`")

    elif text.startswith(".block") and not text.startswith(".unblock"):
        target_id = None
        if event.is_private:
            target_id = event.chat_id
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
                if u:
                    target_id = u.id
        if target_id:
            await client(functions.contacts.BlockRequest(id=target_id))
            await event.edit(f"🚫 Blocked `{target_id}`")
        else:
            await event.edit("❌ Use in a private chat, or: `.block @username`")

    elif text.startswith(".unblock"):
        target_id = None
        if event.is_private:
            target_id = event.chat_id
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
                if u:
                    target_id = u.id
        if target_id:
            await client(functions.contacts.UnblockRequest(id=target_id))
            await event.edit(f"✅ Unblocked `{target_id}`")
        else:
            await event.edit("❌ Use in a private chat, or: `.unblock @username`")

    elif text.startswith(".kick"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        if not event.is_reply:
            await event.edit("❌ Reply to the user you want to kick.")
            return
        reply = await event.get_reply_message()
        u = await client.get_entity(reply.sender_id)
        try:
            await client.kick_participant(event.chat_id, u.id)
            await event.edit(f"🦵 Kicked `{u.first_name or u.id}`")
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif text.startswith(".admin"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
        if not u:
            await event.edit("❌ Reply to a user, or: `.admin @username` / `.admin user_id`")
            return
        try:
            rights = types.ChatAdminRights(
                change_info=True, post_messages=True, edit_messages=True, delete_messages=True,
                ban_users=True, invite_users=True, pin_messages=True, add_admins=False,
                anonymous=False, manage_call=True, other=True,
            )
            await client(EditAdminRequest(event.chat_id, u.id, rights, "admin"))
            await event.edit(f"⭐ **{u.first_name or u.id}** promoted to admin.")
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif text.startswith(".demote"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        u = None
        if event.is_reply:
            reply = await event.get_reply_message()
            u = await client.get_entity(reply.sender_id)
        else:
            parts = raw.split(None, 1)
            if len(parts) > 1:
                u = await get_entity(parts[1].strip())
        if not u:
            await event.edit("❌ Reply to a user, or: `.demote @username` / `.demote user_id`")
            return
        try:
            rights = types.ChatAdminRights(
                change_info=False, post_messages=False, edit_messages=False, delete_messages=False,
                ban_users=False, invite_users=False, pin_messages=False, add_admins=False,
                anonymous=False, manage_call=False, other=False,
            )
            await client(EditAdminRequest(event.chat_id, u.id, rights, ""))
            await event.edit(f"⬇️ **{u.first_name or u.id}** demoted (admin rights removed).")
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif text.startswith(".dm") and not text.startswith(".dmfrwd") and not text.startswith(".frwd"):
        content = raw[3:].strip()
        if event.is_reply:
            reply = await event.get_reply_message()
            if content:
                await client.send_message(reply.sender_id, content)
                await event.edit("✅ DM sent.")
            else:
                await event.edit("❌ Provide a message: `.dm message`")
        else:
            parts = content.split(None, 1)
            if len(parts) < 2 or not parts[0].startswith("@"):
                await event.edit("❌ Usage: `.dm @username message`")
                return
            u = await get_entity(parts[0])
            if u:
                await client.send_message(u.id, parts[1])
                await event.edit(f"✅ DM sent to @{u.username or u.id}")
            else:
                await event.edit("❌ User not found.")

    elif text.startswith(".frwd") and not text.startswith(".frwdall"):
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message you want to forward.")
            return
        replied = await event.get_reply_message()
        dm_ids = await get_dm_ids()
        total = len(dm_ids)
        await event.edit(f"📨 Forwarding to {total} DMs... (anti-ban mode, be patient)")
        sent, failed = 0, 0
        for uid in dm_ids:
            try:
                await client.forward_messages(uid, replied)
                sent += 1
            except Exception:
                failed += 1
            await safe_sleep(sent)
        await event.edit(f"✅ Forwarded to **{sent}** DMs. Failed: {failed}")

    elif text.startswith(".gc"):
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message you want to broadcast.")
            return
        replied = await event.get_reply_message()
        await event.edit("🔍 Finding groups where you're admin...")
        group_ids = await get_admin_group_ids()
        if not group_ids:
            group_ids = await get_all_group_ids()
        total = len(group_ids)
        await event.edit(f"📢 Broadcasting to {total} groups (admin mode, anti-ban)...")
        sent, failed = 0, 0
        for gid in group_ids:
            try:
                await client.forward_messages(gid, replied)
                sent += 1
            except Exception:
                failed += 1
            await safe_sleep(sent)
        await event.edit(f"✅ Broadcasted to **{sent}** groups. Failed: {failed}")

    elif text.startswith(".broad"):
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message you want to broadcast.")
            return
        replied = await event.get_reply_message()
        dm_ids = await get_dm_ids()
        total = len(dm_ids)
        await event.edit(f"📣 Broadcasting to {total} users... (anti-ban mode)")
        sent, failed = 0, 0
        for uid in dm_ids:
            try:
                await client.send_message(uid, replied.text or "")
                sent += 1
            except Exception:
                failed += 1
            await safe_sleep(sent)
        await event.edit(f"✅ Broadcasted to **{sent}** users. Failed: {failed}")

    elif text.startswith(".frwdall"):
        if not event.is_reply:
            await event.edit("⚠️ Reply to the message you want to forward.")
            return
        replied = await event.get_reply_message()
        await event.edit("🔍 Collecting targets...")
        dm_ids = await get_dm_ids()
        group_ids = await get_admin_group_ids()
        all_ids = dm_ids + group_ids
        total = len(all_ids)
        await event.edit(f"🚀 Forwarding to {total} targets (anti-ban mode, takes time)...")
        sent, failed = 0, 0
        for target_id in all_ids:
            try:
                await client.forward_messages(target_id, replied)
                sent += 1
            except Exception:
                failed += 1
            await safe_sleep(sent)
        await event.edit(f"✅ Done! Forwarded to **{sent}** targets. Failed: {failed}")

    elif text.startswith(".mm"):
        if not event.is_reply:
            await event.edit("❌ Reply to a user with `.mm`")
            return
        reply = await event.get_reply_message()
        u = await client.get_entity(reply.sender_id)
        try:
            await client(functions.messages.CreateChatRequest(
                users=[u.id], title="Syed Rehan's Middleman Service"
            ))
            await event.edit(f"✅ **Syed Rehan's Middleman Service**\nGroup created with `{u.first_name or u.id}`")
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif text.startswith(".tag"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        custom_msg = raw[4:].strip() or "👋"
        await event.edit("🔍 Collecting members...")
        try:
            participants = await client.get_participants(event.chat_id, limit=50)
            me = await client.get_me()
            tags = " ".join(
                f"[{p.first_name or 'user'}](tg://user?id={p.id})"
                for p in participants if not p.bot and p.id != me.id
            )
            if tags:
                await client.send_message(event.chat_id, f"{custom_msg}\n{tags}")
                await event.delete()
            else:
                await event.edit("❌ No members found.")
        except Exception as e:
            await event.edit(f"❌ {e}")

    elif text == ".del":
        if not event.is_private:
            await event.edit("❌ Private chats only.")
            return
        try:
            await client(DeleteHistoryRequest(peer=event.chat_id, max_id=0, revoke=True))
            msg = await event.respond("🧹 Chat history cleared.")
            await asyncio.sleep(3)
            await msg.delete()
        except Exception as e:
            await event.respond(f"❌ {e}")

    elif text.startswith(".purge"):
        parts = raw.split(None, 1)
        try:
            n = int(parts[1])
        except Exception:
            await event.edit("❌ Usage: `.purge N`")
            return
        msgs = await client.get_messages(event.chat_id, limit=n + 1)
        ids = [m.id for m in msgs]
        try:
            await client.delete_messages(event.chat_id, ids)
            conf = await event.respond(f"✅ Purged {n} messages.")
            await asyncio.sleep(3)
            await conf.delete()
        except Exception as e:
            await event.respond(f"❌ {e}")

    elif text.startswith(".close"):
        if not event.is_group:
            await event.edit("❌ Groups only.")
            return
        parts = raw.split(None, 1)
        try:
            sec = int(parts[1])
        except Exception:
            await event.edit("❌ Usage: `.close N`")
            return
        await event.edit(f"💣 Leaving group in {sec} seconds.")
        await asyncio.sleep(sec)
        try:
            await client.delete_dialog(event.chat_id)
        except Exception as e:
            await event.respond(f"❌ {e}")

    elif text.startswith(".count ") or text == ".count":
        parts = raw.split(None, 2)
        try:
            sec = int(parts[1])
            assert 1 <= sec <= 300
        except Exception:
            await event.edit("❌ Usage: `.count N` or `.count N message` (1–300)")
            return
        final_msg = parts[2] if len(parts) > 2 else None
        m = await event.edit(f"⏳ **{sec}**s")
        for i in range(sec - 1, -1, -1):
            await asyncio.sleep(1)
            try:
                await m.edit(f"⏳ **{i}**s")
            except Exception:
                pass
        if final_msg:
            await m.edit(f"**{final_msg}**")
        else:
            try:
                await m.delete()
            except Exception:
                pass

    elif text.startswith(".calc"):
        expr = raw[6:].strip()
        if not expr:
            await event.edit("❌ Usage: `.calc 2+2` or `.calc sqrt(144)`")
            return
        try:
            if SYMPY_OK:
                result = sympy.sympify(expr)
            else:
                result = eval(expr, {"__builtins__": {}}, {})
            await event.edit(f"🧮 `{expr}` = `{result}`")
        except Exception:
            await event.edit("❌ Invalid expression.")

    elif text.startswith(".tr ") or text == ".tr" or text.startswith(".translate"):
        cmd_end = 3 if text.startswith(".tr") else 10
        rest = raw[cmd_end:].strip()
        if not rest and event.is_reply:
            await event.edit("❌ Provide target language: `.tr hi` (while replying)")
            return
        parts = rest.split(None, 1)
        if len(parts) < 1:
            await event.edit("❌ Usage: `.tr hi text` or reply + `.tr hi`")
            return
        lang = parts[0].lower()
        if len(parts) >= 2:
            content = parts[1]
        elif event.is_reply:
            reply = await event.get_reply_message()
            content = reply.text or ""
        else:
            await event.edit("❌ Provide text or reply to a message. Usage: `.tr hi Hello`")
            return
        if not content.strip():
            await event.edit("❌ No text to translate.")
            return
        await event.edit("🌐 Translating...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _translate, content, lang)
        await event.edit(result)

    # ---------------- FUN & UTILITY COMMANDS ----------------
    elif text.startswith(".weather"):
        city = raw[8:].strip()
        if not city:
            await event.edit("❌ Usage: `.weather Mumbai`")
            return
        await event.edit(f"🌦 Fetching weather for **{city}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _weather_info, city)
        await event.edit(result)

    elif text.startswith(".crypto"):
        coin = raw[7:].strip()
        if not coin:
            await event.edit("❌ Usage: `.crypto bitcoin`")
            return
        await event.edit(f"💰 Fetching price for **{coin}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _crypto_price, coin)
        await event.edit(result)

    elif text.startswith(".define"):
        word = raw[7:].strip()
        if not word:
            await event.edit("❌ Usage: `.define serendipity`")
            return
        await event.edit(f"📖 Looking up **{word}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _dictionary_lookup, word)
        await event.edit(result)

    elif text.startswith(".github"):
        gh_user = raw[7:].strip().lstrip("@")
        if not gh_user:
            await event.edit("❌ Usage: `.github torvalds`")
            return
        await event.edit(f"🐙 Fetching GitHub profile for **{gh_user}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _github_info, gh_user)
        await event.edit(result)

    elif text.startswith(".short"):
        url = raw[6:].strip()
        if not url.startswith("http"):
            await event.edit("❌ Usage: `.short https://example.com/very/long/link`")
            return
        await event.edit("🔗 Shortening...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _short_url, url)
        await event.edit(result)

    elif text.startswith(".qr"):
        qr_text = raw[3:].strip()
        if not qr_text:
            await event.edit("❌ Usage: `.qr https://example.com` or `.qr any text`")
            return
        await event.edit("🔳 Generating QR code...")
        try:
            qr_url = (
                "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data="
                + requests.utils.quote(qr_text)
            )
            await client.send_file(event.chat_id, qr_url, caption=f"🔳 QR for: `{qr_text}`")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ QR generation failed: {e}")

    elif text == ".quote":
        await event.edit("💭 Fetching a quote...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _quote_of_the_day)
        await event.edit(result)

    elif text == ".joke":
        await event.edit("😂 Fetching a joke...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _random_joke)
        await event.edit(result)

    elif text.startswith(".8ball"):
        question = raw[6:].strip()
        if not question:
            await event.edit("❌ Usage: `.8ball Will it rain today?`")
            return
        answers = [
            "It is certain.", "Without a doubt.", "Yes, definitely.",
            "You may rely on it.", "Most likely.", "Outlook good.",
            "Signs point to yes.", "Reply hazy, try again.",
            "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.",
            "My sources say no.", "Outlook not so good.",
            "Very doubtful.",
        ]
        await event.edit(f"🎱 **Q:** {question}\n**A:** {random.choice(answers)}")

    elif text.startswith(".roll"):
        parts = raw.split(None, 1)
        sides = 6
        if len(parts) > 1:
            try:
                sides = int(parts[1])
                assert sides >= 2
            except Exception:
                await event.edit("❌ Usage: `.roll` or `.roll 20` (for a d20)")
                return
        result = random.randint(1, sides)
        await event.edit(f"🎲 You rolled a **{result}** (1–{sides})")

    elif text == ".flip":
        result = random.choice(["🪙 Heads", "🪙 Tails"])
        await event.edit(f"**{result}**")

    elif text.startswith(".reverse"):
        content = raw[8:].strip()
        if not content:
            await event.edit("❌ Usage: `.reverse hello world`")
            return
        await event.edit(f"🔁 `{content[::-1]}`")

    elif text == ".ping":
        start = time.time()
        msg = await event.edit("🏓 Pinging...")
        latency_ms = int((time.time() - start) * 1000)
        await msg.edit(f"🏓 **Pong!** `{latency_ms}ms`")
    # ------------------------------------------------

    # ---------------- MEME FETCHER ----------------
    elif text == ".meme":
        await event.edit("😹 Fetching a meme...")
        loop = asyncio.get_event_loop()
        try:
            img_url, caption = await loop.run_in_executor(None, _random_meme)
            if img_url:
                await client.send_file(event.chat_id, img_url, caption=caption)
                await event.delete()
            else:
                await event.edit(caption)
        except Exception as e:
            log_error(".meme", e)
            await event.edit(f"❌ Meme fetch failed: {e}")
    # ------------------------------------------------

    # ---------------- TRIVIA ----------------
    elif text == ".trivia":
        await event.edit("🧠 Fetching a trivia question...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _random_trivia)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- RANDOM FACT ----------------
    elif text == ".fact":
        await event.edit("🧾 Fetching a random fact...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _random_fact)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- HOROSCOPE ----------------
    elif text.startswith(".horoscope"):
        sign = raw[10:].strip()
        if not sign:
            await event.edit("❌ Usage: `.horoscope leo` (or any zodiac sign)")
            return
        await event.edit(f"🔮 Fetching horoscope for **{sign}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _daily_horoscope, sign)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- COUNTRY INFO ----------------
    elif text.startswith(".country"):
        country_name = raw[8:].strip()
        if not country_name:
            await event.edit("❌ Usage: `.country Japan`")
            return
        await event.edit(f"🌍 Looking up **{country_name}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _country_info, country_name)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- ANIME LOOKUP ----------------
    elif text.startswith(".anime"):
        anime_name = raw[6:].strip()
        if not anime_name:
            await event.edit("❌ Usage: `.anime Naruto`")
            return
        await event.edit(f"🎬 Looking up **{anime_name}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _anime_info, anime_name)
        await event.edit(result)
    # ------------------------------------------------
    # ------------------------------------------------

    # ---------------- MESSAGE SCHEDULER ----------------
    elif text.startswith(".schedule"):
        args = raw[9:].strip()
        parsed = _parse_schedule(args)
        if not parsed:
            await event.edit(
                "❌ Usage: `.schedule 30m Hello`, `.schedule 2h Hi`, `.schedule 1d Good Morning`, "
                "or `.schedule 2026-08-01 09:00 Hello`"
            )
            return
        send_at, message = parsed
        delay = (send_at - datetime.datetime.now()).total_seconds()
        if delay <= 0:
            await event.edit("❌ That time is in the past.")
            return
        try:
            asyncio.create_task(_run_scheduled_send(event.chat_id, message, delay))
            await event.edit(
                f"✅ Message Scheduled.\n🕒 Will send at `{send_at.strftime('%Y-%m-%d %H:%M:%S')}`."
            )
        except Exception as e:
            log_error(".schedule", e)
            await event.edit(f"❌ Failed to schedule message: {e}")
    # ------------------------------------------------

    # ---------------- OSINT TOOLKIT ----------------
    elif text.startswith(".osint"):
        args = raw[6:].strip()
        parts = args.split(None, 1)
        if len(parts) < 2:
            await event.edit(
                "❌ Usage: `.osint email <addr>` / `.osint username <name>` / `.osint domain <domain>`"
            )
            return
        sub, target = parts[0].lower(), parts[1].strip()
        await event.edit(f"🕵️ Running OSINT ({sub}) on **{target}**...")
        loop = asyncio.get_event_loop()
        try:
            if sub == "email":
                result = await loop.run_in_executor(None, _osint_email, target)
            elif sub == "username":
                result = await loop.run_in_executor(None, _osint_username, target)
            elif sub == "domain":
                result = await loop.run_in_executor(None, _osint_domain, target)
            else:
                await event.edit("❌ Unknown subcommand. Use `email`, `username`, or `domain`.")
                return
            await event.edit(result[:4000])
        except Exception as e:
            log_error(".osint", e)
            await event.edit(f"❌ OSINT lookup failed: {e}")
    # ------------------------------------------------

    # ---------------- IP LOOKUP ----------------
    elif text.startswith(".ip"):
        ip_target = raw[3:].strip()
        if not ip_target:
            await event.edit("❌ Usage: `.ip 8.8.8.8`")
            return
        await event.edit(f"🌍 Looking up **{ip_target}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _ip_lookup, ip_target)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- SCAM URL DETECTOR ----------------
    elif text.startswith(".scan ") or text == ".scan":
        target_url = raw[5:].strip()
        if not target_url:
            await event.edit("❌ Usage: `.scan https://example.com`")
            return
        await event.edit(f"🔍 Scanning **{target_url}**...")
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, _scan_url, target_url)
            await event.edit(result[:4000])
        except Exception as e:
            log_error(".scan", e)
            await event.edit(f"❌ Scan failed: {e}")
    # ------------------------------------------------

    # ---------------- CRYPTO PORTFOLIO ----------------
    elif text.startswith(".portfolio"):
        args = raw[10:].strip()
        parts = args.split(None, 2)
        if not parts:
            await event.edit("❌ Usage: `.portfolio add/remove/list ...`")
            return
        action = parts[0].lower()
        if action == "list":
            await event.edit("📊 Loading portfolio...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _format_portfolio)
            await event.edit(result)
        elif action == "add":
            if len(parts) < 3:
                await event.edit("❌ Usage: `.portfolio add bitcoin 2`")
                return
            coin, amount_str = parts[1].lower(), parts[2]
            try:
                amount = float(amount_str)
            except ValueError:
                await event.edit("❌ Amount must be a number.")
                return
            portfolio[coin] = portfolio.get(coin, 0) + amount
            save_portfolio(portfolio)
            await event.edit(f"✅ Added `{amount}` **{coin}** to your portfolio.")
        elif action == "remove":
            if len(parts) < 2:
                await event.edit("❌ Usage: `.portfolio remove bitcoin`")
                return
            coin = parts[1].lower()
            if coin in portfolio:
                del portfolio[coin]
                save_portfolio(portfolio)
                await event.edit(f"✅ Removed **{coin}** from your portfolio.")
            else:
                await event.edit(f"❌ **{coin}** not found in your portfolio.")
        else:
            await event.edit("❌ Usage: `.portfolio add/remove/list ...`")
    # ------------------------------------------------

    # ---------------- GITHUB REPO STATS ----------------
    elif text.startswith(".repo"):
        repo_arg = raw[5:].strip()
        if "/" not in repo_arg:
            await event.edit("❌ Usage: `.repo owner/repository`")
            return
        await event.edit(f"🐙 Fetching stats for **{repo_arg}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _repo_stats, repo_arg)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- OCR ----------------
    elif text == ".ocr":
        if not event.is_reply:
            await event.edit("❌ Reply to an image with `.ocr`")
            return
        reply = await event.get_reply_message()
        is_image = bool(reply.photo) or (
            reply.document and reply.document.mime_type
            and reply.document.mime_type.startswith("image/")
        )
        if not is_image:
            await event.edit("❌ Reply to an image with `.ocr`")
            return
        if not EASYOCR_OK and not TESSERACT_OK:
            await event.edit("❌ OCR engine not installed (need `easyocr` or `pytesseract`).")
            return
        await event.edit("🔍 Extracting text from image...")
        img_path = os.path.join(TEMP_DIR, f"{uuid4().hex}.jpg")
        try:
            await client.download_media(reply, file=img_path)
            loop = asyncio.get_event_loop()
            text_result = await loop.run_in_executor(None, _run_ocr, img_path)
            if text_result == "ENGINE_MISSING":
                await event.edit("❌ OCR engine not installed.")
            elif not text_result:
                await event.edit("No readable text found.")
            else:
                await event.edit(f"📝 **Extracted Text:**\n```\n{text_result[:3800]}\n```")
        except Exception as e:
            log_error(".ocr", e)
            await event.edit(f"❌ OCR failed: {e}")
        finally:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass
    # ------------------------------------------------

    # ---------------- GHOST MODE ----------------
    elif text.startswith(".ghost"):
        arg = raw[6:].strip().lower()
        if arg == "on":
            ghost_mode.enable()
            await event.edit("👻 **Ghost Mode Enabled**")
        elif arg == "off":
            ghost_mode.disable()
            await event.edit("👻 **Ghost Mode Disabled**")
        else:
            await event.edit("❌ Usage: `.ghost on` or `.ghost off`")
    # ------------------------------------------------

    # ---------------- CHAT ANALYTICS ----------------
    elif text == ".analytics":
        await event.edit("📊 Analyzing chat (this may take a moment)...")
        try:
            data = await _build_chat_analytics(event.chat_id, limit=1000)
            await event.edit(_format_analytics(data))
        except Exception as e:
            log_error(".analytics", e)
            await event.edit(f"❌ Analytics failed: {e}")
    # ------------------------------------------------

    # ---------------- MOOD DETECTOR ----------------
    elif text == ".mood":
        if not event.is_reply:
            await event.edit("❌ Reply to a message with `.mood`")
            return
        await event.edit("🧠 Analyzing mood...")
        try:
            reply = await event.get_reply_message()
            result = _analyze_mood(reply.text or "")
            await event.edit(_format_mood(result))
        except Exception as e:
            log_error(".mood", e)
            await event.edit(f"❌ Mood analysis failed: {e}")
    # ------------------------------------------------

    # ---------------- SECRET NOTES (AES-256-GCM) ----------------
    elif text.startswith(".secret"):
        if not CRYPTO_OK:
            await event.edit("❌ `cryptography` package not installed — `.secret` is unavailable.")
            return
        if not SECRET_MASTER_PASSWORD:
            await event.edit(
                "❌ `SECRET_MASTER_PASSWORD` environment variable is not set. "
                "Set it and restart the bot to use `.secret`."
            )
            return
        args = raw[7:].strip()
        parts = args.split(None, 1)
        if not parts:
            await event.edit("❌ Usage: `.secret add/list/view/delete ...`")
            return
        action = parts[0].lower()
        try:
            if action == "add":
                if len(parts) < 2:
                    await event.edit("❌ Usage: `.secret add <text>`")
                    return
                notes = _load_secret_notes()
                notes.append(parts[1])
                _save_secret_notes(notes)
                await event.delete()  # never leave the plaintext note visible in chat
                await client.send_message(event.chat_id, f"🔐 Secret note #{len(notes)} saved (encrypted).")
            elif action == "list":
                notes = _load_secret_notes()
                if not notes:
                    await event.edit("🔐 No secret notes stored yet.")
                    return
                preview = "\n".join(f"{i + 1}. {n[:30]}{'...' if len(n) > 30 else ''}" for i, n in enumerate(notes))
                await event.edit(f"🔐 **Secret Notes ({len(notes)}):**\n{preview}")
            elif action == "view":
                if len(parts) < 2 or not parts[1].strip().isdigit():
                    await event.edit("❌ Usage: `.secret view <n>`")
                    return
                idx = int(parts[1].strip()) - 1
                notes = _load_secret_notes()
                if not (0 <= idx < len(notes)):
                    await event.edit("❌ Note not found.")
                    return
                await event.edit(f"🔐 **Note #{idx + 1}:**\n{notes[idx]}")
            elif action == "delete":
                if len(parts) < 2 or not parts[1].strip().isdigit():
                    await event.edit("❌ Usage: `.secret delete <n>`")
                    return
                idx = int(parts[1].strip()) - 1
                notes = _load_secret_notes()
                if not (0 <= idx < len(notes)):
                    await event.edit("❌ Note not found.")
                    return
                notes.pop(idx)
                _save_secret_notes(notes)
                await event.edit(f"✅ Note #{idx + 1} deleted.")
            else:
                await event.edit("❌ Usage: `.secret add/list/view/delete ...`")
        except Exception as e:
            log_error(".secret", e)
            await event.edit(f"❌ Secret notes operation failed: {e}")
    # ------------------------------------------------

    # ---------------- NETWORK MONITOR ----------------
    elif text == ".net":
        await event.edit("🌐 Running network diagnostics...")
        try:
            report = await asyncio.wait_for(_build_network_report(), timeout=60)
            await event.edit(_format_network_report(report))
        except asyncio.TimeoutError:
            await event.edit("❌ Network check timed out.")
        except Exception as e:
            log_error(".net", e)
            await event.edit(f"❌ Network check failed: {e}")
    # ------------------------------------------------

    # ---------------- CRYPTO WHALE ALERT ----------------
    elif text.startswith(".whale"):
        global whale_alert_active, _whale_task
        arg = raw[6:].strip().lower()
        if arg == "on":
            if whale_alert_active and _whale_task and not _whale_task.done():
                await event.edit("🐋 Whale Alert is already running.")
                return
            whale_alert_active = True
            _save_whale_state(True)
            _whale_task = asyncio.create_task(_whale_monitor_loop())
            await event.edit("🐋 **Whale Alert enabled** — monitoring BTC/ETH/SOL/BNB in the background.")
        elif arg == "off":
            whale_alert_active = False
            _save_whale_state(False)
            await event.edit("🐋 **Whale Alert disabled.**")
        else:
            await event.edit("❌ Usage: `.whale on` or `.whale off`")
    # ------------------------------------------------

    # ---------------- FLAIR (honest custom badge) ----------------
    elif text.startswith(".flair"):
        args = raw[6:].strip()
        try:
            me = await client.get_me()
            current_name = me.first_name or "You"
        except Exception:
            current_name = "You"

        if not args:
            await event.edit(_build_flair_preview_all(current_name))
        elif args in ("1", "2", "3"):
            await event.edit(_build_flair_preview_one(args, current_name))
        elif args.startswith("apply "):
            key = args[6:].strip()
            style = FLAIR_STYLES.get(key)
            if not style:
                await event.edit("❌ Usage: `.flair apply 1` / `2` / `3`")
                return
            try:
                state = _load_flair_state()
                if "original_name" not in state:
                    state["original_name"] = current_name
                new_name = style["template"].format(name=state["original_name"])
                await client(functions.account.UpdateProfileRequest(first_name=new_name))
                state["applied"] = key
                _save_flair_state(state)
                await event.edit(
                    f"✅ Flair applied: `{new_name}`\n\n{FLAIR_DISCLAIMER}"
                )
            except Exception as e:
                log_error(".flair apply", e)
                await event.edit(f"❌ Failed to apply flair: {e}")
        elif args == "reset":
            try:
                state = _load_flair_state()
                original = state.get("original_name")
                if not original:
                    await event.edit("ℹ️ No flair has been applied yet.")
                    return
                await client(functions.account.UpdateProfileRequest(first_name=original))
                state.pop("applied", None)
                _save_flair_state(state)
                await event.edit(f"✅ Flair removed — name reset to `{original}`.")
            except Exception as e:
                log_error(".flair reset", e)
                await event.edit(f"❌ Failed to reset flair: {e}")
        else:
            await event.edit("❌ Usage: `.flair` / `.flair 1-3` / `.flair apply 1-3` / `.flair reset`")
    # ------------------------------------------------

    # ---------------- QR CODE SCANNER ----------------
    elif text == ".scanqr":
        if not event.is_reply:
            await event.edit("❌ Reply to an image containing a QR code with `.scanqr`")
            return
        reply = await event.get_reply_message()
        is_image = bool(reply.photo) or (
            reply.document and reply.document.mime_type
            and reply.document.mime_type.startswith("image/")
        )
        if not is_image:
            await event.edit("❌ Reply to an image containing a QR code with `.scanqr`")
            return
        await event.edit("🔍 Decoding QR code...")
        img_path = os.path.join(TEMP_DIR, f"{uuid4().hex}.jpg")
        try:
            await client.download_media(reply, file=img_path)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _decode_qr, img_path)
            if result.startswith("❌"):
                await event.edit(result)
            else:
                await event.edit(f"🔳 **QR Content:**\n`{result}`")
        except Exception as e:
            log_error(".scanqr", e)
            await event.edit(f"❌ QR decode failed: {e}")
        finally:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass
    # ------------------------------------------------

    # ---------------- HASH GENERATOR ----------------
    elif text.startswith(".hash"):
        content = raw[5:].strip()
        if not content:
            await event.edit("❌ Usage: `.hash <text>`")
            return
        try:
            hashes = _generate_hashes(content)
            await event.edit(_format_hashes(content, hashes))
        except Exception as e:
            log_error(".hash", e)
            await event.edit(f"❌ Hash generation failed: {e}")
    # ------------------------------------------------

    # ---------------- CURRENCY CONVERTER ----------------
    elif text.startswith(".currency"):
        args = raw[9:].strip().split()
        if len(args) != 3:
            await event.edit("❌ Usage: `.currency <amount> <from> <to>` e.g. `.currency 100 USD INR`")
            return
        amount_str, from_cur, to_cur = args
        try:
            amount = float(amount_str)
        except ValueError:
            await event.edit("❌ Amount must be a number.")
            return
        await event.edit(f"💱 Converting **{amount} {from_cur.upper()}** to **{to_cur.upper()}**...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _convert_currency, amount, from_cur, to_cur)
        await event.edit(result)
    # ------------------------------------------------

    # ---------------- CUSTOM FLAIR BADGE ----------------
    elif text.startswith(".flair"):
        args = raw[6:].strip().split(None, 1)
        if not args:
            preview_lines = ["🎨 **Flair Styles — Preview**\n"]
            try:
                me = await client.get_me()
                base_name = me.first_name or "You"
            except Exception:
                base_name = "You"
            for key, style in FLAIR_STYLES.items():
                preview_lines.append(f"`{key}` → {style['template'].format(name=base_name)}")
            preview_lines.append("\nApply with: `.flair <1/2/3> apply`")
            preview_lines.append(
                "\nℹ️ These are decorative personal styles only — they don't "
                "claim or mimic official Telegram verification."
            )
            await event.edit("\n".join(preview_lines))
            return

        style_key = args[0].strip()
        apply_now = len(args) > 1 and args[1].strip().lower() == "apply"

        try:
            me = await client.get_me()
            base_name = me.first_name or "You"
        except Exception as e:
            log_error(".flair", e)
            await event.edit(f"❌ Couldn't fetch your profile: {e}")
            return

        preview = _flair_preview(style_key, base_name)
        if not preview:
            await event.edit("❌ Unknown style. Use `.flair` to see options `1`, `2`, `3`.")
            return

        if not apply_now:
            await event.edit(
                f"🎨 **Preview:** {preview}\n\nApply with: `.flair {style_key} apply`"
            )
            return

        try:
            await client(functions.account.UpdateProfileRequest(first_name=preview))
            await event.edit(f"✅ Flair applied: **{preview}**")
        except Exception as e:
            log_error(".flair apply", e)
            await event.edit(f"❌ Failed to update profile: {e}")
    # ------------------------------------------------

    # ---------------- PASSWORD GENERATOR ----------------
    elif text.startswith(".genpass"):
        arg = raw[8:].strip()
        length = 16
        if arg:
            try:
                length = int(arg)
            except ValueError:
                await event.edit("❌ Usage: `.genpass [length]` (default 16, 8–64)")
                return
        pwd = _generate_password(length)
        await event.edit(f"🔑 **Generated Password ({length} chars):**\n`{pwd}`")
    # ------------------------------------------------

    # ---------------- BASE64 TOOL ----------------
    elif text.startswith(".b64"):
        args = raw[4:].strip().split(None, 1)
        if len(args) < 2 or args[0].lower() not in ("encode", "decode"):
            await event.edit("❌ Usage: `.b64 encode <text>` or `.b64 decode <text>`")
            return
        result = _base64_tool(args[0].lower(), args[1])
        await event.edit(f"🔠 **Base64 {args[0].capitalize()}:**\n`{result}`")
    # ------------------------------------------------

    # ---------------- HASH CALCULATOR ----------------
    elif text.startswith(".hash"):
        content = raw[5:].strip()
        if not content:
            await event.edit("❌ Usage: `.hash <text>`")
            return
        hashes = _hash_text(content)
        lines = ["🧮 **Hashes:**"]
        for algo, value in hashes.items():
            lines.append(f"**{algo}:** `{value}`")
        await event.edit("\n".join(lines))
    # ------------------------------------------------

    elif text.startswith(".say"):
        content = raw[4:].strip()
        if not content:
            await event.edit("❌ Usage: `.say hello world`")
            return
        await event.delete()
        await client.send_message(event.chat_id, content)


# ------------------------------------------------------------------
# Event handlers
# ------------------------------------------------------------------
@client.on(events.NewMessage(outgoing=True))
async def cmd_handler(event):
    """Handles all `.command` messages sent from your own account."""
    raw_text = event.raw_text.strip()

    # Any outgoing manual message automatically disables AFK
    # (but don't let the AFK/back commands themselves re-trigger weirdly).
    if afk.active and not raw_text.startswith("."):
        afk.disable()
        try:
            await event.respond("✅ **AFK auto-disabled** — welcome back!")
        except Exception:
            pass

    if not raw_text.startswith("."):
        return

    try:
        await _cmd_dispatch(event)
        # Ghost Mode: auto-delete the command's output after a delay so it
        # doesn't linger visibly in the chat. Skip for commands that already
        # delete themselves (they'll simply no-op on the second delete).
        if ghost_mode.enabled:
            async def _ghost_cleanup():
                await asyncio.sleep(ghost_mode.delete_delay)
                try:
                    await event.delete()
                except Exception:
                    pass
            asyncio.create_task(_ghost_cleanup())
    except Exception as e1:
        log_error(event.raw_text, e1)
        if auto_fix_active:
            await asyncio.sleep(1.5)
            try:
                await _cmd_dispatch(event)
                return
            except Exception as e2:
                log_error(event.raw_text + " [retry]", e2)
                try:
                    await event.respond(
                        f"⚠️ **Auto-fix**: `{event.raw_text}` failed twice.\n`{e2}`\nFull traceback → `.fixlog`"
                    )
                except Exception:
                    pass
        else:
            try:
                await event.respond(f"❌ Error: `{e1}`\n(Enable `.fix` for auto-retry + logging)")
            except Exception:
                pass


@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    """Handles moderation (mute/ban) + the AFK auto-reply logic."""
    global muted_users, banned_users
    me = await client.get_me()
    if event.sender_id == me.id:
        return

    # Existing mute/ban enforcement
    if event.sender_id in banned_users or event.sender_id in muted_users:
        try:
            await event.delete()
        except Exception:
            pass
        return

    # ---- AFK auto-reply: private chats only ----
    # Replies once per user, then again if that user messages after a
    # 6-hour silence (should_reply() encodes this rule).
    if afk.active and event.is_private:
        sender_id = event.sender_id
        if afk.should_reply(sender_id):
            afk.mark_replied(sender_id)
            duration = afk.duration_text()
            try:
                await event.respond(
                    f"{afk.message}\n\n_I have been away for {duration}._"
                )
            except Exception as e:
                log_error("afk_auto_reply", e)


# ------------------------------------------------------------------
# Health server for Render (keeps the service alive on its assigned PORT)
# ------------------------------------------------------------------
async def web_server():
    if not AIOHTTP_OK:
        log.warning("aiohttp not installed — no health endpoint. Run: pip install aiohttp")
        return
    from aiohttp import web as aw

    app = aw.Application()
    app.router.add_get("/", lambda r: aw.Response(text="SelfBot Running"))
    app.router.add_get("/health", lambda r: aw.Response(text="OK"))
    runner = aw.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = aw.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info(f"Health server running on port {port}")


# ------------------------------------------------------------------
# Entrypoint with crash-safe restart loop
# ------------------------------------------------------------------
async def run_client():
    try:
        if PHONE:
            # Interactive/local login flow — only used when no StringSession
            # is available and a phone number is supplied.
            await client.start(phone=PHONE)
        else:
            # StringSession (from SESSION_STRING) or an existing local
            # .session file is required here.
            await client.start()
    except (AuthKeyUnregisteredError, ValueError) as e:
        # ValueError is raised by Telethon when a StringSession string is
        # malformed/invalid; AuthKeyUnregisteredError means the session
        # was revoked/expired. Fail gracefully instead of crashing.
        log.error("Invalid SESSION_STRING. Please generate a new Telethon StringSession.")
        log_error("session_start", e)
        return

    me = await client.get_me()
    log.info(f"Logged in as: {me.first_name} (@{me.username}) | ID: {me.id}")
    log.info("SelfBot by Syed Rehan — running")
    log.info("Type .help or .commands in Telegram for the full command list")

    # Restore Whale Alert monitoring if it was left enabled before restart
    global _whale_task
    if whale_alert_active:
        _whale_task = asyncio.create_task(_whale_monitor_loop())
        log.info("Whale Alert monitor resumed from saved state.")

    await web_server()
    await client.run_until_disconnected()


async def main():
    """Crash-safe entrypoint: if the client loop dies unexpectedly, restart it."""
    backoff = 5
    while True:
        try:
            await run_client()
            break  # clean disconnect (e.g. manual stop) — exit loop
        except Exception as e:
            log.error(f"Fatal error, restarting in {backoff}s: {e}")
            log_error("main_loop", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    asyncio.run(main())
