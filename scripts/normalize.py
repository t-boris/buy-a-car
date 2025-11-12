"""
Data normalization and deduplication for AutoFinder.

Transforms raw vehicle data from various sources into a canonical format
with stable IDs and deduplication logic.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, List
from models import (
    RawCarData,
    NormalizedCar,
    DealerInfo,
    MediaInfo,
    Timestamps,
    FinanceInfo,
    PriceTrend
)


def generate_stable_id(raw: RawCarData) -> str:
    """
    Generate a stable ID for a vehicle listing.

    Strategy (from spec):
    1. Prefer VIN as the canonical ID if available
    2. If no VIN: compute SHA-1 hash of key fields
       Hash components: source|year|make|model|trim|price|dealer_url

    Args:
        raw: Raw vehicle data

    Returns:
        Stable unique identifier
    """
    # Prefer VIN
    if raw.vin and len(raw.vin.strip()) > 0:
        return raw.vin.strip().upper()

    # Fallback: generate hash from key fields
    components = [
        raw.source or "",
        str(raw.year or ""),
        raw.make or "",
        raw.model or "",
        raw.trim or "",
        str(raw.price or ""),
        raw.dealer_url or ""
    ]

    hash_input = "|".join(components).lower()
    hash_obj = hashlib.sha1(hash_input.encode('utf-8'))
    return f"hash-{hash_obj.hexdigest()}"


def normalize_car(
    raw: RawCarData,
    existing_car: NormalizedCar = None
) -> NormalizedCar:
    """
    Normalize raw vehicle data into canonical format.

    Args:
        raw: Raw vehicle data from a source
        existing_car: Optional existing car data (for timestamp preservation)

    Returns:
        NormalizedCar instance

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Validate required fields
    if not raw.year:
        raise ValueError(f"Missing required field: year in {raw.source}")
    if not raw.make:
        raise ValueError(f"Missing required field: make in {raw.source}")
    if not raw.model:
        raise ValueError(f"Missing required field: model in {raw.source}")
    if not raw.price or raw.price <= 0:
        raise ValueError(f"Invalid price: {raw.price} in {raw.source}")
    if not raw.dealer_url:
        raise ValueError(f"Missing required field: dealer_url in {raw.source}")

    # Generate stable ID
    vehicle_id = generate_stable_id(raw)

    # Build title
    title_parts = [str(raw.year), raw.make, raw.model]
    if raw.trim:
        title_parts.append(raw.trim)
    title = " ".join(title_parts)

    # Normalize condition
    condition = (raw.condition or "used").lower()
    if condition not in ["new", "used", "certified"]:
        condition = "used"  # Default fallback

    # Current timestamp
    now = datetime.now(timezone.utc).astimezone().isoformat()

    # Determine timestamps and tracking info
    if existing_car and existing_car.id == vehicle_id:
        # Vehicle seen again - preserve first_seen, update last_seen
        first_seen = existing_car.timestamps.first_seen
        last_seen = now
        # Reset days_to_live since it's still available
        days_to_live = 3
        expired_at = None
    else:
        # New listing
        first_seen = now
        last_seen = now
        days_to_live = 3
        expired_at = None

    # Create normalized car
    return NormalizedCar(
        id=vehicle_id,
        vin=raw.vin,
        source=raw.source,
        title=title,
        year=raw.year,
        make=raw.make,
        model=raw.model,
        trim=raw.trim,
        condition=condition,
        price=raw.price,
        mileage=raw.mileage or 0,
        distance_miles=raw.distance_miles or 0.0,
        dealer=DealerInfo(
            name=raw.dealer_name or "Unknown Dealer",
            phone=raw.dealer_phone,
            url=raw.dealer_url
        ),
        media=MediaInfo(
            thumbnail=raw.thumbnail_url
        ),
        timestamps=Timestamps(
            first_seen=first_seen,
            last_seen=last_seen
        ),
        finance=FinanceInfo(
            est_down=0,  # Will be filled in by finance module
            est_monthly=0,
            assumptions={
                "apr_percent": 0,
                "term_months": 0,
                "ttl_percent_of_price": 0,
                "doc_fees": 0
            }
        ),
        price_trend=PriceTrend(
            direction="new",
            delta=0
        ),
        days_to_live=days_to_live,
        expired_at=expired_at
    )


