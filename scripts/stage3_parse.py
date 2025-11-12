#!/usr/bin/env python3
"""
Stage 3: Parse with Gemini AI

Fetches HTML content from inventory pages and uses Gemini 2.5 Pro
to extract structured vehicle data.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models import AppConfig
from sources.google_search import parse_inventory_pages


def load_config() -> AppConfig:
    """Load application configuration."""
    config_path = Path(__file__).parent.parent / "config" / "app.config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration not found: {config_path}")

    with open(config_path, 'r') as f:
        data = json.load(f)

    return AppConfig(**data)


def load_inventory_pages() -> list:
    """Load inventory pages from Stage 2."""
    cache_file = Path(__file__).parent.parent / "data" / ".cache" / "stage2_inventory_pages.json"

    if not cache_file.exists():
        raise FileNotFoundError(
            "Stage 2 results not found. Run stage2_inventory.py first."
        )

    with open(cache_file, 'r') as f:
        data = json.load(f)

    return data.get("pages", [])


async def main():
    print("\n" + "=" * 70)
    print("STAGE 3: PARSING WITH GEMINI AI")
    print("=" * 70 + "\n")

    # Load config and pages
    config = load_config()
    pages = load_inventory_pages()

    print(f"📄 Processing ALL {len(pages)} inventory pages from Stage 2")
    print(f"🤖 Using Gemini 2.5 Pro for extraction")
    print(f"⚡ Processing ALL pages - no limits, maximum coverage")
    print()

    # Parse pages with Gemini
    vehicles = await parse_inventory_pages(config, pages)

    # Print summary
    print("\n" + "─" * 70)
    print(f"✓ Extracted {len(vehicles)} vehicles")
    print("─" * 70)

    if vehicles:
        # Group by dealership
        by_dealer = {}
        for vehicle in vehicles:
            dealer = vehicle.dealer_name
            by_dealer.setdefault(dealer, []).append(vehicle)

        print(f"\nVehicles by dealership:")
        for dealer, dealer_vehicles in sorted(by_dealer.items()):
            print(f"  {dealer}: {len(dealer_vehicles)} vehicles")

        # Show some examples
        print(f"\nExample vehicles found:")
        for i, vehicle in enumerate(vehicles[:5], 1):
            print(f"  {i}. {vehicle.year} {vehicle.make} {vehicle.model}")
            print(f"     Price: ${vehicle.price:,.0f}, Miles: {vehicle.mileage:,}")
            print(f"     Dealer: {vehicle.dealer_name}")

    # Convert to JSON-serializable format
    vehicles_data = [
        {
            "vin": v.vin,
            "source": v.source,
            "year": v.year,
            "make": v.make,
            "model": v.model,
            "trim": v.trim,
            "condition": v.condition,
            "price": v.price,
            "mileage": v.mileage,
            "distance_miles": v.distance_miles,
            "dealer_name": v.dealer_name,
            "dealer_phone": v.dealer_phone,
            "dealer_url": v.dealer_url,
            "thumbnail_url": v.thumbnail_url
        }
        for v in vehicles
    ]

    # Save to cache file for fetch.py
    cache_dir = Path(__file__).parent.parent / "data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / "stage3_vehicles.json"
    with open(cache_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "vehicles": vehicles_data
        }, f, indent=2)

    print(f"\n💾 Saved to: {cache_file}")
    print("\n" + "=" * 70)
    print(f"STAGE 3 COMPLETE: {len(vehicles)} vehicles ready for final processing")
    print("=" * 70 + "\n")

    return len(vehicles)


if __name__ == "__main__":
    try:
        count = asyncio.run(main())
        sys.exit(0)  # Don't fail if no vehicles found, continue pipeline
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
