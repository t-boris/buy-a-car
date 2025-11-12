"""
Google Custom Search integration for finding dealerships and vehicle inventory.

Three-stage pipeline:
1. Find dealerships near ZIP code
2. Search for inventory on dealership sites
3. Parse pages and extract vehicle data via Gemini
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from pathlib import Path
from models import RawCarData, AppConfig


# Google Custom Search API configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# Gemini API for parsing
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

# Cache configuration
DEALERSHIPS_CACHE = Path("data/dealerships.json")
CACHE_DAYS = 7  # Refresh dealerships weekly (reduced from 30 for more updates)


# ============================================================================
# STAGE 1: Find Dealerships
# ============================================================================

async def find_dealerships(config: AppConfig) -> List[Dict]:
    """
    Stage 1: Find car dealerships near the configured ZIP code.

    Results are cached for CACHE_DAYS to minimize API calls.

    Args:
        config: Application configuration with ZIP and radius

    Returns:
        List of dealership info dicts with name, website, etc.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("  Warning: Google Search credentials not set")
        return []

    # Check cache
    cached = load_dealerships_cache()
    if cached:
        print(f"  Using cached dealerships: {len(cached)} found")
        return cached

    print(f"  Searching for dealerships near {config.zip} within {config.radius_miles} miles...")

    dealerships = []

    # Cities within 15 miles of Gurnee, IL (60031)
    nearby_cities = [
        "Gurnee IL",
        "Waukegan IL",
        "Libertyville IL",
        "Vernon Hills IL",
        "Mundelein IL",
        "Grayslake IL",
        "Lake Forest IL"
    ]

    # Search queries - comprehensive coverage
    queries = []

    # General dealership searches
    for city in nearby_cities:
        queries.append(f"car dealership {city}")
        queries.append(f"used cars {city}")

    # Make-specific searches (ALL makes, not limited)
    if config.filters.include_makes:
        for make in config.filters.include_makes:  # ALL makes, no limit
            for city in nearby_cities[:3]:  # Top 3 cities for each make
                queries.append(f"{make} dealer {city}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, query in enumerate(queries, 1):
            print(f"    [{i}/{len(queries)}] Searching: {query}")
            try:
                results = await google_search(client, query, num=10)

                for item in results:
                    dealership = {
                        "name": item.get("title", ""),
                        "website": extract_domain(item.get("link", "")),
                        "snippet": item.get("snippet", ""),
                        "found_at": datetime.now().isoformat(),
                    }

                    # Deduplicate by website
                    if dealership["website"] and not any(d["website"] == dealership["website"] for d in dealerships):
                        dealerships.append(dealership)

            except Exception as e:
                print(f"    Warning: Search failed for '{query}': {e}")
                continue

    print(f"  Found {len(dealerships)} unique dealerships")

    # Cache results
    save_dealerships_cache(dealerships)

    return dealerships


async def google_search(client: httpx.AsyncClient, query: str, num: int = 10, site: Optional[str] = None) -> List[Dict]:
    """
    Execute a Google Custom Search query.

    Args:
        client: HTTP client
        query: Search query
        num: Number of results (max 10 per request)
        site: Optional site restriction (e.g., "example.com")

    Returns:
        List of search result items
    """
    if site:
        query = f"site:{site} {query}"

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": min(num, 10),  # API limit is 10 per request
    }

    response = await client.get(GOOGLE_SEARCH_URL, params=params)
    response.raise_for_status()

    data = response.json()
    return data.get("items", [])


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www.
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def load_dealerships_cache() -> Optional[List[Dict]]:
    """Load dealerships from cache if fresh enough."""
    if not DEALERSHIPS_CACHE.exists():
        return None

    try:
        with open(DEALERSHIPS_CACHE, "r") as f:
            data = json.load(f)

        cached_at = datetime.fromisoformat(data.get("cached_at", ""))
        age_days = (datetime.now() - cached_at).days

        if age_days < CACHE_DAYS:
            return data.get("dealerships", [])
        else:
            print(f"  Cache expired ({age_days} days old)")
            return None

    except Exception as e:
        print(f"  Warning: Failed to load cache: {e}")
        return None


def save_dealerships_cache(dealerships: List[Dict]):
    """Save dealerships to cache."""
    try:
        DEALERSHIPS_CACHE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "cached_at": datetime.now().isoformat(),
            "dealerships": dealerships,
        }

        with open(DEALERSHIPS_CACHE, "w") as f:
            json.dump(data, f, indent=2)

    except Exception as e:
        print(f"  Warning: Failed to save cache: {e}")


# ============================================================================
# STAGE 2: Search Inventory
# ============================================================================

async def search_inventory(config: AppConfig, dealerships: List[Dict]) -> List[Dict]:
    """
    Stage 2: Search for vehicle inventory on dealership websites.

    Args:
        config: Application configuration with filters
        dealerships: List of dealerships from Stage 1

    Returns:
        List of search result pages with URLs and snippets
    """
    if not dealerships:
        return []

    print(f"  Searching inventory across {len(dealerships)} dealerships...")

    pages = []

    # Build search terms based on filters - comprehensive
    search_terms = [
        "used cars",
        "inventory",
        "vehicles for sale",
        "pre-owned vehicles",
        "certified pre-owned"
    ]

    if config.filters.include_makes:
        for make in config.filters.include_makes:  # ALL makes
            search_terms.append(f"{make} for sale")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Process ALL dealerships, no limit
        for dealership in dealerships:
            website = dealership.get("website")
            if not website:
                continue

            # Use ALL search terms, no limit
            for term in search_terms:
                try:
                    query = f"{term}"
                    results = await google_search(client, query, num=5, site=website)

                    for item in results:
                        page = {
                            "url": item.get("link", ""),
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "dealership": dealership["name"],
                            "dealership_site": website,
                        }

                        # Deduplicate by URL
                        if page["url"] and not any(p["url"] == page["url"] for p in pages):
                            pages.append(page)

                except Exception as e:
                    continue  # Skip on error, continue with next

    print(f"  Found {len(pages)} inventory pages")
    return pages


