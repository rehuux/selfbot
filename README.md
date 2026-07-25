# 🤖 Telegram SelfBot — by Syed Rehan

A production-ready Telegram **userbot (selfbot)** built with [Telethon](https://github.com/LonamiWebs/Telethon), featuring group/DM moderation tools, broadcasting utilities, OSINT lookups, and a smart **AFK auto-reply system** — deployable on [Render](https://render.com) with zero manual setup after the first run.

---

## 📌 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Getting Telegram API Credentials](#-getting-telegram-api-credentials)
- [Generating a Session String](#-generating-a-session-string)
- [Local Setup](#-local-setup)
- [Deploying on Render](#-deploying-on-render)
- [Environment Variables](#-environment-variables)
- [Command Reference](#-command-reference)
- [AFK System](#-afk-system)
- [Reliability & Auto-Fix](#-reliability--auto-fix)
- [Security Notes](#-security-notes)
- [Troubleshooting](#-troubleshooting)
- [Disclaimer](#-disclaimer)
- [Credits](#-credits)

---

## ✨ Features

- **Full moderation toolkit** — mute, ban, block, kick, promote/demote admins
- **Broadcast utilities** — forward or send messages across DMs and groups with built-in anti-ban delays
- **AFK auto-reply system** — DM-only, replies once per user, auto-disables when you send a message
- **OSINT / info lookups** — Telegram user info, chat info, Instagram profile lookups
- **Utility commands** — translator, calculator, countdown timer, ghost-send, auto chat cleanup
- **Self-healing** — auto-fix mode retries failed commands and logs errors
- **Render-ready** — environment-variable driven config, health-check endpoint, crash-safe restart loop
- **No interactive login required after deployment** — session is loaded from an environment variable

---

## 📁 Project Structure

```
selfbot/
├── main.py                # Core bot logic — all commands, AFK system, event handlers
├── generate_session.py    # One-time local script to produce SESSION_STRING
├── requirements.txt       # Python dependencies
├── render.yaml             # Render Blueprint service definition
├── Procfile                 # Fallback start command for PaaS platforms
├── runtime.txt                # Pins the Python version
├── .gitignore                   # Keeps session files & secrets out of git
└── README.md                      # This file
```

---

## ✅ Requirements

- Python **3.11+**
- A Telegram account (the one the selfbot will run as)
- Telegram API credentials (`API_ID`, `API_HASH`)
- A [Render](https://render.com) account (free tier works)
- A GitHub repository to connect to Render

---

## 🔑 Getting Telegram API Credentials

1. Go to **https://my.telegram.org**
2. Log in with your phone number
3. Open **API Development Tools**
4. Create an app (any name/description works)
5. Copy the **`api_id`** and **`api_hash`** shown — you'll need both

---

## 🧩 Generating a Session String

Render deployments must **never** require an interactive phone/OTP login — so you generate a session **once, locally**, and feed it to Render as an environment variable.

```bash
pip install telethon
python generate_session.py
```

You will be prompted for:
- `API_ID`
- `API_HASH`
- Your phone number + the OTP Telegram sends you

At the end, a long base64 string is printed. **Copy and store it securely** — this is your `SESSION_STRING`. Treat it exactly like a password: anyone with this string has full access to your Telegram account.

---

## 💻 Local Setup

```bash
git clone https://github.com/rehuux/selfbot.git
cd selfbot
pip install -r requirements.txt

# Set environment variables (Linux/macOS)
export API_ID=your_api_id
export API_HASH=your_api_hash
export SESSION_STRING=your_generated_session_string

# Or on Windows (PowerShell)
$env:API_ID="your_api_id"
$env:API_HASH="your_api_hash"
$env:SESSION_STRING="your_generated_session_string"

python main.py
```

If everything is set correctly, you'll see:

```
Logged in as: YourName (@yourusername) | ID: xxxxxxxx
SelfBot by Syed Rehan — running
Type .help in Telegram for the full command list
Health server running on port 8080
```

---

## ☁️ Deploying on Render

### Option A — Blueprint (recommended, fastest)

1. Push your project to a GitHub repository (see structure above)
2. Log in to [Render](https://render.com) with GitHub
3. Click **New +** → **Blueprint**
4. Select your repository — Render automatically detects `render.yaml`
5. Fill in the requested environment variables:
   - `API_ID`
   - `API_HASH`
   - `SESSION_STRING`
6. Click **Apply** / **Deploy**

### Option B — Manual Web Service

1. **New +** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Go to the **Environment** tab and add the same three variables
5. Click **Create Web Service**

### Verifying Deployment

- Check the **Logs** tab — you should see `Logged in as: ...`
- Visit your Render service URL — it should return `SelfBot Running`
- `GET /health` should return `OK`
- From Telegram, send `.help` from your own account to confirm commands respond

---

## 🔐 Environment Variables

| Variable         | Required | Description                                                        |
|-------------------|:--------:|----------------------------------------------------------------------|
| `API_ID`          | ✅       | Telegram API ID from my.telegram.org                                |
| `API_HASH`        | ✅       | Telegram API Hash from my.telegram.org                              |
| `SESSION_STRING`  | ✅       | Base64-encoded session, generated once via `generate_session.py`    |
| `PORT`            | ⚙️ auto  | Set automatically by Render; used by the health-check web server    |
| `PHONE`           | ❌ optional | Only needed for interactive local login instead of `SESSION_STRING` |

---

## 📖 Command Reference

### Channels
| Command | Description |
|---|---|
| `.autoaccept` | Toggle auto-accepting chat requests |

### User Controls *(reply, @username, or user ID)*
| Command | Description |
|---|---|
| `.mute` / `.unmute` | Silence a user (their messages get deleted) |
| `.unban` | Remove a user from the ban list |
| `.block` / `.unblock` | Telegram-level block/unblock |
| `.kick` | Remove a user from a group |
| `.admin` | Promote a user to group admin |
| `.demote` | Remove a user's admin rights |

### Broadcasting *(reply to the message you want to send)*
| Command | Description |
|---|---|
| `.frwd` | Forward the replied message to all your DMs |
| `.gc` | Broadcast the replied message to all your groups |
| `.broad` | Send the replied message's text to all DM contacts |
| `.frwdall` | Combined DM + group broadcast |
| `.dm @user message` | Send a single direct message |

> All broadcast commands use randomized delays (5–10s, with a 40s pause every 15 messages) to reduce the risk of rate limits or account restrictions.

### Info & Lookups
| Command | Description |
|---|---|
| `.info` / `.tinfo` | Full Telegram user info (reply or `@username`) |
| `.chatinfo` | Details about the current group/channel |
| `.id` | Get a user's or chat's ID |
| `.insta @username` | Instagram profile lookup |

### Utilities
| Command | Description |
|---|---|
| `.count N [message]` | Countdown timer (1–300 seconds) |
| `.del` | Clear private chat history |
| `.purge N` | Delete the last N messages in a chat |
| `.close N` | Leave the current group after N seconds |
| `.mm` | Create a middleman group with a user |
| `.tag [message]` | Tag all group members |
| `.say text` | Send a message anonymously (deletes your command) |
| `.calc expression` | Evaluate a math expression |
| `.tr <lang> [text]` | Translate text or a replied message |

### Reliability
| Command | Description |
|---|---|
| `.fix` | Toggle auto-fix mode (retries failed commands once, logs errors) |
| `.fixlog` | Show the last logged errors |

### AFK
| Command | Description |
|---|---|
| `.afk [custom message]` | Enable AFK auto-reply |
| `.back` | Disable AFK and show how long you were away |

---

## 🌙 AFK System

The AFK module is designed to behave like a professional "away" auto-responder:

- **DM-only** — never replies inside groups
- **Replies once per user** — no spam if someone sends multiple messages while you're away
- **Custom messages** — `.afk Busy with a client call` sets your own away message
- **Duration tracking** — `.back` reports how long you were away (e.g. *"I have been away for 12 minutes"*)
- **Auto-disable** — sending any manual message from your account turns AFK off automatically
- **State reset** — the replied-users list clears every time AFK is toggled on/off

Default message (used when no custom text is given):

> *"Hello, I will be with you shortly (approximately 5–20 minutes). To help me assist you efficiently, please describe what you are interested in or what services you require."*

---

## 🛠 Reliability & Auto-Fix

- `.fix` toggles a safety net: if any command throws an error, it's logged to `errors.log` and retried once automatically
- `.fixlog` shows the last 40 logged error entries
- The bot's main loop also has a **crash-safe restart** with exponential backoff (5s → 10s → 20s ... capped at 60s), so a fatal error won't take the whole service down permanently on Render

---

## 🔒 Security Notes

- **Never commit** your `.session` file or `SESSION_STRING` to GitHub — `.gitignore` already excludes session/data/log files
- Treat `SESSION_STRING` like a password — it grants full account access without needing your OTP again
- Store all secrets only in Render's **Environment Variables** panel, never in code
- If you ever suspect your session is compromised, terminate it from **Telegram → Settings → Devices** and generate a new one

---

## 🩺 Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| Bot won't log in | Missing/incorrect `API_ID`, `API_HASH`, or `SESSION_STRING` | Re-check env vars, regenerate session if needed |
| Render service sleeps / goes idle | Free tier limitation | Upgrade plan, or use a scheduled uptime ping |
| Commands not responding | Not sent from your own account, or missing `.` prefix | Only outgoing messages starting with `.` are handled |
| Broadcast getting flagged/limited | Telegram anti-spam | Built-in delays help, but avoid mass-broadcasting frequently |
| `aiohttp not installed` warning | Dependency missing | Confirm `requirements.txt` installed correctly on Render |

---

## ⚠️ Disclaimer

This project automates a **regular Telegram user account** (not a Bot API bot). Mass messaging, forwarding, and broadcast features can conflict with Telegram's Terms of Service if misused (spam, unsolicited messages, etc.). Use it responsibly — only in groups/chats you own or manage, and only for legitimate purposes such as customer support automation, community management, and personal productivity (AFK replies).

---

## 👤 Credits

**Developed by [Syed Rehan](https://rehuux.vercel.app)**
Freelance Developer & Ethical Hacker — Web Development, Telegram Bots, OSINT, UI/UX, AI Integration.
