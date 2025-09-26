"""
Pytest configuration and fixtures for the project.
"""
import pytest
import sys
import os

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_user_data():
    """Fixture providing sample user data for testing."""
    return {
        'admin': ['admin@test.com', 'admin2@test.com'],
        'employee': ['employee@test.com', 'employee2@test.com'],
        'guest': ['guest@test.com']
    }


@pytest.fixture
def sample_dataframe():
    """Fixture providing sample DataFrame for testing."""
    import pandas as pd
    return pd.DataFrame({
        'Name': ['Test User', 'Another User'],
        'Email': ['test@example.com', 'another@example.com'],
        'Role': ['admin', 'employee']
    })


@pytest.fixture
def mock_streamlit_secrets():
    """Fixture providing mocked Streamlit secrets."""
    secrets = {
        'roles': {
            'admin_emails': ['admin@test.com'],
            'empleado_emails': ['employee@test.com']
        }
    }
    return secrets
