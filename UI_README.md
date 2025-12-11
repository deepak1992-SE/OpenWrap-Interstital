# DFP Line Item Generator - Web UI

A modern web-based user interface for configuring and generating line items in Google Ad Manager (DFP/GAM).

## Features

- **Intuitive Web Interface**: Easy-to-use form-based UI for all settings
- **Tabbed Navigation**: Organized settings into logical sections
- **Dynamic Form Fields**: Fields show/hide based on selected options
- **CSV File Upload**: Upload price bucket CSV files directly through the UI
- **Real-time Validation**: Form validation before submission
- **Default Settings Loading**: Load existing settings from `settings.py`
- **Progress Feedback**: Real-time feedback during line item generation

## Installation

1. Install Flask and dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your `googleads.yaml` and `key.json` files are configured (see main README.md)

## Running the Web UI

Start the Flask application:

```bash
python app.py
```

The web UI will be available at: `http://localhost:5000`

To access from other machines on your network:
```bash
python app.py
# Then access via http://YOUR_IP:5000
```

## Usage

### 1. Select Partner Type
- Choose between **OpenWrap** or **Prebid**

### 2. Configure DFP Settings
- **Order Name**: Name for the GAM order
- **User Email**: GAM user email address
- **Advertiser Name**: Advertiser name in GAM
- **Line Item Type**: PRICE_PRIORITY, SPONSORSHIP, NETWORK, or HOUSE
- **Placements**: Comma-separated placement names (leave empty for RON)
- **Sizes**: Add creative sizes (width x height)
- **Currency**: Currency code (e.g., USD, EUR)

### 3. Configure OpenWrap/Prebid Settings
- **Setup Type**: Select creative type (WEB, AMP, NATIVE, VIDEO, ADPOD, etc.)
- **Bidder Code**: Comma-separated bidder codes (leave empty for all)
- **Price Bucket CSV**: Upload or specify CSV file name
- **Creative Template**: Required for NATIVE setup types
- **Video Lengths**: Required for ADPOD setup
- **ADPOD Slots**: Required for ADPOD setup

### 4. Advanced Settings
- **Line Item Prefix**: Optional prefix for line item names
- **Device Categories**: Target specific device types
- **Roadblock Type**: ONE_OR_MORE or AS_MANY_AS_POSSIBLE
- **Video Position**: PREROLL, MIDROLL, or POSTROLL
- **Deal Line Items**: Configure deal targeting for ADPOD

### 5. Generate Line Items
- Click **"Generate Line Items"** to create line items in DFP
- Review the output in the result section
- Check your GAM account to verify the created items

## Form Behavior

### Dynamic Field Visibility
- Fields automatically show/hide based on:
  - **Setup Type**: Different fields for WEB, NATIVE, VIDEO, ADPOD, etc.
  - **Partner Type**: Prebid vs OpenWrap specific fields
  - **Deal Line Item**: Additional fields when enabled

### Validation
- Required fields are marked with *
- Form validates before submission
- Custom validation for ADPOD and NATIVE setup types

### CSV Upload
- Click "Upload CSV" button to upload price bucket files
- Files are saved to the project root directory
- File name is automatically populated in the form

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, modify `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port
```

### Settings Not Saving
The UI temporarily modifies `settings.py` during generation, then restores it. Make sure you have write permissions.

### CSV Upload Fails
- Check file size (max 16MB)
- Ensure file is valid CSV format
- Check file permissions

### Generation Fails
- Check the error output in the result section
- Verify GAM credentials (`googleads.yaml` and `key.json`)
- Ensure all required fields are filled
- Check network connectivity to GAM API

## Security Notes

- The web UI runs on Flask's development server (not production-ready)
- For production use, deploy with a proper WSGI server (gunicorn, uWSGI)
- Consider adding authentication/authorization
- Use HTTPS in production

## Architecture

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Settings Management**: Dynamic settings.py generation
- **Task Execution**: Subprocess execution of existing task modules

## File Structure

```
.
├── app.py                 # Flask application
├── templates/
│   └── index.html         # Main UI template
├── static/
│   ├── css/
│   │   └── style.css     # Stylesheet
│   └── js/
│       └── main.js        # JavaScript logic
└── UI_README.md          # This file
```

## Future Enhancements

- [ ] Save/load configuration profiles
- [ ] Preview line items before creation
- [ ] Batch operations
- [ ] User authentication
- [ ] API endpoints for programmatic access
- [ ] Real-time progress updates via WebSockets
- [ ] Export configuration to JSON/YAML



