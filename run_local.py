#!/usr/bin/env python3
"""
Local AutoFinder Runner

Run this script locally to fetch vehicle inventory with detailed logging.
Shows all HTTP requests, timings, and progress in real-time.

Usage:
    python run_local.py              # Run all stages
    python run_local.py --stage 1    # Run only stage 1
    python run_local.py --stage 2-4  # Run stages 2 through 4
    python run_local.py --verbose    # Enable verbose logging
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text):
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_step(step_num, total_steps, text):
    """Print a step indicator."""
    print(f"{Colors.BOLD}[{step_num}/{total_steps}]{Colors.END} {Colors.CYAN}{text}{Colors.END}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ{Colors.END} {text}")

def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"

def check_env_vars():
    """Check if required environment variables are set."""
    import os

    required_vars = {
        'GOOGLE_API_KEY': 'Google Custom Search API key',
        'GOOGLE_CSE_ID': 'Google Custom Search Engine ID',
        'GEMINI_API_KEY': 'Gemini API key'
    }

    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  • {var} ({desc})")

    if missing:
        print_error("Missing required environment variables:")
        for var in missing:
            print(var)
        print("\nSet them with:")
        print("  export GOOGLE_API_KEY='your-key-here'")
        print("  export GOOGLE_CSE_ID='your-cse-id-here'")
        print("  export GEMINI_API_KEY='your-key-here'")
        return False

    return True

async def run_stage(stage_num, stage_name, script_path):
    """Run a stage and return timing info."""
    print_step(stage_num, 4, f"{stage_name}")

    start_time = time.time()

    # Import and run the stage
    sys.path.insert(0, str(Path(script_path).parent))

    if stage_num == 1:
        from stage1_dealerships import main as stage_main
    elif stage_num == 2:
        from stage2_inventory import main as stage_main
    elif stage_num == 3:
        from stage3_parse import main as stage_main
    else:
        from fetch import main as stage_main

    try:
        result = await stage_main()
        elapsed = time.time() - start_time
        print_success(f"Completed in {format_duration(elapsed)}")
        return elapsed, result
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Failed after {format_duration(elapsed)}: {e}")
        raise

async def main(start_stage=1, end_stage=4):
    """Main execution."""
    print_header("AutoFinder Local Runner")

    # Check environment variables
    if not check_env_vars():
        sys.exit(1)

    # Show configuration
    config_path = Path(__file__).parent / "config" / "app.config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)

    print_info(f"Location: ZIP {config['zip']}, Radius: {config['radius_miles']} miles")
    print_info(f"Makes: {', '.join(config['filters']['include_makes'])}")
    print_info(f"Budget: ${config['max_down_payment']} down, ${config['max_monthly_payment']}/mo")

    if start_stage > 1 or end_stage < 4:
        print_info(f"Running stages {start_stage} to {end_stage} only")
    print()

    # Track overall timing
    total_start = time.time()
    timings = {}

    # Define all stages
    stages = [
        (1, "Finding Dealerships", Path(__file__).parent / "scripts" / "stage1_dealerships.py"),
        (2, "Searching Inventory Pages", Path(__file__).parent / "scripts" / "stage2_inventory.py"),
        (3, "Parsing with Gemini AI", Path(__file__).parent / "scripts" / "stage3_parse.py"),
        (4, "Final Processing & Deduplication", Path(__file__).parent / "scripts" / "fetch.py"),
    ]

    try:
        # Run selected stages
        for stage_num, stage_name, script_path in stages:
            if start_stage <= stage_num <= end_stage:
                elapsed, count = await run_stage(stage_num, stage_name, script_path)
                timings[f'Stage {stage_num}'] = elapsed
                print()

        # Summary
        total_elapsed = time.time() - total_start

        print_header("COMPLETION SUMMARY")

        print(f"{Colors.BOLD}Timing Breakdown:{Colors.END}")
        for stage, duration in timings.items():
            percent = (duration / total_elapsed) * 100
            print(f"  {stage:.<30} {format_duration(duration):>10} ({percent:.1f}%)")
        print(f"  {'─' * 45}")
        print(f"  {Colors.BOLD}Total:{Colors.END:.<30} {Colors.BOLD}{format_duration(total_elapsed):>10}{Colors.END}")
        print()

        # Show output files
        data_dir = Path(__file__).parent / "data"
        inventory_file = data_dir / "inventory.json"

        if inventory_file.exists():
            with open(inventory_file, 'r') as f:
                inventory = json.load(f)

            vehicle_count = len(inventory['items'])
            print_success(f"Generated inventory with {vehicle_count} vehicles")
            print_info(f"Saved to: {inventory_file}")
            print()

            # Show quick stats
            if vehicle_count > 0:
                prices = [v['price'] for v in inventory['items']]
                print(f"{Colors.BOLD}Quick Stats:{Colors.END}")
                print(f"  Vehicles: {vehicle_count}")
                print(f"  Avg Price: ${sum(prices) / len(prices):,.0f}")
                print(f"  Price Range: ${min(prices):,.0f} - ${max(prices):,.0f}")
                print()

        print_info("To view the site locally, run:")
        print(f"  cd site && npm run dev")
        print()

    except KeyboardInterrupt:
        print()
        print_error("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def parse_stage_arg(stage_arg):
    """Parse stage argument (e.g., '2', '2-4')."""
    if '-' in stage_arg:
        start, end = stage_arg.split('-')
        return int(start), int(end)
    else:
        stage = int(stage_arg)
        return stage, stage


if __name__ == "__main__":
    import os

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='AutoFinder Local Runner - Fetch vehicle inventory with detailed logging',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_local.py              # Run all stages (1-4)
  python run_local.py --stage 1    # Run only stage 1
  python run_local.py --stage 2-4  # Run stages 2 through 4
  python run_local.py --stage 3    # Run only stage 3
        """
    )
    parser.add_argument(
        '--stage',
        type=str,
        help='Stage(s) to run: single number (e.g., "3") or range (e.g., "2-4")'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (shows all HTTP requests)'
    )

    args = parser.parse_args()

    # Parse stage range
    start_stage, end_stage = 1, 4
    if args.stage:
        try:
            start_stage, end_stage = parse_stage_arg(args.stage)
            if not (1 <= start_stage <= 4) or not (1 <= end_stage <= 4) or start_stage > end_stage:
                print_error("Stage must be between 1-4")
                sys.exit(1)
        except ValueError:
            print_error("Invalid stage format. Use: --stage 3 or --stage 2-4")
            sys.exit(1)

    # Enable verbose logging for HTTP requests
    if args.verbose:
        os.environ['AUTOFINDER_VERBOSE'] = '1'

    try:
        asyncio.run(main(start_stage, end_stage))
    except KeyboardInterrupt:
        print()
        sys.exit(0)
