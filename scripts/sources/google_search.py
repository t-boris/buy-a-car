"""
Google Custom Search integration for finding dealerships and vehicle inventory.

Three-stage pipeline:
1. Find dealerships near ZIP code
2. Search for inventory on dealership sites
3. Parse pages and extract vehicle data via Gemini
"""

import os
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from pathlib import Path
from models import RawCarData, AppConfig


# Verbose logging flag
VERBOSE = os.getenv('AUTOFINDER_VERBOSE', '').lower() in ('1', 'true', 'yes')


def log_request(method: str, url: str, duration: float, status: int = None, size: int = None):
    """Log HTTP request details if verbose mode is enabled."""
    if not VERBOSE:
        return

    # Colors for terminal
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

    # Format duration
    if duration < 1:
        duration_str = f"{duration*1000:.0f}ms"
    else:
        duration_str = f"{duration:.2f}s"

    # Status color
    if status:
        if status < 300:
            status_color = GREEN
        elif status < 400:
            status_color = YELLOW
        else:
            status_color = RED
        status_str = f"{status_color}{status}{RESET}"
    else:
        status_str = "---"

    # Size formatting
    if size:
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024 * 1024:
            size_str = f"{size/1024:.1f}KB"
        else:
            size_str = f"{size/(1024*1024):.1f}MB"
    else:
        size_str = "---"

    # Truncate URL for display
    display_url = url
    if len(display_url) > 80:
        display_url = display_url[:77] + "..."

    print(f"      {CYAN}→{RESET} {method:4} {status_str:3} {duration_str:>8} {size_str:>8} {display_url}")


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
            print(f"    [{i}/{len(queries)}] Searching: {query:<50}", end='', flush=True)
            try:
                results = await google_search(client, query, num=10)

                found_new = 0
                for item in results:
                    name = item.get("title", "")
                    domain = extract_domain(item.get("link", ""))

                    # Filter: only local dealerships, no aggregators/manufacturers
                    if not is_local_dealership(domain, name):
                        continue

                    dealership = {
                        "name": name,
                        "website": domain,
                        "snippet": item.get("snippet", ""),
                        "found_at": datetime.now().isoformat(),
                    }

                    # Deduplicate by website
                    if dealership["website"] and not any(d["website"] == dealership["website"] for d in dealerships):
                        dealerships.append(dealership)
                        found_new += 1

                # Show result on same line
                if not VERBOSE:
                    print(f" → {found_new} new, {len(dealerships)} total")
                else:
                    print(f"\n        ✓ {found_new} new dealers, {len(dealerships)} total")

            except Exception as e:
                if not VERBOSE:
                    print(f" → Error: {str(e)[:40]}")
                else:
                    print(f"\n        ✗ Search failed: {e}")
                continue

    print(f"\n  ✓ Found {len(dealerships)} unique dealerships")

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
    # Build query with site restriction if needed
    if site:
        # Use site: operator at the end of query
        full_query = f"{query} site:{site}"
    else:
        full_query = query

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": full_query,
        "num": min(num, 10),  # API limit is 10 per request
    }

    start_time = time.time()
    response = await client.get(GOOGLE_SEARCH_URL, params=params)
    duration = time.time() - start_time

    # Check for errors and provide helpful messages
    if response.status_code == 400:
        error_data = response.json() if response.content else {}
        error_msg = error_data.get("error", {}).get("message", "Unknown error")

        if VERBOSE:
            print(f"\n        ✗ Google API 400 error: {error_msg}")
            print(f"        Query: {full_query}")
            if site:
                print(f"        Site: {site}")

        # Return empty results instead of raising error
        return []

    response.raise_for_status()

    data = response.json()
    result_count = len(data.get("items", []))

    log_request(
        "GET",
        f"{GOOGLE_SEARCH_URL}?q={full_query[:50]}..." if site else f"{GOOGLE_SEARCH_URL}?q={query[:50]}...",
        duration,
        response.status_code,
        len(response.content)
    )

    if VERBOSE and result_count > 0:
        print(f"        ✓ Found {result_count} results")

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


