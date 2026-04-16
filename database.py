"""
Capa de abstracción de base de datos SQLite para Gestor de Proyectos

Reemplaza google_sheets_client.py para usar SQLite como almacenamiento local.
"""

import sqlite3
import pandas as pd
import os
from typing import Optional
from database_schema import SCHEMA, get_create_table_sql


# Ruta por defecto de la base de datos
DEFAULT_DB_PATH = "data/gestor.db"

# Variable de entorno para overrides
DATABASE_URL = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


def get_database_path() -> str:
    """Obtiene la ruta de la base de datos."""
    return DATABASE_URL


def ensure_db_directory(db_path: str) -> None:
    """Asegura que el directorio de la base de datos existe."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos."""
    if db_path is None:
        db_path = get_database_path()
    
    ensure_db_directory(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Inicializa la base de datos creando todas las tablas."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    for table_name in SCHEMA:
        sql = get_create_table_sql(table_name)
        cursor.execute(sql)
    
    conn.commit()
    conn.close()
    print(f"Base de datos inicializada en: {get_database_path()}")


def get_table_names() -> list:
    """Retorna la lista de nombres de tablas."""
    return list(SCHEMA.keys())


def get_data(table_name: str, db_path: Optional[str] = None) -> pd.DataFrame:
    """
    Obtiene todos los datos de una tabla y los retorna como DataFrame.
    
    Args:
        table_name: Nombre de la tabla
        db_path: Ruta opcional de la base de datos
        
    Returns:
        DataFrame con los datos de la tabla
    """
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        # Normalizar nombres de columnas (eliminar espacios)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    finally:
        conn.close()


def insert_data(table_name: str, data: dict, db_path: Optional[str] = None) -> bool:
    """
    Inserta un nuevo registro en la tabla.
    
    Args:
        table_name: Nombre de la tabla
        data: Diccionario con los datos a insertar
        db_path: Ruta opcional de la base de datos
        
    Returns:
        True si la inserción fue exitosa
    """
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    try:
        columns = list(data.keys())
        # Envolver nombres de columnas en comillas dobles
        columns_quoted = [f'"{col}"' if ' ' in col else col for col in columns]
        placeholders = ["?"] * len(columns)
        sql = f'INSERT INTO {table_name} ({", ".join(columns_quoted)}) VALUES ({", ".join(placeholders)})'
        cursor.execute(sql, list(data.values()))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error de integridad: {e}")
        return False
    except Exception as e:
        print(f"Error al insertar: {e}")
        return False
    finally:
        conn.close()


def update_data(table_name: str, id_value: str, column_name: str, new_value: any, 
              id_column: str = "ID", db_path: Optional[str] = None) -> bool:
    """
    Actualiza un registro en la tabla por ID.
    
    Args:
        table_name: Nombre de la tabla
        id_value: Valor del ID del registro a actualizar
        column_name: Nombre de la columna a actualizar
        new_value: Nuevo valor
        id_column: Nombre de la columna de ID (default: "ID")
        db_path: Ruta opcional de la base de datos
        
    Returns:
        True si la actualización fue exitosa
    """
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    try:
        # Wrap column names with spaces in quotes
        col_quoted = f'"{column_name}"' if ' ' in column_name else column_name
        id_col_quoted = f'"{id_column}"' if ' ' in id_column else id_column
        sql = f"UPDATE {table_name} SET {col_quoted} = ? WHERE {id_col_quoted} = ?"
        cursor.execute(sql, (new_value, id_value))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al actualizar: {e}")
        return False
    finally:
        conn.close()


def delete_data(table_name: str, id_value: str, id_column: str = "ID",
               db_path: Optional[str] = None) -> bool:
    """
    Elimina un registro de la tabla por ID.
    
    Args:
        table_name: Nombre de la tabla
        id_value: Valor del ID del registro a eliminar
        id_column: Nombre de la columna de ID (default: "ID")
        db_path: Ruta opcional de la base de datos
        
    Returns:
        True si la eliminación fue exitosa
    """
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    try:
        # Wrap column names with spaces in quotes
        id_col_quoted = f'"{id_column}"' if ' ' in id_column else id_column
        sql = f"DELETE FROM {table_name} WHERE {id_col_quoted} = ?"
        cursor.execute(sql, (id_value,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al eliminar: {e}")
        return False
    finally:
        conn.close()


def row_count(table_name: str, db_path: Optional[str] = None) -> int:
    """Retorna la cantidad de registros en una tabla."""
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def table_exists(table_name: str, db_path: Optional[str] = None) -> bool:
    """Verifica si una tabla existe en la base de datos."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def export_to_csv(table_name: str, output_path: str, db_path: Optional[str] = None) -> bool:
    """
    Exporta una tabla a archivo CSV.
    
    Args:
        table_name: Nombre de la tabla
        output_path: Ruta del archivo CSV de salida
        db_path: Ruta opcional de la base de datos
        
    Returns:
        True si la exportación fue exitosa
    """
    df = get_data(table_name, db_path)
    df.to_csv(output_path, index=False)
    return True


def import_from_dataframe(table_name: str, df: pd.DataFrame, 
                        db_path: Optional[str] = None) -> bool:
    """
    Importa datos desde un DataFrame a la tabla.
    Reemplaza todos los datos de la tabla.
    
    Args:
        table_name: Nombre de la tabla
        df: DataFrame con los datos a importar
        db_path: Ruta opcional de la base de datos
        
    Returns:
        True si la importación fue exitosa
    """
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    try:
        # Limpiar la tabla
        cursor.execute(f"DELETE FROM {table_name}")
        
        # Normalizar nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        
        # Insertar los datos
        for _, row in df.iterrows():
            data = row.to_dict()
            columns = list(data.keys())
            # Wrap column names with spaces in quotes
            columns_quoted = [f'"{col}"' if ' ' in col else col for col in columns]
            placeholders = ["?"] * len(columns)
            sql = f"INSERT INTO {table_name} ({', '.join(columns_quoted)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(sql, list(data.values()))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al importar: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# Funciones de compatibilidad con la API anterior (google_sheets_client)
# Estas funciones mantienen la misma interfaz para minimizar cambios en el código


class DatabaseClient:
    """Cliente de base de datos compatible con la API anterior."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_database_path()
        
    def get_table(self, table_name: str):
        """Retorna un DataFrame con los datos de la tabla."""
        return get_data(table_name, self.db_path)
    
    def update_cell_by_id(self, table_name: str, id_to_find: str, column_name: str, new_value: any) -> bool:
        """Actualiza una celda buscando por ID."""
        return update_data(table_name, id_to_find, column_name, new_value, db_path=self.db_path)


def get_database_client(db_path: Optional[str] = None) -> DatabaseClient:
    """Factory function para crear un cliente de base de datos."""
    return DatabaseClient(db_path)


# Mapeo de nombres de hojas a tablas SQLite
TABLE_NAMES = {
    "Tareas": "tareas",
    "Vacaciones": "vacaciones",
    "Compensados": "compensados",
    "Personal": "personal",
    "Eventos": "eventos",
    "Feriados_Manuales": "feriados",
}


def connect_to_database():
    """Conecta a la base de datos SQLite. Compatible con connect_to_google_sheets()."""
    return get_database_client()


def init_session_state(client):
    """Inicializa el estado de la sesión para cada tabla. Compatible con google_sheets_client.init_session_state()."""
    import streamlit as st
    sheets = ["Tareas", "Vacaciones", "Compensados", "Personal", "Eventos", "Feriados_Manuales"]
    for sheet_name in sheets:
        session_key = f"df_{sheet_name.lower()}"
        if session_key not in st.session_state:
            df = client.get_table(TABLE_NAMES.get(sheet_name, sheet_name.lower()))
            st.session_state[session_key] = df


def get_sheet(client, sheet_name):
    """Retorna un wrapper de tabla compatible con get_sheet() de google_sheets_client."""
    table_name = TABLE_NAMES.get(sheet_name, sheet_name.lower())
    return TableWrapper(client, table_name)


class TableWrapper:
    """Wrapper para simular la interfaz de worksheet de gspread."""
    
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        
    def get_all_records(self):
        """Retorna todos los registros como lista de diccionarios."""
        df = self.client.get_table(self.table_name)
        if df.empty:
            return []
        return df.to_dict('records')
    
    def append_row(self, values):
        """Agrega una nueva fila a la tabla."""
        from database import insert_data, get_data, refresh_data
        import streamlit as st
        
        schema = SCHEMA.get(self.table_name, {"columns": []})
        columns = [col[0] for col in schema.get("columns", [])]
        
        if isinstance(values, list):
            data = dict(zip(columns, values))
        else:
            data = values
        
        success = insert_data(self.table_name, data)
        
        if success and st.session_state:
            sheet_name_map = {v: k for k, v in TABLE_NAMES.items()}
            sheet_name = sheet_name_map.get(self.table_name, self.table_name)
            refresh_data(self.client, sheet_name)
        
        return success
    
    def update_cell(self, row, col, value):
        """Actualiza una celda específica por fila y columna."""
        from database import get_data, update_data, table_exists
        import streamlit as st
        
        if not table_exists(self.table_name):
            return False
        
        df = self.client.get_table(self.table_name)
        
        if df.empty:
            return False
        
        row_idx = row - 2  # gspread usa 1-based + header
        if row_idx < 0 or row_idx >= len(df):
            return False
        
        # Obtener nombre de columna (col es 1-based)
        col_names = list(df.columns)
        if col < 1 or col > len(col_names):
            return False
        
        col_name = col_names[col - 1]
        
        # Obtener ID de la fila
        pk = SCHEMA.get(self.table_name, {}).get("primary_key")
        if pk is None:
            return False
        
        row_data = df.iloc[row_idx]
        id_value = row_data.get(pk)
        
        if id_value is None:
            return False
        
        return update_data(self.table_name, id_value, col_name, value)


def get_sheet_data(client, sheet_name):
    """Obtiene los datos de una hoja como DataFrame. Compatible con google_sheets_client."""
    import pandas as pd
    table_name = TABLE_NAMES.get(sheet_name, sheet_name.lower())
    return client.get_table(table_name)


def refresh_data(client, sheet_name):
    """Refresca los datos de una tabla específica en el estado de la sesión."""
    import streamlit as st
    table_name = TABLE_NAMES.get(sheet_name, sheet_name.lower())
    st.session_state[f"df_{sheet_name.lower()}"] = client.get_table(table_name)
    st.cache_data.clear()


def refresh_all_data(client):
    """Refresca todos los DataFrames del estado de la sesión."""
    import streamlit as st
    sheets = ["Tareas", "Vacaciones", "Compensados", "Personal", "Eventos", "Feriados_Manuales"]
    for sheet_name in sheets:
        table_name = TABLE_NAMES.get(sheet_name, sheet_name.lower())
        st.session_state[f"df_{sheet_name.lower()}"] = client.get_table(table_name)
    st.cache_data.clear()


def update_cell_by_id(client, sheet_name, id_to_find, column_name, new_value):
    """Actualiza una celda específica buscando por ID. Compatible con google_sheets_client."""
    table_name = TABLE_NAMES.get(sheet_name, sheet_name.lower())
    return client.update_cell_by_id(table_name, id_to_find, column_name, new_value)


if __name__ == "__main__":
    # Inicializar base de datos si se ejecuta directamente
    print("Inicializando base de datos...")
    init_db()
    print("Base de datos inicializada correctamente.")
    print(f"Ubicación: {get_database_path()}")
    print(f"Tablas: {get_table_names()}")