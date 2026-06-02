#!/usr/bin/env python3
"""
Cinema City Date Watcher - API-based approach (lightweight, no browser needed).
Directly queries Cinema City's API endpoints for available dates.
This is the preferred method - faster and lighter than Selenium.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

# --- Configuration ---
CONFIG = {
    "check_interval_minutes": 5,
    "screenshot_dir": os.path.expanduser("~/CinemaCityWatcher"),
    "state_file": os.path.expanduser("~/CinemaCityWatcher/last_dates.json"),
    # Cinema City API endpoints (may need adjustment based on site updates)
    "base_url": "https://www.cinema-city.co.il",
    "api_base": "https://www.cinema-city.co.il/api",
    # Rishon LeZion cinema ID (common IDs: 1072 for Rishon, check via API)
    "cinema_id": "1072",
    "cinema_name": "ראשון לציון",
    "movie_name": "אובססיה",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
    "Referer": "https://www.cinema-city.co.il/",
    "Origin": "https://www.cinema-city.co.il",
}


def setup_directories():
    Path(CONFIG["screenshot_dir"]).mkdir(parents=True, exist_ok=True)


def send_notification(title, message):
    """Send notification via Termux:API."""
    try:
        subprocess.run(
            [
                "termux-notification",
                "--title", title,
                "--content", message,
                "--priority", "high",
                "--vibrate", "500,200,500",
                "--led-color", "ff0000",
                "--sound",
            ],
            check=True,
            timeout=10,
        )
        print(f"[NOTIFICATION] {title}: {message}")
    except FileNotFoundError:
        print("[WARNING] termux-notification not found.")
        print(f"  -> {title}: {message}")
    except subprocess.TimeoutExpired:
        print("[WARNING] Notification timed out")


def send_vibrate():
    try:
        subprocess.run(["termux-vibrate", "-d", "1000"], timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def load_previous_dates():
    try:
        with open(CONFIG["state_file"], "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("dates", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_dates(dates):
    with open(CONFIG["state_file"], "w", encoding="utf-8") as f:
        json.dump({
            "dates": list(dates),
            "last_check": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)


def save_response_data(data, reason="check"):
    """Save API response as JSON for debugging."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_response_{reason}_{timestamp}.json"
    filepath = os.path.join(CONFIG["screenshot_dir"], filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {filepath}")
    return filepath


def discover_api_endpoints(session):
    """
    Try to discover the Cinema City API structure.
    Cinema City Israel typically uses these patterns:
    - /api/cinemas - list of cinemas
    - /api/movies - list of movies
    - /api/screenings - available screenings with dates
    """
    endpoints_to_try = [
        "/api/cinemas",
        "/api/theaters",
        "/api/movies",
        "/api/films",
        "/api/screenings",
        "/api/shows",
        "/api/schedule",
        "/api/dates",
        "/apiext/visually/getcinemas",
        "/apiext/visually/getmovies",
        "/apiext/visually/getscreenings",
        "/he/api/cinemas",
        "/he/api/movies",
    ]

    print("  Discovering API endpoints...")
    discovered = {}
    for endpoint in endpoints_to_try:
        try:
            url = CONFIG["base_url"] + endpoint
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    discovered[endpoint] = data
                    print(f"    [OK] {endpoint} -> {type(data).__name__}")
                except ValueError:
                    if len(resp.text) < 5000:
                        print(f"    [HTML] {endpoint} -> not JSON")
            else:
                pass  # silently skip 404s
        except requests.RequestException:
            pass

    return discovered


def get_dates_from_website(session):
    """
    Fetch dates by parsing the Cinema City website.
    Strategy: Load the page, find embedded JSON data or API calls.
    """
    dates = set()

    # Strategy 1: Try known API patterns
    api_urls = [
        f"{CONFIG['api_base']}/screenings?cinema={CONFIG['cinema_id']}",
        f"{CONFIG['api_base']}/shows?cinemaId={CONFIG['cinema_id']}",
        f"{CONFIG['base_url']}/apiext/visually/getscreenings?cinemaId={CONFIG['cinema_id']}",
        f"{CONFIG['base_url']}/api/schedule/{CONFIG['cinema_id']}",
    ]

    for url in api_urls:
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # Try to extract dates from response
                    extracted = extract_dates_from_json(data)
                    if extracted:
                        dates.update(extracted)
                        print(f"    [API] Found {len(extracted)} dates from {url}")
                        return dates
                except ValueError:
                    pass
        except requests.RequestException:
            continue

    # Strategy 2: Parse the HTML page for embedded data
    try:
        page_url = f"{CONFIG['base_url']}/tickets"
        resp = session.get(page_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            # Look for embedded JSON data (common in React/Next.js sites)
            import re

            # Find __NEXT_DATA__ or similar embedded state
            patterns = [
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.__DATA__\s*=\s*({.*?});',
                r'"dates"\s*:\s*\[(.*?)\]',
                r'"screeningDates"\s*:\s*\[(.*?)\]',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    for match in matches:
                        try:
                            data = json.loads(match) if match.startswith('{') else None
                            if data:
                                extracted = extract_dates_from_json(data)
                                if extracted:
                                    dates.update(extracted)
                        except (json.JSONDecodeError, TypeError):
                            # Try to extract date patterns directly
                            date_pattern = r'\d{2}/\d{2}/\d{4}'
                            found_dates = re.findall(date_pattern, match)
                            dates.update(found_dates)

            # Also look for date patterns in the entire HTML
            if not dates:
                date_pattern = r'יום [א-ש]{1,2} \d{2}/\d{2}/\d{4}'
                found = re.findall(date_pattern, html)
                dates.update(found)

    except requests.RequestException as e:
        print(f"    [ERROR] Failed to fetch page: {e}")

    return dates


def extract_dates_from_json(data, movie_filter=None):
    """Recursively extract date-like values from JSON response."""
    dates = set()

    if isinstance(data, dict):
        for key, value in data.items():
            if any(d in key.lower() for d in ["date", "day", "screen", "show"]):
                if isinstance(value, str) and ("/" in value or "-" in value):
                    dates.add(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            dates.add(item)
                        elif isinstance(item, dict):
                            dates.update(extract_dates_from_json(item))
            elif isinstance(value, (dict, list)):
                dates.update(extract_dates_from_json(value))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                dates.update(extract_dates_from_json(item))
            elif isinstance(item, str) and ("/" in item or "-" in item):
                dates.add(item)

    return dates


def run_check():
    """Run a single check cycle."""
    session = requests.Session()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking Cinema City dates...")

    current_dates = get_dates_from_website(session)

    if not current_dates:
        print("  [WARNING] No dates found via API. Trying endpoint discovery...")
        discovered = discover_api_endpoints(session)
        if discovered:
            save_response_data(discovered, "discovery")
            print("  Discovered endpoints saved. Check the JSON file to identify correct API.")
        else:
            print("  No endpoints discovered. The Selenium version may be needed.")
        return

    previous_dates = load_previous_dates()
    print(f"  Previous: {previous_dates or 'None (first run)'}")
    print(f"  Current:  {current_dates}")

    new_dates = current_dates - previous_dates

    if previous_dates and new_dates:
        print(f"\n  *** NEW DATES FOUND: {new_dates} ***")
        save_response_data({"new_dates": list(new_dates), "all_dates": list(current_dates)}, "new_date_found")
        send_vibrate()
        send_notification(
            "Cinema City - תאריך חדש!",
            f"תאריכים חדשים: {', '.join(new_dates)}"
        )
    elif not previous_dates:
        print("  First run - saving initial state.")
    else:
        print("  No changes detected.")

    save_dates(current_dates)


def main():
    setup_directories()
    interval = CONFIG["check_interval_minutes"] * 60

    print("=" * 60)
    print("  Cinema City Date Watcher (API Mode)")
    print("=" * 60)
    print(f"  Cinema: {CONFIG['cinema_name']} (ID: {CONFIG['cinema_id']})")
    print(f"  Movie:  {CONFIG['movie_name']}")
    print(f"  Check:  Every {CONFIG['check_interval_minutes']} min")
    print(f"  Output: {CONFIG['screenshot_dir']}")
    print("=" * 60)

    send_notification("Cinema Watcher Started", "API mode - monitoring dates...")

    while True:
        try:
            run_check()
            print(f"\n  Next check in {CONFIG['check_interval_minutes']} min...")
            print("-" * 40)
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[STOPPED] Watcher stopped.")
            break


if __name__ == "__main__":
    main()
