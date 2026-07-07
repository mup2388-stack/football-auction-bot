# 🧠 For Node.js Devs — Reading This Python Bot

You already know Discord bots. This is just a different library (discord.py instead of discord.js)
in a different language. Here's the translation table so the code stops looking alien.

---

## 1. Tooling equivalents

| Node.js / discord.js | This project (Python / discord.py) |
|---|---|
| `npm install` | `pip install -r requirements.txt` |
| `package.json` | `requirements.txt` (just the package names + versions) |
| `node index.js` | `python main.py` |
| `dotenv` package + `process.env.TOKEN` | `python-dotenv` + `os.getenv("TOKEN")` (identical concept) |
| `package-lock.json`, `node_modules/` | (Python has no single lockfile by default; `pip` just installs into the environment) |
| `npm i -g` / global bins | create a **venv**: `python3 -m venv .venv && source .venv/bin/activate` |
| `require('x')` / `import x` | `import x` (Python) |
| `export function foo` / `module.exports` | just `def foo` / `import` it (no exports keyword needed) |
| `async/await`, `Promise` | `async/await`, `asyncio` (same idea) |
| `.js` / `.mjs` files | `.py` files |
| `// comment` | `# comment` |

> Indentation matters in Python! Blocks are defined by spaces, not `{ }`. No semicolons.

---

## 2. discord.js ↔ discord.py concept map

| discord.js | discord.py | Where it lives in this bot |
|---|---|---|
| `new Client({ intents })` | `commands.Bot(command_prefix=..., intents=...)` | `main.py` top |
| `client.on('ready', ...)` | `@bot.event  async def on_ready():` | `main.py` |
| `SlashCommandBuilder` + `commands.set()` | `@bot.tree.command(description="...")` | each command in `main.py` |
| `interaction.options.get('x')` | function **arguments** become options automatically via `@app_commands.describe` | `main.py` |
| `client.on('interactionCreate', switch...)` | one async function per command, no switch needed | `main.py` |
| `interaction.reply(...)` | `interaction.response.send_message(...)` | everywhere |
| `interaction.reply({ ephemeral:true })` | `send_message(..., ephemeral=True)` | everywhere |
| Autocomplete handler (`interaction.respond`) | `@app_commands.autocomplete(name=fn)` returning a list of `Choice` | `main.py` `player_autocomplete` |
| `ActionRowBuilder` + `ButtonBuilder` | a `discord.ui.View` class + `@discord.ui.button` methods | `auction.py` `AuctionView` |
| `interaction.update(...)` (button click) | `interaction.response.edit_message(...)` | `auction.py` |
| `ModalBuilder` + `showModal()` | `discord.ui.Modal` subclass + `interaction.response.send_modal(...)` | `auction.py` `CustomBidModal` |
| `StringSelectMenuBuilder` | `@discord.ui.select` inside a View | `main.py` `MarketView` |
| `EmbedBuilder` | `discord.Embed(...)` + `.add_field(...)` | everywhere |

---

## 3. The "aha": where are the commands?

In discord.js you'd build a command array and register it. In discord.py **each command is just
a decorated async function** — that's it. The decorator IS the registration.

```js
// discord.js
client.application.commands.create({
  name: 'balance',
  description: 'Check your balance',
  options: [{ name: 'user', type: USER, required: false }]
});
client.on('interactionCreate', i => {
  if (i.commandName === 'balance') { ... }
});
```

```python
# discord.py — same thing, in main.py
@bot.tree.command(description="Check your wallet balance.")
@app_commands.describe(user="Whose balance to check (optional).")
async def balance(interaction, user: discord.Member = None):
    ...                                          # the whole handler in one place
```

So to find or change any command in `main.py`: **search for `@bot.tree.command`** — the function
right under it is the handler, and the function arguments ARE the Discord slash options.

---

## 4. Files at a glance (compared to a typical Node project)

```
football-auction-bot/
├── main.py            ← like index.js + your command files
├── auction.py         ← the live-auction logic (buttons, timers)
├── economy.py         ← wallets, daily, squads (your "database helpers")
├── players.py         ← the player dataset + value/search helpers
├── database.py        ← the SQLite connection (like a db.js)
├── config.py          ← like a config.js / env loader
├── data/players.json  ← your dataset (same JSON you'd use in Node)
├── requirements.txt   ← your package.json dependencies
└── .env.example       ← exactly the same idea as Node's .env
```

A big difference: there's no SQLite "server" to run. The DB is just a file (`data/auction.db`)
that Python reads/writes — like using `better-sqlite3` in Node, but with zero setup.

---

## 5. Quickstart in Node-brain terms

```bash
cd football-auction-bot

# "npm install" — install dependencies
pip install -r requirements.txt

# create your .env (same as Node dotenv)
cp .env.example .env
#   -> open .env, paste your DISCORD_TOKEN
#   -> add GUILD_ID=<your server id> for INSTANT slash commands

# "node main.js" — run it
python main.py
```

You'll see `[✓] Logged in as ...` and `[✓] 132 players loaded.` Then go to Discord, type `/`,
and all 14 commands autocomplete. Start with `/help`.

---

## 6. The #1 gotcha for Node devs

In discord.js you often return a promise from an event handler and move on. In discord.py,
**you must respond to an interaction exactly once**, and you choose the response mode:
`interaction.response.send_message(...)` (reply), `.edit_message(...)` (update), or
`.send_modal(...)` (popup). Calling two of these on the same interaction throws.

This bot already handles all of that correctly — just don't be surprised by the pattern when
reading the code.
