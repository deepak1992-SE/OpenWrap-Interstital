#!/bin/bash

# Kill any existing Flask processes
pkill -f "python3 app.py" 2>/dev/null
lsof -ti:5002 | xargs kill -9 2>/dev/null 2>/dev/null
sleep 2

# Start Flask app
cd "$(dirname "$0")"
echo "Starting Flask app on port 5002..."
export USE_BACKGROUND_THREAD=true
python3 app.py



