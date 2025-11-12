"""
Data sources module for AutoFinder.

This module contains adapters for various data sources:
- AI-powered meta search (Gemini API)
- Direct dealer feeds/APIs
- Aggregator services

Each source should implement a consistent interface that returns
List[RawCarData] for normalization.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List
from models import RawCarData, AppConfig


async def gather_candidates(config: AppConfig) -> List[RawCarData]:
    """
    Gather vehicle candidates from all configured sources.

    This is the main entry point for data collection. It orchestrates
    calls to all enabled sources and aggregates results.

    Args:
        config: Application configuration

    Returns:
        List of raw vehicle data from all sources
    """
    candidates: List[RawCarData] = []

    # Import source modules
    from sources import mock_sources
    import json

    # Try to load Google Search results from Stage 3 cache
    stage3_cache = Path(__file__).parent.parent / "data" / ".cache" / "stage3_vehicles.json"

    if stage3_cache.exists():
        try:
            with open(stage3_cache, 'r') as f:
                data = json.load(f)

            # Convert to RawCarData objects
            for item in data.get("vehicles", []):
                try:
                    vehicle = RawCarData(**item)
                    candidates.append(vehicle)
                except Exception as e:
                    print(f"    Warning: Failed to load vehicle: {e}")
                    continue

            print(f"  Google Search (from cache): {len(candidates)} vehicles")
        except Exception as e:
            print(f"  Failed to load Stage 3 cache: {e}")
    else:
        print("  Google Search: No cached results (run stage scripts first)")

    # Mock/Demo sources (for testing)
    # Uncomment to use mock data for development
    try:
        mock_results = mock_sources.get_mock_vehicles(config)
        candidates.extend(mock_results)
        print(f"  Mock Sources: {len(mock_results)} vehicles")
    except Exception as e:
        print(f"  Mock Sources failed: {e}")

    print(f"\nTotal candidates gathered: {len(candidates)}")
    return candidates