def is_local_dealership(domain: str, name: str) -> bool:
    """
    Filter to keep only LOCAL dealerships, excluding aggregators and manufacturer sites.

    Args:
        domain: Website domain (e.g., "carwisegurnee.com")
        name: Dealership name from search result

    Returns:
        True if this is a local dealership, False if it's an aggregator/manufacturer
    """
    if not domain:
        return False

    text = (domain + " " + name).lower()

    # Exclude aggregators
    aggregators = [
        "cars.com", "autotrader.com", "carmax.com", "carvana.com",
        "truecar.com", "edmunds.com", "kbb.com", "carfax.com",
        "cargurus.com", "vroom.com", "shift.com", "autotempest.com",
        "carbuyingtips.com"
    ]

    if any(agg in domain for agg in aggregators):
        return False

    # Exclude manufacturer websites
    manufacturers = [
        "toyota.com", "honda.com", "ford.com", "chevrolet.com",
        "nissan.com", "hyundai.com", "kia.com", "subaru.com",
        "mazda.com", "volkswagen.com", "gm.com", "bmw.com",
        "mercedes-benz.com", "lexus.com", "acura.com"
    ]

    if any(mfr in domain for mfr in manufacturers):
        return False

    # Exclude general directories/listings
    directories = [
        "yelp.com", "google.com", "facebook.com", "yellowpages.com",
        "mapquest.com", "dealerrater.com"
    ]

    if any(directory in domain for directory in directories):
        return False

    # If it's a local-sounding domain (contains city name or dealership keywords), keep it
    local_keywords = ["dealer", "dealership", "auto", "motor", "car"]

    return any(keyword in text for keyword in local_keywords)


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

def is_inventory_page(title: str, snippet: str) -> bool:
    """
    Filter out non-inventory pages based on title and snippet.

    Args:
        title: Page title from Google search
        snippet: Page snippet from Google search

    Returns:
        True if page likely contains vehicle inventory
    """
    text = (title + " " + snippet).lower()

    # Skip pages that are clearly not inventory
    skip_keywords = [
        "about us", "about our", "contact",  "financing", "finance application",
        "service", "service center", "hours", "directions", "location",
        "careers", "employment", "reviews", "testimonials", "meet the team",
        "warranty", "parts", "accessories", "specials disclaimer"
    ]

    if any(keyword in text for keyword in skip_keywords):
        return False

    # Keep pages that likely have inventory
    keep_keywords = [
        "inventory", "vehicles", "cars", "used", "certified",
        "$", "price", "for sale", "stock", "available"
    ]

    return any(keyword in text for keyword in keep_keywords)


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
        for idx, dealership in enumerate(dealerships, 1):
            website = dealership.get("website")
            if not website:
                continue

            dealer_name = dealership["name"]
            dealer_pages_before = len(pages)

            print(f"    [{idx}/{len(dealerships)}] {dealer_name:<40}", end='', flush=True)

            # Use ALL search terms, no limit
            search_results_count = 0
            for term in search_terms:
                try:
                    # Try site-specific search first
                    results = await google_search(client, term, num=10, site=website)

                    # If no results with site restriction, try general search and filter
                    if not results:
                        results = await google_search(client, f"{term} {website}", num=10, site=None)
                        # Filter results to only include this website
                        results = [r for r in results if website in r.get("link", "")]

                    search_results_count += len(results)

                    for item in results:
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        url = item.get("link", "")

                        # Filter out non-inventory pages
                        if not is_inventory_page(title, snippet):
                            if VERBOSE:
                                print(f"\n        ✗ Filtered: {title[:60]}")
                            continue

                        page = {
                            "url": url,
                            "title": title,
                            "snippet": snippet,
                            "dealership": dealership["name"],
                            "dealership_site": website,
                        }

                        # Deduplicate by URL
                        if page["url"] and not any(p["url"] == page["url"] for p in pages):
                            pages.append(page)
                            if VERBOSE:
                                print(f"\n        ✓ Added: {title[:60]}")

                except Exception as e:
                    if VERBOSE:
                        print(f"\n        ✗ Search error for '{term}': {e}")
                    continue  # Skip on error, continue with next

            # Show result for this dealer
            dealer_pages_found = len(pages) - dealer_pages_before
            if dealer_pages_found > 0:
                print(f" → {dealer_pages_found} pages ({len(pages)} total)")
            else:
                # Show why we got 0 pages
                if search_results_count == 0:
                    print(f" → 0 results from Google")
                else:
                    print(f" → {search_results_count} results, 0 passed filter")

    print(f"\n  ✓ Found {len(pages)} inventory pages total")
    return pages


# ============================================================================
# STAGE 3: Parse with Gemini
# ============================================================================

