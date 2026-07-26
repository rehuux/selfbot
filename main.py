import os
import re
import json
import time
import asyncio
import random
import logging
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
DEV_ROLE = "CyberSecurity Researcher & Ethical Hacker"
DEV_PORTFOLIO = "https://rehuux.vercel.app"
DEV_SKILLS = (
    "Security Researcher, Telegram Bot Development, "
    "Security/OSINT, Full-Stack Dev, and AI Integration"
)

# Spam command safety cap — prevents accidental account-flagging floods
SPAM_MAX_REPEATS = 20


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


HELP_TEXT = (
    "[𝗦𝗘𝗟𝗙𝗕𝗢𝗧 𝗕𝗬 𝗦𝘆𝗲𝗱 𝗥𝗲𝗵𝗮𝗻](https://rehuux.vercel.app)\n\n"
    "**Channels : **\n**`.autoaccept`** — toggle auto-accept requests\n\n"
    "**User Controls : ** _(reply, @user, or user id)_\n"
    "**`.mute`** / **`.unmute`** — silence a user\n"
    "**`.unban`** — unban user\n"
    "**`.block`** / **`.unblock`** — Telegram block\n"
    "**`.kick`** — kick from group\n"
    "**`.admin`** — promote user to group admin\n"
    "**`.demote`** — remove user's admin rights\n\n"
    "**Broadcasting : **\n**`.frwd`** _(reply)_ — forward to all DMs\n"
    "**`.gc`** _(reply)_ — blast all your groups\n"
    "**`.broad`** _(reply)_ — text all users\n"
    "**`.frwdall`** _(reply)_ — DMs + groups combined\n"
    "**`.dm @user msg`** — single DM\n"
    "**`.spm text N`** / **`.spam text N`** — repeat-send text N times in this chat\n\n"
    "**AFK : **\n**`.afk [message]`** — enable AFK auto-reply (DMs only, re-triggers after 6h)\n"
    "**`.back`** — disable AFK\n\n"
    "**Details : ** _(reply to get info)_\n"
    "**`.info`** — full user info\n**`.chatinfo`** — group/chat details\n**`.id`** — user or chat ID\n"
    "**`.insta @user`** — Instagram profile lookup\n\n"
    "**`.count N`** — countdown (1–300s)\n**`.del`** — nuke private chat history\n"
    "**`.purge N`** — delete last N messages\n**`.close N`** — leave group after N sec\n"
    "**`.mm`** _(reply)_ — open middleman group\n**`.tag`** — tag all group members\n"
    "**`.say text`** — ghost-send a message\n"
    "**`.calc expr`** — calculator\n**`.tr <lang> [text]`** — translate text or a reply\n\n"
    "**Reliability : **\n**`.fix`** — toggle auto-fix (retry + log errors)\n"
    "**`.fixlog`** — show last logged errors\n\n"
    "**Fun & Utility : **\n"
    "**`.weather <city>`** — current weather\n"
    "**`.crypto <coin>`** — live crypto price (e.g. `.crypto bitcoin`)\n"
    "**`.define <word>`** — dictionary lookup\n"
    "**`.github <user>`** — GitHub profile info\n"
    "**`.short <url>`** — shorten a link\n"
    "**`.qr <text>`** — generate a QR code\n"
    "**`.quote`** — random inspirational quote\n"
    "**`.joke`** — random joke\n"
    "**`.8ball <question>`** — magic 8-ball answer\n"
    "**`.roll [N]`** — roll a dice (default 1–6)\n"
    "**`.flip`** — flip a coin\n"
    "**`.reverse text`** — reverse text\n"
    "**`.ping`** — check bot response latency\n\n"
    "**Info : **\n**`.help`** / **`.commands`** — this list\n**`.dev`** — about the developer\n\n"
    "𝗗𝗘𝗩 ~ 𝗦𝘆𝗲𝗱 𝗥𝗲𝗵𝗮𝗻"
)


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
        await event.edit(HELP_TEXT)

    elif text == ".dev":
        await event.edit(
            "**👨‍💻 Developer Info**\n\n"
            f"✓ **Name:** `{DEV_NAME}`\n"
            f"✓ **Role:** `{DEV_ROLE}`\n"
            f"✓ **Skills:** {DEV_SKILLS}\n"
            f"✓ **Portfolio:** {DEV_PORTFOLIO}\n\n"
            "_This selfbot was built and is maintained by Syed Rehan — "
            "covering everything from the AFK system, moderation tools, "
            "and broadcast engine, to the Render deployment setup._"
        )

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

    elif text.startswith(".count"):
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

    elif text.startswith(".tr") or text.startswith(".translate"):
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
