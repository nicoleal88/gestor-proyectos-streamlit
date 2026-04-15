# Migración: Google Sheets → SQLite

## Resumen

Este documento describe la migración completada desde Google Sheets hacia SQLite como base de datos local.

---

## 1.Estado Final

| Componente | Estado |
|------------|--------|
| Esquema SQLite | ✅ Completado |
| Capa de datos (database.py) | ✅ Completado |
| Script de migración | ✅ Completado |
| Tests de integración | ✅ 21 tests passing |
| Integración con app | ✅ Completado |

---

## 2. Archivos Creados/Modificados

### Nuevos Archivos
- `database.py` - Capa de abstracción SQLite
- `database_schema.py` - Definición de tablas
- `migrations/migrate_from_sheets.py` - Script de migración
- `tests/test_database.py` - Tests CRUD
- `tests/test_migration.py` - Tests de migración

### Archivos Modificados
- `app.py` - Usa SQLite en vez de Google Sheets
- `pages/*.py` - 8 archivos actualizados
- `ui_sections/*.py` - 7 archivos actualizados
- `.gitignore` - Excluye *.db

---

## 3. Estructura de Datos

| Tabla SQLite | Registros | Primary Key |
|-------------|----------|------------|
| tareas | 31 | ID |
| vacaciones | 113 | (none) |
| compensados | 180 | (none) |
| notas | 29 | (none) |
| personal | 44 | (none) |
| eventos | 2 | (none) |
| vehiculos | 12 | ID |
| viajes | - | ID |
| viajes_updates | - | TripID |
| destinos | 11 | Nombre |
| feriados | - | Fecha |

---

## 4. Uso

### Inicializar DB
```bash
python3 -c "from database import init_db; init_db()"
```

### Migrar datos desde Google Sheets
```bash
python3 migrations/migrate_from_sheets.py
```

### Ejecutar app
```bash
python3 -m streamlit run app.py
```

### Configuración para producción
```bash
export DATABASE_PATH=/var/lib/gestor/gestor.db
```

---

## 5. Diferencias con Google Sheets

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Storage | Google Sheets | Archivo local SQLite |
| Acceso | Online | Offline |
| Concurrencia | Limitada | Completa |
| Dependencias | gspread, Google API | sqlite3 (built-in) |

---

##6. Pendientes

- Viajes: tiene error de sintaxis en columnas
- ViajesUpdates: tiene duplicados
- Feriados: nombre de columna no coincide
- Tests unitarios adicionales
- Documentación de producción

---

##7. Rollback

Para revertir a Google Sheets:
```bash
git checkout main app.py pages/ ui_sections/
```

---

*Última actualización: 2026-04-15*