#!/usr/bin/env python3
"""
Stage 2: Search Inventory Pages

Searches for vehicle inventory pages on dealership websites found in Stage 1.
Uses Google Custom Search with site: operator to target specific dealerships.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models import AppConfig
from sources.google_search import search_inventory


def load_config() -> AppConfig:
    """Load application configuration."""
    config_path = Path(__file__).parent.parent / "config" / "app.config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration not found: {config_path}")

    with open(config_path, 'r') as f:
        data = json.load(f)

    return AppConfig(**data)


def load_dealerships() -> list:
    """Load dealerships from Stage 1."""
    cache_file = Path(__file__).parent.parent / "data" / ".cache" / "stage1_dealerships.json"

    if not cache_file.exists():
        raise FileNotFoundError(
            "Stage 1 results not found. Run stage1_dealerships.py first."
        )

    with open(cache_file, 'r') as f:
        data = json.load(f)

    return data.get("dealerships", [])


async def main():
    print("\n" + "=" * 70)
    print("STAGE 2: SEARCHING INVENTORY PAGES")
    print("=" * 70 + "\n")

    # Load config and dealerships
    config = load_config()
    dealerships = load_dealerships()

    print(f"📋 Processing {len(dealerships)} dealerships from Stage 1")

    if config.filters.include_makes:
        print(f"🔍 Search terms: used cars, inventory, vehicles for sale")
        print(f"🚗 Target makes ({len(config.filters.include_makes)}): {', '.join(config.filters.include_makes)}")

    print()

    # Search inventory pages
    pages = await search_inventory(config, dealerships)

    # Print summary by dealership
    print("\n" + "─" * 70)
    print(f"✓ Found {len(pages)} inventory pages")
    print("─" * 70)

    if pages:
        # Group by dealership
        by_dealer = {}
        for page in pages:
            dealer = page['dealership']
            by_dealer.setdefault(dealer, []).append(page)

        print(f"\nPages by dealership (top 10):")
        for i, (dealer, dealer_pages) in enumerate(list(by_dealer.items())[:10], 1):
            print(f"  {i}. {dealer}: {len(dealer_pages)} pages")
            # Show first page URL as example
            if dealer_pages:
                print(f"     Example: {dealer_pages[0]['url'][:60]}...")

    # Save to cache file for next stage
    cache_dir = Path(__file__).parent.parent / "data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / "stage2_inventory_pages.json"
    with open(cache_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "pages": pages
        }, f, indent=2)

    print(f"\n💾 Saved to: {cache_file}")
    print("\n" + "=" * 70)
    print(f"STAGE 2 COMPLETE: {len(pages)} pages ready for Stage 3")
    print("=" * 70 + "\n")

    return len(pages)


if __name__ == "__main__":
    try:
        count = asyncio.run(main())
        sys.exit(0 if count > 0 else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
