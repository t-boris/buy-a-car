"""
AI-powered meta search using Gemini API for vehicle discovery.

This module uses AI to intelligently search for vehicle listings
across the web near a specified location.
"""

import os
import json
from typing import List, Optional
import httpx
from models import RawCarData, AppConfig


# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"


async def search_vehicles(config: AppConfig) -> List[RawCarData]:
    """
    Use Gemini AI to search for vehicle listings near the configured location.

    The AI is given a structured prompt to find dealership inventory
    and return results in a parseable format.

    Args:
        config: Application configuration with search parameters

    Returns:
        List of raw vehicle data discovered by AI
    """
    if not GEMINI_API_KEY:
        print("  Warning: GEMINI_API_KEY not set, skipping AI meta search")
        return []

    # Build search prompt
    prompt = build_search_prompt(config)

    try:
        # Call Gemini API
        response = await call_gemini_api(prompt)

        # Parse response into RawCarData
        vehicles = parse_gemini_response(response, config)

        return vehicles

    except Exception as e:
        print(f"  AI search error: {e}")
        return []


def build_search_prompt(config: AppConfig) -> str:
    """
    Build a structured prompt for the AI to find vehicles.

    Args:
        config: Application configuration

    Returns:
        Prompt string for Gemini
    """
    makes_list = ", ".join(config.filters.include_makes) if config.filters.include_makes else "any make"

    prompt = f"""
You are a vehicle inventory search assistant. Your task is to find car dealership listings near ZIP code {config.zip} within {config.radius_miles} miles.

Search criteria:
- Location: ZIP {config.zip}, radius {config.radius_miles} miles
- Makes: {makes_list}
- Min year: {config.filters.min_year}
- Max mileage: {config.filters.max_mileage}
- Conditions: {', '.join(config.filters.allowed_conditions)}

Please search for currently available vehicle listings that match these criteria.
For each vehicle found, provide the following information in JSON format:

{{
  "vehicles": [
    {{
      "vin": "Vehicle VIN if available",
      "year": 2020,
      "make": "Honda",
      "model": "Accord",
      "trim": "EX-L",
      "condition": "used",
      "price": 22990,
      "mileage": 45000,
      "dealer_name": "Dealer Name",
      "dealer_url": "https://dealer-site.com/vehicle-page",
      "dealer_phone": "+1-XXX-XXX-XXXX",
      "thumbnail_url": "image URL if available"
    }}
  ]
}}

Return ONLY valid JSON, no additional text.
If you cannot find specific listings, return an empty vehicles array.
"""

    return prompt


async def call_gemini_api(prompt: str) -> dict:
    """
    Make API call to Gemini.

    Args:
        prompt: The prompt to send

    Returns:
        API response as dictionary

    Raises:
        httpx.HTTPError: If API call fails
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for factual responses
                "topK": 20,
                "topP": 0.8,
                "maxOutputTokens": 2048
            }
        }

        response = await client.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()
        return response.json()


def parse_gemini_response(response: dict, config: AppConfig) -> List[RawCarData]:
    """
    Parse Gemini API response into RawCarData objects.

    Args:
        response: API response dictionary
        config: Application configuration for defaults

    Returns:
        List of raw vehicle data
    """
    vehicles: List[RawCarData] = []

    try:
        # Extract text from response
        candidates = response.get("candidates", [])
        if not candidates:
            return vehicles

        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        # Try to parse as JSON
        # Sometimes the AI wraps in markdown code blocks, so we need to extract
        text_content = text_content.strip()
        if text_content.startswith("```json"):
            text_content = text_content[7:]  # Remove ```json
        if text_content.startswith("```"):
            text_content = text_content[3:]  # Remove ```
        if text_content.endswith("```"):
            text_content = text_content[:-3]  # Remove trailing ```

        data = json.loads(text_content.strip())

        # Parse vehicles
        for item in data.get("vehicles", []):
            try:
                raw_car = RawCarData(
                    vin=item.get("vin"),
                    source="ai-meta-search",
                    year=item.get("year"),
                    make=item.get("make"),
                    model=item.get("model"),
                    trim=item.get("trim"),
                    condition=item.get("condition"),
                    price=item.get("price"),
                    mileage=item.get("mileage"),
                    distance_miles=0.0,  # Would need geocoding for accurate distance
                    dealer_name=item.get("dealer_name"),
                    dealer_phone=item.get("dealer_phone"),
                    dealer_url=item.get("dealer_url"),
                    thumbnail_url=item.get("thumbnail_url")
                )

                # Basic validation
                if raw_car.year and raw_car.make and raw_car.model and raw_car.price and raw_car.dealer_url:
                    vehicles.append(raw_car)

            except Exception as e:
                print(f"    Warning: Failed to parse vehicle item: {e}")
                continue

    except json.JSONDecodeError as e:
        print(f"    Warning: Failed to parse AI response as JSON: {e}")
    except Exception as e:
        print(f"    Warning: Error parsing AI response: {e}")

    return vehicles


# ============================================================================
# Mock implementation for testing without API key
# ============================================================================

def get_mock_ai_results(config: AppConfig) -> List[RawCarData]:
    """
    Generate mock AI search results for testing.

    Args:
        config: Application configuration

    Returns:
        Mock vehicle data
    """
    return [
        RawCarData(
            vin="1HGCM82633A123456",
            source="ai-meta-search",
            year=2020,
            make="Honda",
            model="Accord",
            trim="Sport",
            condition="used",
            price=21990,
            mileage=38000,
            distance_miles=15.2,
            dealer_name="AutoNation Honda",
            dealer_phone="+1-847-555-0100",
            dealer_url="https://example-autonation.com/inventory/123",
            thumbnail_url="https://example.com/accord.jpg"
        )
    ]
