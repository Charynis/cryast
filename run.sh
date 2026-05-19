#!/bin/bash
# Launch the Crypto Swing Trading Assistant
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from template"
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Installing dependencies..."
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

echo "Starting Crypto Swing Trading Assistant..."
.venv/bin/streamlit run app.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false \
    --theme.base dark
