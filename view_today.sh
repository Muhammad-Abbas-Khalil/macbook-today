#!/bin/bash

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run data collector to refresh statistics
python3 "$SCRIPT_DIR/dashboard_collector.py"

# Open the beautiful dashboard in default browser
open "$SCRIPT_DIR/dashboard.html"

echo "Dashboard launched! Have a beautiful day."
