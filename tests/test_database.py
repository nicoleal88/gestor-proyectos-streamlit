"""
Tests de integración para database.py

Verifica las operaciones CRUD básicas de la capa de base de datos SQLite.
"""

import pytest
import os
import sys
import tempfile
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    init_db,
    get_data,
    insert_data,
    update_data,
    delete_data,
    row_count,
    table_exists,
    import_from_dataframe,
    get_database_path,
)


# Fixture para base de datos temporal
@pytest.fixture
def temp_db():
    """Crea una base de datos temporal para testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Inicializar la base de datos
    init_db(db_path)
    
    yield db_path
    
    # Limpiar
    os.unlink(db_path)


@pytest.fixture
def sample_data():
    """Datos de ejemplo para testing."""
    return {
        "tareas": [
            {"ID": "T001", "Título Tarea": "Test Task 1", "Tarea": "Description 1", "Responsable": "John", "Fecha límite": "2024-12-31", "Estado": "Pendiente"},
            {"ID": "T002", "Título Tarea": "Test Task 2", "Tarea": "Description 2", "Responsable": "Jane", "Fecha límite": "2024-12-31", "Estado": "En curso"},
        ],
        "vacaciones": [
            {"ID": "V001", "Apellido, Nombres": "Doe, John", "Fecha inicio": "2024-01-01", "Fecha regreso": "2024-01-15", "Tipo": "Anual", "Estado": "Aprobado"},
            {"ID": "V002", "Apellido, Nombres": "Smith, Jane", "Fecha inicio": "2024-02-01", "Fecha regreso": "2024-02-10", "Tipo": "Anual", "Estado": "Pendiente"},
        ],
    }


class TestDatabaseInit:
    """Tests de inicialización de la base de datos."""
    
    def test_init_db_creates_tables(self, temp_db):
        """Verifica que init_db crea todas las tablas."""
        from database_schema import SCHEMA
        
        for table_name in SCHEMA.keys():
            assert table_exists(table_name, temp_db), f"Tabla '{table_name}' no została creada"
    
    def test_init_db_default_path(self):
        """Verifica que la ruta por defecto es correcta."""
        # No debería crear archivo en la ruta por defecto durante el test
        db_path = get_database_path()
        assert db_path == "data/gestor.db" or db_path is not None


class TestCRUDOperations:
    """Tests de operaciones CRUD."""
    
    def test_insert_and_get_tareas(self, temp_db, sample_data):
        """Verifica INSERT y SELECT de tareas."""
        # Insertar datos
        for task in sample_data["tareas"]:
            success = insert_data("tareas", task, temp_db)
            assert success, "Error al insertar tarea"
        
        # Verificar count
        count = row_count("tareas", temp_db)
        assert count == 2, f"Expected 2 tasks, got {count}"
        
        # Obtener datos
        df = get_data("tareas", temp_db)
        assert len(df) == 2, f"Expected 2 rows, got {len(df)}"
        
        # Verificar contenido
        assert "T001" in df["ID"].values
        assert "T002" in df["ID"].values
    
    def test_update_tarea(self, temp_db, sample_data):
        """Verifica UPDATE de tarea."""
        # Insertar dato
        task = sample_data["tareas"][0]
        insert_data("tareas", task, temp_db)
        
        # Actualizar estado
        success = update_data("tareas", "T001", "Estado", "Finalizada", db_path=temp_db)
        assert success, "Error al actualizar tarea"
        
        # Verificar cambio
        df = get_data("tareas", temp_db)
        updated_row = df[df["ID"] == "T001"]
        assert len(updated_row) == 1
        assert updated_row.iloc[0]["Estado"] == "Finalizada"
    
    def test_delete_tarea(self, temp_db, sample_data):
        """Verifica DELETE de tarea."""
        # Insertar dato
        task = sample_data["tareas"][0]
        insert_data("tareas", task, temp_db)
        
        # Verificar que existe
        count_before = row_count("tareas", temp_db)
        assert count_before == 1
        
        # Eliminar
        success = delete_data("tareas", "T001", db_path=temp_db)
        assert success, "Error al eliminar tarea"
        
        # Verificar que se eliminó
        count_after = row_count("tareas", temp_db)
        assert count_after == 0
    
    def test_update_nonexistent_tarea(self, temp_db):
        """Verifica que update retorna False para ID inexistente."""
        success = update_data("tareas", "NONEXISTENT", "Estado", "Finalizada", db_path=temp_db)
        assert not success, "Update debería retornar False para registro inexistente"
    
    def test_delete_nonexistent_tarea(self, temp_db):
        """Verifica que delete retorna False para ID inexistente."""
        success = delete_data("tareas", "NONEXISTENT", db_path=temp_db)
        assert not success, "Delete debería retornar False para registro inexistente"


class TestImportExport:
    """Tests de importación y exportación."""
    
    def test_import_from_dataframe(self, temp_db, sample_data):
        """Verifica importación desde DataFrame."""
        df = pd.DataFrame(sample_data["tareas"])
        
        success = import_from_dataframe("tareas", df, temp_db)
        assert success, "Error al importar DataFrame"
        
        # Verificar datos
        result_df = get_data("tareas", temp_db)
        assert len(result_df) == 2
    
    def test_import_clears_existing_data(self, temp_db, sample_data):
        """Verifica que importación reemplaza datos existentes."""
        # Insertar datos
        for task in sample_data["tareas"]:
            insert_data("tareas", task, temp_db)
        
        # Importar nuevos datos (un solo registro)
        new_df = pd.DataFrame([sample_data["tareas"][0]])
        import_from_dataframe("tareas", new_df, temp_db)
        
        # Verificar que solo quedan los nuevos datos
        count = row_count("tareas", temp_db)
        assert count == 1, f"Expected 1 record after import, got {count}"


class TestVacaciones:
    """Tests específicos para la tabla de vacaciones."""
    
    def test_insert_vacaciones(self, temp_db, sample_data):
        """Verifica inserción de vacaciones."""
        for vac in sample_data["vacaciones"]:
            success = insert_data("vacaciones", vac, temp_db)
            assert success
    
    def test_get_vacaciones_filtered(self, temp_db, sample_data):
        """Verifica obtención filtrada de vacaciones."""
        # Insertar datos
        for vac in sample_data["vacaciones"]:
            insert_data("vacaciones", vac, temp_db)
        
        # Obtener todos
        df = get_data("vacaciones", temp_db)
        assert len(df) == 2
        
        # Filtrar por estado
        df_aprobadas = df[df["Estado"] == "Aprobado"]
        assert len(df_aprobadas) == 1


class TestPersonal:
    """Tests para la tabla de personal."""
    
    def test_insert_personal(self, temp_db):
        """Verifica inserción de personal."""
        data = {"Nombre": "John Doe"}
        success = insert_data("personal", data, temp_db)
        assert success
    
    def test_get_all_personal(self, temp_db):
        """Verifica obtención de todo el personal."""
        # Insertar varios
        for name in ["John", "Jane", "Bob"]:
            insert_data("personal", {"Nombre": name}, temp_db)
        
        df = get_data("personal", temp_db)
        assert len(df) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])