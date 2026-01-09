#!/bin/bash

# ============================================
# Stock Auto Trader - Backend Setup Script
# ============================================

echo "🚀 Setting up Stock Auto Trader Backend..."

# Navigate to backend directory
cd "$(dirname "$0")"

# Remove existing venv if exists
if [ -d "venv" ]; then
    echo "🗑️  Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Verify installation
echo ""
echo "✅ Setup complete! Installed packages:"
pip list

echo ""
echo "============================================"
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To initialize the database, run:"
echo "  python models.py"
echo ""
echo "To start the server (after Step 3), run:"
echo "  python main.py"
echo "============================================"