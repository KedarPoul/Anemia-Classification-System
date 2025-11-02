#!/bin/bash
# setup.sh - Force Python 3.9 and install dependencies

echo "🔧 Setting up Python environment..."
python --version

echo "📦 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "✅ Setup completed successfully!"