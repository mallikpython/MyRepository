#!/bin/bash
# Daily QQQ options trader - run at 9:45 AM ET on weekdays
# Set up with: crontab -e
# 45 9 * * 1-5 /path/to/mallikrasala-finance/trading/run_daily.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load credentials from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Activate virtualenv if it exists
if [ -f venv/bin/activate ]; then
  source venv/bin/activate
fi

python trader.py "$@"
