#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Job queue system for PythonAnywhere Always-on tasks

This worker processes jobs from the job_history table with status='pending'
and runs them using the same process_generate function from app.py
"""
import sqlite3
import json
import subprocess
import os
import sys
import time
import logging

# Setup logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler('job_queue.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_project_root():
    """Get project root directory, compatible with PythonAnywhere"""
    project_root = os.environ.get('PROJECT_ROOT')
    if project_root and os.path.exists(project_root):
        return project_root
    # Fallback to current file's directory parent
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_db_path():
    """Get database path"""
    project_root = get_project_root()
    return os.path.join(project_root, 'dfp_generator.db')

def process_next_job():
    """Process the next pending job from the queue"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get next pending job
        cursor = conn.execute("""
            SELECT job_id, config_snapshot, user_id, client_name, order_name
            FROM job_history
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
        """)
        
        job = cursor.fetchone()
        if not job:
            return False
        
        job_id = job['job_id']
        config_data = json.loads(job['config_snapshot'])
        
        logger.info(f"Processing job {job_id} (client: {job['client_name']}, order: {job['order_name']})")
        
        # Update status to processing
        conn.execute(
            "UPDATE job_history SET status = 'processing' WHERE job_id = ?",
            (job_id,)
        )
        conn.commit()
        
        # Add project root to path
        project_root = get_project_root()
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Set environment variable
        os.environ['PROJECT_ROOT'] = project_root
        
        # Import and call the processing function
        # We need to import app module to get process_generate
        try:
            import app
            app.process_generate(job_id, config_data)
            logger.info(f"Job {job_id} processing completed")
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            # Update status to failed
            conn.execute(
                "UPDATE job_history SET status = 'failed' WHERE job_id = ?",
                (job_id,)
            )
            conn.commit()
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error in process_next_job: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def run_worker():
    """Main worker loop for Always-on task"""
    logger.info("=" * 60)
    logger.info("Starting job queue worker...")
    logger.info(f"Project root: {get_project_root()}")
    logger.info(f"Database path: {get_db_path()}")
    logger.info("=" * 60)
    
    consecutive_empty_checks = 0
    max_empty_checks = 100  # After 100 empty checks (1000 seconds), log a message
    
    while True:
        try:
            processed = process_next_job()
            if not processed:
                consecutive_empty_checks += 1
                if consecutive_empty_checks >= max_empty_checks:
                    logger.info(f"No jobs found (checked {consecutive_empty_checks} times). Waiting...")
                    consecutive_empty_checks = 0
                # No jobs, wait before checking again
                time.sleep(10)
            else:
                # Job processed, reset counter and check for next one immediately
                consecutive_empty_checks = 0
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(60)  # Wait longer on error

if __name__ == '__main__':
    run_worker()
