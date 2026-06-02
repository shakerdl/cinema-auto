#!/usr/bin/env python3
"""
Cinema City Watcher - Discover the correct API endpoints and cinema/movie IDs.
Run this script ONCE to find the correct configuration for your needs.
"""

import json
import re
import sys

import requests

BASE_URL = "https://www.cinema-city.co.il"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}


def discover():
    session = requests.Session()
    print("=" * 60)
    print("  Cinema City - API Discovery Tool")
    print("=" * 60)

    # Step 1: Fetch main page and find embedded data
    print("\n[1] Fetching main page...")
    resp = session.get(BASE_URL, headers=HEADERS, timeout=15)
    print(f"    Status: {resp.status_code}")

    # Look for JavaScript bundles and API URLs
    api_urls_found = set()
    api_pattern = r'["\'](/api[^"\']*)["\']'
    matches = re.findall(api_pattern, resp.text)
    for m in matches:
        api_urls_found.add(m)

    # Look for Next.js data
    next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if next_data_match:
        print("    Found __NEXT_DATA__ - Next.js site detected")
        try:
            next_data = json.loads(next_data_match.group(1))
            print(f"    Keys: {list(next_data.keys())}")
            # Save for analysis
            with open("discovery_next_data.json", "w", encoding="utf-8") as f:
                json.dump(next_data, f, ensure_ascii=False, indent=2)
            print("    Saved to discovery_next_data.json")
        except json.JSONDecodeError:
            print("    Could not parse __NEXT_DATA__")

    # Step 2: Try common API endpoints
    print("\n[2] Probing API endpoints...")
    endpoints = [
        "/api/cinemas",
        "/api/theaters",
        "/api/movies",
        "/api/films",
        "/api/screenings",
        "/api/dates",
        "/api/schedule",
        "/api/shows",
        "/api/categories",
        "/api/genres",
        "/api/v1/cinemas",
        "/api/v1/movies",
        "/api/v1/screenings",
        "/api/v2/cinemas",
        "/api/v2/movies",
        "/he/cinemas",
        "/he/movies",
        "/graphql",
        "/_next/data",
    ]

    # Add any API URLs found in the HTML
    endpoints.extend(api_urls_found)

    results = {}
    for endpoint in sorted(set(endpoints)):
        url = BASE_URL + endpoint
        try:
            r = session.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                content_type = r.headers.get("content-type", "")
                if "json" in content_type:
                    data = r.json()
                    results[endpoint] = {"type": "json", "sample": str(data)[:200]}
                    print(f"    [JSON] {endpoint}")
                elif "html" in content_type and len(r.text) < 50000:
                    results[endpoint] = {"type": "html", "size": len(r.text)}
                    print(f"    [HTML] {endpoint} ({len(r.text)} bytes)")
            elif r.status_code == 405:
                # Maybe needs POST
                results[endpoint] = {"type": "needs_post", "status": 405}
                print(f"    [POST?] {endpoint}")
        except requests.RequestException:
            pass

    # Step 3: Try tickets/booking page
    print("\n[3] Fetching tickets page...")
    tickets_urls = [
        "/tickets",
        "/he/tickets",
        "/booking",
        "/order",
        "/he/order",
        "/he/booking",
    ]

    for path in tickets_urls:
        try:
            r = session.get(BASE_URL + path, headers=HEADERS, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                print(f"    [OK] {path} -> {r.url}")

                # Look for cinema names
                cinema_pattern = r'ראשון[^"<]*לציון'
                if re.search(cinema_pattern, r.text):
                    print(f"         Contains 'ראשון לציון' reference!")

                # Look for date patterns
                date_pattern = r'יום [א-ש]{1,2} \d{2}/\d{2}/\d{4}'
                dates = re.findall(date_pattern, r.text)
                if dates:
                    print(f"         Found dates: {dates}")

                # Look for API calls in JavaScript
                js_api = re.findall(r'fetch\(["\']([^"\']+)["\']', r.text)
                if js_api:
                    print(f"         JS fetch calls: {js_api[:5]}")

                # Look for XHR/axios patterns
                xhr_pattern = r'(?:axios|fetch|http)\.\w+\(["\']([^"\']+)["\']'
                xhr_calls = re.findall(xhr_pattern, r.text)
                if xhr_calls:
                    print(f"         XHR calls: {xhr_calls[:5]}")

        except requests.RequestException as e:
            print(f"    [FAIL] {path}: {e}")

    # Step 4: Look for script bundles
    print("\n[4] Looking for JS bundles with API info...")
    script_pattern = r'<script[^>]+src="([^"]*(?:main|app|chunk|bundle)[^"]*\.js)"'
    scripts = re.findall(script_pattern, resp.text)
    print(f"    Found {len(scripts)} potential bundles")

    for script_url in scripts[:3]:  # Check first 3
        if not script_url.startswith("http"):
            script_url = BASE_URL + script_url
        try:
            r = session.get(script_url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                # Look for API base URLs
                api_bases = re.findall(r'["\'](?:https?://[^"\']*api[^"\']*)["\']', r.text)
                if api_bases:
                    print(f"    API URLs in bundle: {api_bases[:5]}")

                # Look for cinema IDs
                cinema_ids = re.findall(r'cinema[Ii]d["\s:=]+["\']?(\d+)', r.text)
                if cinema_ids:
                    print(f"    Cinema IDs: {cinema_ids[:10]}")

        except requests.RequestException:
            pass

    # Save all results
    print("\n[5] Saving results...")
    output = {
        "api_urls_in_html": list(api_urls_found),
        "probed_endpoints": results,
        "timestamp": str(__import__("datetime").datetime.now()),
    }
    with open("discovery_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("    Saved to discovery_results.json")

    print("\n" + "=" * 60)
    print("  Discovery complete! Check the JSON files for details.")
    print("  Update CONFIG in cinema_watcher_api.py with correct IDs.")
    print("=" * 60)


if __name__ == "__main__":
    discover()
