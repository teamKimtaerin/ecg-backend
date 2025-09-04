#!/bin/bash

# Pre-commit 설치 스크립트

echo "Installing pre-commit..."
pip install pre-commit

echo "Installing pre-commit hooks..."
pre-commit install

echo "Running pre-commit on all files..."
pre-commit run --all-files

echo "✅ Pre-commit setup complete!"
echo ""
echo "Now, every time you commit:"
echo "1. Black will auto-format your code"
echo "2. Ruff will auto-fix linting issues"
echo "3. Mypy will check types"
echo ""
echo "If fixes are applied, you'll need to stage them and commit again."