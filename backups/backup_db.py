#!/usr/bin/env python3
"""
Backup script for SQLite database.
Creates timestamped backups locally and via SSH to remote servers.
Retains only the last 7 days of backups.
Writes a status JSON file for frontend consumption.
"""

import os
import sqlite3
import shutil
import subprocess
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configuration - can be overridden by environment variables or .env
DB_PATH = os.getenv("DATABASE_PATH", "data/gestor.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
BACKUP_REMOTE_SERVERS = os.getenv("BACKUP_REMOTE_SERVERS", "").split()  # space-separated list of "user@host:/path/"
BACKUP_SSH_KEY = os.getenv("BACKUP_SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))
STATUS_FILE = os.path.join(BACKUP_DIR, "backup_status.json")
LOG_FILE = os.path.join(BACKUP_DIR, "backup.log")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_timestamp():
    """Return current timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def is_sqlite3_file(filepath):
    """Check if file is a valid SQLite3 database by header."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(16)
            return header == b'SQLite format 3\0'
    except Exception:
        return False

def create_local_backup(src_db, backup_dir):
    """
    Create a consistent backup of SQLite database using the backup API.
    Returns path to backup file or None on failure.
    """
    timestamp = get_timestamp()
    backup_filename = f"gestor_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Ensure source DB exists and is valid
        if not os.path.exists(src_db):
            logger.error(f"Source database not found: {src_db}")
            return None
        if not is_sqlite3_file(src_db):
            logger.error(f"Source file is not a valid SQLite3 database: {src_db}")
            return None
            
        # Connect to source and destination
        src_conn = sqlite3.connect(src_db)
        dst_conn = sqlite3.connect(backup_path)
        
        # Perform backup
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        
        # Verify backup
        if not is_sqlite3_file(backup_path):
            logger.error(f"Backup verification failed: {backup_path}")
            os.remove(backup_path)
            return None
            
        logger.info(f"Local backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create local backup: {e}")
        # Cleanup partial file
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
        return None

def copy_via_ssh(local_file, remote_spec):
    """
    Copy file to remote server via SCP using SSH key.
    remote_spec format: "user@host:/remote/path/"
    Returns True on success.
    """
    if not remote_spec.strip():
        logger.warning("Empty remote spec, skipping SSH copy")
        return True  # treat as success (nothing to do)
        
    try:
        # Ensure remote spec ends with slash for directory
        if not remote_spec.endswith('/'):
            remote_spec += '/'
            
        # Build scp command
        cmd = [
            "scp",
            "-i", BACKUP_SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            local_file,
            remote_spec
        ]
        
        logger.info(f"Copying to remote: {remote_spec}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"SCP failed: {result.stderr}")
            return False
        else:
            logger.info(f"Successfully copied to {remote_spec}")
            return True
    except subprocess.TimeoutExpired:
        logger.error("SCP timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during SCP: {e}")
        return False

def cleanup_old_backups(backup_dir, days):
    """Remove backup files older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)
    pattern = "gestor_*.db"
    deleted = 0
    
    try:
        for item in Path(backup_dir).glob(pattern):
            # Extract timestamp from filename
            try:
                # filename format: gestor_YYYYMMDD_HHMMSS.db
                timestamp_str = item.stem.split('_', 1)[1]  # after first _
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                if file_time < cutoff:
                    item.unlink()
                    logger.info(f"Deleted old backup: {item.name}")
                    deleted += 1
            except (ValueError, IndexError):
                # Skip files that don't match pattern
                continue
        if deleted:
            logger.info(f"Cleaned up {deleted} old backups")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def write_status(status, last_success=None, last_error=None, message=""):
    """Write status JSON file atomically."""
    data = {
        "status": status,  # "ok", "error", "never_run"
        "last_success": last_success.isoformat() if last_success else None,
        "last_error": last_error.isoformat() if last_error else None,
        "message": message,
        "checked_at": datetime.now().isoformat()
    }
    temp_file = STATUS_FILE + ".tmp"
    try:
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, STATUS_FILE)
        logger.info(f"Status written: {status}")
    except Exception as e:
        logger.error(f"Failed to write status file: {e}")

def main():
    """Main backup routine."""
    logger.info("=== Starting backup process ===")
    ensure_dir(BACKUP_DIR)
    
    # Initialize status as error until proven otherwise
    success = False
    error_msg = ""
    backup_path = None
    
    try:
        # Step 1: Create local backup
        logger.info(f"Creating backup of {DB_PATH}")
        backup_path = create_local_backup(DB_PATH, BACKUP_DIR)
        if backup_path is None:
            error_msg = "Failed to create local backup"
            raise RuntimeError(error_msg)
        
        # Step 2: Copy to remote servers (if any configured)
        if BACKUP_REMOTE_SERVERS and any(BACKUP_REMOTE_SERVERS):
            logger.info(f"Copying to {len([s for s in BACKUP_REMOTE_SERVERS if s.strip()])} remote server(s)")
            all_success = True
            for remote in BACKUP_REMOTE_SERVERS:
                if not remote.strip():
                    continue
                if not copy_via_ssh(backup_path, remote):
                    all_success = False
            if not all_success:
                error_msg = "One or more remote copies failed"
                # We still consider partial success? For now, treat as error if any remote fails.
                raise RuntimeError(error_msg)
        else:
            logger.info("No remote servers configured, skipping SSH copy")
        
        # Step 3: Cleanup old backups (local only; remote cleanup should be handled similarly on remote)
        logger.info(f"Cleaning up backups older than {RETENTION_DAYS} days")
        cleanup_old_backups(BACKUP_DIR, RETENTION_DAYS)
        
        # If we reach here, everything succeeded
        success = True
        logger.info("Backup process completed successfully")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Backup process failed: {error_msg}")
        success = False
    finally:
        # Write status
        if success:
            write_status(
                status="ok",
                last_success=datetime.now(),
                last_error=None,
                message="Backup completed successfully"
            )
        else:
            write_status(
                status="error",
                last_success=None,
                last_error=datetime.now(),
                message=error_msg
            )
    
    logger.info("=== Backup process finished ===")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())