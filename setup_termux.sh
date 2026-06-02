#!/bin/bash
# ============================================================
# Cinema City Watcher - Termux Setup Script
# Run this script inside Termux on your Android device
# ============================================================

echo "========================================="
echo " Cinema City Watcher - Termux Setup"
echo "========================================="

# Update packages
echo "[1/7] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python
echo "[2/7] Installing Python..."
pkg install -y python python-pip

# Install Chromium and ChromeDriver for Selenium
echo "[3/7] Installing Chromium..."
pkg install -y chromium

# Install required system packages
echo "[4/7] Installing system dependencies..."
pkg install -y termux-api git wget

# Install Python packages
echo "[5/7] Installing Python packages..."
pip install --upgrade pip
pip install selenium requests

# Create output directory
echo "[6/7] Creating CinemaCityWatcher directory..."
mkdir -p ~/CinemaCityWatcher

# Grant Termux:API permissions
echo "[7/7] Setting up permissions..."
echo ""
echo "========================================="
echo " IMPORTANT: Manual Steps Required!"
echo "========================================="
echo ""
echo "1. Install 'Termux:API' app from F-Droid:"
echo "   https://f-droid.org/packages/com.termux.api/"
echo ""
echo "2. Grant permissions to Termux:API:"
echo "   - Open Android Settings > Apps > Termux:API"
echo "   - Grant: Notifications, Storage"
echo ""
echo "3. Grant Termux storage access:"
echo "   Run: termux-setup-storage"
echo ""
echo "4. Test notification:"
echo "   termux-notification --title 'Test' --content 'Working!'"
echo ""
echo "========================================="
echo " Setup Complete!"
echo "========================================="
echo ""
echo "To start monitoring:"
echo "  python cinema_watcher.py"
echo ""
echo "To run in background:"
echo "  nohup python cinema_watcher.py > ~/CinemaCityWatcher/log.txt 2>&1 &"
echo ""
echo "To stop:"
echo "  pkill -f cinema_watcher"
echo ""
