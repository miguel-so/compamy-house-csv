#!/bin/bash
# Quick setup script for Companies House CSV Export

set -e

echo "Companies House CSV Export - Setup"
echo "======================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python $PYTHON_VERSION found"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "No .env file found. Creating from template..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "Created .env file from env.example"
        echo ""
        echo "IMPORTANT: Please edit .env and add your Companies House API key!"
        echo "   Get your free API key from: https://developer.company-information.service.gov.uk/get-started"
    else
        echo "env.example not found. Please create .env manually."
    fi
else
    echo ".env file exists"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To run the application:"
echo "  python3 app.py"
echo ""
echo "Then open http://localhost:5000 in your browser"
