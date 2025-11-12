"""
Price tracking and change detection for AutoFinder.

Compares current prices with historical data to detect:
- Price increases (▲)
- Price decreases (▼)
- New listings (●)
- Stable prices (–)
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from models import NormalizedCar, PriceTrend, History, HistoryItem, HistoryRun


def build_price_index(history: History) -> Dict[str, float]:
    """
    Build a lookup of vehicle ID -> most recent price from history.

    Args:
        history: Historical price data

    Returns:
        Dictionary mapping vehicle IDs to their last known prices
    """
    price_index: Dict[str, float] = {}

    if not history.runs or len(history.runs) == 0:
        return price_index

    # Get the most recent run
    latest_run = history.runs[-1]

    # Build index from latest run
    for item in latest_run.items:
        price_index[item.id] = item.price

    return price_index


def detect_price_change(
    car: NormalizedCar,
    previous_price: Optional[float]
) -> PriceTrend:
    """
    Detect price change for a single vehicle.

    Args:
        car: Current vehicle data
        previous_price: Price from previous run (or None if new listing)

    Returns:
        PriceTrend object with direction, delta, and metadata
    """
    current_price = car.price
    now = datetime.now(timezone.utc).astimezone().isoformat()

    # New listing - no previous price
    if previous_price is None:
        return PriceTrend(
            direction="new",
            delta=0,
            prev_price=None,
            last_change_at=None
        )

    # Price decreased (good for buyer!)
    if current_price < previous_price:
        delta = previous_price - current_price
        return PriceTrend(
            direction="down",
            delta=delta,
            prev_price=previous_price,
            last_change_at=now
        )

    # Price increased
    elif current_price > previous_price:
        delta = current_price - previous_price
        return PriceTrend(
            direction="up",
            delta=delta,
            prev_price=previous_price,
            last_change_at=now
        )

    # Price unchanged
    else:
        return PriceTrend(
            direction="flat",
            delta=0,
            prev_price=previous_price,
            last_change_at=None
        )


def update_price_trends(
    cars: List[NormalizedCar],
    history: History
) -> List[NormalizedCar]:
    """
    Update price trends for all cars based on historical data.

    Modifies the price_trend field of each car in place.

    Args:
        cars: List of current vehicles
        history: Historical price data

    Returns:
        Updated list of cars with price trends
    """
    # Build price index from history
    price_index = build_price_index(history)

    # Update each car
    for car in cars:
        previous_price = price_index.get(car.id)
        car.price_trend = detect_price_change(car, previous_price)

    return cars


def create_history_snapshot(
    cars: List[NormalizedCar],
    timestamp: Optional[str] = None
) -> HistoryRun:
    """
    Create a compact history snapshot for the current run.

    Args:
        cars: Current vehicle inventory
        timestamp: Optional ISO 8601 timestamp (defaults to now)

    Returns:
        HistoryRun object containing IDs and prices
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).astimezone().isoformat()

    items = [
        HistoryItem(id=car.id, price=car.price)
        for car in cars
    ]

    return HistoryRun(
        generated_at=timestamp,
        items=items
    )


def append_to_history(
    history: History,
    new_run: HistoryRun,
    max_runs: int = 100
) -> History:
    """
    Append a new run to history and trim old entries.

    Args:
        history: Existing history
        new_run: New run to append
        max_runs: Maximum number of runs to keep (oldest are dropped)

    Returns:
        Updated history
    """
    history.runs.append(new_run)

    # Trim to max_runs (keep most recent)
    if len(history.runs) > max_runs:
        history.runs = history.runs[-max_runs:]

    return history


def get_price_statistics(
    car_id: str,
    history: History
) -> Optional[Dict[str, float]]:
    """
    Calculate price statistics for a vehicle across its history.

    Args:
        car_id: Vehicle ID
        history: Historical price data

    Returns:
        Dictionary with min, max, avg prices, or None if not found
    """
    prices: List[float] = []

    # Collect all prices for this vehicle
    for run in history.runs:
        for item in run.items:
            if item.id == car_id:
                prices.append(item.price)

    if not prices:
        return None

    return {
        "min": min(prices),
        "max": max(prices),
        "avg": sum(prices) / len(prices),
        "current": prices[-1],
        "count": len(prices)
    }


