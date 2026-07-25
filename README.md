# 🤖 Telegram SelfBot by Syed Rehan

A production-ready Telegram **userbot (selfbot)** built with [Telethon](https://github.com/LonamiWebs/Telethon) — full moderation toolkit, broadcast system, OSINT lookups, a smart **AFK auto-reply system**, and one-click deployment on [Render](https://render.com) using a native **Telethon StringSession** (no SQLite file headaches, no interactive login after first setup).

> Personal automation for your own Telegram account — moderation, broadcasting, info lookups, and an AFK auto-responder, running 24/7 in the cloud.

---

## 📌 Table of Contents

- [What This Project Is](#-what-this-project-is)
- [How It Works](#-how-it-works)
- [Architecture Overview](#-architecture-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Getting Telegram API Credentials](#-getting-telegram-api-credentials)
- [Generating a StringSession](#-generating-a-stringsession)
- [Local Setup](#-local-setup)
- [Deploying on Render](#-deploying-on-render)
- [Environment Variables](#-environment-variables)
- [Command Reference](#-command-reference)
- [AFK System — In Depth](#-afk-system--in-depth)
- [Moderation System — In Depth](#-moderation-system--in-depth)
- [Broadcast System — In Depth](#-broadcast-system--in-depth)
- [Reliability, Auto-Fix & Crash Recovery](#-reliability-auto-fix--crash-recovery)
- [Health Server & Uptime](#-health-server--uptime)
- [Security Notes](#-security-notes)
- [Frequently Asked Questions](#-frequently-asked-questions)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Changelog](#-changelog)
- [License](#-license)
- [Disclaimer](#-disclaimer)
- [Credits](#-credits)

---

## 🧠 What This Project Is

This is a **selfbot** — it runs on your **own personal Telegram account** (not a Bot API bot with a `@BotFather` token). It logs in as *you*, using Telethon's MTProto client library, and listens for special `.command` messages that you type from your own account.

Unlike a regular Telegram Bot (which has its own identity, limited permissions, and can't read normal DMs unless messaged first), a selfbot has the **full capabilities of a user account** — it can read all your chats, act in any group you're in, message anyone, and more. This makes it powerful, but also means it must be used carefully and responsibly (see [Disclaimer](#-disclaimer)).

It's designed for people who want to:
- Auto-reply to messages when they're away (AFK)
- Moderate their own groups more efficiently (mute/ban/kick/promote via commands)
- Broadcast announcements across their DMs/groups
- Quickly look up user/chat/Instagram info without leaving Telegram
- Run all of this as a **24/7 hosted service** instead of keeping a laptop/phone script running

---

## ⚙️ How It Works

1. **Login / Session** — The bot authenticates to Telegram using a Telethon **StringSession**: a single encrypted string representing an already-authorized login. Generated once, locally, via `generate_session.py`, then stored as the `SESSION_STRING` environment variable on Render. No phone/OTP prompt ever happens on the server.
2. **Persistent Connection** — Telethon opens and maintains a persistent MTProto connection to Telegram's servers, receiving real-time updates instead of polling.
3. **Event Listening** — The bot listens for two categories of events:
   - **Outgoing messages** starting with `.` → parsed as commands (`.mute`, `.frwd`, `.afk`, etc.)
   - **Incoming messages** → checked against the moderation list (muted/banned users) and evaluated for AFK auto-reply
4. **Command Dispatch** — Every `.command` flows through a single dispatcher (`_cmd_dispatch`) that identifies the command, executes the matching handler, edits your own message in place with the result, and logs any failures.
5. **AFK State Machine** — A lightweight in-memory object (`AFKState`) tracks whether AFK is on, the timestamp it was enabled, your custom away message, and which user IDs have already received an auto-reply this session.
6. **Health Server** — An `aiohttp` web server runs alongside the bot on Render's assigned `PORT`, responding to `/` and `/health` so Render's health checks keep the service alive and marked "healthy."
7. **Crash Recovery Loop** — The entire client run-loop lives inside a `main()` function with exponential backoff — if something fatal happens, the error is logged and the client restarts automatically (5s → 10s → 20s → ... capped at 60s) instead of the whole service dying permanently.
8. **Graceful Session Failure** — If `SESSION_STRING` is invalid, malformed, or has been revoked from Telegram's side, the bot logs a clear, actionable message and exits cleanly instead of endlessly crash-looping.

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
                        │         Telethon Client       │
                        │   (StringSession-authorized)   │
                        └───────────────┬───────────────┘
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │ Outgoing Handler │ │ Incoming Handler │ │   Health Server  │
          │  (.command logic)│ │ (mod + AFK logic)│ │  (aiohttp /PORT) │
          └─────────────────┘ └─────────────────┘ └─────────────────┘
                    │                   │
                    ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐
          │  Command Modules │ │   AFK State      │
          │ mod / broadcast /│ │ (in-memory, per  │
          │ info / utility   │ │  process runtime)│
          └─────────────────┘ └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │ selfbot_data.json│  ← persists muted/banned user lists
          │   errors.log      │  ← persists auto-fix error history
          └─────────────────┘
```

The whole process runs as a single long-lived Python asyncio event loop, deployed as a Render **Web Service** so the health endpoint keeps it alive and monitored.

---

## ✨ Features

- **Full moderation toolkit** — mute, ban, block, kick, promote/demote admins
- **Broadcast system** — forward or send messages across DMs and groups with built-in anti-ban delays
- **AFK auto-reply system** — DM-only, replies once per user, auto-disables when you send a manual message
- **OSINT / info lookups** — Telegram user info, chat info, Instagram profile lookups
- **Utility commands** — translator, calculator, countdown timer, ghost-send, auto chat cleanup
- **Self-healing** — auto-fix mode retries failed commands and logs errors
- **StringSession-based auth** — no SQLite file corruption issues, no interactive login on the server
- **Render-ready** — environment-variable driven config, health-check endpoint, crash-safe restart loop
- **Local dev fallback** — automatically uses a local SQLite session file if no `SESSION_STRING` is set
- **Persistent moderation data** — muted/banned lists survive restarts via `selfbot_data.json`
- **Error logging** — every failure is timestamped and traceback-logged to `errors.log`, viewable in-chat via `.fixlog`

---

## 📁 Project Structure

```
selfbot/
├── main.py                # Core bot logic — all commands, AFK system, event handlers, session logic
├── generate_session.py    # One-time local script to produce a Telethon StringSession
├── requirements.txt       # Python dependencies
├── render.yaml             # Render Blueprint service definition
├── Procfile                 # Fallback start command for PaaS platforms
├── runtime.txt                # Pins the Python version
├── .gitignore                   # Keeps session files & secrets out of git
├── LICENSE                        # Custom attribution license (copy/edit allowed, credit required)
└── README.md                        # This file
```

---

## ✅ Requirements

- Python **3.11+**
- Telethon **1.36+** (fully compatible with 1.44+)
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

## 🧩 Generating a StringSession

The bot uses a native **Telethon StringSession** — a single string that represents a fully authorized login. This replaces the older Base64-encoded SQLite `.session` file approach (which caused `sqlite3.DatabaseError: file is not a database` errors on Render).

Generate it **once, locally** — never on Render:

```bash
pip install telethon
python generate_session.py
```

You will be prompted for:
- `API_ID`
- `API_HASH`
- Your phone number + the OTP Telegram sends you

At the end, a long string is printed — this is your `SESSION_STRING`. Copy and store it securely; it grants full access to your Telegram account, just like a password.

> ⚠️ If you generated a session with an *older* version of this project (Base64 SQLite format), it is **not compatible** anymore. Re-run `generate_session.py` to get a proper StringSession.

---

## 💻 Local Setup

```bash
git clone https://github.com/rehuux/selfbot.git
cd selfbot
pip install -r requirements.txt

# Set environment variables (Linux/macOS)
export API_ID=your_api_id
export API_HASH=your_api_hash
export SESSION_STRING=your_generated_string_session

# Or on Windows (PowerShell)
$env:API_ID="your_api_id"
$env:API_HASH="your_api_hash"
$env:SESSION_STRING="your_generated_string_session"

python main.py
```

If `SESSION_STRING` is **not** set, the bot automatically falls back to a local SQLite session file (`selfbot_session.session`) and will prompt for phone/OTP login interactively — useful for local development without generating a StringSession every time.

On successful startup you'll see:

```
Loaded Telethon StringSession from environment.
Logged in as: YourName (@yourusername) | ID: xxxxxxxx
SelfBot by Syed Rehan — running
Type .help in Telegram for the full command list
Health server running on port 8080
```

(or `Using local SQLite session file.` if running without `SESSION_STRING`)

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

- Check the **Logs** tab — you should see `Loaded Telethon StringSession from environment.` followed by `Logged in as: ...`
- Visit your Render service URL — it should return `SelfBot Running`
- `GET /health` should return `OK`
- From Telegram, send `.help` from your own account to confirm commands respond

### Redeploying After Changes

Render auto-deploys on every push to your connected branch (if `autoDeploy: true` in `render.yaml`). To redeploy manually: **Dashboard → your service → Manual Deploy → Deploy latest commit**.

---

## 🔐 Environment Variables

| Variable         | Required | Description                                                              |
|-------------------|:--------:|------------------------------------------------------------------------|
| `API_ID`          | ✅       | Telegram API ID from my.telegram.org                                    |
| `API_HASH`        | ✅       | Telegram API Hash from my.telegram.org                                  |
| `SESSION_STRING`  | ✅ (prod) | Telethon StringSession, generated once via `generate_session.py`        |
| `PORT`            | ⚙️ auto  | Set automatically by Render; used by the health-check web server        |
| `PHONE`           | ❌ optional | Only used for interactive login when `SESSION_STRING` is not set        |

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

## 🌙 AFK System — In Depth

- **DM-only** — never replies inside groups, avoiding spammy behavior in shared spaces
- **Replies once per user** — no repeated auto-replies if someone sends multiple messages while you're away
- **Custom messages** — `.afk Busy with a client call` sets your own away message for that session
- **Duration tracking** — `.back` reports how long you were away (e.g. *"I have been away for 12 minutes"*)
- **Auto-disable on activity** — sending any manual (non-command) message from your account turns AFK off automatically, with a confirmation reply
- **State reset** — the replied-users list clears every time AFK is toggled on or off, so a new AFK session starts clean
- **In-memory only** — AFK state does not persist across restarts by design (a restart implies you're "back")

**Default message** (used when no custom text is given):

> *"Hello, I will be with you shortly (approximately 5–20 minutes). To help me assist you efficiently, please describe what you are interested in or what services you require."*

---

## 🛡 Moderation System — In Depth

- **Mute/Ban list** — stored persistently in `selfbot_data.json`, so it survives bot restarts/redeploys
- **Auto-delete enforcement** — any incoming message from a muted/banned user ID is automatically deleted as soon as it's received
- **Group-scoped actions** — `.kick`, `.admin`, and `.demote` only work inside groups/supergroups you're already an admin in (Telegram enforces this server-side)
- **Flexible targeting** — every moderation command accepts a reply, an `@username`, or a raw numeric user ID

---

## 📡 Broadcast System — In Depth

- **`.frwd`** — forwards the replied message to every DM you have open with a real user (bots excluded)
- **`.gc`** — broadcasts to every group/channel where you hold admin rights (falls back to all groups if none are found)
- **`.broad`** — sends the *text content* of the replied message (not a forward) to every DM contact
- **`.frwdall`** — combines DM + admin-group targets into one broadcast run
- **Anti-ban pacing** — `safe_sleep()` adds a random 5–10 second delay between sends, plus a 40-second cooldown every 15 messages, to reduce the chance of triggering Telegram's spam/flood protections
- **Failure counting** — every broadcast reports how many sends succeeded vs failed once complete

---

## 🛠 Reliability, Auto-Fix & Crash Recovery

- `.fix` toggles a safety net: if any command throws an error, it's logged to `errors.log` and retried once automatically
- `.fixlog` shows the last 40 logged error entries directly in Telegram
- The main run-loop restarts automatically with exponential backoff (5s → 10s → 20s → ... capped at 60s) on unexpected crashes
- **Graceful session failure**: if `SESSION_STRING` is invalid, expired, or revoked, the bot logs:
  ```
  Invalid SESSION_STRING. Please generate a new Telethon StringSession.
  ```
  and exits cleanly instead of crash-looping — check the Render logs, regenerate a session with `generate_session.py`, and redeploy.

---

## 🩺 Health Server & Uptime

- An `aiohttp` server runs on the port Render assigns via the `PORT` environment variable
- `GET /` → returns `SelfBot Running`
- `GET /health` → returns `OK`
- Render uses this endpoint to determine if the service is alive; on the free tier, an idle service may spin down after inactivity and cold-start on the next request/health check

---

## ❓ Frequently Asked Questions

**Q: Is this a Bot API bot (like ones made with @BotFather)?**
No — this is a *userbot/selfbot*. It logs in as your real Telegram account via Telethon, not as a separate bot identity.

**Q: Will this get my account banned?**
Any automation on a personal account carries some risk if used to spam or mass-message. Built-in delays reduce this risk for broadcast commands, but there's no absolute guarantee. Use it on chats/groups you control, and avoid aggressive mass-broadcasting.

**Q: Can I run this without Render?**
Yes — any host that can run a long-lived Python process works (VPS, Railway, Fly.io, a local machine, etc.). Just set the same environment variables.

**Q: Do I need to regenerate `SESSION_STRING` often?**
No — a StringSession stays valid until you manually terminate that session from Telegram's **Settings → Devices**, or Telegram invalidates it for security reasons.

**Q: Can multiple people use one deployed instance?**
No — a selfbot instance is tied to a single Telegram account via its session. Each user needs their own deployment with their own `SESSION_STRING`.

**Q: What happens to AFK state if Render restarts my service?**
AFK state is in-memory only, so a restart clears it (equivalent to `.back`). Moderation data (mute/ban lists) persists via `selfbot_data.json`.

---

## 🩹 Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| `sqlite3.DatabaseError: file is not a database` | Old Base64 SQLite session used with the new StringSession code | Regenerate session with the current `generate_session.py` |
| `Invalid SESSION_STRING...` in logs | Session string malformed, expired, or revoked | Regenerate a new StringSession and update the env var |
| Bot won't log in | Missing/incorrect `API_ID`, `API_HASH`, or `SESSION_STRING` | Re-check env vars, regenerate session if needed |
| Render service sleeps / goes idle | Free tier limitation | Upgrade plan, or use a scheduled uptime ping |
| Commands not responding | Not sent from your own account, or missing `.` prefix | Only outgoing messages starting with `.` are handled |
| Broadcast getting flagged/limited | Telegram anti-spam | Built-in delays help, but avoid mass-broadcasting frequently |
| `aiohttp not installed` warning | Dependency missing | Confirm `requirements.txt` installed correctly on Render |
| AFK not replying | Message sent in a group, not a DM | AFK only triggers in private chats by design |

---

## 🗺 Roadmap

Ideas that could be added in future versions (not yet implemented):
- Persisting AFK state across restarts
- Per-chat custom moderation rules
- Web dashboard for viewing logs/stats
- Multi-account support from a single deployment

---

## 📝 Changelog

**Latest — StringSession Migration**
- Replaced Base64-encoded SQLite session handling with a native Telethon `StringSession`
- Fixes `sqlite3.DatabaseError: file is not a database` on Render
- Added graceful failure handling for invalid/expired sessions
- Improved startup logging (`Loaded Telethon StringSession from environment.` / `Using local SQLite session file.`)
- `generate_session.py` updated to produce a proper StringSession instead of a Base64 SQLite blob
- All commands, AFK system, broadcast system, moderation system, health server, logging, auto-fix, and Render compatibility remain unchanged

**Previous — Initial Render Build**
- Converted original selfbot script into a production-ready, environment-variable-driven project
- Added AFK auto-reply system (DM-only, once-per-user, duration tracking, auto-disable)
- Added crash-safe restart loop, health server, and full Render deployment files

---

## 📄 License

This project is released under a **Custom Attribution License** (based on MIT) — see [`LICENSE`](./LICENSE) for the full text.

**In short:**
- ✅ You may copy, modify, extend, rebrand, and redistribute this project — personal or commercial use is fine
- ✅ You may fork it and build your own version
- ❌ You must **keep credit to the original author, Syed Rehan**, visible in the README, source header, or an in-app credits section — in the original project and in any derivative/fork
- ❌ Provided with **no warranty** — use at your own risk

---

## ⚠️ Disclaimer

This project automates a **regular Telegram user account** (not a Bot API bot). Mass messaging, forwarding, and broadcast features can conflict with Telegram's Terms of Service if misused (spam, unsolicited messages, mass adds, etc.). Telegram may flag, limit, or ban accounts that automate actions in ways that resemble spam or abuse — the built-in delays reduce but do not eliminate this risk.

Use this project responsibly:
- Only in groups/chats you own, moderate, or have explicit permission to manage
- Only for legitimate purposes — customer support automation, community moderation, personal productivity (AFK replies), OSINT research on public data, etc.
- Never for unsolicited spam, harassment, impersonation, or any activity that violates Telegram's Terms of Service or local law

The developer is not responsible for any misuse of this software, any account restrictions/bans that result from it, or any data loss. This software is provided "as is" without warranty of any kind. **Use at your own risk.**

---

## 👤 Credits

**Developed by [Syed Rehan](https://rehuux.vercel.app)**
CyberSecurity Researcher & Ethical Hacker, Web Development, Telegram Bots, OSINT, AI Integration

Built with [Telethon](https://github.com/LonamiWebs/Telethon) · Deployed on [Render](https://render.com)

If you fork or reuse this project, please keep credit to **Syed Rehan** intact — see [LICENSE](./LICENSE) for details.
