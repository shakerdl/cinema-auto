#!/usr/bin/env python3
"""
Cinema City Date Watcher - Interactive Dashboard
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

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
SCREENSHOT_DIR = os.path.expanduser("~/CinemaCityWatcher")

DEFAULT_CONFIG = {
    "cinema": "ראשון לציון",
    "movie_type": "רגיל",
    "movies": ["אובססיה"],
    "check_interval_minutes": 5,
    "headless": True,
}


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
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
    except (FileNotFoundError, subprocess.TimeoutExpired):
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
    print(f"  {C.WHITE}קולנוע:{C.RESET}  {C.BOLD}{config['cinema']}{C.RESET}")
    print(f"  {C.WHITE}סוג:{C.RESET}     {config['movie_type']}")
    print(f"  {C.WHITE}סרטים:{C.RESET}   {', '.join(config['movies'])}")
    print(f"  {C.WHITE}בדיקה:{C.RESET}   כל {config['check_interval_minutes']} דקות")
    print()


def print_status(state, config):
    print(f"  {C.DIM}{'─' * 46}{C.RESET}")
    print(f"  {C.WHITE}{C.BOLD}סטטוס נוכחי:{C.RESET}")
    print()

    if not state:
        print(f"    {C.YELLOW}⏳ טרם בוצעה בדיקה ראשונה{C.RESET}")
        return

    last_check = state.get("last_check", "")
    if last_check:
        print(f"    {C.DIM}בדיקה אחרונה: {last_check}{C.RESET}")

    print()
    for movie, data in state.get("movies", {}).items():
        dates = data.get("dates", [])
        print(f"    {C.MAGENTA}🎬 {movie}{C.RESET}")
        if dates:
            for d in sorted(dates):
                print(f"       {C.GREEN}📅 {d}{C.RESET}")
        else:
            print(f"       {C.DIM}אין תאריכים{C.RESET}")
        print()

    total_checks = state.get("total_checks", 0)
    changes_found = state.get("changes_found", 0)
    print(f"    {C.DIM}בדיקות: {total_checks} | שינויים: {changes_found}{C.RESET}")


def print_change_alert(movie, new_dates):
    print()
    print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}")
    print(f"  ╔══════════════════════════════════════════════╗")
    print(f"  ║   🚨  תאריך חדש נמצא!  🚨                  ║")
    print(f"  ╠══════════════════════════════════════════════╣")
    print(f"  ║   סרט: {movie:<37} ║")
    for d in new_dates:
        print(f"  ║   📅  {d:<38} ║")
    print(f"  ╚══════════════════════════════════════════════╝")
    print(f"  {C.RESET}")
    print()


def print_no_change():
    print(f"\n    {C.GREEN}✓ אין שינוי{C.RESET}")


def print_countdown(seconds_left):
    mins = seconds_left // 60
    secs = seconds_left % 60
    print(f"\r    {C.CYAN}⏱  בדיקה הבאה בעוד: {mins:02d}:{secs:02d}{C.RESET}  ", end="", flush=True)


# ─── Browser Logic ────────────────────────────────────────────

def get_driver(config):
    options = Options()
    if config["headless"]:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1080,1920")
    options.add_argument("--lang=he")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
    )
    return webdriver.Chrome(service=Service(), options=options)


def check_movie_dates(driver, config, movie_name):
    """Navigate and extract dates for a specific movie."""
    driver.get("https://www.cinema-city.co.il/")
    time.sleep(3)

    # Select cinema
    for selector in [
        f"//*[contains(text(), '{config['cinema']}')]",
        f"//option[contains(text(), '{config['cinema']}')]",
        f"//button[contains(text(), '{config['cinema']}')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            el.click()
            break
        except Exception:
            continue
    time.sleep(2)

    # Select type
    for selector in [
        f"//*[contains(text(), '{config['movie_type']}')]",
        f"//button[contains(text(), '{config['movie_type']}')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            el.click()
            break
        except Exception:
            continue
    time.sleep(2)

    # Select movie
    for selector in [
        f"//*[contains(text(), '{movie_name}')]",
        f"//button[contains(text(), '{movie_name}')]",
        f"//a[contains(text(), '{movie_name}')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            el.click()
            break
        except Exception:
            continue
    time.sleep(2)

    # Read dates
    dates = set()
    date_selectors = [
        "//select[contains(@class, 'date')]",
        "//select[contains(@name, 'date')]",
        "//select[contains(@id, 'date')]",
        "//*[contains(@class, 'date-select')]//select",
    ]

    for selector in date_selectors:
        try:
            select_el = driver.find_element(By.XPATH, selector)
            options = select_el.find_elements(By.TAG_NAME, "option")
            for opt in options:
                text = opt.text.strip()
                if text and "בחר" not in text and "תאריך" not in text:
                    dates.add(text)
            if dates:
                break
        except Exception:
            continue

    # Fallback: date elements
    if not dates:
        for selector in [
            "//*[contains(@class, 'date-item')]",
            "//*[contains(@class, 'day-item')]",
            "//*[contains(@class, 'screening-date')]",
        ]:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for el in elements:
                    text = el.text.strip()
                    if text:
                        dates.add(text)
                if dates:
                    break
            except Exception:
                continue

    return dates


def take_screenshot(driver, movie_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = movie_name.replace(" ", "_")
    filename = f"change_{safe_name}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(filepath)
    return filepath


# ─── Main Logic ───────────────────────────────────────────────

def run_check(config, state):
    """Run one check cycle. Returns updated state."""
    driver = None
    changes_detected = False

    try:
        driver = get_driver(config)

        if "movies" not in state:
            state["movies"] = {}

        for movie in config["movies"]:
            print(f"\n    {C.CYAN}🔍 בודק: {movie}...{C.RESET}", end="", flush=True)

            current_dates = check_movie_dates(driver, config, movie)

            previous_dates = set(state.get("movies", {}).get(movie, {}).get("dates", []))

            if current_dates:
                new_dates = current_dates - previous_dates

                if previous_dates and new_dates:
                    changes_detected = True
                    print_change_alert(movie, new_dates)
                    take_screenshot(driver, movie)
                    send_vibrate()
                    send_notification(
                        f"🚨 תאריך חדש - {movie}!",
                        f"חדש: {', '.join(new_dates)}"
                    )
                    state["changes_found"] = state.get("changes_found", 0) + 1
                else:
                    print(f" {C.GREEN}✓{C.RESET}")

                state.setdefault("movies", {})[movie] = {
                    "dates": list(current_dates),
                    "last_update": datetime.now().isoformat(),
                }
            else:
                print(f" {C.YELLOW}⚠ לא נמצאו תאריכים{C.RESET}")

        state["last_check"] = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
        state["total_checks"] = state.get("total_checks", 0) + 1

    except WebDriverException as e:
        print(f"\n    {C.RED}✗ שגיאת דפדפן: {str(e)[:60]}{C.RESET}")
    except Exception as e:
        print(f"\n    {C.RED}✗ שגיאה: {str(e)[:60]}{C.RESET}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    if not changes_detected:
        print_no_change()

    return state


def show_menu(config):
    """Show interactive menu."""
    print(f"""
  {C.DIM}{'─' * 46}{C.RESET}
  {C.WHITE}{C.BOLD}תפריט:{C.RESET}

    {C.CYAN}[1]{C.RESET} הוסף סרט
    {C.CYAN}[2]{C.RESET} הסר סרט
    {C.CYAN}[3]{C.RESET} שנה תדירות בדיקה
    {C.CYAN}[4]{C.RESET} בדוק עכשיו
    {C.CYAN}[5]{C.RESET} אפס מצב (reset)
    {C.CYAN}[q]{C.RESET} יציאה
