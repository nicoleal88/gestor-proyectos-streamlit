"""
Tests de migración de datos

Verifica la integridad de los datos migrados desde Google Sheets hacia SQLite.
"""

import pytest
import os
import sys
import tempfile
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, get_data, import_from_dataframe, row_count
from database_schema import SCHEMA


# Mapeo de hojas a tablas (mismo que en migrate_from_sheets.py)
SHEET_TO_TABLE_MAP = {
    "Tareas": "tareas",
    "Vacaciones": "vacaciones",
    "Compensados": "compensados",
    "Notas": "notas",
    "Personal": "personal",
    "Eventos": "eventos",
    "Vehiculos": "vehiculos",
    "Viajes": "viajes",
    "ViajesUpdates": "viajes_updates",
    "Destinos": "destinos",
    "Feriados_Manuales": "feriados",
}


@pytest.fixture
def temp_db_migration():
    """Base de datos temporal para testing migración."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    init_db(db_path)
    yield db_path
    
    os.unlink(db_path)


@pytest.fixture
def mock_google_sheets_data():
    """Datos mock que simulan lo que vendría de Google Sheets."""
    return {
        "tareas": pd.DataFrame([
            {"ID": "T001", "Título Tarea": "Tarea 1", "Tarea": "Descripción 1", "Responsable": "John", "Fecha límite": "2024-12-31", "Estado": "Pendiente"},
            {"ID": "T002", "Título Tarea": "Tarea 2", "Tarea": "Descripción 2", "Responsable": "Jane", "Fecha límite": "2024-12-31", "Estado": "En curso"},
        ]),
        "vacaciones": pd.DataFrame([
            {"ID": "V001", "Apellido, Nombres": "Doe, John", "Fecha inicio": "2024-01-01", "Fecha regreso": "2024-01-15", "Tipo": "Anual", "Estado": "Aprobado"},
            {"ID": "V002", "Apellido, Nombres": "Smith, Jane", "Fecha inicio": "2024-02-01", "Fecha regreso": "2024-02-10", "Tipo": "Anual", "Estado": "Pendiente"},
        ]),
        "compensados": pd.DataFrame([
            {"ID": "C001", "Apellido, Nombres": "Doe, John", "Desde fecha": "2024-01-01", "Hasta fecha": "2024-01-01", "Desde hora": "08:00", "Hasta hora": "12:00", "Tipo": "Hora extra", "Estado": "Aprobado"},
        ]),
        "notas": pd.DataFrame([
            {"ID": "N001", "Remitente": "John", "Destinatario": "Jane", "Motivo": "Solicitud", "Fecha": "2024-01-01", "Estado": "Pendiente"},
        ]),
        "personal": pd.DataFrame([
            {"Nombre": "John Doe"},
            {"Nombre": "Jane Smith"},
        ]),
    }


class TestMigrationIntegrity:
    """Tests de integridad de la migración."""
    
    def test_row_count_matches(self, temp_db_migration, mock_google_sheets_data):
        """Verifica que la cantidad de registros migrados coincide."""
        # Importar cada tabla
        for table_name, df in mock_google_sheets_data.items():
            import_from_dataframe(table_name, df, temp_db_migration)
        
        # Verificar counts
        assert row_count("tareas", temp_db_migration) == 2
        assert row_count("vacaciones", temp_db_migration) == 2
        assert row_count("compensados", temp_db_migration) == 1
        assert row_count("notas", temp_db_migration) == 1
        assert row_count("personal", temp_db_migration) == 2
    
    def test_data_integrity_after_migration(self, temp_db_migration, mock_google_sheets_data):
        """Verifica que los datos se migran correctamente."""
        # Migrar tareas
        df = mock_google_sheets_data["tareas"]
        import_from_dataframe("tareas", df, temp_db_migration)
        
        # Obtener de SQLite
        result = get_data("tareas", temp_db_migration)
        
        # Verificar cada columna
        assert list(result.columns) == list(df.columns)
        
        # Verificar valores
        assert result[result["ID"] == "T001"]["Título Tarea"].values[0] == "Tarea 1"
        assert result[result["ID"] == "T002"]["Responsable"].values[0] == "Jane"
    
    def test_empty_sheets_handled(self, temp_db_migration):
        """Verifica que hojas vacías no causan errores."""
        empty_df = pd.DataFrame()
        
        # No debería lanzar error
        success = import_from_dataframe("tareas", empty_df, temp_db_migration)
        # assert not success  # Depende de la implementación
        
        # Verificar que la tabla existe (aunque vacía)
        assert row_count("tareas", temp_db_migration) == 0
    
    def test_all_tables_migrated(self, temp_db_migration, mock_google_sheets_data):
        """Verifica que todas las tablas principales se migran."""
        tables_to_migrate = ["tareas", "vacaciones", "compensados", "notas", "personal"]
        
        for table_name in tables_to_migrate:
            if table_name in mock_google_sheets_data:
                df = mock_google_sheets_data[table_name]
                import_from_dataframe(table_name, df, temp_db_migration)
                
                assert row_count(table_name, temp_db_migration) > 0, f"Tabla '{table_name}' no migrada"


class TestMigrationEdgeCases:
    """Tests de casos extremos en la migración."""
    
    def test_special_characters_in_data(self, temp_db_migration):
        """Verifica que caracteres especiales se migran correctamente."""
        df = pd.DataFrame([
            {"ID": "T001", "Título Tarea": "Test with ñ and accents", "Tarea": "Descripción con símbolos: @#$%", "Responsable": "José", "Fecha límite": "2024-12-31", "Estado": "Pendiente"},
        ])
        
        import_from_dataframe("tareas", df, temp_db_migration)
        result = get_data("tareas", temp_db_migration)
        
        assert result.iloc[0]["Título Tarea"] == "Test with ñ and accents"
        assert result.iloc[0]["Tarea"] == "Descripción con símbolos: @#$%"
    
    def test_dates_preserved(self, temp_db_migration):
        """Verifica que las fechas se preservan correctamente."""
        df = pd.DataFrame([
            {"ID": "V001", "Apellido, Nombres": "Doe, John", "Fecha inicio": "01/01/2024", "Fecha regreso": "15/01/2024", "Tipo": "Anual", "Estado": "Aprobado"},
        ])
        
        import_from_dataframe("vacaciones", df, temp_db_migration)
        result = get_data("vacaciones", temp_db_migration)
        
        # Las fechas deben preservarse como strings (el formato puede variar)
        assert "01/01/2024" in result["Fecha inicio"].values[0] or "2024-01-01" in result["Fecha inicio"].values[0]


class TestSchemaCompatibility:
    """Tests de compatibilidad con el esquema."""
    
    def test_all_schema_tables_exist(self, temp_db_migration):
        """Verifica que todas las tablas del esquema existen."""
        from database import table_exists
        
        for table_name in SCHEMA.keys():
            assert table_exists(table_name, temp_db_migration), f"Tabla '{table_name}' no existe"
    
    def test_required_columns_exist(self, temp_db_migration):
        """Verifica que las columnas requeridas existen."""
        # Verificar algunas tablas clave
        df_tareas = get_data("tareas", temp_db_migration)
        required_cols = ["ID", "Título Tarea", "Estado"]
        
        for col in required_cols:
            assert col in df_tareas.columns, f"Columna '{col}' no encontrada en tareas"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])