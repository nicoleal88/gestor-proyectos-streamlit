#!/bin/bash
# Script to install development dependencies and run tests

echo "🔧 Installing development dependencies..."
pip install pytest pytest-cov black flake8 mypy

echo "✅ Development dependencies installed successfully!"

echo "🧪 Running tests..."
python3 -m pytest tests/ -v --tb=short

echo "📊 Test execution completed!"
