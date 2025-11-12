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
    from sources import ai_meta_search, mock_sources

    # AI Meta Search (if enabled)
    if config.sources.ai_meta_search:
        try:
            ai_results = await ai_meta_search.search_vehicles(config)
            candidates.extend(ai_results)
            print(f"  AI Meta Search: {len(ai_results)} vehicles")
        except Exception as e:
            print(f"  AI Meta Search failed: {e}")

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