async def parse_inventory_pages(config: AppConfig, pages: List[Dict]) -> List[RawCarData]:
    """
    Stage 3: Fetch page content and extract vehicle data using Gemini.

    Uses batch processing: groups pages by dealership and processes 8 pages
    at a time in a single Gemini request for efficiency.

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

    print(f"  Parsing {len(pages)} pages with Gemini (batched processing)...")

    # Group pages by dealership
    by_dealer = {}
    for page in pages:
        dealer_site = page['dealership_site']
        by_dealer.setdefault(dealer_site, []).append(page)

    # Create batches of 8 pages each
    all_batches = []
    for dealer_site, dealer_pages in by_dealer.items():
        # Split dealer pages into batches of 8
        for i in range(0, len(dealer_pages), 8):
            batch = dealer_pages[i:i+8]
            all_batches.append(batch)

    print(f"  Created {len(all_batches)} batches from {len(by_dealer)} dealerships")

    vehicles = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for batch_num, batch in enumerate(all_batches, 1):
            dealer_name = batch[0]['dealership']
            print(f"    [{batch_num}/{len(all_batches)}] {dealer_name:<35} ({len(batch)} pages)", end='', flush=True)

            try:
                # Process batch with combined Gemini request
                batch_vehicles = await parse_batch_with_gemini(client, batch, config)
                vehicles.extend(batch_vehicles)

                if not VERBOSE:
                    print(f" → {len(batch_vehicles)} vehicles ({len(vehicles)} total)")
                else:
                    print(f"\n        ✓ Found {len(batch_vehicles)} vehicles, {len(vehicles)} total")

                # Rate limiting: 4 seconds between batches (15 RPM)
                if batch_num < len(all_batches):
                    import asyncio
                    if VERBOSE:
                        print(f"        → Waiting 4s for rate limit...")
                    await asyncio.sleep(4)

            except Exception as e:
                if not VERBOSE:
                    print(f" → Error: {str(e)[:40]}")
                else:
                    print(f"\n        ✗ Error: {e}")
                continue

    print(f"\n  ✓ Extracted {len(vehicles)} vehicles total")
    return vehicles


async def fetch_page_content(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Fetch HTML content from URL."""
    try:
        start_time = time.time()
        response = await client.get(url, follow_redirects=True)
        duration = time.time() - start_time

        response.raise_for_status()

        log_request(
            "GET",
            url,
            duration,
            response.status_code,
            len(response.content)
        )

        return response.text
    except Exception as e:
        if VERBOSE:
            print(f"        ✗ Failed to fetch {url[:60]}... ({e})")
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

    # Truncate to 10000 chars per page (for batching)
    return text[:10000]


async def parse_batch_with_gemini(client: httpx.AsyncClient, batch: List[Dict], config: AppConfig) -> List[RawCarData]:
    """
    Process a batch of pages with a single Gemini request.

    Fetches HTML from multiple pages, combines them, and sends one request
    to Gemini for extraction. More efficient than individual requests.

    Args:
        client: HTTP client
        batch: List of page dicts to process together
        config: App configuration

    Returns:
        List of raw vehicle data from all pages in batch
    """
    # Fetch and combine page content
    combined_text = ""
    dealer_name = batch[0]['dealership']
    dealer_site = batch[0]['dealership_site']

    for i, page in enumerate(batch, 1):
        try:
            html = await fetch_page_content(client, page["url"])
            if not html:
                continue

            text = extract_text_from_html(html)
            if len(text) < 100:
                continue

            # Add page separator
            combined_text += f"\n\n{'='*60}\nPAGE {i}: {page['url']}\n{'='*60}\n{text}\n"

        except Exception as e:
            print(f"        Warning: Failed to fetch page {i}: {e}")
            continue

    if not combined_text:
        return []

    # Build combined prompt
    prompt = f"""
Extract ALL vehicle listings from these {len(batch)} car dealership webpages.

Dealership: {dealer_name}
Website: {dealer_site}

IMPORTANT: Process ALL pages and return ALL vehicles found across all pages in a SINGLE combined array.

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
- Process ALL pages below and combine results
- Only include vehicles with year, make, model, and price
- Set mileage to null for new cars if not listed
- If no vehicles found in ANY page, return {{"vehicles": []}}

Combined page content:
{combined_text}
"""

    try:
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.8,
                "maxOutputTokens": 8192  # Increased for batch results
            }
        }

        start_time = time.time()
        response = await client.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60.0  # Longer timeout for batch
        )
        duration = time.time() - start_time

        response.raise_for_status()
        data = response.json()

        log_request(
            "POST",
            f"Gemini API (batch of {len(batch)} pages)",
            duration,
            response.status_code,
            len(response.content)
        )

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
                    distance_miles=0.0,
                    dealer_name=dealer_name,
                    dealer_url=batch[0]["url"],  # Use first page URL
                    dealer_phone=None,
                    thumbnail_url=None
                )

                if vehicle.year and vehicle.make and vehicle.model and vehicle.price:
                    vehicles.append(vehicle)

            except Exception as e:
                continue

        return vehicles

    except Exception as e:
        print(f"        Gemini batch parse error: {e}")
        return []


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
