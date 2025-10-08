"""
Tests for the main app navigation and authentication system.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import obtener_rol_usuario, tiene_permiso, get_available_pages, ROLES_PERMISOS


class TestAuthentication:
    """Test cases for user authentication and role management."""

    def test_obtener_rol_usuario_admin(self):
        """Test that admin email returns admin role."""
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.get.return_value = {'admin_emails': ['admin@test.com']}
            result = obtener_rol_usuario('admin@test.com')
            assert result == 'admin'

    def test_obtener_rol_usuario_employee(self):
        """Test that employee email returns employee role."""
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.get.return_value = {
                'admin_emails': ['admin@test.com'],
                'empleado_emails': ['employee@test.com']
            }
            result = obtener_rol_usuario('employee@test.com')
            assert result == 'empleado'

    def test_obtener_rol_usuario_guest(self):
        """Test that unknown email returns guest role."""
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.get.return_value = {'admin_emails': ['admin@test.com']}
            result = obtener_rol_usuario('unknown@test.com')
            assert result == 'invitado'

    def test_obtener_rol_usuario_none_email(self):
        """Test that None email returns guest role."""
        result = obtener_rol_usuario(None)
        assert result == 'invitado'

    def test_obtener_rol_usuario_empty_email(self):
        """Test that empty email returns guest role."""
        result = obtener_rol_usuario('')
        assert result == 'invitado'


class TestPermissions:
    """Test cases for role-based permissions."""

    def test_tiene_permiso_admin_all_access(self):
        """Test that admin has access to all sections."""
        assert tiene_permiso('admin', 'tareas') == True
        assert tiene_permiso('admin', 'vacaciones') == True
        assert tiene_permiso('admin', 'horarios') == True

    def test_tiene_permiso_employee_limited_access(self):
        """Test that employee has limited access."""
        assert tiene_permiso('empleado', 'tareas') == True
        assert tiene_permiso('empleado', 'vacaciones') == True
        assert tiene_permiso('empleado', 'horarios') == False

    def test_tiene_permiso_guest_minimal_access(self):
        """Test that guest has minimal access."""
        assert tiene_permiso('invitado', 'inicio') == True
        assert tiene_permiso('invitado', 'tareas') == False

    def test_tiene_permiso_invalid_role(self):
        """Test that invalid role has no access."""
        assert tiene_permiso('invalid_role', 'tareas') == False

    def test_tiene_permiso_invalid_section(self):
        """Test that valid role with invalid section has no access."""
        assert tiene_permiso('admin', 'invalid_section') == False


class TestNavigation:
    """Test cases for navigation system."""

    def test_get_available_pages_admin(self):
        """Test that admin gets all available pages."""
        # Create temporary page files for testing
        test_pages_dir = 'test_pages'
        os.makedirs(test_pages_dir, exist_ok=True)

        # Create test page files
        test_files = [
            '00_Inicio.py',
            '01_Tareas.py',
            '02_Vacaciones.py'
        ]

        for filename in test_files:
            with open(os.path.join(test_pages_dir, filename), 'w') as f:
                f.write('def page():\n    pass\n')

        try:
            with patch('app.os.path.dirname') as mock_dirname, \
                 patch('app.os.path.exists') as mock_exists, \
                 patch('app.os.listdir') as mock_listdir:

                mock_dirname.return_value = '/test'
                mock_exists.return_value = True
                mock_listdir.return_value = test_files

                result = get_available_pages('admin')
                assert len(result) == len(test_files)

        finally:
            # Clean up test files
            for filename in test_files:
                test_file = os.path.join(test_pages_dir, filename)
                if os.path.exists(test_file):
                    os.remove(test_file)
            os.rmdir(test_pages_dir)

    def test_get_available_pages_employee(self):
        """Test that employee gets limited pages."""
        # This test would require mocking the PAGE_PERMISSIONS mapping
        # and verifying that only allowed pages are returned
        pass

    def test_get_available_pages_no_pages_dir(self):
        """Test behavior when pages directory doesn't exist."""
        with patch('app.os.path.dirname') as mock_dirname, \
             patch('app.os.path.exists') as mock_exists:

            mock_dirname.return_value = '/test'
            mock_exists.return_value = False

            result = get_available_pages('admin')
            assert result == []


if __name__ == '__main__':
    pytest.main([__file__])
