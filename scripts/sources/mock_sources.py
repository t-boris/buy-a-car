"""
Mock data sources for testing and development.

This module provides realistic sample data that conforms to the
application's filters and constraints. Useful for:
- Development without API keys
- Testing the full pipeline
- Demos and documentation
"""

from typing import List
from models import RawCarData, AppConfig


def get_mock_vehicles(config: AppConfig) -> List[RawCarData]:
    """
    Generate mock vehicle listings that match configuration filters.

    Args:
        config: Application configuration (used for filtering)

    Returns:
        List of mock raw vehicle data
    """
    # Base mock dataset
    mock_data = [
        RawCarData(
            vin="1HGCM82633A004352",
            source="mock-honda-dealer",
            year=2019,
            make="Honda",
            model="Accord",
            trim="EX-L",
            condition="used",
            price=18990,
            mileage=54200,
            distance_miles=18.4,
            dealer_name="Mock Honda Dealership",
            dealer_phone="+1-847-555-1234",
            dealer_url="https://mock-honda.example.com/vehicle/001",
            thumbnail_url="https://via.placeholder.com/400x300?text=2019+Honda+Accord"
        ),
        RawCarData(
            vin="5YJ3E1EA7KF317000",
            source="mock-toyota-dealer",
            year=2020,
            make="Toyota",
            model="Camry",
            trim="SE",
            condition="used",
            price=22990,
            mileage=32000,
            distance_miles=12.1,
            dealer_name="Mock Toyota Center",
            dealer_phone="+1-847-555-5678",
            dealer_url="https://mock-toyota.example.com/vehicle/002",
            thumbnail_url="https://via.placeholder.com/400x300?text=2020+Toyota+Camry"
        ),
        RawCarData(
            vin="5NPD84LF8KH456789",
            source="mock-hyundai-dealer",
            year=2019,
            make="Hyundai",
            model="Elantra",
            trim="SEL",
            condition="used",
            price=15490,
            mileage=48000,
            distance_miles=22.5,
            dealer_name="Mock Hyundai Sales",
            dealer_phone="+1-847-555-9012",
            dealer_url="https://mock-hyundai.example.com/vehicle/003",
            thumbnail_url="https://via.placeholder.com/400x300?text=2019+Hyundai+Elantra"
        ),
        RawCarData(
            vin="KNDJP3A57K7654321",
            source="mock-kia-dealer",
            year=2020,
            make="Kia",
            model="Forte",
            trim="LXS",
            condition="certified",
            price=17890,
            mileage=28500,
            distance_miles=8.7,
            dealer_name="Mock Kia Motors",
            dealer_phone="+1-847-555-3456",
            dealer_url="https://mock-kia.example.com/vehicle/004",
            thumbnail_url="https://via.placeholder.com/400x300?text=2020+Kia+Forte"
        ),
        RawCarData(
            vin="JF2SKAEC9LH987654",
            source="mock-subaru-dealer",
            year=2021,
            make="Subaru",
            model="Impreza",
            trim="Premium",
            condition="used",
            price=21490,
            mileage=35000,
            distance_miles=16.3,
            dealer_name="Mock Subaru Outlet",
            dealer_phone="+1-847-555-7890",
            dealer_url="https://mock-subaru.example.com/vehicle/005",
            thumbnail_url="https://via.placeholder.com/400x300?text=2021+Subaru+Impreza"
        ),
        RawCarData(
            vin="JM1BM1W79K1234567",
            source="mock-mazda-dealer",
            year=2019,
            make="Mazda",
            model="3",
            trim="Touring",
            condition="used",
            price=16990,
            mileage=41000,
            distance_miles=19.8,
            dealer_name="Mock Mazda Direct",
            dealer_phone="+1-847-555-2345",
            dealer_url="https://mock-mazda.example.com/vehicle/006",
            thumbnail_url="https://via.placeholder.com/400x300?text=2019+Mazda+3"
        ),
        RawCarData(
            vin="4T1B11HK2KU789012",
            source="mock-toyota-dealer",
            year=2019,
            make="Toyota",
            model="Corolla",
            trim="LE",
            condition="used",
            price=14990,
            mileage=52000,
            distance_miles=14.2,
            dealer_name="Mock Toyota Center",
            dealer_phone="+1-847-555-5678",
            dealer_url="https://mock-toyota.example.com/vehicle/007",
            thumbnail_url="https://via.placeholder.com/400x300?text=2019+Toyota+Corolla"
        ),
        RawCarData(
            vin="1HGCV1F16JA345678",
            source="mock-honda-dealer",
            year=2018,
            make="Honda",
            model="Civic",
            trim="EX",
            condition="used",
            price=16490,
            mileage=58000,
            distance_miles=25.6,
            dealer_name="Mock Honda Dealership",
            dealer_phone="+1-847-555-1234",
            dealer_url="https://mock-honda.example.com/vehicle/008",
            thumbnail_url="https://via.placeholder.com/400x300?text=2018+Honda+Civic"
        ),
        RawCarData(
            source="mock-hyundai-dealer",
            year=2021,
            make="Hyundai",
            model="Sonata",
            trim="SEL",
            condition="certified",
            price=24490,
            mileage=22000,
            distance_miles=11.4,
            dealer_name="Mock Hyundai Sales",
            dealer_phone="+1-847-555-9012",
            dealer_url="https://mock-hyundai.example.com/vehicle/009",
            thumbnail_url="https://via.placeholder.com/400x300?text=2021+Hyundai+Sonata"
        ),
        RawCarData(
            vin="JM3KFBDM8K0876543",
            source="mock-mazda-dealer",
            year=2020,
            make="Mazda",
            model="CX-5",
            trim="Touring",
            condition="used",
            price=23990,
            mileage=38000,
            distance_miles=20.1,
            dealer_name="Mock Mazda Direct",
            dealer_phone="+1-847-555-2345",
            dealer_url="https://mock-mazda.example.com/vehicle/010",
            thumbnail_url="https://via.placeholder.com/400x300?text=2020+Mazda+CX-5"
        )
    ]

    # Filter by configured makes (if specified)
    if config.filters.include_makes:
        filtered = [
            car for car in mock_data
            if car.make in config.filters.include_makes
        ]
    else:
        filtered = mock_data

    # Filter by year
    filtered = [
        car for car in filtered
        if car.year and car.year >= config.filters.min_year
    ]

    # Filter by mileage
    filtered = [
        car for car in filtered
        if car.mileage and car.mileage <= config.filters.max_mileage
    ]

    # Filter by condition
    filtered = [
        car for car in filtered
        if car.condition in config.filters.allowed_conditions
    ]

    return filtered


# ============================================================================
# Additional mock utilities
# ============================================================================

def get_price_varied_mock_data(config: AppConfig) -> List[RawCarData]:
    """
    Get mock data with varied prices for testing price trends.

    Returns the same vehicles but with slightly different prices
    to simulate price changes between runs.

    Args:
        config: Application configuration

    Returns:
        Mock vehicles with price variations
    """
    base_vehicles = get_mock_vehicles(config)

    # Randomly adjust prices up or down
    import random
    random.seed(42)  # Reproducible for testing

    for vehicle in base_vehicles:
        if vehicle.price:
            # 50% chance of price change
            if random.random() > 0.5:
                # ±5% price variation
                change_pct = random.uniform(-0.05, 0.05)
                vehicle.price = round(vehicle.price * (1 + change_pct), 2)

    return base_vehicles
