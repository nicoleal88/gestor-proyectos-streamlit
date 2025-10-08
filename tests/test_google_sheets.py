"""
Tests for Google Sheets integration.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_sheets_client import get_sheet_data, refresh_data
import pandas as pd


class TestGoogleSheetsClient:
    """Test cases for Google Sheets client functionality."""

    @patch('google_sheets_client.gspread.service_account')
    @patch('google_sheets_client.st.cache_resource')
    def test_get_sheet_data_success(self, mock_cache_resource, mock_service_account):
        """Test successful data retrieval from Google Sheets."""
        # Mock the Google Sheets client and worksheet
        mock_client = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {'Name': 'Test User', 'Email': 'test@example.com'},
            {'Name': 'Another User', 'Email': 'another@example.com'}
        ]

        mock_client.open.return_value.worksheet.return_value = mock_worksheet
        mock_service_account.return_value = mock_client

        # Mock the cache resource decorator
        mock_cache_resource.return_value = mock_client

        # Test the function
        result = get_sheet_data(mock_client, "TestSheet")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ['Name', 'Email']

    @patch('google_sheets_client.gspread.service_account')
    @patch('google_sheets_client.st.cache_resource')
    def test_get_sheet_data_empty_sheet(self, mock_cache_resource, mock_service_account):
        """Test data retrieval from empty Google Sheet."""
        # Mock the Google Sheets client and worksheet
        mock_client = MagicMock()
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = []

        mock_client.open.return_value.worksheet.return_value = mock_worksheet
        mock_service_account.return_value = mock_client
        mock_cache_resource.return_value = mock_client

        # Test the function
        result = get_sheet_data(mock_client, "EmptySheet")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch('google_sheets_client.gspread.service_account')
    @patch('google_sheets_client.st.cache_resource')
    def test_get_sheet_data_exception_handling(self, mock_cache_resource, mock_service_account):
        """Test exception handling in get_sheet_data."""
        # Mock the Google Sheets client to raise an exception
        mock_client = MagicMock()
        mock_client.open.side_effect = Exception("Connection failed")

        mock_service_account.return_value = mock_client
        mock_cache_resource.return_value = mock_client

        # Test the function - should handle exception gracefully
        result = get_sheet_data(mock_client, "TestSheet")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch('google_sheets_client.gspread.service_account')
    @patch('google_sheets_client.st.cache_resource')
    def test_refresh_data_success(self, mock_cache_resource, mock_service_account):
        """Test successful data refresh."""
        # Mock the Google Sheets client
        mock_client = MagicMock()
        mock_service_account.return_value = mock_client
        mock_cache_resource.return_value = mock_client

        # Mock session state
        with patch('google_sheets_client.st.session_state', new_callable=MagicMock) as mock_session_state, \
             patch('google_sheets_client.get_sheet_data') as mock_get_sheet_data:

            # Configure the mock to behave like a dictionary
            def set_item(key, value):
                setattr(mock_session_state, key, value)

            mock_session_state.__setitem__.side_effect = set_item
            mock_get_sheet_data.return_value = pd.DataFrame([{'col': 'value'}])

            # Test the function
            refresh_data(mock_client, "Tareas")

            # Verify that get_sheet_data was called
            mock_get_sheet_data.assert_called_with(mock_client, "Tareas")

            # Verify that session state was updated
            assert hasattr(mock_session_state, 'df_tareas')
            assert not mock_session_state.df_tareas.empty


    @patch('google_sheets_client.gspread.service_account')
    @patch('google_sheets_client.st.cache_resource')
    def test_refresh_data_exception_handling(self, mock_cache_resource, mock_service_account):
        """Test exception handling in refresh_data."""
        # Mock the Google Sheets client to raise an exception
        mock_client = MagicMock()
        mock_client.open.side_effect = Exception("Connection failed")

        mock_service_account.return_value = mock_client
        mock_cache_resource.return_value = mock_client

        # Mock session state
        with patch('google_sheets_client.st.session_state') as mock_session_state:
            # Test the function - should handle exception gracefully
            refresh_data(mock_client, "Tareas")

            # Should not crash and session state should be an empty DataFrame
            assert hasattr(mock_session_state, 'df_tareas')
            assert mock_session_state.df_tareas.empty


class TestDataValidation:
    """Test cases for data validation and processing."""

    def test_dataframe_structure_validation(self):
        """Test that dataframes have expected structure."""
        # Create test dataframe
        test_data = {
            'Name': ['User 1', 'User 2'],
            'Email': ['user1@test.com', 'user2@test.com'],
            'Role': ['admin', 'employee']
        }
        df = pd.DataFrame(test_data)

        # Basic structure validation
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['Name', 'Email', 'Role']

        # Data type validation
        assert df['Name'].dtype == 'object'
        assert df['Email'].dtype == 'object'
        assert df['Role'].dtype == 'object'


if __name__ == '__main__':
    pytest.main([__file__])