""")


def handle_menu(config, state):
    """Handle menu input. Returns (config, state, should_check_now)."""
    show_menu(config)
    choice = input(f"    {C.WHITE}בחירה: {C.RESET}").strip()

    if choice == "1":
        name = input(f"    {C.WHITE}שם הסרט: {C.RESET}").strip()
        if name and name not in config["movies"]:
            config["movies"].append(name)
            save_config(config)
            print(f"    {C.GREEN}✓ נוסף: {name}{C.RESET}")
        elif name in config["movies"]:
            print(f"    {C.YELLOW}כבר קיים{C.RESET}")

    elif choice == "2":
        for i, m in enumerate(config["movies"], 1):
            print(f"      {C.CYAN}[{i}]{C.RESET} {m}")
        idx = input(f"    {C.WHITE}מספר להסרה: {C.RESET}").strip()
        try:
            idx = int(idx) - 1
            removed = config["movies"].pop(idx)
            save_config(config)
            print(f"    {C.GREEN}✓ הוסר: {removed}{C.RESET}")
        except (ValueError, IndexError):
            print(f"    {C.RED}מספר לא תקין{C.RESET}")

    elif choice == "3":
        mins = input(f"    {C.WHITE}דקות בין בדיקות (נוכחי: {config['check_interval_minutes']}): {C.RESET}").strip()
        try:
            config["check_interval_minutes"] = max(1, int(mins))
            save_config(config)
            print(f"    {C.GREEN}✓ עודכן ל-{config['check_interval_minutes']} דקות{C.RESET}")
        except ValueError:
            print(f"    {C.RED}מספר לא תקין{C.RESET}")

    elif choice == "4":
        return config, state, True

    elif choice == "5":
        state = {}
        save_state(state)
        print(f"    {C.GREEN}✓ מצב אופס{C.RESET}")

    elif choice.lower() == "q":
        print(f"\n  {C.DIM}להתראות! 👋{C.RESET}\n")
        sys.exit(0)

    return config, state, False


def main():
    Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
    config = load_config()
    state = load_state()

    send_notification("Cinema Watcher", "המעקב התחיל ▶")

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
        print(f"  {C.DIM}לחץ Enter לתפריט, או המתן לבדיקה הבאה...{C.RESET}")

        start_wait = time.time()
        while True:
            elapsed = time.time() - start_wait
            remaining = max(0, interval - int(elapsed))
            print_countdown(remaining)

            if remaining <= 0:
                break

            # Check for user input (non-blocking)
            import select
            if sys.stdin in select.select([sys.stdin], [], [], 1)[0]:
                sys.stdin.readline()
                config, state, check_now = handle_menu(config, state)
                if check_now:
                    break
                input(f"\n    {C.DIM}Enter להמשך...{C.RESET}")
                break

        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.DIM}נעצר. להתראות! 👋{C.RESET}\n")
