#!/usr/bin/env python3
"""
Cinema City Date Watcher - Interactive Dashboard
Works without Chrome/Selenium - uses HTTP requests only.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ─── Colors ───────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    BG_RED  = "\033[41m"
    BG_GREEN = "\033[42m"


# ─── Configuration ────────────────────────────────────────────
CONFIG_FILE = os.path.expanduser("~/CinemaCityWatcher/config.json")
STATE_FILE = os.path.expanduser("~/CinemaCityWatcher/last_dates.json")
OUTPUT_DIR = os.path.expanduser("~/CinemaCityWatcher")

DEFAULT_CONFIG = {
    "cinema": "ראשון לציון",
    "movie_type": "רגיל",
    "movies": ["אובססיה"],
    "check_interval_minutes": 5,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
    "Referer": "https://www.cinema-city.co.il/",
}


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def send_notification(title, message):
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", message,
             "--priority", "high", "--vibrate", "500,200,500,200,500",
             "--led-color", "ff0000", "--sound"],
            check=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass


def send_vibrate():
    try:
        subprocess.run(["termux-vibrate", "-d", "1500"], timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


# ─── Display ──────────────────────────────────────────────────

def print_header(config):
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════╗
║         🎬  Cinema City Watcher  🎬              ║
╚══════════════════════════════════════════════════╝{C.RESET}
""")
    print(f"  {C.WHITE}Cinema:{C.RESET}   {C.BOLD}{config['cinema']}{C.RESET}")
    print(f"  {C.WHITE}Type:{C.RESET}     {config['movie_type']}")
    print(f"  {C.WHITE}Movies:{C.RESET}   {', '.join(config['movies'])}")
    print(f"  {C.WHITE}Interval:{C.RESET} Every {config['check_interval_minutes']} min")
    print()


def print_status(state, config):
    print(f"  {C.DIM}{'─' * 46}{C.RESET}")
    print(f"  {C.WHITE}{C.BOLD}Current Status:{C.RESET}")
    print()

    if not state:
        print(f"    {C.YELLOW}⏳ Waiting for first check...{C.RESET}")
        return

    last_check = state.get("last_check", "")
    if last_check:
        print(f"    {C.DIM}Last check: {last_check}{C.RESET}")

    print()
    for movie, data in state.get("movies", {}).items():
        dates = data.get("dates", [])
        print(f"    {C.MAGENTA}🎬 {movie}{C.RESET}")
        if dates:
            for d in sorted(dates):
                print(f"       {C.GREEN}📅 {d}{C.RESET}")
        else:
            print(f"       {C.DIM}No dates found{C.RESET}")
        print()

    total_checks = state.get("total_checks", 0)
    changes_found = state.get("changes_found", 0)
    print(f"    {C.DIM}Checks: {total_checks} | Changes: {changes_found}{C.RESET}")


def print_change_alert(movie, new_dates):
    print()
    print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}")
    print(f"  ╔══════════════════════════════════════════════╗")
    print(f"  ║   🚨  NEW DATE FOUND!  🚨                   ║")
    print(f"  ╠══════════════════════════════════════════════╣")
    print(f"  ║   Movie: {movie:<35} ║")
    for d in new_dates:
        print(f"  ║   📅  {d:<38} ║")
    print(f"  ╚══════════════════════════════════════════════╝")
    print(f"  {C.RESET}")
    print()


def print_no_change():
    print(f"\n    {C.GREEN}✓ No changes{C.RESET}")


def print_countdown(seconds_left):
    mins = seconds_left // 60
    secs = seconds_left % 60
    print(f"\r    {C.CYAN}⏱  Next check in: {mins:02d}:{secs:02d}{C.RESET}  ", end="", flush=True)


# ─── Web Scraping (no browser needed) ────────────────────────

