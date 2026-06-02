#!/usr/bin/env python3
"""
Cinema City Date Watcher - Android/Termux Automation
Monitors Cinema City Rishon LeZion for new screening dates.
"""

import json
import os
import time
import subprocess
import sys
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

# --- Configuration ---
CONFIG = {
    "url": "https://www.cinema-city.co.il/",
    "cinema": "ראשון לציון",
    "movie_type": "רגיל",
    "movie_name": "אובססיה",
    "check_interval_minutes": 5,
    "screenshot_dir": os.path.expanduser("~/CinemaCityWatcher"),
    "state_file": os.path.expanduser("~/CinemaCityWatcher/last_dates.json"),
    "headless": True,
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
        print("[WARNING] termux-notification not found. Install Termux:API.")
        print(f"  -> {title}: {message}")
    except subprocess.TimeoutExpired:
        print("[WARNING] Notification timed out")


def send_vibrate():
    """Vibrate to get attention."""
    try:
        subprocess.run(["termux-vibrate", "-d", "1000"], timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def get_chrome_options():
    options = Options()
    if CONFIG["headless"]:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1080,1920")
    options.add_argument("--lang=he")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    )
    return options


def load_previous_dates():
    """Load previously seen dates from file."""
    try:
        with open(CONFIG["state_file"], "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("dates", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_dates(dates):
    """Save current dates to state file."""
    with open(CONFIG["state_file"], "w", encoding="utf-8") as f:
        json.dump({"dates": list(dates), "last_check": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def take_screenshot(driver, reason="new_date"):
    """Take and save a screenshot."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cinema_city_{reason}_{timestamp}.png"
    filepath = os.path.join(CONFIG["screenshot_dir"], filename)
    driver.save_screenshot(filepath)
    print(f"[SCREENSHOT] Saved: {filepath}")
    return filepath


def check_dates(driver):
    """
    Navigate to Cinema City, select cinema/movie/type, and read date options.
    Returns a set of date strings found in the dropdown.
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Opening Cinema City website...")
    driver.get(CONFIG["url"])

    wait = WebDriverWait(driver, 20)

    # Step 1: Wait for the page to load and look for the booking/order section
    time.sleep(3)

    # Step 2: Select Cinema - Rishon LeZion
    print("  Selecting cinema: Rishon LeZion...")
    try:
        # Look for cinema selector - Cinema City uses various UI patterns
        # Try clicking on cinema dropdown/selector
        cinema_selectors = [
            "//select[contains(@class, 'cinema')]//option[contains(text(), 'ראשון')]",
            "//*[contains(@class, 'cinema-select')]//*[contains(text(), 'ראשון')]",
            "//*[contains(@class, 'select')]//option[contains(text(), 'ראשון לציון')]",
            "//div[contains(@class, 'dropdown')]//*[contains(text(), 'ראשון')]",
            "//*[@data-cinema='rishon']",
            "//button[contains(text(), 'ראשון')]",
            "//a[contains(text(), 'ראשון לציון')]",
        ]
        cinema_found = False
        for selector in cinema_selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                element.click()
                cinema_found = True
                print("    -> Cinema selected")
                break
            except Exception:
                continue

        if not cinema_found:
            # Try using the booking flow URL directly
            driver.get("https://www.cinema-city.co.il/tickets")
            time.sleep(3)
            for selector in cinema_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    element.click()
                    cinema_found = True
                    print("    -> Cinema selected (via tickets page)")
                    break
                except Exception:
                    continue

        time.sleep(2)

    except Exception as e:
        print(f"  [ERROR] Cinema selection: {e}")

    # Step 3: Select movie type - Regular
    print("  Selecting movie type: Regular...")
    try:
        type_selectors = [
            "//*[contains(text(), 'רגיל')]",
            "//button[contains(text(), 'רגיל')]",
            "//a[contains(text(), 'רגיל')]",
            "//*[contains(@class, 'type')]//*[contains(text(), 'רגיל')]",
        ]
        for selector in type_selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                element.click()
                print("    -> Type selected")
                break
            except Exception:
                continue
        time.sleep(2)
    except Exception as e:
        print(f"  [ERROR] Type selection: {e}")

    # Step 4: Select movie - Unbassia
    print("  Selecting movie: Unbassia...")
    try:
        movie_selectors = [
            "//*[contains(text(), 'אובססיה')]",
            "//*[contains(text(), 'OBSESSION')]",
            "//*[contains(text(), 'obsession')]",
            "//button[contains(text(), 'אובססיה')]",
            "//a[contains(text(), 'אובססיה')]",
            "//*[contains(@class, 'movie')]//*[contains(text(), 'אובססיה')]",
        ]
        for selector in movie_selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                element.click()
                print("    -> Movie selected")
                break
            except Exception:
                continue
        time.sleep(2)
    except Exception as e:
        print(f"  [ERROR] Movie selection: {e}")

    # Step 5: Open date dropdown and read values
    print("  Reading date dropdown...")
    dates = set()
    try:
        date_selectors = [
            "//select[contains(@class, 'date')]",
            "//select[contains(@name, 'date')]",
            "//*[contains(@class, 'date-select')]//select",
            "//*[contains(@class, 'date-picker')]//select",
            "//*[contains(@class, 'dropdown')]//select",
            "//select[contains(@id, 'date')]",
        ]

        select_element = None
        for selector in date_selectors:
            try:
                select_element = driver.find_element(By.XPATH, selector)
                break
            except Exception:
                continue

        if select_element:
            # Read all options from the select element
            options = select_element.find_elements(By.TAG_NAME, "option")
            for option in options:
                text = option.text.strip()
                if text and text != "בחירת תאריך" and text != "-- בחר תאריך --":
                    dates.add(text)
                    print(f"    Found date: {text}")
        else:
            # Try alternative: date buttons/links
            date_elements_selectors = [
                "//*[contains(@class, 'date-item')]",
                "//*[contains(@class, 'day-item')]",
                "//*[contains(@class, 'date-button')]",
                "//*[contains(@class, 'screening-date')]",
            ]
            for selector in date_elements_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        for el in elements:
                            text = el.text.strip()
                            if text:
                                dates.add(text)
                                print(f"    Found date: {text}")
                        break
                except Exception:
                    continue

    except Exception as e:
        print(f"  [ERROR] Date reading: {e}")

    return dates


def run_check():
    """Run a single check cycle."""
    driver = None
    try:
        options = get_chrome_options()
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)

        current_dates = check_dates(driver)

        if not current_dates:
            print("  [WARNING] No dates found. Site structure may have changed.")
            take_screenshot(driver, "no_dates_found")
            return

        previous_dates = load_previous_dates()
        print(f"\n  Previous dates: {previous_dates or 'None (first run)'}")
        print(f"  Current dates:  {current_dates}")

        # Check for new dates
        new_dates = current_dates - previous_dates

        if previous_dates and new_dates:
            print(f"\n  *** NEW DATES FOUND: {new_dates} ***")
            screenshot_path = take_screenshot(driver, "new_date_found")
            send_vibrate()
            send_notification(
                "Cinema City - תאריך חדש!",
                f"נמצאו תאריכים חדשים: {', '.join(new_dates)}"
            )
            # Take another screenshot of the full page
            driver.execute_script("window.scrollTo(0, 0)")
            take_screenshot(driver, "full_page")
        elif not previous_dates:
            print("\n  First run - saving initial dates.")
            take_screenshot(driver, "initial_state")
        else:
            print("\n  No new dates. Current list unchanged.")

        # Save current state
        save_dates(current_dates)

    except WebDriverException as e:
        print(f"[ERROR] WebDriver error: {e}")
        send_notification("Cinema Watcher Error", f"WebDriver: {str(e)[:100]}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        send_notification("Cinema Watcher Error", str(e)[:100])
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    """Main loop - check periodically."""
    setup_directories()
    interval = CONFIG["check_interval_minutes"] * 60

    print("=" * 60)
    print("  Cinema City Date Watcher")
    print("=" * 60)
    print(f"  Cinema:   {CONFIG['cinema']}")
    print(f"  Type:     {CONFIG['movie_type']}")
    print(f"  Movie:    {CONFIG['movie_name']}")
    print(f"  Interval: Every {CONFIG['check_interval_minutes']} minutes")
    print(f"  Screenshots: {CONFIG['screenshot_dir']}")
    print("=" * 60)
    print()

    send_notification("Cinema Watcher Started", "Monitoring for new dates...")

    while True:
        try:
            run_check()
            print(f"\n  Next check in {CONFIG['check_interval_minutes']} minutes...")
            print("-" * 40)
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n[STOPPED] Cinema watcher stopped by user.")
            send_notification("Cinema Watcher Stopped", "Monitoring ended.")
            break


if __name__ == "__main__":
    main()
