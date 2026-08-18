# 🤖 Telegram SelfBot by Syed Rehan

A production-ready, ultra-fast Telegram **userbot (selfbot)** built with [Telethon](https://github.com/LonamiWebs/Telethon) — featuring **200+ commands**, full moderation toolkit, OSINT & security utilities, smart **AFK auto-reply engine**, media/music downloaders, Instagram HD PFP downloader (`.igpfp`), text-to-speech voice notes (`.tts`), crypto market tracking, broadcast system, and 24/7 one-click cloud deployment on [Render](https://render.com) using native **Telethon StringSession** (zero SQLite corruption, zero interactive prompts).

> Personal automation for your Telegram account — moderation, OSINT, broadcasting, AI speech, info lookups, and an intelligent AFK auto-responder running 24/7 in the cloud.

---

## 📌 Table of Contents

- [What This Project Is](#-what-this-project-is)
- [How It Works](#-how-it-works)
- [Architecture Overview](#-architecture-overview)
- [✨ Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Getting Telegram API Credentials](#-getting-telegram-api-credentials)
- [Generating a StringSession](#-generating-a-stringsession)
- [Local Setup](#-local-setup)
- [Deploying on Render](#-deploying-on-render)
- [Environment Variables](#-environment-variables)
- [📖 Full Command Reference (200+ Commands)](#-full-command-reference-200-commands)
  - [1. 🤖 Info & Telegram](#1--info--telegram)
  - [2. 🛡 Security & OSINT](#2--security--osint)
  - [3. 🛠 Productivity & Utilities](#3--productivity--utilities)
  - [4. 👤 User & Stealth](#4--user--stealth)
  - [5. 🧩 Moderation](#5--moderation)
  - [6. 📡 Broadcast & Messaging](#6--broadcast--messaging)
  - [7. 🎨 Text & Font Styles](#7--text--font-styles)
  - [8. 🎉 Fun & Games](#8--fun--games)
  - [9. 💰 Crypto & Financial Markets](#9--crypto--financial-markets)
  - [10. ⚙️ System & Diagnostics](#10-️-system--diagnostics)
- [🌙 AFK System — In Depth](#-afk-system--in-depth)
- [🛡 Moderation System — In Depth](#-moderation-system--in-depth)
- [📡 Broadcast System — In Depth](#-broadcast-system--in-depth)
- [🛠 Reliability, Auto-Fix & Crash Recovery](#-reliability-auto-fix--crash-recovery)
- [🩺 Health Server & Uptime](#-health-server--uptime)
- [❓ Frequently Asked Questions](#-frequently-asked-questions)
- [🩹 Troubleshooting](#-troubleshooting)
- [📄 License](#-license)
- [⚠️ Disclaimer](#-disclaimer)
- [👤 Credits](#-credits)

---

## 🧠 What This Project Is

This is a **selfbot** — it runs on your **own personal Telegram account** (not a Bot API bot with a `@BotFather` token). It logs in as *you*, using Telethon's MTProto client library, and listens for special `.command` messages that you type from your own account.

Unlike a regular Telegram Bot (which has its own identity, limited permissions, and cannot read normal DMs unless messaged first), a selfbot has the **full capabilities of a user account** — it can read all your chats, act in any group you're in, message anyone, and execute complex workflows on your behalf.

It is designed for people who want to:
- Auto-reply to messages when away with smart duration tracking (**AFK**)
- Download Instagram Full HD Profile Pictures (`.igpfp`) without logging in
- Convert text or replied messages to AI voice notes instantly (`.tts`)
- Moderate groups efficiently (mute/ban/kick/warn/clean via commands)
- Perform OSINT lookups (IP, WHOIS, DNS, Subdomains, SSL certificates, CVEs)
- Broadcast announcements safely across DMs and groups with anti-flood pacing
- Track real-time crypto prices, gas fees, and market cap metrics
- Run all of this as a **24/7 hosted service** on Render, Railway, VPS, or local machine

---

## ⚙️ How It Works

1. **Authentication via StringSession** — The bot connects to Telegram using a native Telethon **StringSession**: an encrypted token representing an authorized login. Generated once via `generate_session.py`, stored as the `SESSION_STRING` environment variable.
2. **Persistent Connection** — Telethon maintains a persistent MTProto socket connection to Telegram's servers for low-latency event delivery.
3. **Dual Event Handling**:
   - **Outgoing messages** starting with `.` → parsed as commands (`.igpfp`, `.tts`, `.mute`, `.afk`, etc.)
   - **Incoming messages** → checked against moderation rules (muted/banned users) and evaluated for AFK auto-replies.
4. **Self-Healing Command Dispatcher** — Commands execute via `_cmd_dispatch` which edits your message in place with rich Markdown results and handles retries / logging.
5. **Multi-Threaded / Async Execution** — Heavy tasks (TTS generation, OSINT scrapers, image processing, downloads) run in non-blocking thread executors (`run_in_executor`).
6. **Health Server** — An internal `aiohttp` HTTP server runs on the assigned `PORT`, serving `/` and `/health` so cloud health checks keep the bot running 24/7.
7. **Crash Recovery Loop** — A resilient wrapper with exponential backoff automatically restarts the client on network or server disruptions.

---

## 🏗 Architecture Overview

```
                        ┌─────────────────────────────┐
                        │        Telegram Servers      │
                        │         (MTProto API)        │
                        └───────────────┬───────────────┘
                                        │ persistent connection
                                        ▼
                        ┌─────────────────────────────┐
                        │       Telethon Client        │
                        │   (StringSession-authorized) │
                        └───────────────┬───────────────┘
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │ Outgoing Handler │ │ Incoming Handler │ │  Health Server   │
          │  (200+ commands) │ │ (mod + AFK logic)│ │  (aiohttp /PORT) │
          └─────────────────┘ └─────────────────┘ └─────────────────┘
                    │                   │
                    ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐
          │  Engine Modules  │ │   AFK State     │
          │ OSINT/Media/TTS/│ │ (in-memory, per │
          │ Mod/Broadcast   │ │  process runtime)│
          └─────────────────┘ └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │ selfbot_data.json│  ← persists muted/banned user & group lists
          │   errors.log     │  ← persists auto-fix error logs
          └─────────────────┘
```

---

## ✨ Key Features

- 📸 **Instagram Profile Downloader (`.igpfp`)** — Fetches full HD profile pictures and account stats without login or API keys.
- 🎙 **AI Text-To-Speech (`.tts`)** — Converts text or replied messages into voice notes with multi-language support (`en`, `hi`, etc.).
- 🛡 **Security & OSINT Hub** — Real-time IP intelligence, WHOIS, DNS queries, Subdomain enumeration, SSL inspection, CVE lookups, Base64/Hash/Hex tools.
- 🌙 **Smart AFK Engine** — DM-only auto-responder, replies once per user, duration counters, auto-deactivates on outgoing message.
- 🧩 **Advanced Group Moderation** — Mute, Ban, Softban, Kick, Promote/Demote, Timed Mute/Ban, Warn system, and Batch Message Purges.
- 📡 **Anti-Flood Broadcast System** — Forward or send messages across all DMs/groups with randomized delays and rate-limit protection.
- 💰 **Crypto & Finance Tools** — Real-time prices (`.btc`, `.eth`, `.sol`), Fear & Greed index, gas fees, fiat rates, portfolio valuation.
- 🎨 **Text Styling & Font Generator** — Over 20 aesthetic Unicode fonts, text flips, vaporwave, leet-speak, and spoilers.
- 🛠 **24/7 Cloud Resilience** — Native Telethon StringSession, automatic crash recovery, health endpoint for Render/Railway/VPS.

---

## 📁 Project Structure

```
selfbot/
├── main.py                # Core selfbot logic — 200+ commands, AFK engine, handlers
├── generate_session.py    # Local script to produce a Telethon StringSession
├── requirements.txt       # Python dependencies
├── render.yaml            # Render Blueprint service definition
├── Procfile               # PaaS start command definition
├── runtime.txt            # Python runtime version pin
├── .gitignore             # Excludes session files & secrets from git
├── LICENSE                # Custom attribution license (credit required)
└── README.md              # Project documentation
```

---

## ✅ Requirements

- Python **3.10+** (Python 3.11 recommended)
- Telegram account (API credentials from [my.telegram.org](https://my.telegram.org))
- A free account on [Render](https://render.com) (or any VPS/PaaS)

---

## 🔑 Getting Telegram API Credentials

1. Go to **https://my.telegram.org** and sign in with your phone number.
2. Navigate to **API Development Tools**.
3. Create a new application (enter any name and short title).
4. Copy your **`api_id`** (numeric) and **`api_hash`** (hex string).

---

## 🧩 Generating a StringSession

Generate your session **once locally** on your computer:

```bash
pip install telethon
python generate_session.py
```

Follow the terminal prompts (API ID, API Hash, Phone Number with country code, and OTP code).
Copy the resulting `SESSION_STRING` string securely.

---

## 💻 Local Setup

```bash
# Clone the repository
git clone https://github.com/rehuux/selfbot.git
cd selfbot

# Install requirements
pip install -r requirements.txt

# Set Environment Variables (Linux/macOS)
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export SESSION_STRING="your_generated_session_string"

# Or on Windows (PowerShell)
$env:API_ID="your_api_id"
$env:API_HASH="your_api_hash"
$env:SESSION_STRING="your_generated_session_string"

# Run the selfbot
python main.py
```

---

## ☁️ Deploying on Render

### Option A — Render Blueprint (Fastest)
1. Push this repository to your GitHub account.
2. In Render, click **New +** → **Blueprint**.
3. Select your repository. Render will automatically read `render.yaml`.
4. Enter `API_ID`, `API_HASH`, and `SESSION_STRING`.
5. Click **Apply**.

### Option B — Manual Web Service
1. In Render, click **New +** → **Web Service**.
2. Select your repository.
3. Configure settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. In the **Environment** tab, add:
   - `API_ID`
   - `API_HASH`
   - `SESSION_STRING`
5. Click **Deploy**.

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|:---:|---|
| `API_ID` | ✅ | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | Telegram API Hash from my.telegram.org |
| `SESSION_STRING` | ✅ | Telethon StringSession generated via `generate_session.py` |
| `PORT` | ⚙️ auto | Port assigned by hosting provider (default `8080`) |

---

## 📖 Full Command Reference (200+ Commands)

> All commands use the `.` prefix and are typed directly from your account in any Telegram chat.

### 1. 🤖 Info & Telegram
| Command | Description |
|---|---|
| `.info` / `.userinfo` | Get complete details of a user (reply, `@username`, or ID) |
| `.chatinfo` / `.tinfo` | Display current group or channel metadata and stats |
| `.id` | Get user ID, chat ID, and replied message ID |
| `.myid` | Quickly display your own user ID |
| `.igpfp <username>` | Download full-resolution Instagram Profile Picture & stats |
| `.insta <username>` | View Instagram profile details (followers, bio, link) |
| `.github <username>` | Look up GitHub user profile and public repos |
| `.repo <owner/repo>` | View GitHub repository details and stats |
| `.time` / `.worldtime` | Display current UTC and major global timezones |
| `.admins` | List all administrators in current group |
| `.bots` | List all active bots in current group |
| `.members` | Display member statistics and active user count |
| `.zombies` | Scan and remove deleted accounts from the group |
| `.dc` | Show Telegram Data Center (DC) information |
| `.link` | Generate an invite or direct link for current message/chat |
| `.pin` / `.unpin` | Pin or unpin a replied message |
| `.unpinall` | Unpin all pinned messages in the chat |
| `.pinned` | View the latest pinned message |
| `.title <new_title>` | Change the title of the current group |
| `.setdesc <text>` | Change the description of the current group |
| `.slow <seconds>` | Set group slowmode duration (0 to disable) |
| `.lock <type>` | Restrict group permissions (media, stickers, polls, etc.) |
| `.unlock <type>` | Re-enable restricted group permissions |
| `.dialogs` | Show total count of chats, channels, and groups |
| `.firstmsg` | Find the first message in the current chat |
| `.unread` | View unread chat count |
| `.ocr` | Extract text from replied image or document |

---

### 2. 🛡 Security & OSINT
| Command | Description |
|---|---|
| `.ip <ip/domain>` | Comprehensive IP geolocation, ISP, ASN, and map lookup |
| `.myip` | Show server public IP and hosting location |
| `.whois <domain>` | WHOIS domain registration and registrar lookup |
| `.dns <domain>` | Query DNS records (A, AAAA, MX, TXT, NS) |
| `.subdomains <domain>` | Enumerate known public subdomains |
| `.ssl <domain>` | Check SSL/TLS certificate validity, issuer, and expiry |
| `.headers <url>` | Inspect HTTP response headers of a target website |
| `.unshort <short_url>`| Unshorten and trace redirect URL chains |
| `.httpstatus <code>` | Explain HTTP response status codes |
| `.bin <6_digits>` | Credit/Debit card BIN lookup (brand, type, issuing bank) |
| `.cve <CVE-ID>` | Query National Vulnerability Database for CVE advisory |
| `.genpass <length>` | Generate a secure, cryptographically random password |
| `.b64 <enc/dec> <txt>`| Encode or decode Base64 strings |
| `.hash <txt>` | Compute MD5, SHA1, SHA256, and SHA512 hashes |
| `.hex <enc/dec> <txt>`| Convert text to or from hexadecimal format |
| `.binary <enc/dec>` | Convert text to or from binary |
| `.rot13 <text>` | Apply ROT13 Caesar cipher encryption/decryption |
| `.morse <enc/dec>` | Convert text to or from Morse code |
| `.urlencode <text>` | URL-encode a given string |
| `.urldecode <text>` | Decode a URL-encoded string |
| `.uuid` | Generate a fresh UUIDv4 identifier |
| `.jwt <token>` | Parse and inspect JWT payload without signature verification |
| `.secret <text>` | Encrypt or encode sensitive scratchpads |
| `.net <host>` | Check host latency and network availability |

---

### 3. 🛠 Productivity & Utilities
| Command | Description |
|---|---|
| `.tts [lang] <text>` | Convert text or replied message to natural voice note |
| `.music <query>` | Search and download music/audio tracks |
| `.song <query>` | Quick audio lookup |
| `.lyrics <song name>` | Fetch complete song lyrics |
| `.paste <text>` | Upload code or text to Spacebin/Hastebin |
| `.calc <expression>` | Safe mathematical calculator |
| `.weather <city>` | Live weather, temperature, humidity, and forecast |
| `.tr <lang> [text]` | Translate text to any language (or reply to a message) |
| `.qr <text/url>` | Generate a high-contrast QR Code image |
| `.scanqr` | Decode QR code from a replied photo |
| `.wiki <query>` | Search Wikipedia and return concise summaries |
| `.define <word>` | English dictionary definition, phonetics, and synonyms |
| `.short <long_url>` | Shorten a long URL via CleanURI/TinyURL |
| `.currency <amt> <f> <t>`| Convert live fiat currencies (e.g. `.currency 100 USD INR`) |
| `.remind <time> <msg>`| Set a reminder alert (e.g. `.remind 10m Check server`) |
| `.timer <seconds>` | Countdown timer in chat |
| `.todo <add/list/del>`| In-chat personal task checklist |
| `.note <name> <text>` | Save persistent quick-notes |
| `.notes` | List all saved notes |
| `.unit <val> <from> <to>`| Convert units of measurement (km to miles, etc.) |
| `.json <text>` | Format and validate raw JSON |
| `.wordcount` | Count words, characters, and reading time of replied text |
| `.epoch [timestamp]` | Convert between Epoch timestamps and human dates |
| `.age <YYYY-MM-DD>` | Calculate exact age and days lived |
| `.daysuntil <date>` | Count days remaining until target date |
| `.randnum <min> <max>`| Generate a random number within range |
| `.pick <item1, item2>`| Pick a random option from a comma-separated list |
| `.color <hex>` | Display color preview swatch from hex code |
| `.lorem [words]` | Generate placeholder Lorem Ipsum text |

---

### 4. 👤 User & Stealth
| Command | Description |
|---|---|
| `.afk [reason]` | Activate AFK auto-responder |
| `.back` / `.unafk` | Deactivate AFK and display time spent away |
| `.status` | Display bot and account operational state |
| `.me` | Display your account profile snapshot |
| `.myusername` | Display your handle and profile permalink |
| `.ghost` | Toggle ghost mode status indicator |
| `.analytics` | View message and command usage analytics |
| `.mood <text>` | Set temporary mood status flair |
| `.speed` | Measure server ping, download, and upload speeds |
| `.clearcache` | Clear temporary media and download cache |
| `.setname <first> [last]`| Update your Telegram first/last name |
| `.setbio <text>` | Update your Telegram profile bio |
| `.setpfp` | Set replied image as your new profile photo |
| `.delpfp` | Delete your latest profile photo |
| `.block` | Block a user (reply, `@username`, or ID) |
| `.unblock` | Unblock a user |

---

### 5. 🧩 Moderation
| Command | Description |
|---|---|
| `.mute` / `.unmute` | Mute/unmute user (auto-deletes incoming messages) |
| `.unmuteall` | Clear all muted users from database |
| `.ban` / `.unban` | Ban/unban user from bot and current group |
| `.unbanall` | Clear all banned users from database |
| `.kick` | Remove user from current group |
| `.softban` | Ban and immediately unban to clear user's messages |
| `.tban <time> <user>` | Temporarily ban user (e.g. `.tban 1h @spammer`) |
| `.tmute <time> <user>`| Temporarily mute user |
| `.admin [title]` | Promote user to group admin with optional custom title |
| `.demote` | Demote an admin back to regular member |
| `.del` | Delete replied message |
| `.purge <N>` | Delete last N messages in the chat |
| `.purgeme <N>` | Delete only your own last N messages |
| `.delall` | Clear private chat history |
| `.delmsgs <N>` | Batch delete specific message range |
| `.warn [reason]` | Issue a moderation warning to a user |
| `.warns` | Check user warning count |
| `.resetwarns` | Reset warnings for target user |
| `.clean` | Clean spam and bot clutter in group |
| `.close <seconds>` | Leave current group after a specified delay |

---

### 6. 📡 Broadcast & Messaging
| Command | Description |
|---|---|
| `.frwd` | Forward replied message to all open DMs |
| `.gc` | Broadcast replied message to all admin groups |
| `.broad` | Send text content of replied message to all DMs |
| `.frwdall` | Broadcast to both all DMs and all admin groups |
| `.dm <@user> <msg>` | Send direct message to a user |
| `.massdm <msg>` | Send direct message to all contact chats |
| `.broadcastgc <msg>` | Broadcast text announcement to all groups |
| `.dmfrwd <@user>` | Forward replied message to a specific user |
| `.tag [message]` | Mention all members in the current group |
| `.say <message>` | Send a message and silently delete your `.say` command |
| `.echo <message>` | Echo text back into the chat |
| `.type <message>` | Animated typewriter text effect |
| `.poll <Q> \| <A> \| <B>`| Create a fast Telegram poll |
| `.count <N> [msg]` | Countdown timer message |
| `.spam <N> <text>` | Safe repetitive sender with built-in pacing |
| `.mm <@user>` | Initiate a middleman trade transaction prompt |

---

### 7. 🎨 Text & Font Styles
| Command | Description |
|---|---|
| `.font <style> <text>`| Apply styles (`bold`, `italic`, `mono`, `gothic`, etc.) |
| `.shout <text>` | S H O U T E D  S P A C E D  T E X T |
| `.mock <text>` | mOcKiNg sPoNgEbOb cAsE |
| `.leet <text>` | 1337 5P34K translation |
| `.zalgo <text>` | C̶o̶r̶r̶u̶p̶t̶e̶d̶ glitch text |
| `.spoiler <text>` | Wrap message in Telegram spoiler tags |
| `.bubble <text>` | Ⓟⓤⓑⓑⓛⓔ ⓣⓔⓧⓣ |
| `.gothic <text>` | 𝔊𝔬𝔱𝔥𝔦𝔠 / 𝔉𝔯𝔞𝔨𝔱𝔲𝔯 𝔣𝔬𝔫𝔱 |
| `.square <text>` | 🅂🅀🅄🄰🅁🄴 🅃🄴🅇🅃 |
| `.cursive <text>` | 𝒞𝓊𝓇𝓈𝒾𝓋ℯ 𝓈𝒸𝓇𝒾𝓅𝓉 |
| `.smallcaps <text>` | sᴍᴀʟʟ ᴄᴀᴘs ғᴏɴᴛ |
| `.flip <text>` | ʇxǝʇ pǝddᴉlɟ uʍop-ǝpᴉsd∩ |
| `.mirror <text>` | ɈxɘɈ bɘɿoɿɿiM |
| `.upper <text>` | CONVERT TEXT TO ALL UPPERCASE |
| `.lower <text>` | convert text to all lowercase |
| `.titlecase <text>` | Capitalize Each Word Correctly |
| `.vaporwave <text>` | Ｗ Ｉ Ｄ Ｅ  Ｖ Ａ Ｐ Ｏ Ｒ Ｗ Ａ Ｖ Ｅ |
| `.superscript <txt>` | Sᵘᵖᵉʳˢᶜʳᶦᵖᵗ text |
| `.subscript <txt>` | Sᵤbₛ꜀ᵣᵢₚₜ text |

---

### 8. 🎉 Fun & Games
| Command | Description |
|---|---|
| `.react <emoji>` | Add animated reaction to replied message |
| `.meme` | Fetch a random trending meme from Reddit |
| `.cat` / `.dog` | Fetch cute cat or dog photos |
| `.anime [query]` | Look up anime synopsis, rating, and episodes |
| `.quote` | Inspiring famous quotes |
| `.joke` | Tech, dad, and programming jokes |
| `.trivia` | Random trivia question with spoiler answer |
| `.fact` | Interesting verified world fact |
| `.8ball <question>` | Magic 8-Ball oracle answer |
| `.roll [max]` | Roll a random die (default 1–100) |
| `.flip` | Flip a coin (Heads or Tails) |
| `.dice` | Roll animated Telegram dice |
| `.slap <@user>` | Slap a user with a humorous object |
| `.roast <@user>` | Generate a lighthearted programming roast |
| `.compliment <@user>`| Send a wholesome compliment |
| `.insult <@user>` | Cyber & tech-themed insult |
| `.truth` | Truth prompt for parties |
| `.dare` | Dare prompt for parties |
| `.rps <rock/paper/scissors>`| Play Rock, Paper, Scissors |
| `.bored` | Productivity activities when feeling bored |
| `.hack <@user>` | Fun fake terminal hacking simulation |

---

### 9. 💰 Crypto & Financial Markets
| Command | Description |
|---|---|
| `.crypto <symbol>` | Real-time crypto price, 24h change, and volume |
| `.btc` / `.eth` / `.sol`| Instant price check for Bitcoin, Ethereum, and Solana |
| `.fng` / `.feargreed` | Live Crypto Fear & Greed Index |
| `.gas` | Live Ethereum network gas tracker (Gwei) |
| `.marketcap` | Total cryptocurrency global market capitalization |
| `.convertcrypto <amt> <f> <t>`| Convert between crypto pairs (e.g. `.convertcrypto 1 BTC USDT`) |
| `.fiat <USD/EUR/INR>`| Check major fiat exchange rates |
| `.whale` | Scan recent large on-chain transactions |
| `.portfolio` | Summary calculation of crypto holdings |

---

### 10. ⚙️ System & Diagnostics
| Command | Description |
|---|---|
| `.help [category/cmd]`| Interactive help matrix |
| `.ping` | Check bot response latency (ms) |
| `.alive` | Display uptime, system load, and status card |
| `.uptime` | Show exact hours, minutes, and seconds running |
| `.sysinfo` | CPU usage, RAM utilization, OS, and Python version |
| `.dev` / `.owner` | Display developer profile and credits |
| `.autoaccept` | Toggle auto-accepting chat join requests |
| `.fix` | Toggle auto-fix and retry mode |
| `.fixlog` | View recent system error entries from `errors.log` |
| `.restart` | Safely reboot the selfbot process |
| `.version` | Display current build version |

---

## 🌙 AFK System — In Depth

- **DM-Only Operation:** Never responds in group chats to avoid spamming public channels.
- **Rate-Limited Responding:** Replies strictly **once per user** per AFK session.
- **Custom Away Message:** Pass custom context like `.afk Writing code, back at 6 PM`.
- **Duration Reporting:** When returning with `.back`, computes total time spent away.
- **Smart Activity Detection:** Any outgoing manual message automatically deactivates AFK.

---

## 🛡 Moderation System — In Depth

- **Persistent Blacklists:** Muted and banned user lists are stored in `selfbot_data.json` and survive service restarts.
- **Instant Message Interception:** Incoming messages from muted accounts are deleted instantly.
- **Group Admin Checks:** High-privilege actions (`.kick`, `.admin`, `.slow`) automatically enforce Telegram permission checks.

---

## 📡 Broadcast System — In Depth

- **Smart Pacing (`safe_sleep`):** Enforces 5–10s randomized delays and a 40s rest after every 15 chats.
- **Failure Resilience:** Tracks successful vs failed deliveries and produces an accurate end-of-broadcast report.

---

## 🛠 Reliability, Auto-Fix & Crash Recovery

- **Automatic Retries:** `.fix` intercepts errors, retries the command once, and logs failure traces into `errors.log`.
- **Exponential Backoff:** If disconnected, client attempts reconnects (5s → 10s → 20s → up to 60s).
- **Graceful Token Handling:** Detects expired or revoked StringSessions cleanly without entering crash loops.

---

## 🩺 Health Server & Uptime

- Built-in `aiohttp` microservice listening on `$PORT`.
- `GET /` → Returns `SelfBot Running`.
- `GET /health` → Returns HTTP 200 `OK`.
- Keeps cloud services on Render, Railway, and Fly.io healthy and active.

---

## ❓ Frequently Asked Questions

**Q: Is this a regular Bot API bot?**
No. This is a *userbot* (selfbot) that runs on your personal Telegram account via Telethon.

**Q: Will my account get banned?**
Using standard utility commands carries virtually no risk. Mass-broadcasting or spamming large volumes of unsolicited messages may trigger Telegram's anti-spam algorithms. Always broadcast responsibly.

**Q: Can I run this on my own VPS or computer?**
Yes. Any environment running Python 3.10+ will run this selfbot seamlessly.

---

## 🩹 Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `sqlite3.DatabaseError` | Old SQLite session used with StringSession | Run `python generate_session.py` to get a fresh string |
| `Invalid SESSION_STRING` | Malformed or revoked string | Regenerate your `SESSION_STRING` and update env vars |
| Bot not responding | Message not sent from your account or missing `.` | Send commands directly from your logged-in account |
| `.igpfp` not finding user | Private or rate-limited account | Verify username spelling; bot uses multiple public proxy mirrors |

---

## 📄 License

This project is licensed under a **Custom Attribution License** (based on MIT).
- You are free to fork, customize, and deploy this project.
- **Attribution to the original author, Syed Rehan, is mandatory** in any fork, documentation, or deployed instances.

---

## ⚠️ Disclaimer

This project is intended strictly for personal productivity, community moderation, and ethical research. Automated mass-messaging can violate Telegram's Terms of Service if misused. Use this software responsibly. The author is not liable for any account restrictions or damages resulting from misuse.

---

## 👤 Credits

**Developed by [Syed Rehan](https://rehuux.vercel.app)**
*CyberSecurity Researcher & Ethical Hacker · Web & Bot Developer · OSINT · AI Integration*

- **Website / Portfolio:** [rehuux.vercel.app](https://rehuux.vercel.app)
- **GitHub:** [@rehuux](https://github.com/rehuux)
- **Telegram:** Contact via your personal account instance

*Built with [Telethon](https://github.com/LonamiWebs/Telethon) & Python Asyncio.*
