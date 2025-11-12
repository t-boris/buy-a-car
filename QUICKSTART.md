# Quick Start Guide

Get AutoFinder running locally in 5 minutes.

## 1. Prerequisites

```bash
# Check Python version (need 3.11+)
python3 --version

# Check Node.js version (need 18+)
node --version
```

## 2. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd site && npm install && cd ..
```

## 3. Set API Keys

### Option A: Use secrets.md (Recommended)

Your API keys are already saved in `secrets.md`:

```bash
# Load keys from secrets.md
source load_secrets.sh

# Or manually
source <(grep '^export' secrets.md)
```

### Option B: Manual Export

```bash
export GOOGLE_API_KEY='your-google-api-key'
export GOOGLE_CSE_ID='your-cse-id'
export GEMINI_API_KEY='your-gemini-key'
```

### Getting New API Keys

If you need to regenerate keys:
- **Google Custom Search**: https://developers.google.com/custom-search/v1/overview
- **Gemini API**: https://ai.google.dev/

💡 **Tip**: Add exports to your `~/.zshrc` or `~/.bashrc` to make them permanent.

## 4. Run Locally

### See Demo Logging (No API Keys Needed)

```bash
python demo_logging.py
```

This shows what the verbose logging looks like without making real API calls.

### Full Run with API Keys

```bash
python run_local.py
```

**What happens:**
1. **Stage 1**: Finds dealerships near your ZIP (2-3 min)
2. **Stage 2**: Searches inventory pages (3-4 min)
3. **Stage 3**: Parses pages with Gemini AI (8-10 min)
4. **Stage 4**: Final processing and dedup (few seconds)

**Total time:** 15-20 minutes

### View the Site

```bash
cd site
npm run dev
```

Open: http://localhost:5173

## What You'll See

```
================================================================================
                        AutoFinder Local Runner
================================================================================

ℹ Location: ZIP 60031, Radius: 15 miles
ℹ Makes: Toyota, Honda, Hyundai, Kia, Subaru, Mazda

[1/4] Finding Dealerships
    [1/32] Searching: car dealership Gurnee IL
      → GET  200    1.2s   15.2KB https://www.googleapis.com/customsearch/v1?q=...
        ✓ Found 10 results
    ...

[2/4] Searching Inventory Pages
    ...

[3/4] Parsing with Gemini AI
    [1/23] Processing batch (8 pages)...
      → GET  200    0.5s  124.2KB https://www.carwisegurnee.com/used-vehicles/
      → POST 200   12.3s   45.1KB Gemini API (batch of 8 pages)
        ✓ Found 27 vehicles
    ...

[4/4] Final Processing & Deduplication
✓ Completed in 2.1s

================================================================================
                          COMPLETION SUMMARY
================================================================================

Timing Breakdown:
  Stage 1:.......................... 2m 15s (15.3%)
  Stage 2:.......................... 3m 42s (25.4%)
  Stage 3:.......................... 8m 31s (58.1%)
  Stage 4:..........................   2.1s (1.2%)
  ─────────────────────────────────────────────
  Total:........................... 14m 30s

✓ Generated inventory with 52 vehicles
ℹ Saved to: /path/to/data/inventory.json

Quick Stats:
  Vehicles: 52
  Avg Price: $20,236
  Price Range: $11,333 - $24,056
```

## Configuration

Edit `config/app.config.json` to customize:

```json
{
  "zip": "60031",              // Your ZIP code
  "radius_miles": 15,          // Search radius
  "max_down_payment": 3000,    // Your budget
  "max_monthly_payment": 450,
  "filters": {
    "min_year": 2018,          // Minimum year
    "max_mileage": 90000,      // Maximum mileage
    "include_makes": [         // Brands to search
      "Toyota", "Honda", "Hyundai", "Kia"
    ]
  }
}
```

## Troubleshooting

### Missing API Keys

```bash
# Check if keys are set
echo $GOOGLE_API_KEY
echo $GOOGLE_CSE_ID
echo $GEMINI_API_KEY
```

If empty, export them again.

### Rate Limits

Google Custom Search free tier: 100 queries/day

If you hit limits:
- Wait 24 hours, or
- Upgrade to paid tier, or
- Use cached results (don't delete `data/.cache/`)

### No Vehicles Found

Possible reasons:
- Filters too restrictive (check `config/app.config.json`)
- Dealership websites changed
- Gemini couldn't parse HTML

Check `data/.cache/` files to debug each stage.

## Next Steps

- See **[LOCAL_SETUP.md](LOCAL_SETUP.md)** for detailed documentation
- Customize search in `config/app.config.json`
- Deploy to GitHub Pages (push to GitHub, Actions run automatically)

## Cost Estimates

**Per full run:**
- Google Search: ~150-200 queries
  - Free tier: 100/day (need paid tier or run less frequently)
  - Paid tier: ~$0.005/query = $0.75-$1.00
- Gemini API: ~20-30 requests
  - ~$0.50-$2.00 per run (depends on results)

**Total: ~$1.25-$3.00 per full run**

💡 **Tip**: Use cache to reduce costs. Dealerships are cached for 7 days.

## File Outputs

```
data/
├── inventory.json           # Final inventory (public)
├── history.json            # Price history (public)
└── .cache/                 # Intermediate results
    ├── stage1_dealerships.json
    ├── stage2_inventory_pages.json
    └── stage3_vehicles.json
```

## Commands Cheat Sheet

```bash
# Run full pipeline with logs
python run_local.py

# See demo without API calls
python demo_logging.py

# Run individual stages
python scripts/stage1_dealerships.py
python scripts/stage2_inventory.py
python scripts/stage3_parse.py
python scripts/fetch.py

# Start frontend dev server
cd site && npm run dev

# Build frontend for production
cd site && npm run build

# Clear cache to force fresh search
rm -rf data/.cache/
```

## Need Help?

- Report issues: https://github.com/t-boris/buy-a-car/issues
- Check terminal logs for detailed errors
- Review cache files in `data/.cache/` to debug stages
