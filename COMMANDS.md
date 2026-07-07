# 📕 Football Auction Bot — Slash Command Reference

These are the **14 `/` commands** the bot registers in Discord. They work exactly like
slash commands in any discord.js bot — type `/` in your server and Discord autocompletes them.

> 💡 While a command's typing out, Discord shows a description for each argument too.
> Anything in `[brackets]` is optional. `<angle brackets>` are required.

---

## 💰 Money & your manager

| Command | Args | What it does |
|---|---|---|
| `/balance` | `[@user]` | Show a wallet balance (yours, or someone else's). |
| `/daily` | — | Claim free coins once a day. 🔥 Builds a streak for bigger rewards (caps at 7 days). |
| `/profile` | `[@user]` | Your "manager card" — cash, squad value, **net worth**, top 3 players. |
| `/squad` | `[@user]` | Full list of every player you own, with OVR + what you paid. |
| `/leaderboard` | — | 🏆 Top 10 richest managers by net worth (cash + squad value). |

## 🎯 Transfers & auctions

| Command | Args | What it does |
|---|---|---|
| `/auction` | `<name>` | 🔥 **Start a live auction.** `name` autocompletes as you type. |
| `/random` | — | 🎲 Instantly auctions a random top player (OVR ≥ 82). |
| `/market` | — | 🌍 Paginated list of all 132 players. Pick one from the dropdown to auction it. |
| `/player` | `<name>` | View a player's card: OVR, 6 stats (bars), club, tier, market value. |
| `/sell` | `<name>` | Sell a player from your squad back to the bank (60% of market value). |

## 🛠️ Admin only

| Command | Args | What it does |
|---|---|---|
| `/give` | `<@user> <amount>` | Grant coins to a user. |
| `/reset` | `<@user>` | Wipe a user's wallet + squad back to the £100M start. |
| `/stop` | — | Cancel the auction currently running in the server. |

## ℹ️ Misc

| Command | What it does |
|---|---|
| `/help` | Shows an in-Discord summary of everything above. |

---

## 🔥 How an auction actually plays out

1. Someone runs **`/auction name:mbappe`** (the name field autocompletes).
2. The bot posts a big player card with a live countdown (60s) and **3 buttons**:
   - **`⬆️ Bid £…`** — bids the minimum allowed amount.
   - **`⚡ Bid +£5M`** — bids minimum + a £5M jump (for fast bidding).
   - **`✍️ Custom`** — opens a popup to type any amount.
3. Anyone can out-bid by hitting a button. **Late bids extend the timer** (anti-snipe).
4. As time runs out: `🔥 Going once…` → `🔥🔥 Going twice…` → **`🎉 SOLD!`**
5. Coins are deducted from the winner and the player is added to their squad automatically.

**One auction runs at a time per server.** If one's live, `/auction`, `/random` and `/market` will tell you to wait.

---

## ⚡ Make the commands appear instantly

By default slash commands sync **globally** and can take **up to 1 hour** to show up in Discord.
To make them appear instantly, add your server ID to `.env`:

```
GUILD_ID=123456789012345678
```

(To get your server ID: Discord Settings → Advanced → enable **Developer Mode** → right-click your server → **Copy ID**.)

---

## 🔧 Want to add or change a command?

Every command is one function in `main.py`. Look for `@bot.tree.command(description="...")`.
The function right below it is the handler. Arguments become Discord options via
`@app_commands.describe(...)`. See `FOR-NODE-DEVS.md` for the full mental map from discord.js.
