#!/bin/bash
# Convenience script to run the application with venv activated

cd "$(dirname "$0")"
source .venv/bin/activate
cd src
python main.py
