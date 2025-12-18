#!/bin/bash

# 1. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# 2. Activate virtual environment
# Check for Windows path (Scripts) first, then Linux/Mac (bin)
if [ -f "venv/Scripts/activate" ]; then
    echo "Activating Windows virtual environment..."
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    echo "Activating Unix virtual environment..."
    source venv/bin/activate
else
    echo "Error: Could not find activation script."
    exit 1
fi

# 3. Install dependencies
echo "Installing dependencies..."
# Use python -m to ensure we use the venv's pip
python -m pip install -r requirements.txt

# 4. Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install chromium


# 5. Start the web server
echo "Starting server via dedicated startup script..."
python server.py