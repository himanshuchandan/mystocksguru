# 🤖 AI Market Copilot

AI-powered Indian stock market research assistant with multi-agent architecture.

## Features

- **Multi-LLM Support**: Anthropic Claude (default) + OpenAI GPT-4o
- **Technical Analysis**: RSI, MACD, EMA, ATR, Volume analysis on NSE top stocks
- **Macro Monitoring**: Nifty, Sensex, USD/INR, Crude, Gold, VIX, global indices
- **News Aggregation**: Moneycontrol, Economic Times headlines
- **Portfolio Tracking**: Zerodha Kite integration (read-only)
- **Risk Management**: Position sizing, stop loss calculation, risk-reward
- **Telegram Alerts**: Get AI-generated trade setups on Telegram
- **Scheduled Scans**: Auto-scans during market hours
- **Dashboard Ready**: Enable via config when needed

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/alerts/` | GET | Get recent alerts |
| `/api/alerts/trigger-scan` | POST | Manually trigger market scan |
| `/api/analysis/market-summary` | GET | Get macro summary |
| `/api/analysis/stock` | POST | Analyze specific stock |
| `/api/portfolio/holdings` | GET | Get Kite holdings |
| `/api/portfolio/analysis` | GET | AI portfolio analysis |

## Configuration

Set `LLM_PROVIDER=openai` in `.env` to switch to OpenAI.
Set `ENABLE_DASHBOARD=true` when you're ready for the web UI.

## Architecture

```
Orchestrator
├── Macro Agent (global signals)
├── News Agent (headlines)
├── Technical Agent (stock scanning)
├── Portfolio Agent (Kite holdings)
├── Risk Agent (position sizing)
└── Decision Agent (LLM synthesis)
    └── Telegram Alert
```

## Telegram Setup

1. Create a bot via @BotFather on Telegram
2. Get your chat ID via @userinfobot
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `.env`

## Kite Setup

1. Get API key from [Kite Connect](https://developers.kite.trade/)
2. Add `KITE_API_KEY` and `KITE_API_SECRET` to `.env`
3. Generate access token via OAuth flow (daily)

## Encrypting Secrets

Your API keys and tokens are stored encrypted in `.env`. To encrypt:

```bash
source venv/bin/activate
python -c "from app.utils import setup_env_encryption; setup_env_encryption()"
```

This will:
- Auto-detect unencrypted sensitive values in `.env`
- Encrypt them with a local master key (`.master_key`)
- Replace plaintext values with `ENC:...` format

**Important:**
- `.master_key` is auto-generated on first run — keep it safe!
- Both `.env` and `.master_key` are in `.gitignore`
- The app auto-decrypts values at runtime (no extra steps needed)
