"""
Script de migración de datos desde Google Sheets hacia SQLite

Este script exporta los datos de Google Sheets y los importa a la base de datos SQLite.

Uso:
    python migrations/migrate_from_sheets.py

Para ejecutar este script necesitas:
    - Archivo credenciales.json de Google Cloud
    - Acceso al Google Sheet "GestorProyectosStreamlit"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database import init_db, get_data, import_from_dataframe, row_count
from database_schema import SCHEMA

# Hojas a migrar (ordenadas por prioridad)
SHEETS_TO_MIGRATE = [
    "Vacaciones", 
    "Compensados",
    "Personal",
    "Feriados_Manuales",
]

# Mapeo de nombres de hoja Google Sheets a tabla SQLite
SHEET_TO_TABLE_MAP = {
    "Vacaciones": "vacaciones",
    "Compensados": "compensados",
    "Personal": "personal",
    "Feriados_Manuales": "feriados",
}


def connect_to_google_sheets():
    """Conecta a Google Sheets."""
    try:
        import gspread
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        creds_path = os.path.join(current_dir, "credenciales.json")
        client = gspread.service_account(creds_path)
        return client
    except Exception as e:
        print(f"Error al conectar con Google Sheets: {e}")
        return None


def get_sheet_data(client, sheet_name: str) -> pd.DataFrame:
    """Obtiene los datos de una hoja de cálculo."""
    try:
        sheet = client.open("GestorProyectosStreamlit").worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        # Solo limpiar espacios al inicio/final
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"Error al obtener datos de '{sheet_name}': {e}")
        return pd.DataFrame()


def migrate_sheet(client, sheet_name: str) -> dict:
    """
    Migra los datos de una hoja de Google Sheets a SQLite.
    
    Returns:
        Diccionario con estadísticas de la migración
    """
    table_name = SHEET_TO_TABLE_MAP.get(sheet_name, sheet_name.lower())
    
    # Verificar que la tabla existe en el esquema
    if table_name not in SCHEMA:
        print(f"  ⚠️ Tabla '{table_name}' no encontrada en el esquema, saltando...")
        return {"status": "skipped", "reason": "table not in schema"}
    
    # Obtener datos de Google Sheets
    print(f"  📥 Obteniendo datos de '{sheet_name}'...")
    df_gs = get_sheet_data(client, sheet_name)
    
    if df_gs.empty:
        print(f"  ⚠️ No hay datos en '{sheet_name}', saltando...")
        return {"status": "skipped", "reason": "empty sheet"}
    
    print(f"  📊 {len(df_gs)} registros encontrados")
    
    # Contar registros antes
    count_before = row_count(table_name)
    
    # Importar a SQLite
    print(f"  💾 Importando a SQLite...")
    success = import_from_dataframe(table_name, df_gs)
    
    if not success:
        return {"status": "failed", "reason": "import error"}
    
    # Contar registros después
    count_after = row_count(table_name)
    
    print(f"  ✅ Migración completada: {count_before} → {count_after} registros")
    
    return {
        "status": "success",
        "sheet": sheet_name,
        "table": table_name,
        "records": len(df_gs),
        "count_before": count_before,
        "count_after": count_after,
    }


def verify_migration(results: list) -> dict:
    """
    Verifica la migración comparando registros.
    
    Returns:
        Diccionario con verificación
    """
    total_sheets = 0
    total_records = 0
    successful = 0
    failed = 0
    
    for result in results:
        if result.get("status") == "success":
            total_sheets += 1
            total_records += result.get("records", 0)
            successful += 1
        elif result.get("status") == "failed":
            failed += 1
    
    return {
        "total_sheets": total_sheets,
        "total_records": total_records,
        "successful": successful,
        "failed": failed,
    }


def main():
    """Función principal de migración."""
    print("=" * 60)
    print("MIGRACIÓN: Google Sheets → SQLite")
    print("=" * 60)
    
    # Paso 1: Inicializar base de datos
    print("\n[1/3] Inicializando base de datos SQLite...")
    init_db()
    print("  ✅ Base de datos inicializada")
    
    # Paso 2: Conectar a Google Sheets
    print("\n[2/3] Conectando a Google Sheets...")
    client = connect_to_google_sheets()
    
    if client is None:
        print("  ❌ No se pudo conectar a Google Sheets")
        print("  💡 Verifica que el archivo 'credenciales.json' existe")
        return
    
    print("  ✅ Conectado a Google Sheets")
    
    # Paso 3: Migrar cada hoja
    print("\n[3/3] Migrando datos...")
    results = []
    
    for i, sheet_name in enumerate(SHEETS_TO_MIGRATE, 1):
        print(f"\n  [{i}/{len(SHEETS_TO_MIGRATE)}] Migrando '{sheet_name}'...")
        result = migrate_sheet(client, sheet_name)
        results.append(result)
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE MIGRACIÓN")
    print("=" * 60)
    
    verification = verify_migration(results)
    
    print(f"Hojas procesadas: {verification['total_sheets']}")
    print(f"Total de registros migrados: {verification['total_records']}")
    print(f"Exitosos: {verification['successful']}")
    print(f"Fallidos: {verification['failed']}")
    
    if verification['failed'] == 0:
        print("\n🎉 ¡Migración completada exitosamente!")
    else:
        print("\n⚠️ La migración tuvo algunos problemas")
    
    print(f"\n📁 Base de datos: data/gestor.db")
    print("=" * 60)


if __name__ == "__main__":
    main()