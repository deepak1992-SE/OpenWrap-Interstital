# Configuration Guide for googleads.yaml

## Required DFP/GAM Information

To use this tool, you need to configure `googleads.yaml` with your Google Ad Manager credentials.

### Step 1: Get Your GAM Network Code

1. Log into Google Ad Manager: https://admanager.google.com/
2. Look at the URL in your browser. It will look like:
   ```
   https://admanager.google.com/12398712#delivery
   ```
3. The number `12398712` is your **network_code**
4. Alternatively, go to **Admin > Global Settings** in GAM to see your Network Code

### Step 2: Get Your Application Name

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Select your project (or create one if you haven't)
3. The project name at the top-left is your **application_name**
4. This should match the project where you created your service account

### Step 3: Configure googleads.yaml

Edit `googleads.yaml` and update these fields:

```yaml
ad_manager:
  application_name: "Your-Project-Name"  # Your Google Cloud Project name
  network_code: 12398712                  # Your GAM Network Code (from URL)
  path_to_private_key_file: key.json     # Path to your service account key
```

### Step 4: Verify Your key.json File

Make sure `key.json` is in the project root directory and contains:
- `type`: "service_account"
- `project_id`: Your Google Cloud Project ID
- `private_key_id`: Your private key ID
- `private_key`: Your private key
- `client_email`: Your service account email
- `client_id`: Your client ID
- `auth_uri`: "https://accounts.google.com/o/oauth2/auth"
- `token_uri`: "https://oauth2.googleapis.com/token"

### Step 5: Enable API Access in GAM

1. Log into GAM with admin rights
2. Go to **Admin > Global Settings**
3. Enable **API access** if not already enabled
4. Click **Add a service account user**
5. Enter the service account email (from `key.json` → `client_email`)
6. Set role to **Administrator**
7. Click **Save**

### Step 6: Test Your Configuration

Run this command to verify your setup:

```bash
python3 -m dfp.get_orders
```

If successful, it will return all orders in your GAM account.

## Example Configuration

```yaml
ad_manager:
  application_name: "My-GAM-Project"
  network_code: 12398712
  path_to_private_key_file: key.json
```

## Troubleshooting

### Error: "Invalid network code"
- Double-check your network code from the GAM URL
- Make sure there are no extra spaces or characters

### Error: "Authentication failed"
- Verify your `key.json` file is correct
- Ensure the service account email is added to GAM with Administrator role
- Check that API access is enabled in GAM

### Error: "Application name not found"
- Verify your Google Cloud Project name matches exactly
- Check that the service account belongs to this project



