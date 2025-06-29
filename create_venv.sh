#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get current working directory
PROJECT_DIR=$(pwd)

# Define the venv path
VENV_DIR="$PROJECT_DIR/venv"

echo "📁 Project directory: $PROJECT_DIR"
echo "📦 Creating Python virtual environment in: $VENV_DIR"

# Create virtual environment
python3 -m venv "$VENV_DIR"

echo "✅ Virtual environment created successfully."

# Instruction to activate
echo ""
echo "➡️ To activate it, run:"
echo "source \"$VENV_DIR/bin/activate\""
