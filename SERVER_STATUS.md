# Flask Server Status

## Current Status

✅ **Flask app is running on port 8888**

## Access the Web UI

Open your browser and navigate to:
```
http://localhost:8888
```

## Port Change

The server was moved from port 5002 to port 8888 due to port conflicts.

## To Restart the Server

If you need to restart the server:

```bash
# Kill existing processes
pkill -f "python3 app.py"
lsof -ti:8888 | xargs kill -9 2>/dev/null

# Start the server
cd /Users/jatinyadav/Nextcloud2/dev/Openwrap-DFP-Setup
python3 app.py
```

Or use the startup script:
```bash
./start_server.sh
```

## Troubleshooting "Failed to fetch" Error

If you're still seeing "Failed to fetch":

1. **Hard refresh your browser**:
   - Mac: `Cmd + Shift + R`
   - Windows/Linux: `Ctrl + Shift + R`

2. **Clear browser cache**:
   - Open Developer Tools (F12)
   - Right-click refresh button → "Empty Cache and Hard Reload"

3. **Verify server is running**:
   ```bash
   curl http://localhost:8888/api/settings/defaults
   ```
   Should return JSON data.

4. **Check browser console** (F12 → Console tab) for any JavaScript errors

5. **Ensure you're using the correct URL**: `http://localhost:8888`

## Testing the API

Test the generate endpoint:
```bash
curl -X POST http://localhost:8888/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "partner_type": "openwrap",
    "DFP_ORDER_NAME": "test",
    "DFP_PLACEMENT_SIZES": [{"width": "320", "height": "480"}]
  }'
```

## Current Server Process

Check if server is running:
```bash
ps aux | grep "python3 app.py" | grep -v grep
```

Check port usage:
```bash
lsof -ti:8888
```



