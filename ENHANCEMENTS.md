# Optional Enhancements (Good-to-Have)

These are planned future features that can be added incrementally to the stock market research copilot.

---

## 1. Fundamental Agent
- **What:** Analyze company fundamentals — PE ratio, PB, ROE, revenue/profit growth, debt-to-equity, promoter holding changes.
- **Data sources:** Screener.in, MoneyControl, BSE/NSE filings.
- **Integration:** Add as a new agent in `app/agents/fundamental_agent.py`, called by orchestrator alongside technical/macro agents.

## 2. Options Chain Analysis
- **What:** Fetch and analyze options data — Open Interest (OI), Put-Call Ratio (PCR), Max Pain, IV skew.
- **Data sources:** NSE options chain API, Sensibull.
- **Use case:** Gauge institutional sentiment and expected price ranges.

## 3. Sector Rotation Analysis
- **What:** Track relative strength across Nifty sectors (IT, Bank, Pharma, Auto, Metal, etc.) to identify where money is flowing.
- **Data sources:** Sector index data from NSE, compare 1W/1M/3M returns.
- **Integration:** New agent or extension of macro agent.

## 4. Advanced Portfolio Analytics
- **What:** Sharpe ratio, Sortino ratio, max drawdown, correlation matrix, sector concentration risk, beta analysis.
- **Integration:** Extend `app/agents/portfolio_agent.py` and risk agent.
- **Requires:** Historical NAV/trade data from Zerodha or manual input.

## 5. Earnings Calendar & Event Tracking
- **What:** Track upcoming results, board meetings, dividends, splits. Alert before key events for portfolio holdings.
- **Data sources:** BSE corporate announcements, TradingView earnings calendar.

## 6. Scheduled Auto-Scans (Cron)
- **What:** Run scans automatically at market open/close or custom intervals. Push top picks + debate summaries to Telegram without manual trigger.
- **Integration:** Use APScheduler or system cron; already partially supported via `SCAN_INTERVAL_MINUTES`.

## 7. Historical Report Storage & Comparison
- **What:** Store each scan/debate report in DB. Compare current vs past signals for the same stock to track accuracy over time.
- **Integration:** SQLite/PostgreSQL with report versioning.

## 8. Custom Watchlist Support
- **What:** Allow users to define a custom watchlist (beyond Nifty indices) via `.env` or API.
- **Example:** `CUSTOM_WATCHLIST=RELIANCE,TCS,INFY,HDFCBANK`

## 9. Multi-Timeframe Technical Analysis
- **What:** Analyze daily, weekly, and monthly charts. Align signals across timeframes for higher-confidence picks.

## 10. UI/UX Improvements
- **What:** Interactive charts (TradingView widget embed), filters, historical report browser, dark mode, mobile-responsive layout.
- **Tech:** Enhance `app/templates/index.html` with Chart.js or TradingView Lightweight Charts.

---

## Priority Recommendation

| Priority | Enhancement | Effort |
|----------|-------------|--------|
| High | Scheduled Auto-Scans | Low |
| High | Custom Watchlist | Low |
| Medium | Fundamental Agent | Medium |
| Medium | Sector Rotation | Medium |
| Medium | Options Chain | Medium |
| Low | Advanced Portfolio | High |
| Low | Historical Reports | Medium |
| Low | UI/UX Charts | Medium |

---

*These can be implemented on-demand. To add any of these, just ask!*