# ============================================================================
# STAGE 3: Parse with Gemini
# ============================================================================

async def parse_inventory_pages(config: AppConfig, pages: List[Dict]) -> List[RawCarData]:
    """
    Stage 3: Fetch page content and extract vehicle data using Gemini.

    Args:
        config: Application configuration
        pages: List of inventory page URLs from Stage 2

    Returns:
        List of raw vehicle data
    """
    if not pages:
        return []

    if not GEMINI_API_KEY:
        print("  Warning: GEMINI_API_KEY not set, skipping parsing")
        return []

    print(f"  Parsing {len(pages)} pages with Gemini...")

    vehicles = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Process ALL pages, no limit - we don't want to miss any deals
        for i, page in enumerate(pages, 1):
            try:
                # Fetch page content
                html = await fetch_page_content(client, page["url"])
                if not html:
                    continue

                # Extract text (simple approach - remove tags)
                text = extract_text_from_html(html)
                if len(text) < 100:  # Skip if too little content
                    continue

                # Parse with Gemini
                page_vehicles = await parse_with_gemini(client, text, page, config)
                vehicles.extend(page_vehicles)

                print(f"    [{i}/{min(len(pages), 20)}] {page['dealership']}: {len(page_vehicles)} vehicles")

            except Exception as e:
                print(f"    Warning: Failed to parse {page['url']}: {e}")
                continue

    print(f"  Extracted {len(vehicles)} vehicles total")
    return vehicles


async def fetch_page_content(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Fetch HTML content from URL."""
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except:
        return None


def extract_text_from_html(html: str) -> str:
    """
    Extract text content from HTML.

    Simple approach: remove script/style tags and extract text.
    Truncate to reasonable length for Gemini.
    """
    import re

    # Remove script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Truncate to 15000 chars (Gemini token limit consideration)
    return text[:15000]


async def parse_with_gemini(client: httpx.AsyncClient, text: str, page: Dict, config: AppConfig) -> List[RawCarData]:
    """
    Use Gemini to extract structured vehicle data from page text.

    Args:
        client: HTTP client
        text: Extracted page text
        page: Page metadata
        config: App configuration

    Returns:
        List of raw vehicle data
    """
    prompt = f"""
Extract vehicle listings from this car dealership webpage text.

Dealership: {page['dealership']}
Website: {page['dealership_site']}

Return ONLY valid JSON with this structure (no markdown, no extra text):
{{
  "vehicles": [
    {{
      "vin": "VIN if available or null",
      "year": 2020,
      "make": "Honda",
      "model": "Accord",
      "trim": "EX-L or null",
      "condition": "used or certified or new",
      "price": 22990,
      "mileage": 45000
    }}
  ]
}}

Requirements:
- Only include vehicles with year, make, model, and price
- Set mileage to null for new cars if not listed
- If no vehicles found, return {{"vehicles": []}}

Page text (truncated):
{text}
"""

    try:
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.8,
                "maxOutputTokens": 4096
            }
        }

        response = await client.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )

        response.raise_for_status()
        data = response.json()

        # Extract text from response
        candidates = data.get("candidates", [])
        if not candidates:
            return []

        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        # Clean markdown if present
        text_content = text_content.strip()
        if text_content.startswith("```json"):
            text_content = text_content[7:]
        if text_content.startswith("```"):
            text_content = text_content[3:]
        if text_content.endswith("```"):
            text_content = text_content[:-3]

        # Parse JSON
        parsed = json.loads(text_content.strip())

        # Convert to RawCarData
        vehicles = []
        for item in parsed.get("vehicles", []):
            try:
                vehicle = RawCarData(
                    vin=item.get("vin"),
                    source="google-search",
                    year=item.get("year"),
                    make=item.get("make"),
                    model=item.get("model"),
                    trim=item.get("trim"),
                    condition=item.get("condition", "used"),
                    price=item.get("price"),
                    mileage=item.get("mileage"),
                    distance_miles=0.0,  # Would need geocoding
                    dealer_name=page["dealership"],
                    dealer_url=page["url"],
                    dealer_phone=None,
                    thumbnail_url=None
                )

                # Validate required fields
                if vehicle.year and vehicle.make and vehicle.model and vehicle.price:
                    vehicles.append(vehicle)

            except Exception as e:
                continue

        return vehicles

    except Exception as e:
        print(f"      Gemini parse error: {e}")
        return []


# ============================================================================
# Main Entry Point
# ============================================================================

async def search_vehicles(config: AppConfig) -> List[RawCarData]:
    """
    Execute full three-stage pipeline to find vehicles.

    Args:
        config: Application configuration

    Returns:
        List of raw vehicle data
    """
    print("\n  === Google Search Pipeline ===")

    # Stage 1: Find dealerships
    print("\n  [Stage 1/3] Finding dealerships...")
    dealerships = await find_dealerships(config)

    if not dealerships:
        print("  No dealerships found, aborting pipeline")
        return []

    # Stage 2: Search inventory
    print(f"\n  [Stage 2/3] Searching inventory...")
    pages = await search_inventory(config, dealerships)

    if not pages:
        print("  No inventory pages found")
        return []

    # Stage 3: Parse with Gemini
    print(f"\n  [Stage 3/3] Extracting vehicle data...")
    vehicles = await parse_inventory_pages(config, pages)

    print(f"\n  Pipeline complete: {len(vehicles)} vehicles found")
    return vehicles
