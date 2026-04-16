"""
Esquema de base de datos SQLite para Gestor de Proyectos

Este archivo define las tablas y columnas correspondientes a las hojas de Google Sheets.
"""

# Esquema de tablas basado en las hojas existentes de Google Sheets
# Formato: "column_name": ("tipo", primary_key)
SCHEMA = {
    "tareas": {
        "columns": [
            ("ID", "TEXT"),
            ("Título Tarea", "TEXT"),
            ("Tarea", "TEXT"),
            ("Responsable", "TEXT"),
            ("Fecha límite", "TEXT"),
            ("Estado", "TEXT"),
        ],
        "primary_key": "ID",
        "description": "Lista de tareas del proyecto"
    },
    "vacaciones": {
        "columns": [
            ("Apellido, Nombres", "TEXT"),
            ("Fecha solicitud", "TEXT"),
            ("Tipo", "TEXT"),
            ("Fecha inicio", "TEXT"),
            ("Fecha regreso", "TEXT"),
            ("Observaciones", "TEXT"),
        ],
        "primary_key": None,
        "description": "Registro de vacaciones de empleados"
    },
    "compensados": {
        "columns": [
            ("Apellido, Nombres", "TEXT"),
            ("Fecha Solicitud", "TEXT"),
            ("Tipo", "TEXT"),
            ("Desde fecha", "TEXT"),
            ("Desde hora", "TEXT"),
            ("Hasta fecha", "TEXT"),
            ("Hasta hora", "TEXT"),
        ],
        "primary_key": None,
        "description": "Registro de horas compensadas"
    },
    "personal": {
        "columns": [
            ("Apellido, Nombres", "TEXT"),
            ("Fecha de nacimiento", "TEXT"),
            ("Fecha ingreso PAO", "TEXT"),
            ("ID", "TEXT"),
        ],
        "primary_key": None,
        "description": "Lista de empleados"
    },
    "eventos": {
        "columns": [
            ("Nombre del Evento", "TEXT"),
            ("Fecha Solicitud", "TEXT"),
            ("Tipo", "TEXT"),
            ("Desde fecha", "TEXT"),
            ("Desde hora", "TEXT"),
            ("Hasta fecha", "TEXT"),
            ("Hasta hora", "TEXT"),
        ],
        "primary_key": None,
        "description": "Eventos del calendario"
    },
    "feriados": {
        "columns": [
            ("Fecha", "TEXT"),
            ("Motivo", "TEXT"),
        ],
        "primary_key": "Fecha",
        "description": "Feriados manuales"
    },
}

# SQL para crear todas las tablas
def get_create_table_sql(table_name: str) -> str:
    """Genera el SQL para crear una tabla."""
    if table_name not in SCHEMA:
        raise ValueError(f"Tabla '{table_name}' no encontrada en el esquema")
    
    schema = SCHEMA[table_name]
    columns = schema["columns"]
    
    # Construir la definición de columnas
    col_defs = []
    for col_name, col_type in columns:
        col_defs.append(f'"{col_name}" {col_type}')
    
    # Determinar primary key (None = sin PK, usar rowid)
    pk_cols = schema.get("primary_key")
    if pk_cols is None:
        # Sin primary key - usar INTEGER PRIMARY KEY AUTOINCREMENT para generated ID
        col_defs.append("rowid INTEGER PRIMARY KEY AUTOINCREMENT")
    elif isinstance(pk_cols, list):
        pk_cols_str = ", ".join([f'"{col}"' for col in pk_cols])
        col_defs.append(f'PRIMARY KEY ({pk_cols_str})')
    else:
        col_defs.append(f'PRIMARY KEY ("{pk_cols}")')
    
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    "
    sql += ",\n    ".join(col_defs)
    sql += "\n)"
    
    return sql


# SQL para crear todas las tablas
def get_all_create_tables_sql() -> str:
    """Genera el SQL para crear todas las tablas."""
    sql_statements = []
    for table_name in SCHEMA:
        sql_statements.append(get_create_table_sql(table_name) + ";\n")
    return "\n".join(sql_statements)