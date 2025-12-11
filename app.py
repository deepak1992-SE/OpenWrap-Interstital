#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import tempfile
import csv
import yaml
import glob
import threading
import uuid
import time
import re
import sqlite3
import shutil
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import importlib.util

# Add project root to path
def get_project_root():
    """Get project root directory, compatible with PythonAnywhere"""
    # Try to get from environment variable first (PythonAnywhere)
    project_root = os.environ.get('PROJECT_ROOT')
    if project_root and os.path.exists(project_root):
        return project_root
    # Fallback to current file's directory
    return os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = get_project_root()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure logging
# Configure logging to both console and file
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = os.path.join(PROJECT_ROOT, 'app.log')

# Create file handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(log_format))

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file: {log_file}")

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Progress tracking storage (in-memory)
progress_store = {}
# Use an RLock to be safe if the same thread ever needs to acquire the lock multiple times,
# but in general we try to centralize locking inside update_progress.
progress_lock = threading.RLock()

# Database setup
# PythonAnywhere compatibility: Use absolute paths

DATABASE = os.path.join(PROJECT_ROOT, 'dfp_generator.db')


class User(UserMixin):
    def __init__(self, id, username, email=None):
        self.id = id
        self.username = username
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user[0], username=user[1], email=user[2])
    return None


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_progress_table():
    """Ensure the job_progress table exists for cross-process progress sharing"""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_progress (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                progress INTEGER,
                message TEXT,
                current_batch INTEGER,
                total_batches INTEGER,
                output TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()



def init_db():
    """Initialize database with tables"""
    conn = get_db_connection()
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create saved_configs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS saved_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            client_name TEXT,
            config_name TEXT NOT NULL,
            config_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create job_history table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS job_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            client_name TEXT,
            job_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            order_name TEXT,
            config_snapshot TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# Initialize database on startup
init_db()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_YAML_EXTENSIONS = {'yaml', 'yml'}
ALLOWED_JSON_EXTENSIONS = {'json'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_yaml_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_YAML_EXTENSIONS


def allowed_json_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_JSON_EXTENSIONS


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logger.info(f"Login attempt for username: {username}")
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')
        
        conn = None
        try:
            conn = get_db_connection()
            user = conn.execute(
                'SELECT id, username, password_hash, email, is_active FROM users WHERE username = ?',
                (username,)
            ).fetchone()
            
            if user and user[4] and check_password_hash(user[2], password):
                user_obj = User(id=user[0], username=user[1], email=user[3])
                login_user(user_obj)
                logger.info(f"User logged in successfully: {username}")
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                flash('Invalid username or password', 'error')
        except Exception as e:
            logger.error(f"Error during login: {e}", exc_info=True)
            flash('An error occurred during login. Please try again.', 'error')
        finally:
            if conn:
                conn.close()
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Sign up page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        email = request.form.get('email', '').strip()
        
        logger.info(f"Signup attempt for username: {username}")
        
        # Validation
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        conn = None
        try:
            conn = get_db_connection()
            # Check if username already exists
            existing_user = conn.execute(
                'SELECT id FROM users WHERE username = ?',
                (username,)
            ).fetchone()
            
            if existing_user:
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('signup.html')
            
            # Create new user
            # Use pbkdf2:sha256 method for better compatibility
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            conn.execute(
                'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                (username, password_hash, email if email else None)
            )
            conn.commit()
            logger.info(f"User created successfully: {username}")
            
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error creating user: {e}")
            flash('Username already exists. Please choose a different username.', 'error')
            return render_template('signup.html')
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            flash(f'An error occurred while creating your account: {str(e)}', 'error')
            return render_template('signup.html')
        finally:
            if conn:
                conn.close()
    
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    """Logout route"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main page with settings form"""
    return render_template('index.html', username=current_user.username)


@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors - return JSON for API routes, redirect for pages"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    flash('Please log in to access this page', 'error')
    return redirect(url_for('login'))


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden'}), 403
    flash('You do not have permission to access this page', 'error')
    return redirect(url_for('login'))


@app.route('/api/user-info', methods=['GET'])
@login_required
def get_user_info():
    """Get current user info"""
    try:
        return jsonify({
            'username': current_user.username,
            'email': current_user.email if hasattr(current_user, 'email') else None
        })
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500


@app.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    """Admin route to create users"""
    if request.method == 'POST':
        username = request.json.get('username') if request.is_json else request.form.get('username')
        password = request.json.get('password') if request.is_json else request.form.get('password')
        email = request.json.get('email') if request.is_json else request.form.get('email')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        try:
            conn = get_db_connection()
            password_hash = generate_password_hash(password)
            conn.execute(
                'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                (username, password_hash, email)
            )
            conn.commit()
            conn.close()
            
            if request.is_json:
                return jsonify({'success': True, 'message': f'User {username} created successfully'})
            flash(f'User {username} created successfully', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            error_msg = f'Username {username} already exists'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
    
    return render_template('admin.html')


@app.route('/api/settings/defaults', methods=['GET'])
@login_required
def get_default_settings():
    """Get default settings from settings.py"""
    try:
        # Try to import settings, handle import errors gracefully
        try:
            import settings
        except ImportError as e:
            logger.warning(f"Could not import settings: {e}")
            return jsonify({}), 200  # Return empty defaults
        
        # Try to read network_code from googleads.yaml
        network_code = None
        googleads_yaml_path = os.path.join(os.path.dirname(__file__), 'googleads.yaml')
        if os.path.exists(googleads_yaml_path):
            try:
                with open(googleads_yaml_path, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data and 'ad_manager' in yaml_data:
                        network_code = yaml_data['ad_manager'].get('network_code')
            except Exception as e:
                logger.warning(f"Could not read network_code from googleads.yaml: {e}")
        
        defaults = {
            'DFP_NETWORK_CODE': str(network_code) if network_code else None,
            'DFP_ORDER_NAME': getattr(settings, 'DFP_ORDER_NAME', ''),
            'DFP_USER_EMAIL_ADDRESS': getattr(settings, 'DFP_USER_EMAIL_ADDRESS', ''),
            'DFP_ADVERTISER_NAME': getattr(settings, 'DFP_ADVERTISER_NAME', ''),
            'DFP_ADVERTISER_TYPE': getattr(settings, 'DFP_ADVERTISER_TYPE', 'ADVERTISER'),
            'DFP_LINEITEM_TYPE': getattr(settings, 'DFP_LINEITEM_TYPE', 'PRICE_PRIORITY'),
            'DFP_TARGETED_PLACEMENT_NAMES': getattr(settings, 'DFP_TARGETED_PLACEMENT_NAMES', []),
            'DFP_PLACEMENT_SIZES': getattr(settings, 'DFP_PLACEMENT_SIZES', []),
            'DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST': getattr(settings, 'DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST', True),
            'DFP_USE_EXISTING_ORDER_IF_EXISTS': getattr(settings, 'DFP_USE_EXISTING_ORDER_IF_EXISTS', True),
            'DFP_NUM_CREATIVES_PER_LINE_ITEM': getattr(settings, 'DFP_NUM_CREATIVES_PER_LINE_ITEM', 1),
            'DFP_CURRENCY_CODE': getattr(settings, 'DFP_CURRENCY_CODE', 'USD'),
            'DFP_SAME_ADV_EXCEPTION': getattr(settings, 'DFP_SAME_ADV_EXCEPTION', False),
            'DFP_DEVICE_CATEGORIES': getattr(settings, 'DFP_DEVICE_CATEGORIES', None),
            'DFP_ROADBLOCK_TYPE': getattr(settings, 'DFP_ROADBLOCK_TYPE', 'ONE_OR_MORE'),
            'DFP_TARGETED_GEO': getattr(settings, 'DFP_TARGETED_GEO', None),
            'LINE_ITEM_PREFIX': getattr(settings, 'LINE_ITEM_PREFIX', None),
            'OPENWRAP_CUSTOM_SETUP_TYPE': getattr(settings, 'OPENWRAP_CUSTOM_SETUP_TYPE', None),
            'DFP_NETWORK_CODE': getattr(settings, 'DFP_NETWORK_CODE', None),
            'PREBID_BIDDER_CODE': getattr(settings, 'PREBID_BIDDER_CODE', None),
            'OPENWRAP_BUCKET_CSV': getattr(settings, 'OPENWRAP_BUCKET_CSV', 'LineItem.csv'),
            'PREBID_PRICE_BUCKETS': getattr(settings, 'PREBID_PRICE_BUCKETS', {
                'precision': 2,
                'min': 8,
                'max': 20,
                'increment': 0.50
            }),
            'OPENWRAP_SETUP_TYPE': getattr(settings, 'OPENWRAP_SETUP_TYPE', 'WEB'),
            'OPENWRAP_USE_1x1_CREATIVE': getattr(settings, 'OPENWRAP_USE_1x1_CREATIVE', False),
            'OPENWRAP_CREATIVE_TEMPLATE': getattr(settings, 'OPENWRAP_CREATIVE_TEMPLATE', None),
            'OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR': getattr(settings, 'OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR', None),
            'CURRENCY_EXCHANGE': getattr(settings, 'CURRENCY_EXCHANGE', True),
            'VIDEO_LENGTHS': getattr(settings, 'VIDEO_LENGTHS', []),
            'ADPOD_SLOTS': getattr(settings, 'ADPOD_SLOTS', []),
            'ENABLE_DEAL_LINEITEM': getattr(settings, 'ENABLE_DEAL_LINEITEM', False),
            'DEAL_CONFIG_TYPE': getattr(settings, 'DEAL_CONFIG_TYPE', None),
            'DEAL_CONFIG': getattr(settings, 'DEAL_CONFIG', None),
            'VIDEO_POSITION_TYPE': getattr(settings, 'VIDEO_POSITION_TYPE', None),
            'ADPOD_CREATIVE_CACHE_URL': getattr(settings, 'ADPOD_CREATIVE_CACHE_URL', 'https://ow.pubmatic.com'),
        }
        return jsonify(defaults)
    except Exception as e:
        logger.error(f"Error loading defaults: {str(e)}")
        # Return empty defaults instead of error to allow form to work
        return jsonify({}), 200


@app.route('/api/upload-googleads-yaml', methods=['POST'])
def upload_googleads_yaml():
    """Handle googleads.yaml upload and parse network_code"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_yaml_file(file.filename):
        try:
            # Read and parse YAML content
            yaml_content = file.read().decode('utf-8')
            yaml_data = yaml.safe_load(yaml_content)
            
            # Extract network_code
            network_code = None
            if yaml_data and 'ad_manager' in yaml_data:
                network_code = yaml_data['ad_manager'].get('network_code')
            
            if not network_code:
                return jsonify({'error': 'Could not find network_code in YAML file. Please ensure it follows the correct format.'}), 400
            
            # Save file
            filename = 'googleads.yaml'
            upload_path = os.path.join(os.path.dirname(__file__), filename)
            with open(upload_path, 'w') as f:
                f.write(yaml_content)
            
            return jsonify({
                'filename': filename,
                'network_code': str(network_code),
                'message': 'File uploaded successfully'
            })
        except yaml.YAMLError as e:
            return jsonify({'error': f'Invalid YAML format: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Error processing YAML file: {e}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Please upload a .yaml or .yml file'}), 400


@app.route('/api/upload-key-json', methods=['POST'])
@login_required
def upload_key_json():
    """Handle key.json upload and validate structure"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_json_file(file.filename):
        try:
            # Read and parse JSON content
            json_content = file.read().decode('utf-8')
            json_data = json.loads(json_content)
            
            # Validate required fields
            required_fields = ['client_email', 'private_key']
            missing_fields = [field for field in required_fields if field not in json_data]
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            # Mask email for preview (show first 3 chars and domain)
            email = json_data.get('client_email', '')
            masked_email = email[:3] + '***@' + email.split('@')[1] if '@' in email else '***'
            
            # Save file
            filename = 'key.json'
            upload_path = os.path.join(os.path.dirname(__file__), filename)
            with open(upload_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            return jsonify({
                'filename': filename,
                'client_email': masked_email,
                'message': 'File uploaded successfully'
            })
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Error processing JSON file: {e}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Please upload a .json file'}), 400


@app.route('/api/upload-csv', methods=['POST'])
@login_required
def upload_csv():
    """Handle CSV file upload and return parsed data"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            upload_path = os.path.join(os.path.dirname(__file__), filename)
            file.save(upload_path)
            
            # Parse CSV and return data
            csv_data = []
            with open(upload_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader, None)  # Skip header
                for row in reader:
                    if row and any(cell.strip() for cell in row):  # Skip empty rows
                        csv_data.append({
                            'start_range': row[0].strip() if len(row) > 0 else '',
                            'end_range': row[1].strip() if len(row) > 1 else '',
                            'granularity': row[2].strip() if len(row) > 2 else '',
                            'rate_id': row[3].strip() if len(row) > 3 else ''
                        })
            
            return jsonify({
                'filename': filename,
                'data': csv_data,
                'message': 'File uploaded successfully'
            })
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            return jsonify({'error': f'Error processing CSV file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/api/parse-csv', methods=['POST'])
@login_required
def parse_csv():
    """Parse CSV file and return JSON array of rows"""
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'Filename not provided'}), 400
    
    try:
        file_path = os.path.join(os.path.dirname(__file__), secure_filename(filename))
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        csv_data = []
        with open(file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)  # Skip header
            for row in reader:
                if row and any(cell.strip() for cell in row):  # Skip empty rows
                    csv_data.append({
                        'start_range': row[0].strip() if len(row) > 0 else '',
                        'end_range': row[1].strip() if len(row) > 1 else '',
                        'granularity': row[2].strip() if len(row) > 2 else '',
                        'rate_id': row[3].strip() if len(row) > 3 else ''
                    })
        
        return jsonify({'data': csv_data})
    except Exception as e:
        logger.error(f"Error parsing CSV file: {e}")
        return jsonify({'error': f'Error parsing CSV file: {str(e)}'}), 500


@app.route('/api/save-csv', methods=['POST'])
@login_required
def save_csv():
    """Save CSV data from table editor back to file"""
    data = request.get_json()
    filename = data.get('filename')
    csv_rows = data.get('data', [])
    
    if not filename:
        return jsonify({'error': 'Filename not provided'}), 400
    
    try:
        file_path = os.path.join(os.path.dirname(__file__), secure_filename(filename))
        
        # Write CSV file with header
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['start_range', 'end_range', 'granularity', 'rate_id[1=Average, 2=Minimum] '])
            for row in csv_rows:
                writer.writerow([
                    row.get('start_range', ''),
                    row.get('end_range', ''),
                    row.get('granularity', ''),
                    row.get('rate_id', '')
                ])
        
        return jsonify({'message': 'CSV file saved successfully', 'filename': filename})
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")
        return jsonify({'error': f'Error saving CSV file: {str(e)}'}), 500


@app.route('/api/list-csv-files', methods=['GET'])
@login_required
def list_csv_files():
    """List all CSV files in project directory"""
    try:
        project_dir = os.path.dirname(__file__)
        csv_files = []
        
        for file_path in glob.glob(os.path.join(project_dir, '*.csv')):
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            csv_files.append({
                'filename': filename,
                'size': file_size
            })
        
        # Sort by filename
        csv_files.sort(key=lambda x: x['filename'])
        
        return jsonify({'files': csv_files})
    except Exception as e:
        logger.error(f"Error listing CSV files: {e}")
        return jsonify({'error': f'Error listing CSV files: {str(e)}'}), 500


@app.route('/api/save-config', methods=['POST'])
@login_required
def save_config():
    """Save current form configuration"""
    try:
        data = request.get_json()
        client_name = data.get('client_name', '')
        config_name = data.get('config_name')
        config_data = data.get('config_data')
        
        if not config_name:
            return jsonify({'error': 'Config name is required'}), 400
        
        if not config_data:
            return jsonify({'error': 'Config data is required'}), 400
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO saved_configs (user_id, client_name, config_name, config_data, updated_at) VALUES (?, ?, ?, ?, ?)',
            (current_user.id, client_name, config_name, json.dumps(config_data), datetime.now())
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/saved-configs', methods=['GET'])
@login_required
def get_saved_configs():
    """Get all saved configs for current user"""
    try:
        conn = get_db_connection()
        configs = conn.execute(
            'SELECT id, client_name, config_name, created_at, updated_at FROM saved_configs WHERE user_id = ? ORDER BY updated_at DESC',
            (current_user.id,)
        ).fetchall()
        conn.close()
        
        config_list = []
        for config in configs:
            config_list.append({
                'id': config[0],
                'client_name': config[1],
                'config_name': config[2],
                'created_at': config[3],
                'updated_at': config[4]
            })
        
        return jsonify({'configs': config_list})
    except Exception as e:
        logger.error(f"Error fetching configs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/load-config/<int:config_id>', methods=['GET'])
@login_required
def load_config(config_id):
    """Load a specific saved configuration"""
    try:
        conn = get_db_connection()
        config = conn.execute(
            'SELECT config_data FROM saved_configs WHERE id = ? AND user_id = ?',
            (config_id, current_user.id)
        ).fetchone()
        conn.close()
        
        if not config:
            return jsonify({'error': 'Configuration not found'}), 404
        
        config_data = json.loads(config[0])
        return jsonify({'success': True, 'config': config_data})
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-config/<int:config_id>', methods=['DELETE'])
@login_required
def delete_config(config_id):
    """Delete a saved configuration"""
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            'DELETE FROM saved_configs WHERE id = ? AND user_id = ?',
            (config_id, current_user.id)
        )
        conn.commit()
        conn.close()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Configuration not found'}), 404
        
        return jsonify({'success': True, 'message': 'Configuration deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting config: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/job-history', methods=['GET'])
@login_required
def get_job_history():
    """Get job history for current user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        conn = get_db_connection()
        jobs = conn.execute(
            'SELECT id, client_name, job_id, status, order_name, created_at, completed_at FROM job_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
            (current_user.id, limit)
        ).fetchall()
        conn.close()
        
        job_list = []
        for job in jobs:
            job_list.append({
                'id': job[0],
                'client_name': job[1],
                'job_id': job[2],
                'status': job[3],
                'order_name': job[4],
                'created_at': job[5],
                'completed_at': job[6]
            })
        
        return jsonify({'jobs': job_list})
    except Exception as e:
        logger.error(f"Error fetching job history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/progress/<job_id>', methods=['GET'])
@login_required
def get_progress(job_id):
    """Get progress status for a job"""
    # First try shared DB progress (worker process writes here)
    try:
        conn = get_db_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_progress (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                progress INTEGER,
                message TEXT,
                current_batch INTEGER,
                total_batches INTEGER,
                output TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        row = conn.execute(
            'SELECT status, progress, message, current_batch, total_batches, output FROM job_progress WHERE job_id = ?',
            (job_id,)
        ).fetchone()
        conn.close()
        if row:
            return jsonify({
                'status': row[0],
                'progress': row[1],
                'message': row[2],
                'current_batch': row[3],
                'total_batches': row[4],
                'output': row[5] or ''
            })
    except Exception as e:
        logger.error(f"Error reading job_progress for {job_id}: {e}")
    
    # Fallback to job_history if progress row not found (cross-process visibility)
    try:
        conn = get_db_connection()
        row = conn.execute(
            'SELECT status, completed_at FROM job_history WHERE job_id = ?',
            (job_id,)
        ).fetchone()
        conn.close()
        if row:
            status = row[0]
            if status == 'completed':
                return jsonify({
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Completed',
                    'current_batch': 0,
                    'total_batches': 0,
                    'output': ''
                })
            if status == 'failed':
                return jsonify({
                    'status': 'failed',
                    'progress': 100,
                    'message': 'Failed',
                    'current_batch': 0,
                    'total_batches': 0,
                    'output': ''
                })
            if status == 'processing':
                return jsonify({
                    'status': 'processing',
                    'progress': 25,
                    'message': 'Processing...',
                    'current_batch': 0,
                    'total_batches': 0,
                    'output': ''
                })
            if status == 'pending':
                return jsonify({
                    'status': 'queued',
                    'progress': 0,
                    'message': 'Job queued. Waiting for worker...',
                    'current_batch': 0,
                    'total_batches': 0,
                    'output': ''
                })
    except Exception as e:
        logger.error(f"Error reading job_history for {job_id}: {e}")
    
    # Fallback to in-memory store (works only within same process)
    with progress_lock:
        progress = progress_store.get(job_id, {
            'status': 'not_found',
            'progress': 0,
            'message': 'Job not found',
            'current_batch': 0,
            'total_batches': 0,
            'output': ''
        })
    return jsonify(progress)


@app.route('/api/generate', methods=['POST'])
@login_required
def generate_line_items():
    """Generate line items based on form data"""
    try:
        logger.info("=" * 80)
        logger.info("Received POST request to /api/generate")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request content length: {request.content_length}")
        logger.info(f"User: {current_user.username} (ID: {current_user.id})")
        data = request.get_json()
        logger.info(f"Request data keys: {list(data.keys()) if data else 'None'}")
        logger.info(f"Request data: {json.dumps(data, indent=2) if data else 'None'}")
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        logger.info(f"Generated job_id: {job_id}")
        
        # Save job to history
        try:
            client_name = data.get('client_name', '')
            order_name = data.get('DFP_ORDER_NAME', '')
            logger.info(f"Job details - Client: {client_name}, Order: {order_name}")
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO job_history (user_id, client_name, job_id, status, order_name, config_snapshot) VALUES (?, ?, ?, ?, ?, ?)',
                (current_user.id, client_name, job_id, 'pending', order_name, json.dumps(data))
            )
            conn.commit()
            conn.close()
            logger.info(f"Job saved to history successfully")
        except Exception as e:
            logger.error(f"Error saving job to history: {e}", exc_info=True)
        
        # Initialize progress (avoid taking the lock here to prevent blocking the request)
        logger.info(f"Initializing progress store for job {job_id}")
        progress_store[job_id] = {
            'status': 'queued',
            'progress': 0,
            'message': 'Job queued. Waiting for worker...',
            'current_batch': 0,
            'total_batches': 0,
            'output': ''
        }
        logger.info(f"Progress store initialized: {progress_store[job_id]}")
        
        # Start processing in background thread (only if not on PythonAnywhere)
        # On PythonAnywhere, use Always-on task worker instead
        use_thread = os.environ.get('USE_BACKGROUND_THREAD', 'false').lower() == 'true'
        if use_thread:
            logger.info(f"Starting background thread for job {job_id}")
            thread = threading.Thread(target=process_generate, args=(job_id, data))
            thread.daemon = True
            thread.start()
            logger.info(f"Background thread started (thread name: {thread.name})")
        else:
            logger.info(f"Job {job_id} queued. Worker will process it (PythonAnywhere mode)")
        
        # Return immediately with job ID
        response = {
            'success': True,
            'job_id': job_id,
            'message': 'Job queued successfully. Processing will start shortly.'
        }
        logger.info(f"Returning response: {response}")
        logger.info("=" * 80)
        return jsonify(response)
    except Exception as e:
        logger.error(f"CRITICAL ERROR in generate_line_items: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def process_generate(job_id, data):
    """Process generation in background thread"""
    logger.info(f"[JOB {job_id}] Starting process_generate")
    logger.info(f"[JOB {job_id}] Received data keys: {list(data.keys()) if data else 'None'}")
    
    def update_progress(status, progress, message, current_batch=0, total_batches=0, output=''):
        logger.info(f"[JOB {job_id}] Progress update: status={status}, progress={progress}%, message='{message}', batch={current_batch}/{total_batches}")
        with progress_lock:
            progress_store[job_id] = {
                'status': status,
                'progress': progress,
                'message': message,
                'current_batch': current_batch,
                'total_batches': total_batches,
                'output': output
            }
        
        # Update job history and shared progress in database
        try:
            conn = get_db_connection()
            # Ensure progress table exists (cross-process visibility)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_progress (
                    job_id TEXT PRIMARY KEY,
                    status TEXT,
                    progress INTEGER,
                    message TEXT,
                    current_batch INTEGER,
                    total_batches INTEGER,
                    output TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                'UPDATE job_history SET status = ?, completed_at = ? WHERE job_id = ?',
                (status, datetime.now() if status in ['completed', 'failed'] else None, job_id)
            )
            conn.execute(
                'REPLACE INTO job_progress (job_id, status, progress, message, current_batch, total_batches, output, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (job_id, status, int(progress), message, int(current_batch), int(total_batches), output, datetime.now())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[JOB {job_id}] Error updating job history/progress: {e}")
    
    try:
        # Get user_id from session (we'll need to pass it or get from job_id lookup)
        # For now, we'll get it from the first job_history entry
        user_id = None
        client_name = data.get('client_name', '')
        order_name = data.get('DFP_ORDER_NAME', '')
        
        try:
            conn = get_db_connection()
            job_entry = conn.execute(
                'SELECT user_id FROM job_history WHERE job_id = ?',
                (job_id,)
            ).fetchone()
            if job_entry:
                user_id = job_entry[0]
            conn.close()
        except:
            pass
        
        logger.info(f"[JOB {job_id}] Step 1: Preparing settings...")
        update_progress('preparing', 5, 'Preparing settings...', output='Starting validation...\n')

        
        # Validate required fields
        if not data:
            logger.error(f"[JOB {job_id}] No data provided in request")
            update_progress('failed', 0, 'No data provided in request')
            return
        
        # Ensure sizes are provided
        sizes = data.get('DFP_PLACEMENT_SIZES', [])
        logger.info(f"[JOB {job_id}] Placement sizes: {sizes}")
        if not sizes or len(sizes) == 0:
            logger.error(f"[JOB {job_id}] No placement sizes provided")
            update_progress('failed', 0, 'At least one placement size is required')
            return
        
        # Backup original settings.py
        logger.info(f"[JOB {job_id}] Step 2: Backing up settings.py...")
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.py')
        backup_path = settings_path + '.backup'
        logger.info(f"[JOB {job_id}] Settings path: {settings_path}")
        
        # Check if settings.py exists
        if not os.path.exists(settings_path):
            logger.error(f"[JOB {job_id}] settings.py file not found at {settings_path}")
            update_progress('failed', 0, 'settings.py file not found in project root')
            return
        
        try:
            logger.info(f"[JOB {job_id}] Copying {settings_path} to {backup_path}")
            shutil.copy2(settings_path, backup_path)
            logger.info(f"[JOB {job_id}] Backup completed successfully")
        except Exception as e:
            logger.error(f"[JOB {job_id}] Failed to backup settings.py: {e}", exc_info=True)
            update_progress('failed', 0, f'Failed to backup settings.py: {str(e)}')
            return
        
        try:
            logger.info(f"[JOB {job_id}] Step 3: Generating settings file...")
            update_progress('generating_settings', 10, 'Generating settings file...', output='Backup completed... OK\nGenerating settings file...\n')
            logger.info(f"[JOB {job_id}] Calling generate_settings_file with data...")
            # Create new settings file
            try:
                settings_content = generate_settings_file(data)
            except Exception as gen_error:
                import traceback
                error_trace = traceback.format_exc()
                error_msg = f'Error generating settings file: {str(gen_error)}'
                logger.error(f"[JOB {job_id}] {error_msg}", exc_info=True)
                update_progress('failed', 10, error_msg, output=f'ERROR: {error_msg}\n{error_trace}\n')
                return
            logger.info(f"[JOB {job_id}] Generated settings file ({len(settings_content)} characters)")
            
            # Write new settings
            logger.info(f"[JOB {job_id}] Writing settings to {settings_path}")
            try:
                with open(settings_path, 'w') as f:
                    f.write(settings_content)
            except Exception as write_error:
                import traceback
                error_trace = traceback.format_exc()
                error_msg = f'Error writing settings file: {str(write_error)}'
                logger.error(f"[JOB {job_id}] {error_msg}", exc_info=True)
                update_progress('failed', 12, error_msg, output=f'ERROR: {error_msg}\n{error_trace}\n')
                return
            logger.info(f"[JOB {job_id}] Settings file written successfully")
            update_progress('generating_settings', 15, 'Settings file written', output='Writing settings file... OK\n')
            
            # Update googleads.yaml with network_code if provided
            network_code = data.get('DFP_NETWORK_CODE')
            if network_code:
                logger.info(f"[JOB {job_id}] Updating googleads.yaml with network_code: {network_code}")
                googleads_yaml_path = os.path.join(os.path.dirname(__file__), 'googleads.yaml')
                update_googleads_yaml(googleads_yaml_path, network_code)
                logger.info(f"[JOB {job_id}] Updated googleads.yaml successfully")
            
            # Determine which task to run
            partner_type = data.get('partner_type', 'openwrap')
            logger.info(f"[JOB {job_id}] Partner type: {partner_type}")
            
            # Estimate total batches
            pb_min = float(data.get('pb_min', 0))
            pb_max = float(data.get('pb_max', 20))
            pb_increment = float(data.get('pb_increment', 0.5))
            estimated_items = int((pb_max - pb_min) / pb_increment) + 1
            total_batches = max(1, (estimated_items + 449) // 450)
            logger.info(f"[JOB {job_id}] Estimated items: {estimated_items}, Total batches: {total_batches}")
            
            logger.info(f"[JOB {job_id}] Step 4: Starting subprocess...")
            update_progress('starting_subprocess', 15, f'Starting subprocess... (Estimated {total_batches} batch{"es" if total_batches > 1 else ""})', 0, total_batches)
            
            # Set environment variable to skip confirmation
            env = os.environ.copy()
            env['AUTO_CONFIRM'] = 'true'
            logger.info(f"[JOB {job_id}] Environment AUTO_CONFIRM set to: {env.get('AUTO_CONFIRM')}")
            
            # Execute the appropriate task
            logger.info(f"[JOB {job_id}] Starting subprocess for {partner_type}...")
            if partner_type == 'prebid':
                process = subprocess.Popen(
                    [sys.executable, '-m', 'tasks.add_new_prebid_partner'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(__file__),
                    env=env,
                    bufsize=1
                )
                logger.info("Waiting for prebid subprocess...")
                stdout, stderr = process.communicate(input='y\n', timeout=600)
                logger.info(f"Prebid subprocess completed with return code: {process.returncode}")
            else:
                logger.info(f"[JOB {job_id}] Starting OpenWrap subprocess...")
                script_path = os.path.join(os.path.dirname(__file__), 'tasks', 'add_new_openwrap_partner.py')
                logger.info(f"[JOB {job_id}] Script path: {script_path}")
                logger.info(f"[JOB {job_id}] Python executable: {sys.executable}")
                logger.info(f"[JOB {job_id}] Working directory: {os.path.dirname(__file__)}")
                
                try:
                    logger.info(f"[JOB {job_id}] Creating subprocess...")
                    process = subprocess.Popen(
                        [sys.executable, '-m', 'tasks.add_new_openwrap_partner'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,  # Merge stderr into stdout
                        text=True,
                        cwd=os.path.dirname(__file__),
                        env=env,
                        bufsize=1,
                        universal_newlines=True
                    )
                    logger.info(f"[JOB {job_id}] Subprocess started with PID: {process.pid}")
                    logger.info(f"[JOB {job_id}] Waiting for OpenWrap subprocess output...")
                    
                    # Monitor process output for progress updates
                    # We'll keep the full log in memory for this job and expose it via the `output`
                    # field on the /api/progress endpoint so the frontend can show complete logs.
                    output_lines = []
                    current_batch = 0
                    line_count = 0
                    confirmation_sent = False
                    update_progress('processing', 20, 'Subprocess started, waiting for output...', 0, total_batches)
                    
                    while True:
                        line = process.stdout.readline()
                        if not line:
                            if process.poll() is not None:
                                logger.info(f"[JOB {job_id}] Subprocess finished (poll returned: {process.poll()})")
                                break
                            else:
                                # Process still running but no output yet
                                continue
                        
                        line = line.rstrip()
                        if line:
                            line_count += 1
                            output_lines.append(line + '\n')
                            logger.info(f"[JOB {job_id}] [SUBPROCESS OUTPUT #{line_count}] {line}")
                            
                            # Use the full accumulated log so the frontend sees everything
                            output_text = ''.join(output_lines)
                            
                            # Check for confirmation prompt and send 'y' if not already sent
                            if ('Is this correct' in line or 'correct?' in line.lower()) and not confirmation_sent:
                                logger.info(f"[JOB {job_id}] Confirmation prompt detected, sending 'y'...")
                                try:
                                    process.stdin.write('y\n')
                                    process.stdin.flush()
                                    confirmation_sent = True
                                    logger.info(f"[JOB {job_id}] Confirmation 'y' sent successfully")
                                except Exception as stdin_error:
                                    logger.error(f"[JOB {job_id}] Error writing to stdin: {stdin_error}")
                            
                            # Check for batch progress indicators
                            if 'Processing batch' in line or ('batch' in line.lower() and ('/' in line or 'Processing' in line)):
                                match = re.search(r'batch\s+(\d+)/(\d+)', line, re.IGNORECASE)
                                if match:
                                    current_batch = int(match.group(1))
                                    total_batches = int(match.group(2))
                                    progress = 20 + int((current_batch / total_batches) * 70)  # 20-90%
                                    logger.info(f"[JOB {job_id}] Detected batch progress: {current_batch}/{total_batches}")
                                    current_progress = progress_store.get(job_id, {})
                                    safe_progress = max(current_progress.get('progress', 20), progress)
                                    update_progress(
                                        'processing',
                                        safe_progress,
                                        f'Processing batch {current_batch}/{total_batches}...',
                                        current_batch,
                                        total_batches,
                                        output_text
                                    )
                            
                            # Check for line item creation progress
                            if 'Creating' in line and 'line items' in line.lower():
                                match = re.search(r'Creating\s+(\d+)\s+line items', line, re.IGNORECASE)
                                if match:
                                    num_items = int(match.group(1))
                                    logger.info(f"[JOB {job_id}] Detected line item creation start: {num_items} items")
                                    update_progress('processing', 50, f'Creating {num_items} line items in DFP (this may take several minutes)...', current_batch, total_batches, output_text)
                            
                            # Check for DFP API call progress
                            if 'Calling DFP API' in line or 'DFP API call' in line:
                                logger.info(f"[JOB {job_id}] Detected DFP API call in progress")
                                current_progress = progress_store.get(job_id, {})
                                update_progress('processing', current_progress.get('progress', 55), 'DFP API is processing line items (please wait)...', current_batch, total_batches, output_text)
                            
                            # Check for successful line item creation
                            if 'Successfully created' in line and 'line items' in line.lower():
                                match = re.search(r'Successfully created\s+(\d+)\s+line items', line, re.IGNORECASE)
                                if match:
                                    num_created = int(match.group(1))
                                    logger.info(f"[JOB {job_id}] Detected line item creation completion: {num_created} items")
                                    update_progress('processing', 70, f'Successfully created {num_created} line items. Associating with creatives...', current_batch, total_batches, output_text)
                                    current_progress = progress_store.get(job_id, {})
                                    safe_progress = max(70, current_progress.get('progress', 70))
                                    update_progress('processing', safe_progress, f'Processing batch {current_batch}/{total_batches}...', current_batch, total_batches, output_text)
                        elif 'Waiting' in line and 'seconds' in line:
                            # Update message but keep progress
                            logger.info(f"[JOB {job_id}] Detected wait message: {line}")
                            current_progress = progress_store.get(job_id, {})
                            update_progress(
                                'processing',
                                current_progress.get('progress', 20),
                                line.strip(),
                                current_batch,
                                total_batches,
                                output_text
                            )
                        elif 'error' in line.lower() or 'exception' in line.lower() or 'failed' in line.lower():
                            logger.warning(f"[JOB {job_id}] [ERROR DETECTED] {line}")
                            current_progress = progress_store.get(job_id, {})
                            update_progress(
                                'processing',
                                current_progress.get('progress', 20),
                                f'Warning: {line[:100]}',
                                current_batch,
                                total_batches,
                                output_text
                            )
                        else:
                            # Update output with any line
                            current_progress = progress_store.get(job_id, {})
                            update_progress(
                                'processing',
                                current_progress.get('progress', 20),
                                current_progress.get('message', 'Processing...'),
                                current_progress.get('current_batch', 0),
                                total_batches,
                                output_text
                            )
                    
                    # Close stdin after reading all output
                    try:
                        if not confirmation_sent:
                            logger.warning(f"[JOB {job_id}] Confirmation was never sent, sending now...")
                            process.stdin.write('y\n')
                            process.stdin.flush()
                        process.stdin.close()
                    except:
                        pass
                    
                    stdout = ''.join(output_lines)
                    return_code = process.poll()
                    logger.info(f"[JOB {job_id}] OpenWrap subprocess completed")
                    logger.info(f"[JOB {job_id}] Return code: {return_code}")
                    logger.info(f"[JOB {job_id}] Total output lines: {line_count}")
                    logger.info(f"[JOB {job_id}] Output length: {len(stdout)} characters")
                    if stdout:
                        logger.info(f"[JOB {job_id}] Last 500 chars of output:\n{stdout[-500:]}")
                    
                except Exception as subprocess_error:
                    logger.error(f"[JOB {job_id}] Error starting subprocess: {subprocess_error}", exc_info=True)
                    raise
            
            # Restore original settings
            logger.info(f"[JOB {job_id}] Step 5: Restoring original settings.py...")
            shutil.copy2(backup_path, settings_path)
            os.remove(backup_path)
            logger.info(f"[JOB {job_id}] Settings restored successfully")
            
            return_code = process.returncode if 'process' in locals() else -1
            logger.info(f"[JOB {job_id}] Final return code: {return_code}")
            
            if return_code == 0:
                logger.info(f"[JOB {job_id}] SUCCESS: Subprocess completed successfully")
                update_progress('completed', 100, 'Line items created successfully!', total_batches, total_batches, stdout if 'stdout' in locals() else '')
            else:
                error_output = (stderr if 'stderr' in locals() and stderr else stdout) if 'stdout' in locals() else 'No output captured'
                logger.error(f"[JOB {job_id}] FAILED: Subprocess returned non-zero exit code: {return_code}")
                logger.error(f"[JOB {job_id}] Error output: {error_output[-1000:] if error_output else 'None'}")
                current_progress = progress_store.get(job_id, {})
                update_progress(
                    'failed',
                    current_progress.get('progress', 50),
                    f'Failed to create line items (exit code: {return_code})',
                    current_progress.get('current_batch', 0),
                    total_batches,
                    error_output
                )
                
        except subprocess.TimeoutExpired:
            logger.error(f"[JOB {job_id}] Subprocess timed out after 10 minutes")
            # Restore original settings
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, settings_path)
                os.remove(backup_path)
            current_progress = progress_store.get(job_id, {})
            update_progress(
                'failed',
                current_progress.get('progress', 50),
                'Operation timed out after 10 minutes',
                current_progress.get('current_batch', 0),
                current_progress.get('total_batches', 0)
            )
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[JOB {job_id}] Exception in subprocess execution: {str(e)}", exc_info=True)
            logger.error(f"[JOB {job_id}] Traceback:\n{error_trace}")
            # Restore original settings on error
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, settings_path)
                    os.remove(backup_path)
                    logger.info(f"[JOB {job_id}] Settings restored after error")
                except Exception as restore_error:
                    logger.error(f"[JOB {job_id}] Failed to restore settings: {restore_error}")
            current_progress = progress_store.get(job_id, {})
            update_progress(
                'failed',
                current_progress.get('progress', 0),
                f'Error: {str(e)}',
                current_progress.get('current_batch', 0),
                current_progress.get('total_batches', 0),
                error_trace
            )
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"[JOB {job_id}] CRITICAL ERROR in process_generate: {str(e)}", exc_info=True)
        logger.error(f"[JOB {job_id}] Full traceback:\n{error_trace}")
        if job_id in progress_store:
            progress_store[job_id]['status'] = 'failed'
            progress_store[job_id]['message'] = f'Critical error: {str(e)}'
            progress_store[job_id]['output'] = error_trace
        else:
            # Initialize progress store if it doesn't exist
            progress_store[job_id] = {
                'status': 'failed',
                'progress': 0,
                'message': f'Critical error: {str(e)}',
                'current_batch': 0,
                'total_batches': 0,
                'output': error_trace
            }


def update_googleads_yaml(file_path, network_code):
    """Update or create googleads.yaml file with network_code"""
    try:
        # Try to read existing file
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                yaml_content = f.read()
            yaml_data = yaml.safe_load(yaml_content)
        else:
            yaml_data = {}
        
        # Ensure ad_manager section exists
        if 'ad_manager' not in yaml_data:
            yaml_data['ad_manager'] = {}
        
        # Update network_code
        yaml_data['ad_manager']['network_code'] = int(network_code) if network_code.isdigit() else network_code
        
        # Set defaults if not present
        if 'application_name' not in yaml_data['ad_manager']:
            yaml_data['ad_manager']['application_name'] = 'API-Access'
        if 'path_to_private_key_file' not in yaml_data['ad_manager']:
            yaml_data['ad_manager']['path_to_private_key_file'] = 'key.json'
        
        # Write back to file
        with open(file_path, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.warning(f"Could not update googleads.yaml: {e}")
        # Create a basic file if update fails
        try:
            with open(file_path, 'w') as f:
                f.write(f"""ad_manager:
  application_name: API-Access
  network_code: {network_code}
  path_to_private_key_file: key.json
""")
        except Exception as e2:
            logger.error(f"Failed to create googleads.yaml: {e2}")


def generate_settings_file(data):
    """Generate settings.py content from form data"""
    lines = [
        "import os",
        "",
        "ROOT_DIR = os.path.dirname(os.path.abspath(__file__))",
        "GOOGLEADS_YAML_FILE = os.path.join(ROOT_DIR, 'googleads.yaml')",
        "",
        "#########################################################################",
        "# DFP SETTINGS",
        "#########################################################################",
        "",
        f"DFP_ORDER_NAME = {repr(data.get('DFP_ORDER_NAME', ''))}",
        f"DFP_USER_EMAIL_ADDRESS = {repr(data.get('DFP_USER_EMAIL_ADDRESS', ''))}",
        f"DFP_ADVERTISER_NAME = {repr(data.get('DFP_ADVERTISER_NAME', ''))}",
        f"DFP_ADVERTISER_TYPE = {repr(data.get('DFP_ADVERTISER_TYPE', 'ADVERTISER'))}",
        f"DFP_LINEITEM_TYPE = {repr(data.get('DFP_LINEITEM_TYPE', 'PRICE_PRIORITY'))}",
    ]
    
    # Handle placements
    placements = data.get('DFP_TARGETED_PLACEMENT_NAMES', [])
    if isinstance(placements, str):
        placements = [p.strip() for p in placements.split(',') if p.strip()]
    lines.append(f"DFP_TARGETED_PLACEMENT_NAMES = {repr(placements)}")
    
    # Handle sizes
    sizes = data.get('DFP_PLACEMENT_SIZES', [])
    if isinstance(sizes, str):
        # Try to parse JSON string
        try:
            sizes = json.loads(sizes)
        except:
            sizes = []
    lines.append(f"DFP_PLACEMENT_SIZES = {repr(sizes)}")
    
    # Boolean settings
    lines.append(f"DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST = {data.get('DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST', True)}")
    lines.append(f"DFP_USE_EXISTING_ORDER_IF_EXISTS = {data.get('DFP_USE_EXISTING_ORDER_IF_EXISTS', True)}")
    lines.append(f"DFP_NUM_CREATIVES_PER_LINE_ITEM = {data.get('DFP_NUM_CREATIVES_PER_LINE_ITEM', 1)}")
    lines.append(f"DFP_CURRENCY_CODE = {repr(data.get('DFP_CURRENCY_CODE', 'USD'))}")
    lines.append(f"DFP_SAME_ADV_EXCEPTION = {data.get('DFP_SAME_ADV_EXCEPTION', False)}")
    
    # Device categories
    device_categories = data.get('DFP_DEVICE_CATEGORIES', None)
    if device_categories:
        if isinstance(device_categories, str):
            device_categories = [c.strip() for c in device_categories.split(',') if c.strip()]
        lines.append(f"DFP_DEVICE_CATEGORIES = {repr(device_categories)}")
    else:
        lines.append("DFP_DEVICE_CATEGORIES = None")
    
    lines.append(f"DFP_ROADBLOCK_TYPE = {repr(data.get('DFP_ROADBLOCK_TYPE', 'ONE_OR_MORE'))}")
    
    # Targeted GEO - only set if provided, otherwise use empty list (not None)
    # Empty list is cleaner than None and makes it easier to check if geo targeting is needed
    targeted_geo = data.get('DFP_TARGETED_GEO', None)
    if targeted_geo:
        if isinstance(targeted_geo, str):
            targeted_geo = [g.strip() for g in targeted_geo.split(',') if g.strip()]
        if targeted_geo:  # Only add if list is not empty after processing
            lines.append(f"DFP_TARGETED_GEO = {repr(targeted_geo)}")
        else:
            lines.append("DFP_TARGETED_GEO = []")
    else:
        lines.append("DFP_TARGETED_GEO = []")
    
    prefix = data.get('LINE_ITEM_PREFIX', None)
    if prefix:
        lines.append(f"LINE_ITEM_PREFIX = {repr(prefix)}")
    else:
        lines.append("LINE_ITEM_PREFIX = None")
    
    lines.append("")
    lines.append("#########################################################################")
    lines.append("# PREBID/OPENWRAP SETTINGS")
    lines.append("#########################################################################")
    lines.append("")
    
    # Bidder code
    bidder_code = data.get('PREBID_BIDDER_CODE', None)
    if bidder_code:
        if isinstance(bidder_code, str):
            bidder_code = [b.strip() for b in bidder_code.split(',') if b.strip()]
            if len(bidder_code) == 1:
                bidder_code = bidder_code[0]
        lines.append(f"PREBID_BIDDER_CODE = {repr(bidder_code)}")
    else:
        lines.append("PREBID_BIDDER_CODE = None")
    
    # CSV file
    csv_file = data.get('OPENWRAP_BUCKET_CSV', 'LineItem.csv')
    lines.append(f"OPENWRAP_BUCKET_CSV = {repr(csv_file)}")
    
    # Price buckets (for Prebid)
    price_buckets = data.get('PREBID_PRICE_BUCKETS', {})
    if price_buckets:
        lines.append(f"PREBID_PRICE_BUCKETS = {repr(price_buckets)}")
    
    # Setup type (handle custom setup type)
    setup_type = data.get('OPENWRAP_SETUP_TYPE', 'WEB')
    custom_setup_type = data.get('OPENWRAP_CUSTOM_SETUP_TYPE', None)
    if setup_type == 'CUSTOM' and custom_setup_type:
        setup_type = custom_setup_type
    lines.append(f"OPENWRAP_SETUP_TYPE = {repr(setup_type)}")
    
    lines.append(f"OPENWRAP_USE_1x1_CREATIVE = {data.get('OPENWRAP_USE_1x1_CREATIVE', False)}")
    
    # Creative template
    creative_template = data.get('OPENWRAP_CREATIVE_TEMPLATE', None)
    if creative_template:
        if isinstance(creative_template, str):
            creative_template = [t.strip() for t in creative_template.split(',') if t.strip()]
            if len(creative_template) == 1:
                creative_template = creative_template[0]
        lines.append(f"OPENWRAP_CREATIVE_TEMPLATE = {repr(creative_template)}")
    else:
        lines.append("OPENWRAP_CREATIVE_TEMPLATE = None")
    
    # Native creative var
    native_var = data.get('OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR', None)
    if native_var:
        lines.append(f"OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR = {repr(native_var)}")
    else:
        lines.append("OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR = None")
    
    lines.append(f"CURRENCY_EXCHANGE = {data.get('CURRENCY_EXCHANGE', True)}")
    
    # Video lengths
    video_lengths = data.get('VIDEO_LENGTHS', [])
    if isinstance(video_lengths, str):
        video_lengths = [int(v.strip()) for v in video_lengths.split(',') if v.strip()]
    lines.append(f"VIDEO_LENGTHS = {repr(video_lengths)}")
    
    # ADPOD slots
    adpod_slots = data.get('ADPOD_SLOTS', [])
    if isinstance(adpod_slots, str):
        adpod_slots = [int(s.strip()) for s in adpod_slots.split(',') if s.strip()]
    lines.append(f"ADPOD_SLOTS = {repr(adpod_slots)}")
    
    lines.append(f"ENABLE_DEAL_LINEITEM = {data.get('ENABLE_DEAL_LINEITEM', False)}")
    
    deal_config_type = data.get('DEAL_CONFIG_TYPE', None)
    if deal_config_type:
        lines.append(f"DEAL_CONFIG_TYPE = {repr(deal_config_type)}")
    else:
        lines.append("DEAL_CONFIG_TYPE = None")
    
    # Deal config (complex JSON)
    deal_config = data.get('DEAL_CONFIG', None)
    if deal_config:
        if isinstance(deal_config, str):
            try:
                deal_config = json.loads(deal_config)
            except:
                deal_config = None
        if deal_config:
            lines.append(f"DEAL_CONFIG = {repr(deal_config)}")
        else:
            lines.append("DEAL_CONFIG = None")
    else:
        lines.append("DEAL_CONFIG = None")
    
    video_position = data.get('VIDEO_POSITION_TYPE', None)
    if video_position:
        lines.append(f"VIDEO_POSITION_TYPE = {repr(video_position)}")
    else:
        lines.append("VIDEO_POSITION_TYPE = None")
    
    cache_url = data.get('ADPOD_CREATIVE_CACHE_URL', 'https://ow.pubmatic.com')
    lines.append(f"ADPOD_CREATIVE_CACHE_URL = {repr(cache_url)}")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8888))
    print(f"\n{'='*60}")
    print(f"DFP Line Item Generator Web UI")
    print(f"{'='*60}")
    print(f"Server starting on http://localhost:{port}")
    print(f"Open your browser and navigate to: http://localhost:{port}")
    print(f"{'='*60}\n")
    # Disable reloader to prevent killing subprocess when settings.py changes
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)