def fetch_dates(session, config, movie_name):
    """
    Fetch available dates for a movie from Cinema City website.
    Uses HTTP requests - no browser required.
    """
    dates = set()
    base_url = "https://www.cinema-city.co.il"

    # Strategy 1: Try the main page and ticket pages for embedded data
    pages_to_try = [
        base_url,
        f"{base_url}/tickets",
        f"{base_url}/he/tickets",
        f"{base_url}/booking",
    ]

    for page_url in pages_to_try:
        try:
            resp = session.get(page_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            html = resp.text

            # Look for __NEXT_DATA__ (Next.js embedded state)
            next_match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html, re.DOTALL
            )
            if next_match:
                try:
                    next_data = json.loads(next_match.group(1))
                    found = extract_dates_from_json(next_data, movie_name)
                    if found:
                        dates.update(found)
                        return dates
                except json.JSONDecodeError:
                    pass

            # Look for embedded JSON state
            state_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.__DATA__\s*=\s*({.*?});',
                r'window\.__NUXT__\s*=\s*({.*?});',
            ]
            for pattern in state_patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        found = extract_dates_from_json(data, movie_name)
                        if found:
                            dates.update(found)
                            return dates
                    except json.JSONDecodeError:
                        pass

            # Look for Hebrew date patterns directly in HTML
            # Pattern: יום X DD/MM/YYYY
            date_pattern = r'יום [א-ש]{1,2}[\s\u0027]*\s*\d{2}/\d{2}/\d{4}'
            found_dates = re.findall(date_pattern, html)
            if found_dates:
                # Check if movie name appears near these dates
                if movie_name in html:
                    dates.update(found_dates)
                    return dates

        except requests.RequestException:
            continue

    # Strategy 2: Try API endpoints
    api_endpoints = [
        "/api/screenings",
        "/api/movies",
        "/api/shows",
        "/api/schedule",
        "/api/v1/screenings",
        "/api/v2/screenings",
    ]

    for endpoint in api_endpoints:
        try:
            url = base_url + endpoint
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    found = extract_dates_from_json(data, movie_name)
                    if found:
                        dates.update(found)
                        return dates
                except (json.JSONDecodeError, ValueError):
                    pass
        except requests.RequestException:
            continue

    # Strategy 3: Look for XHR/fetch URLs in JavaScript bundles
    try:
        resp = session.get(base_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            # Find JS bundle URLs
            script_urls = re.findall(r'src="([^"]*\.js[^"]*)"', resp.text)
            for script_url in script_urls[:5]:
                if not script_url.startswith("http"):
                    script_url = base_url + script_url
                try:
                    js_resp = session.get(script_url, headers=HEADERS, timeout=10)
                    if js_resp.status_code == 200:
                        # Find API URLs in the bundle
                        api_urls = re.findall(
                            r'["\'](/api/[^"\']+)["\']', js_resp.text
                        )
                        for api_url in api_urls:
                            try:
                                r = session.get(
                                    base_url + api_url,
                                    headers=HEADERS, timeout=8
                                )
                                if r.status_code == 200:
                                    data = r.json()
                                    found = extract_dates_from_json(data, movie_name)
                                    if found:
                                        dates.update(found)
                                        return dates
                            except (requests.RequestException, ValueError):
                                continue
                except requests.RequestException:
                    continue
    except requests.RequestException:
        pass

    return dates


def extract_dates_from_json(data, movie_filter=None, depth=0):
    """Recursively extract date values from JSON, optionally filtering by movie."""
    if depth > 10:
        return set()

    dates = set()

    if isinstance(data, dict):
        # Check if this object is related to our movie
        values_str = json.dumps(data, ensure_ascii=False)
        is_relevant = movie_filter is None or movie_filter in values_str

        if is_relevant:
            for key, value in data.items():
                key_lower = key.lower()
                if any(d in key_lower for d in ["date", "day", "screen", "show", "time"]):
                    if isinstance(value, str):
                        # Check if it looks like a date
                        if re.match(r'.*\d{2}/\d{2}/\d{4}', value) or \
                           re.match(r'.*\d{4}-\d{2}-\d{2}', value) or \
                           re.match(r'יום', value):
                            dates.add(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                dates.add(item)
                            elif isinstance(item, dict):
                                dates.update(extract_dates_from_json(item, None, depth + 1))

            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    dates.update(extract_dates_from_json(value, movie_filter, depth + 1))

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                dates.update(extract_dates_from_json(item, movie_filter, depth + 1))

    return dates


def save_snapshot(data, reason="check"):
    """Save response data for debugging."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{reason}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ─── Main Logic ───────────────────────────────────────────────

def run_check(config, state):
    """Run one check cycle. Returns updated state."""
    changes_detected = False
    session = requests.Session()

    if "movies" not in state:
        state["movies"] = {}

    for movie in config["movies"]:
        print(f"\n    {C.CYAN}🔍 Checking: {movie}...{C.RESET}", end="", flush=True)

        try:
            current_dates = fetch_dates(session, config, movie)
            previous_dates = set(state.get("movies", {}).get(movie, {}).get("dates", []))

            if current_dates:
                new_dates = current_dates - previous_dates

                if previous_dates and new_dates:
                    changes_detected = True
                    print_change_alert(movie, new_dates)
                    save_snapshot({"movie": movie, "new": list(new_dates), "all": list(current_dates)}, "new_date")
                    send_vibrate()
                    send_notification(
                        f"🚨 New date - {movie}!",
                        f"New: {', '.join(new_dates)}"
                    )
                    state["changes_found"] = state.get("changes_found", 0) + 1
                else:
                    print(f" {C.GREEN}✓{C.RESET}")

                state.setdefault("movies", {})[movie] = {
                    "dates": list(current_dates),
                    "last_update": datetime.now().isoformat(),
                }
            else:
                print(f" {C.YELLOW}⚠ No dates found{C.RESET}")

        except Exception as e:
            print(f" {C.RED}✗ Error: {str(e)[:50]}{C.RESET}")

    state["last_check"] = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    state["total_checks"] = state.get("total_checks", 0) + 1

    if not changes_detected:
        print_no_change()

    return state


def show_menu(config):
    print(f"""
  {C.DIM}{'─' * 46}{C.RESET}
  {C.WHITE}{C.BOLD}Menu:{C.RESET}

    {C.CYAN}[1]{C.RESET} Add movie
    {C.CYAN}[2]{C.RESET} Remove movie
    {C.CYAN}[3]{C.RESET} Change interval
    {C.CYAN}[4]{C.RESET} Check now
    {C.CYAN}[5]{C.RESET} Reset state
    {C.CYAN}[q]{C.RESET} Quit
""")


def handle_menu(config, state):
    show_menu(config)
    choice = input(f"    {C.WHITE}Choice: {C.RESET}").strip()

    if choice == "1":
        name = input(f"    {C.WHITE}Movie name: {C.RESET}").strip()
        if name and name not in config["movies"]:
            config["movies"].append(name)
            save_config(config)
            print(f"    {C.GREEN}✓ Added: {name}{C.RESET}")
        elif name in config["movies"]:
            print(f"    {C.YELLOW}Already exists{C.RESET}")

    elif choice == "2":
        for i, m in enumerate(config["movies"], 1):
            print(f"      {C.CYAN}[{i}]{C.RESET} {m}")
        idx = input(f"    {C.WHITE}Number to remove: {C.RESET}").strip()
        try:
            idx = int(idx) - 1
            removed = config["movies"].pop(idx)
            save_config(config)
            print(f"    {C.GREEN}✓ Removed: {removed}{C.RESET}")
        except (ValueError, IndexError):
            print(f"    {C.RED}Invalid number{C.RESET}")

    elif choice == "3":
        mins = input(f"    {C.WHITE}Minutes between checks (current: {config['check_interval_minutes']}): {C.RESET}").strip()
        try:
            config["check_interval_minutes"] = max(1, int(mins))
            save_config(config)
            print(f"    {C.GREEN}✓ Updated to {config['check_interval_minutes']} min{C.RESET}")
        except ValueError:
            print(f"    {C.RED}Invalid number{C.RESET}")

    elif choice == "4":
        return config, state, True

    elif choice == "5":
        state = {}
        save_state(state)
        print(f"    {C.GREEN}✓ State reset{C.RESET}")

    elif choice.lower() == "q":
        print(f"\n  {C.DIM}Goodbye! 👋{C.RESET}\n")
        sys.exit(0)

    return config, state, False


def main():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    config = load_config()
    state = load_state()

    send_notification("Cinema Watcher", "Monitoring started ▶")

    while True:
        clear_screen()
        print_header(config)
        print_status(state, config)

        # Run check
        state = run_check(config, state)
        save_state(state)

        # Countdown with menu option
        interval = config["check_interval_minutes"] * 60
        print(f"\n  {C.DIM}{'─' * 46}{C.RESET}")
        print(f"  {C.DIM}Press Enter for menu, or wait for next check...{C.RESET}")

        start_wait = time.time()
        while True:
            elapsed = time.time() - start_wait
            remaining = max(0, interval - int(elapsed))
            print_countdown(remaining)

            if remaining <= 0:
                break

            # Check for user input (non-blocking)
            import select
            try:
                if sys.stdin in select.select([sys.stdin], [], [], 1)[0]:
                    sys.stdin.readline()
                    config, state, check_now = handle_menu(config, state)
                    if check_now:
                        break
                    input(f"\n    {C.DIM}Enter to continue...{C.RESET}")
                    break
            except (OSError, ValueError):
                time.sleep(1)

        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}Stopped. Goodbye! 👋{C.RESET}\n")
