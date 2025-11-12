#!/usr/bin/env python3
"""
Stage 1: Find Dealerships

Searches Google for car dealerships near the configured ZIP code.
Results are cached in data/dealerships.json for 30 days.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models import AppConfig
from sources.google_search import find_dealerships


def load_config() -> AppConfig:
    """Load application configuration."""
    config_path = Path(__file__).parent.parent / "config" / "app.config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration not found: {config_path}")

    with open(config_path, 'r') as f:
        data = json.load(f)

    return AppConfig(**data)


async def main():
    print("\n" + "=" * 70)
    print("STAGE 1: FINDING DEALERSHIPS")
    print("=" * 70 + "\n")

    # Load config
    config = load_config()
    print(f"📍 Location: ZIP {config.zip}, Radius: {config.radius_miles} miles")

    if config.filters.include_makes:
        print(f"🚗 Target makes: {', '.join(config.filters.include_makes)}")

    print()

    # Find dealerships
    dealerships = await find_dealerships(config)

    # Print summary
    print("\n" + "─" * 70)
    print(f"✓ Found {len(dealerships)} dealerships")
    print("─" * 70)

    if dealerships:
        print(f"\nAll {len(dealerships)} dealerships found:")
        for i, dealer in enumerate(dealerships, 1):
            print(f"  {i}. {dealer['name']}")
            print(f"     Website: {dealer['website']}")

    # Save to cache file for next stage
    cache_dir = Path(__file__).parent.parent / "data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / "stage1_dealerships.json"
    with open(cache_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dealerships": dealerships
        }, f, indent=2)

    print(f"\n💾 Saved to: {cache_file}")
    print("\n" + "=" * 70)
    print(f"STAGE 1 COMPLETE: {len(dealerships)} dealerships ready for Stage 2")
    print("=" * 70 + "\n")

    return len(dealerships)


if __name__ == "__main__":
    try:
        count = asyncio.run(main())
        sys.exit(0 if count > 0 else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
