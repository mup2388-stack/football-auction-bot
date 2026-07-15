<div align="center">

<img src="pfp.jpeg" width="120" height="120" alt="logo" style="border-radius: 50%;">

# AuctionBot

### Football Life 26 League Management

A full-stack Discord bot + web dashboard for running football auction drafts, managing squads, and simulating league seasons.

[Website](https://auction-bot-wmu4.onrender.com) &bull; [Commands](#commands) &bull; [Features](#features) &bull; [Setup](#setup) &bull; [Made by mumu_111111](https://discord.com/users/856556430370930738)

</div>

---

## Features

### Auction Engine
- Live bidding with anti-snipe timer extension
- 12,176 players from FL26 (active + icons)
- SoFIFA face integration (83% coverage)
- Deal verdicts (STEAL / FAIR / OVERPAY) on every sale
- Real player faces rendered on squad/player/bench cards
- Position-aware budget protection (can't overspend and leave gaps)

### Management & Finance Cards
- 32 unique management cards per session (goals, restrictions, powers)
- 32 finance cards (+£150M to -£20M)
- DM delivery with specific player targets from today's pool
- Power cards: steal a player, swap players, peek at next drop
- Auto-complete tracking + manual admin override
- Force-end with no penalties option

### Squad Management
- 14 FL26 formations with exact tactical positions
- Free Edit mode (PES-style): drag players anywhere on the pitch
- Zone-locked GK, dynamic position labels (LB/CB/RB/CM/CAM/CF/SS)
- Position picker popup for multi-option zones
- FL26 tactics editor (attacking, defensive, advanced instructions)
- Substitutes management with `/tosub` and `/unsub`
- FUT-style metallic squad/player/bench/compare card renderers

### League System
- 5 formats: round-robin, double round-robin, groups + knockout, league + playoffs, pure knockout
- Season draw ceremony with 32 clubs (reaction signup support)
- Auto fixture generation, standings with form dots + club logos
- Knockout bracket renderer (center-out, obsidian palette)
- Match results with per-team stat entry (goals, assists, MOTM, cards, own goals)
- Penalty shootout support for knockout draws
- Season-scoped match stats (per-season leaderboards)
- Top scorers golden boot card, draft recap, head-to-head records

### Web Dashboard
- 24/7 Flask website with Discord OAuth login
- Dashboard, Standings, Fixtures, Bracket, Top Scorers, Players, Watchlist, Squads
- Drag-and-drop lineup editor (slot-based + free edit)
- Player radar charts and position compatibility
- Watchlist system (synced with Discord bot)
- "Your Team" section on squads page
- Mobile responsive with animated hamburger menu
- Skeleton loading screens + navigation progress bar
- Player pool pagination with filters (position, nation, status, OVR, age, club)

### Economy
- £1B starting budget per manager
- Tiered player pricing (£15M floor for low-rated, scaling curve for stars)
- Icon flat-tier pricing (GOAT 95+ = £250M down to £25M)
- Trade system with toggle, pending offers, accept/reject
- Budget analysis (max bid calculation with squad-needs protection)

---

## Commands

### Your Squad
| Command | Description |
|---------|-------------|
| `/balance` | Check your budget |
| `/profile` | Net worth and top players |
| `/team` | Starting XI formation card |
| `/squad` | Full squad overview with match stats |
| `/bench` | Your substitutes |
| `/leaderboard` | Richest managers |
| `/needs` | What positions you still need |
| `/check` | Squad requirements status |
| `/tactics` | View your FL26 tactics |

### Players
| Command | Description |
|---------|-------------|
| `/player` | View a player card (radar + stats) |
| `/playerstats` | Match stats for a player |
| `/compare` | Head-to-head stat duel |
| `/matchup` | Your XI vs a rival |
| `/pool` | Browse available players (sorted by OVR) |
| `/topscorers` | Golden boot race |
| `/watch` | Get pinged when a target goes up |

### League
| Command | Description |
|---------|-------------|
| `/season setup` | Create season with format dropdown |
| `/season add` | Add a manager |
| `/season signup` | Add managers via message reactions |
| `/season draw` | Team draw ceremony |
| `/season start` | Generate fixtures and go live |
| `/season info` | Current season status |
| `/season end` | End the season |
| `/fixtures` | View upcoming matches |
| `/table` | League standings |
| `/bracket` | Knockout bracket |
| `/h2h` | Head-to-head record |
| `/archive` | Browse past seasons |

### Transfers
| Command | Description |
|---------|-------------|
| `/trade` | Offer a player trade |
| `/trades` | Your pending offers |
| `/accepttrade` | Accept a trade |
| `/rejecttrade` | Reject a trade |
| `/sold` | Recent sales |
| `/soldsearch` | Search auction history |
| `/draftrecap` | Full draft summary |

### Lineup & Formation
| Command | Description |
|---------|-------------|
| `/formation` | Set your formation |
| `/setpos` | Assign a player to a slot |
| `/clearpos` | Reset a slot to auto |
| `/resetlineup` | Reset all overrides |
| `/tosub` | Force a player to substitutes |
| `/unsub` | Allow a player back into auto XI |
| `/clearsubs` | Clear all forced substitutes |

### Admin *(button in `/help`)*
| Command | Description |
|---------|-------------|
| `/next` | Drop next player from queue |
| `/drop` | Nominate a specific player |
| `/queue` | Manage the auction queue |
| `/queueorder` | View exact drop order (private) |
| `/unsell` | Remove player from team, refund, re-queue |
| `/sell` | Manually assign a player for a price |
| `/inactive` | Show managers with 0 players |
| `/cards management` | Start/lock/end management cards |
| `/cards finance` | Start/lock finance cards |
| `/cards complete` | Mark a manual goal complete |
| `/cards steal` | Resolve steal power |
| `/cards swap` | Resolve swap power |
| `/cards peek` | Resolve peek power |
| `/give` | Grant budget |
| `/take` | Remove budget |
| `/dump` | Release a player (manager fined) |
| `/replace` | Transfer a team to a new manager |
| `/setteam` | Force a club name |
| `/cancel` | Stop the running auction |
| `/reset` | Reset a manager |
| `/resetall` | Reset everyone |
| `/export` | Download squads as CSV |
| `/exportfl26` | FL26 setup guide |
| `/importmatch` | Import match stats from CSV |
| `/quickresult` | Enter result + stats |
| `/updatestats` | Add match stats manually |
| `/testseason` | Spin up a test league |
| `/testdrop` | Test auction (nothing saved) |

---

## Setup

### Prerequisites
- Python 3.10+
- Discord bot token
- Turso account (free, for cloud database)

### Install
```bash
git clone https://github.com/mup2388-stack/football-auction-bot.git
cd football-auction-bot
pip install -r requirements.txt
```

### Configure
Copy `.env.example` to `.env` and fill in:

```env
DISCORD_TOKEN=your-bot-token
ADMIN_IDS=your-discord-id

# Cloud database (bot + website share one DB)
TURSO_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-token

# Website
WEB_ENABLED=true
WEB_PORT=5000
DISCORD_CLIENT_ID=your-oauth-client-id
DISCORD_CLIENT_SECRET=your-oauth-secret
DISCORD_REDIRECT_URI=http://localhost:5000/callback
FLASK_SECRET_KEY=random-string
```

### Run the bot
```bash
python main.py
```

### Deploy the website separately
```bash
# Render / Fly.io / any Python host
pip install -r requirements.txt
python web.py
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot | discord.py 2.x |
| Web | Flask |
| Database | Turso (libSQL) / SQLite (local) |
| Images | Pillow + NumPy |
| Auth | Discord OAuth2 |
| Hosting | Local (bot) + Render (website) |
| DNS/CDN | Cloudflare |

---

<div align="center">

Made by [mumu_111111](https://discord.com/users/856556430370930738)

</div>