def deduplicate_cars(
    cars: List[NormalizedCar],
    existing_inventory: Dict[str, NormalizedCar] = None
) -> List[NormalizedCar]:
    """
    Deduplicate vehicle listings by ID.

    When duplicates are found:
    1. Keep the one with the most recent data
    2. Preserve earliest first_seen timestamp
    3. Update last_seen to current time

    Args:
        cars: List of normalized cars (may contain duplicates)
        existing_inventory: Optional dict of existing cars by ID

    Returns:
        Deduplicated list of cars
    """
    existing = existing_inventory or {}
    deduped: Dict[str, NormalizedCar] = {}

    for car in cars:
        car_id = car.id

        # Check if we've already seen this car in current batch
        if car_id in deduped:
            # Keep the one with later last_seen, but preserve earliest first_seen
            existing_car = deduped[car_id]
            if car.timestamps.last_seen > existing_car.timestamps.last_seen:
                # Use newer data, but preserve first_seen
                car.timestamps.first_seen = existing_car.timestamps.first_seen
                deduped[car_id] = car
        else:
            # Check against existing inventory
            if car_id in existing:
                # Preserve original first_seen
                car.timestamps.first_seen = existing[car_id].timestamps.first_seen

            deduped[car_id] = car

    return list(deduped.values())


def merge_with_existing(
    new_cars: List[NormalizedCar],
    existing_cars: List[NormalizedCar],
    max_age_days: int = 7
) -> List[NormalizedCar]:
    """
    Merge new car listings with existing inventory.

    Strategy:
    1. Keep all new cars (they are current)
    2. Keep existing cars if they're still fresh (within max_age_days)
    3. Drop old listings that weren't re-discovered

    Args:
        new_cars: Newly discovered cars from current run
        existing_cars: Cars from previous inventory
        max_age_days: Maximum age in days to keep stale listings

    Returns:
        Merged list of current cars
    """
    from datetime import timedelta

    # Build lookup of new car IDs
    new_car_ids = {car.id for car in new_cars}

    # Current time for age comparison
    now = datetime.now(timezone.utc).astimezone()

    # Start with all new cars
    merged = list(new_cars)

    # Add existing cars that are still relevant
    for existing_car in existing_cars:
        # Skip if we already have this car in new batch
        if existing_car.id in new_car_ids:
            continue

        # Check age
        try:
            last_seen = datetime.fromisoformat(existing_car.timestamps.last_seen)
            age = now - last_seen

            # Keep if fresh enough
            if age <= timedelta(days=max_age_days):
                merged.append(existing_car)
        except (ValueError, TypeError):
            # Skip cars with invalid timestamps
            continue

    return merged


def validate_normalized_car(car: NormalizedCar) -> bool:
    """
    Validate that a normalized car has all required fields.

    Args:
        car: Normalized car to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        # Check critical fields
        if not car.id or len(car.id) == 0:
            return False
        if not car.source or len(car.source) == 0:
            return False
        if car.year < 1900 or car.year > datetime.now().year + 2:
            return False
        if not car.make or not car.model:
            return False
        if car.price <= 0:
            return False
        if car.mileage < 0:
            return False
        if not car.dealer.url:
            return False

        return True
    except Exception:
        return False


# ============================================================================
# Example usage
# ============================================================================

if __name__ == "__main__":
    """Test normalization with example data."""

    # Create sample raw data
    raw1 = RawCarData(
        vin="1HGCM82633A004352",
        source="example-dealer.com",
        year=2019,
        make="Honda",
        model="Accord",
        trim="EX-L",
        condition="used",
        price=18990,
        mileage=54200,
        distance_miles=18.4,
        dealer_name="Example Honda",
        dealer_phone="+1-847-555-1234",
        dealer_url="https://example-dealer.com/vehicle/123",
        thumbnail_url="https://example-dealer.com/img/123.jpg"
    )

    raw2 = RawCarData(
        source="another-dealer.com",
        year=2020,
        make="Toyota",
        model="Camry",
        trim="LE",
        condition="used",
        price=22500,
        mileage=32000,
        distance_miles=12.1,
        dealer_name="Another Toyota",
        dealer_url="https://another-dealer.com/vehicle/456"
    )

    print("Normalization Test")
    print("=" * 70)

    # Normalize
    car1 = normalize_car(raw1)
    car2 = normalize_car(raw2)

    print(f"\nCar 1: {car1.title}")
    print(f"  ID: {car1.id}")
    print(f"  VIN: {car1.vin}")
    print(f"  Price: ${car1.price:,.2f}")
    print(f"  Source: {car1.source}")
    print(f"  Valid: {validate_normalized_car(car1)}")

    print(f"\nCar 2: {car2.title}")
    print(f"  ID: {car2.id}")
    print(f"  VIN: {car2.vin or 'N/A (hash-based ID)'}")
    print(f"  Price: ${car2.price:,.2f}")
    print(f"  Source: {car2.source}")
    print(f"  Valid: {validate_normalized_car(car2)}")

    # Test deduplication
    cars = [car1, car2, car1]  # car1 appears twice
    deduped = deduplicate_cars(cars)
    print(f"\n\nDeduplication: {len(cars)} cars -> {len(deduped)} unique cars")
