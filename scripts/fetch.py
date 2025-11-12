#!/usr/bin/env python3
"""
AutoFinder - Main data fetcher script.

This script orchestrates the entire data collection pipeline:
1. Load configuration
2. Gather vehicle data from sources
3. Normalize and deduplicate
4. Calculate finance information
5. Track price changes
6. Save results to JSON files
7. Update history

Run twice daily via GitHub Actions (07:30 and 19:30 CST)
or manually via workflow_dispatch.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models import (
    AppConfig,
    NormalizedCar,
    Inventory,
    History
)
import finance
import normalize
import price_tracker
from sources import gather_candidates


# ============================================================================
# File I/O Utilities
# ============================================================================

def load_config() -> AppConfig:
    """Load application configuration from config/app.config.json."""
    config_path = Path(__file__).parent.parent / "config" / "app.config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration not found: {config_path}")

    with open(config_path, 'r') as f:
        data = json.load(f)

    return AppConfig(**data)


def load_history() -> History:
    """
    Load price history from data/history.json.

    Returns empty history if file doesn't exist.
    """
    history_path = Path(__file__).parent.parent / "data" / "history.json"

    if not history_path.exists():
        return History(runs=[])

    try:
        with open(history_path, 'r') as f:
            data = json.load(f)
        return History(**data)
    except Exception as e:
        print(f"Warning: Failed to load history: {e}")
        return History(runs=[])


def load_existing_inventory() -> Dict[str, NormalizedCar]:
    """
    Load existing inventory from data/inventory.json.

    Returns dict of cars by ID for quick lookup.
    """
    inventory_path = Path(__file__).parent.parent / "data" / "inventory.json"

    if not inventory_path.exists():
        return {}

    try:
        with open(inventory_path, 'r') as f:
            data = json.load(f)

        inventory = Inventory(**data)

        # Build lookup dict
        return {car.id: car for car in inventory.items}

    except Exception as e:
        print(f"Warning: Failed to load existing inventory: {e}")
        return {}


def save_inventory(inventory: Inventory) -> None:
    """Save inventory to data/inventory.json."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    inventory_path = data_dir / "inventory.json"

    # Convert to dict for JSON serialization
    data = inventory.model_dump(mode='json')

    with open(inventory_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved inventory: {inventory_path}")


def save_history(history: History) -> None:
    """Save history to data/history.json."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    history_path = data_dir / "history.json"

    # Convert to dict for JSON serialization
    data = history.model_dump(mode='json')

    with open(history_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved history: {history_path}")


# ============================================================================
# Main Pipeline
# ============================================================================

async def run_fetch_pipeline() -> None:
    """
    Execute the complete data fetching pipeline.

    This is the main entry point that orchestrates all steps.
    """
    print("=" * 70)
    print("AutoFinder - Data Fetcher")
    print("=" * 70)

    timestamp = datetime.now(timezone.utc).astimezone().isoformat()
    print(f"Run started: {timestamp}\n")

    # Step 1: Load configuration
    print("[1/8] Loading configuration...")
    try:
        config = load_config()
        print(f"  ZIP: {config.zip}, Radius: {config.radius_miles} miles")
        print(f"  Budget: ${config.max_down_payment} down, ${config.max_monthly_payment}/mo")
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        sys.exit(1)

    # Step 2: Load existing data
    print("\n[2/8] Loading existing data...")
    history = load_history()
    existing_inventory = load_existing_inventory()
    print(f"  History: {len(history.runs)} previous runs")
    print(f"  Existing inventory: {len(existing_inventory)} vehicles")

    # Step 3: Gather raw data from sources
    print("\n[3/8] Gathering vehicle data from sources...")
    try:
        raw_candidates = await gather_candidates(config)
        print(f"  Total raw candidates: {len(raw_candidates)}")
    except Exception as e:
        print(f"ERROR: Failed to gather data: {e}")
        sys.exit(1)

    if not raw_candidates:
        print("WARNING: No vehicles found. Check your sources or API keys.")
        # Create empty inventory
        inventory = Inventory(
            generated_at=timestamp,
            zip=config.zip,
            radius_miles=config.radius_miles,
            items=[]
        )
        save_inventory(inventory)
        save_history(history)
        return

    # Step 4: Normalize data
    print("\n[4/8] Normalizing and validating...")
    normalized_cars: List[NormalizedCar] = []
    errors = 0

    for raw in raw_candidates:
        try:
            car = normalize.normalize_car(raw, existing_inventory.get(normalize.generate_stable_id(raw)))
            if normalize.validate_normalized_car(car):
                normalized_cars.append(car)
            else:
                errors += 1
        except Exception as e:
            errors += 1
            print(f"  Warning: Skipped vehicle: {e}")

    print(f"  Normalized: {len(normalized_cars)} vehicles")
    if errors > 0:
        print(f"  Skipped: {errors} invalid vehicles")

    # Step 5: Deduplicate
    print("\n[5/8] Deduplicating...")
    deduped_cars = normalize.deduplicate_cars(normalized_cars, existing_inventory)
    print(f"  Unique vehicles: {len(deduped_cars)}")

    # Step 5.5: Handle vehicles not seen this run (potential sold vehicles)
    print("\n[5.5/8] Tracking unseen vehicles...")
    found_ids = {car.id for car in deduped_cars}
    missing_vehicles = []

    for vehicle_id, existing_car in existing_inventory.items():
        if vehicle_id not in found_ids:
            # Vehicle not found in current run
            days_left = existing_car.days_to_live - 1

            if days_left > 0:
                # Still tracking - decrement days_to_live
                existing_car.days_to_live = days_left
                existing_car.expired_at = None
                missing_vehicles.append(existing_car)
                print(f"  {existing_car.title}: {days_left} days remaining")
            elif existing_car.expired_at is None:
                # Just expired - mark with timestamp
                existing_car.days_to_live = 0
                existing_car.expired_at = timestamp
                missing_vehicles.append(existing_car)
                print(f"  {existing_car.title}: SOLD (expired)")
            else:
                # Already expired before - keep the original expired_at
                missing_vehicles.append(existing_car)

    # Combine found and missing vehicles
    all_vehicles = deduped_cars + missing_vehicles
    print(f"  Tracked vehicles: {len(deduped_cars)} active + {len(missing_vehicles)} unseen = {len(all_vehicles)} total")

    # Step 6: Calculate finance info and filter by budget
    print("\n[6/8] Calculating finance and applying budget filters...")
    affordable_cars: List[NormalizedCar] = []

    for car in all_vehicles:
        try:
            meets_budget, finance_info = finance.meets_budget_constraints(
                price=car.price,
                max_down_payment=config.max_down_payment,
                max_monthly_payment=config.max_monthly_payment,
                finance_config=config.finance
            )

            if meets_budget and finance_info:
                car.finance = finance_info
                affordable_cars.append(car)
        except Exception as e:
            print(f"  Warning: Finance calculation failed for {car.id}: {e}")

    print(f"  Affordable vehicles: {len(affordable_cars)}")
    filtered_out = len(all_vehicles) - len(affordable_cars)
    if filtered_out > 0:
        print(f"  Filtered out (over budget): {filtered_out}")

    # Step 7: Update price trends
    print("\n[7/8] Updating price trends...")
    price_tracker.update_price_trends(affordable_cars, history)

    # Count price movements
    trends = {"new": 0, "down": 0, "up": 0, "flat": 0}
    for car in affordable_cars:
        trends[car.price_trend.direction] += 1

    print(f"  New: {trends['new']}, Down: {trends['down']}, Up: {trends['up']}, Flat: {trends['flat']}")

    # Find best deals
    deals = price_tracker.find_best_deals(affordable_cars, top_n=3)
    if deals:
        print("\n  Top price drops:")
        for i, car in enumerate(deals, 1):
            print(f"    {i}. {car.title}: ${car.price_trend.delta:,.0f} off")

    # Step 8: Save results
    print("\n[8/8] Saving results...")

    # Create inventory
    inventory = Inventory(
        generated_at=timestamp,
        zip=config.zip,
        radius_miles=config.radius_miles,
        items=affordable_cars
    )

    # Save inventory
    save_inventory(inventory)

    # Update and save history
    new_run = price_tracker.create_history_snapshot(affordable_cars, timestamp)
    updated_history = price_tracker.append_to_history(history, new_run, max_runs=100)
    save_history(updated_history)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total vehicles in inventory: {len(affordable_cars)}")
    print(f"Average price: ${sum(c.price for c in affordable_cars) / len(affordable_cars):,.2f}" if affordable_cars else "N/A")
    print(f"Price range: ${min(c.price for c in affordable_cars):,.0f} - ${max(c.price for c in affordable_cars):,.0f}" if affordable_cars else "N/A")
    print(f"\nData saved to data/inventory.json and data/history.json")
    print("=" * 70)


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point for the script."""
    try:
        asyncio.run(run_fetch_pipeline())
        print("\n✓ Fetch completed successfully")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
