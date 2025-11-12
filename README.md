# AutoFinder 🚗

> Simple, automated car inventory search with finance estimates and price tracking

AutoFinder is a GitHub Pages-hosted website that automatically searches nearby car inventory twice daily, normalizes results, calculates monthly payments, and tracks price changes — all without a database.

---

## Features

- ✅ **Automated Search**: Runs twice daily (07:30 & 19:30 CST) via GitHub Actions
- 💰 **Finance Estimates**: Calculate monthly payments with configurable parameters
- 📊 **Price Tracking**: Visual indicators (▲▼●) show price movements
- 🔍 **Smart Deduplication**: VIN-based matching prevents duplicates
- 📱 **Responsive UI**: Clean, accessible table interface
- 🏷️ **Sortable Columns**: Click headers to sort by price, mileage, etc.
- 🎯 **Budget Filtering**: Only shows affordable vehicles
- 🌐 **Static Hosting**: Runs on GitHub Pages — no servers needed

---

## Quick Start

### 1. Configure Search

Edit `config/app.config.json` with your ZIP code, budget, and preferences.

### 2. Add Secrets

Settings → Secrets → Actions:
- `GEMINI_API_KEY` (optional AI search)

### 3. Enable GitHub Pages

Settings → Pages → Source: **GitHub Actions**

### 4. Trigger Workflow

Actions tab → "Fetch Vehicle Inventory" → Run workflow

---

## Project Structure

```
buy-a-car/
├── .github/workflows/    # GitHub Actions
├── config/              # Configuration
├── data/                # Generated JSON data
├── scripts/             # Python backend
│   ├── fetch.py         # Main orchestrator
│   ├── models.py        # Data models
│   ├── finance.py       # Finance calculations
│   ├── normalize.py     # Deduplication
│   ├── price_tracker.py # Price changes
│   └── sources/         # Data sources
└── site/                # React frontend
    └── src/
        ├── App.tsx      # Main UI
        ├── types/       # TypeScript types
        └── api/         # Data fetching
```

---

## Development

**Backend:**
```bash
pip install -r scripts/requirements.txt
python scripts/fetch.py
```

**Frontend:**
```bash
cd site
npm install
npm run dev
```

---

## Tech Stack

- **Backend**: Python 3.11, Pydantic, httpx, Gemini API
- **Frontend**: React 18, TypeScript, Vite
- **Infrastructure**: GitHub Actions, GitHub Pages

---

## License

MIT