def find_best_deals(
    cars: List[NormalizedCar],
    top_n: int = 10
) -> List[NormalizedCar]:
    """
    Find vehicles with the biggest price drops.

    Args:
        cars: List of vehicles with price trends
        top_n: Number of best deals to return

    Returns:
        Sorted list of vehicles with largest price decreases
    """
    # Filter to only price drops
    deals = [car for car in cars if car.price_trend.direction == "down"]

    # Sort by delta (descending)
    deals.sort(key=lambda c: c.price_trend.delta, reverse=True)

    return deals[:top_n]


# ============================================================================
# Example usage
# ============================================================================

if __name__ == "__main__":
    """Test price tracking with example data."""
    from models import DealerInfo, MediaInfo, Timestamps, FinanceInfo, FinanceAssumptions

    print("Price Tracking Test")
    print("=" * 70)

    # Create mock history
    history = History(runs=[
        HistoryRun(
            generated_at="2025-11-10T19:30:00-06:00",
            items=[
                HistoryItem(id="VIN123", price=19990),
                HistoryItem(id="VIN456", price=22500),
                HistoryItem(id="VIN789", price=15000)
            ]
        )
    ])

    # Create mock current inventory
    current_cars = [
        NormalizedCar(
            id="VIN123",
            vin="VIN123",
            source="test",
            title="2019 Honda Accord",
            year=2019,
            make="Honda",
            model="Accord",
            trim="EX-L",
            condition="used",
            price=18990,  # Price dropped!
            mileage=54000,
            distance_miles=15.0,
            dealer=DealerInfo(name="Test Dealer", url="https://test.com"),
            media=MediaInfo(),
            timestamps=Timestamps(
                first_seen="2025-11-10T19:30:00-06:00",
                last_seen="2025-11-11T07:30:00-06:00"
            ),
            finance=FinanceInfo(
                est_down=3000,
                est_monthly=350,
                assumptions=FinanceAssumptions(
                    apr_percent=6.0,
                    term_months=60,
                    ttl_percent_of_price=7.5,
                    doc_fees=200
                )
            )
        ),
        NormalizedCar(
            id="VIN456",
            vin="VIN456",
            source="test",
            title="2020 Toyota Camry",
            year=2020,
            make="Toyota",
            model="Camry",
            trim="LE",
            condition="used",
            price=23500,  # Price increased
            mileage=32000,
            distance_miles=12.0,
            dealer=DealerInfo(name="Test Dealer 2", url="https://test2.com"),
            media=MediaInfo(),
            timestamps=Timestamps(
                first_seen="2025-11-10T19:30:00-06:00",
                last_seen="2025-11-11T07:30:00-06:00"
            ),
            finance=FinanceInfo(
                est_down=3000,
                est_monthly=420,
                assumptions=FinanceAssumptions(
                    apr_percent=6.0,
                    term_months=60,
                    ttl_percent_of_price=7.5,
                    doc_fees=200
                )
            )
        ),
        NormalizedCar(
            id="VIN999",
            vin="VIN999",
            source="test",
            title="2021 Mazda CX-5",
            year=2021,
            make="Mazda",
            model="CX-5",
            trim="Sport",
            condition="used",
            price=26000,  # New listing
            mileage=28000,
            distance_miles=20.0,
            dealer=DealerInfo(name="Test Dealer 3", url="https://test3.com"),
            media=MediaInfo(),
            timestamps=Timestamps(
                first_seen="2025-11-11T07:30:00-06:00",
                last_seen="2025-11-11T07:30:00-06:00"
            ),
            finance=FinanceInfo(
                est_down=3000,
                est_monthly=480,
                assumptions=FinanceAssumptions(
                    apr_percent=6.0,
                    term_months=60,
                    ttl_percent_of_price=7.5,
                    doc_fees=200
                )
            )
        )
    ]

    # Update price trends
    updated_cars = update_price_trends(current_cars, history)

    # Display results
    print("\nPrice Trends:")
    for car in updated_cars:
        trend = car.price_trend
        symbol = {"down": "▼", "up": "▲", "new": "●", "flat": "–"}[trend.direction]

        print(f"\n{car.title} (${car.price:,.0f})")
        print(f"  Trend: {symbol} {trend.direction}")

        if trend.direction in ["down", "up"]:
            print(f"  Previous: ${trend.prev_price:,.0f}")
            print(f"  Delta: ${trend.delta:,.0f}")

    # Find best deals
    print("\n\nBest Deals (Price Drops):")
    deals = find_best_deals(updated_cars)
    for i, car in enumerate(deals, 1):
        print(f"{i}. {car.title}: ${car.price_trend.delta:,.0f} off")
