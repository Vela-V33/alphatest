#!/bin/bash
# AlphaTest Launcher for Mac
# Double-click this file to start AlphaTest

cd "$(dirname "$0")"

echo ""
echo "🧪 Starting AlphaTest..."
echo ""

if command -v python3 &> /dev/null; then
    python3 setup_and_run.py
else
    echo "❌ Python 3 not found!"
    echo ""
    echo "Please install Python from: https://python.org"
    echo ""
    read -p "Press Enter to close..."
fi
