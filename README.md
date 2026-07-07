# 🏟️ Football Auction Bot — Auction Management Edition

A **Discord auction management tool** for running real football draft auctions — built for
league simulations (e.g. Football Life 26) where managers build custom teams by winning
live auctions with a virtual budget. **100% free to run** (no paid APIs, no paid hosting).

---

## ✨ What it does

The admin controls the cadence:
1. **`/phase FWD`** — set today's position group (Forwards day, Midfielders day, etc.)
2. **`/next`** — the bot drops ONE player for auction (the top available in that phase)
3. Managers **bid via buttons** under the auction message
4. The player **sells to the highest bidder**, coins are deducted, player joins their squad
5. The bot **STOPS and waits** — no new auction until you say so
6. Repeat: `/next`, `/next`, `/next`… or `/drop <name>` for a specific pick

**No `/pause` needed** — the bot auto-pauses after every single player. You're always in control.

---

## 🔥 Features

- 🎯 **Phase-based drafting** — auction Forwards one day, Midfielders the next, etc.
- ➡️ **One-at-a-time cadence** — `/next` drops one player, bot waits for you, repeat
- 🧠 **Never re-auctions a sold player** — once someone owns a player, they're off the board
- 💸 **Budget enforcement** — bidders literally cannot bid more than their balance
- 🏟️ **Formation team view** — `/team` shows a manager's best XI as a 4-3-3 tactics board + bench
- 📋 **Squad view** — `/squad` lists every owned player grouped by position
- 🌍 **Pool browser** — `/pool` shows who's still available, with a dropdown to drop one
- 📜 **Sales log** — `/sold` tracks every completed sale
- 🔥 **Live auctions** — buttons (min-bid, quick +£5M, custom-bid modal), anti-snipe timer
- 🏆 **Leaderboard** — richest managers by net worth (budget + squad value)
- 💾 **SQLite** persistence — handles 20-30+ managers × 15-30 players with zero setup

---

## 🎮 Commands

### Manager commands
| Command | What it does |
|---|---|
| `/balance [@user]` | Check a budget |
| `/profile [@user]` | Net worth, budget & top 3 players |
| `/team [@user]` | 🏟️ Best XI as a 4-3-3 formation + bench + squad rating |
| `/squad [@user]` | Full squad grouped by position (GK/DEF/MID/FWD) |
| `/player <name>` | Player card, stats & market value |
| `/pool` | 🌍 Browse available players, drop one from the dropdown |
| `/sold` | 📜 Most recent sales |
| `/leaderboard` | 🏆 Richest managers |

### Admin commands
| Command | What it does |
|---|---|
| `/phase <group>` | Set the auction phase: `ALL` / `GK` / `DEF` / `MID` / `FWD` |
| `/next` | ➡️ Drop the next player — from the **queue** if set, else top available |
| `/drop <name>` | Nominate a specific player for auction |
| `/queue <action>` | 📜 Build a **scripted auction list** (list/add/clear/load phase) |
| `/export` | 📥 Download **all squads as a CSV** (for Football Life etc.) |
| `/give @user <amount>` | Grant budget to a manager |
| `/reset @user` | Reset a manager's budget & squad |
| `/cancel` | Cancel the auction currently running |
| `/help` | Show all commands |

> **Squad requirements** (configurable in code): 2 GK, 5 DEF, 5 MID, 3 FWD = 15 players.
> `/check [@user]` shows whether a squad meets these.

---

## 🏃 Quick start

```bash
cd football-auction-bot
pip install -r requirements.txt
cp .env.example .env        # paste your DISCORD_TOKEN, add GUILD_ID for instant commands
python main.py
```
Then type `/help` in Discord. See the original section below for full Discord bot setup.

---

## ⚙️ The auction flow

```
Admin: /phase FWD            ← "today is forwards day"
Admin: /next                 ← bot drops Mbappé
  → Managers bid via buttons (Bid / Bid +£5M / Custom)
  → Timer counts down, anti-snipe extends on late bids
  → "Going once… twice… SOLD!" → coins deducted, player joins winner
  → Bot STOPS. Waits.
Admin: /next                 ← bot drops Haaland (Mbappé can't be re-auctioned!)
  → ...repeat...
Admin: /phase DEF            ← switch to defenders day
Admin: /next                 ← drops top available defender
```

---

## 📊 Economy

- Budget is set in `config.py` (`STARTING_BALANCE`, currently £150M — change to £1B if you like)
- Value curve: top stars (£86M, bids push to £100M+) down to fillers (£0.5M)
- **256 real players** across all positions, clubs updated to June 2026
- Supports ~17 full 15-player squads; add more to `data/players_extra.json` for more managers

---

## 📁 Project structure
```
football-auction-bot/
├── main.py              # Bot + slash commands (manager + admin)
├── auction.py           # Live auction engine (buttons, timers, anti-snipe)
├── display.py           # Rich embeds — formation team view, squad view, player cards
├── economy.py           # Budgets, squads, pool filtering, sales log, leaderboard
├── players.py           # Data, values, tiers, phase groups, search, flags
├── database.py          # SQLite layer (users, squads, history, guild state)
├── config.py            # All tunable settings
├── data/players.json    # 132 curated top players
├── data/players_extra.json  # 129 squad-depth players
└── requirements.txt
```

---

## ☁️ Free hosting
See the original README sections on Oracle Cloud Always Free, Render, Fly.io, or a
Raspberry Pi. The hosting configs (`render.yaml`, `fly.toml`, `football-auction.service`)
are included.
