#!/usr/bin/env python3
"""
Demo: HTTP Request Logging

This script demonstrates what the verbose logging looks like
without actually making real API calls.

Run: python demo_logging.py
"""

import time
import random

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def log_request(method, url, duration, status, size):
    """Demo request logger."""
    # Format duration
    if duration < 1:
        duration_str = f"{duration*1000:.0f}ms"
    else:
        duration_str = f"{duration:.2f}s"

    # Status color
    if status < 300:
        status_color = GREEN
    elif status < 400:
        status_color = YELLOW
    else:
        status_color = RED
    status_str = f"{status_color}{status}{RESET}"

    # Size formatting
    if size < 1024:
        size_str = f"{size}B"
    elif size < 1024 * 1024:
        size_str = f"{size/1024:.1f}KB"
    else:
        size_str = f"{size/(1024*1024):.1f}MB"

    # Truncate URL
    display_url = url
    if len(display_url) > 80:
        display_url = display_url[:77] + "..."

    print(f"      {CYAN}→{RESET} {method:4} {status_str:3} {duration_str:>8} {size_str:>8} {display_url}")

def demo_stage1():
    """Demo Stage 1: Finding Dealerships."""
    print(f"\n{BOLD}[1/4]{RESET} {CYAN}Finding Dealerships{RESET}")

    searches = [
        "car dealership Gurnee IL",
        "used cars Gurnee IL",
        "Toyota dealer Gurnee IL",
        "Honda dealer Waukegan IL"
    ]

    for i, query in enumerate(searches, 1):
        print(f"    [{i}/{len(searches)}] Searching: {query}")
        time.sleep(0.1)  # Simulate work

        # Simulate Google Search request
        duration = random.uniform(0.5, 1.5)
        log_request(
            "GET",
            f"https://www.googleapis.com/customsearch/v1?q={query}",
            duration,
            200,
            random.randint(10000, 20000)
        )

        print(f"        ✓ Found {random.randint(8, 10)} results")

    print(f"{GREEN}✓{RESET} Completed in 1m 23s")

def demo_stage2():
    """Demo Stage 2: Searching Inventory."""
    print(f"\n{BOLD}[2/4]{RESET} {CYAN}Searching Inventory Pages{RESET}")

    dealers = [
        "CarWise Gurnee",
        "Woody Buick GMC",
        "Gillespie Ford"
    ]

    for i, dealer in enumerate(dealers, 1):
        print(f"    [{i}/{len(dealers)}] Searching inventory for: {dealer}")
        time.sleep(0.1)

        # Simulate Google Search
        duration = random.uniform(0.8, 1.2)
        log_request(
            "GET",
            "https://www.googleapis.com/customsearch/v1?q=used+cars+inventory",
            duration,
            200,
            random.randint(15000, 25000)
        )

        print(f"        ✓ Found {random.randint(5, 10)} pages")

    print(f"{GREEN}✓{RESET} Completed in 2m 41s")

def demo_stage3():
    """Demo Stage 3: Parsing with Gemini."""
    print(f"\n{BOLD}[3/4]{RESET} {CYAN}Parsing with Gemini AI{RESET}")

    batches = [
        ("CarWise Gurnee", 8),
        ("Woody Buick GMC", 8),
        ("Gillespie Ford", 6)
    ]

    for i, (dealer, pages) in enumerate(batches, 1):
        print(f"    [{i}/{len(batches)}] Processing {dealer} ({pages} pages)...")

        # Simulate page fetches
        for j in range(min(pages, 3)):  # Show first 3
            time.sleep(0.05)
            duration = random.uniform(0.3, 0.8)
            log_request(
                "GET",
                f"https://www.{dealer.lower().replace(' ', '')}.com/used-vehicles/page-{j+1}/",
                duration,
                200,
                random.randint(80000, 150000)
            )

        if pages > 3:
            print(f"        ... fetched {pages-3} more pages")

        # Simulate Gemini API call
        time.sleep(0.2)
        duration = random.uniform(8.0, 15.0)
        log_request(
            "POST",
            f"Gemini API (batch of {pages} pages)",
            duration,
            200,
            random.randint(40000, 60000)
        )

        vehicles = random.randint(15, 35)
        print(f"        ✓ Found {vehicles} vehicles")

        if i < len(batches):
            print(f"        (waiting 4s for rate limit...)")
            time.sleep(0.3)

    print(f"{GREEN}✓{RESET} Completed in 7m 18s")

def demo_stage4():
    """Demo Stage 4: Final Processing."""
    print(f"\n{BOLD}[4/4]{RESET} {CYAN}Final Processing & Deduplication{RESET}")
    time.sleep(0.2)
    print(f"{GREEN}✓{RESET} Completed in 1.8s")

def demo_summary():
    """Demo completion summary."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{'COMPLETION SUMMARY'.center(80)}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

    print(f"{BOLD}Timing Breakdown:{RESET}")
    stages = [
        ("Stage 1", 83, 11.8),
        ("Stage 2", 161, 22.9),
        ("Stage 3", 438, 62.4),
        ("Stage 4", 2, 2.9)
    ]

    for name, seconds, percent in stages:
        if seconds < 60:
            time_str = f"{seconds}s"
        else:
            mins = seconds // 60
            secs = seconds % 60
            time_str = f"{mins}m {secs}s"
        print(f"  {name:.<30} {time_str:>10} ({percent:.1f}%)")

    print(f"  {'─' * 45}")
    print(f"  {BOLD}Total:{RESET:.<30} {BOLD}11m 24s{RESET}")
    print()

    print(f"{GREEN}✓{RESET} Generated inventory with 52 vehicles")
    print(f"{YELLOW}ℹ{RESET} Saved to: data/inventory.json")
    print()

    print(f"{BOLD}Quick Stats:{RESET}")
    print(f"  Vehicles: 52")
    print(f"  Avg Price: $20,236")
    print(f"  Price Range: $11,333 - $24,056")
    print()

    print(f"{YELLOW}ℹ{RESET} To view the site locally, run:")
    print(f"  cd site && npm run dev")
    print()

def main():
    """Run demo."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{'AutoFinder - Demo Logging'.center(80)}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print()
    print(f"{YELLOW}ℹ{RESET} This is a demo showing what the verbose logging looks like.")
    print(f"{YELLOW}ℹ{RESET} No real API calls are being made.")
    print()
    print(f"{BOLD}Legend:{RESET}")
    print(f"  → METHOD {GREEN}STATUS{RESET}  {BOLD}TIME{RESET}     {BOLD}SIZE{RESET}   URL")
    print()

    demo_stage1()
    demo_stage2()
    demo_stage3()
    demo_stage4()
    demo_summary()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{RED}✗{RESET} Interrupted by user")
