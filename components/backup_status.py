import streamlit as st
import json
import os
from datetime import datetime

def render_backup_status():
    """
    Render backup status indicator in the sidebar.
    Reads backups/backup_status.json and displays:
    - Green light + success message if last backup succeeded
    - Red light + error message if last backup failed
    - Grey light + 'No backups yet' if never run
    """
    status_file = os.path.join(os.path.dirname(__file__), '..', 'backups', 'backup_status.json')
    status_file = os.path.normpath(status_file)
    
    # Default state
    status = "never_run"
    last_success = None
    last_error = None
    message = "No backups have been run yet."
    
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                data = json.load(f)
                status = data.get('status', 'never_run')
                last_success = data.get('last_success')
                last_error = data.get('last_error')
                message = data.get('message', '')
    except Exception as e:
        message = f"Error reading backup status: {e}"
        status = "error"
    
    # Choose icon and color based on status
    if status == "ok":
        icon = "🟢"  # green circle
        if last_success:
            dt = datetime.fromisoformat(last_success)
            # Format: YYYY-MM-DD HH:MM UTC
            datetime_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            message = f"Backup OK - Último: {datetime_str}"
        else:
            message = "Backup OK"
    elif status == "error":
        icon = "🔴"  # red circle
        if last_error:
            dt = datetime.fromisoformat(last_error)
            # Format: YYYY-MM-DD HH:MM UTC
            datetime_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            message = f"Backup FALLIDO: {datetime_str}"
        else:
            message = "Backup FALLIDO"
    else:  # never_run or other
        icon = "⚪"  # white circle
        # message already set
    
    # Display in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**{icon} Copia de Seguridad**")
        st.caption(message)

# For testing outside of Streamlit
if __name__ == "__main__":
    # This won't work outside Streamlit context, but we can test the logic
    print("Backup status component - to be used in Streamlit sidebar")