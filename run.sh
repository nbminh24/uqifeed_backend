#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
elif [ -d "env" ]; then
  source env/bin/activate
fi

# Install or update dependencies
pip install -r requirements.txt

# Run the application
python -m src.main

