# Plan de Migración: Google Sheets → SQLite

## Visión General

Este documento describe el plan de migración desde Google Sheets hacia SQLite como base de datos local.

---

## 1. Hojas Existentes y Estructura

| Tabla SQLite | Hoja Google Sheets | Columnas Identificadas |
|-------------|-------------------|----------------------|
| `tareas` | Tareas | ID, Título Tarea, Tarea, Responsable, Fecha límite, Estado |
| `vacaciones` | Vacaciones | ID, Apellido, Nombres, Fecha inicio, Fecha regreso, Tipo, Estado |
| `compensados` | Compensados | ID, Apellido, Nombres, Desde fecha, Hasta fecha, Desde hora, Hasta hora, Tipo |
| `notas` | Notas | ID, Remitente, Destinatario, Motivo, Fecha, Estado |
| `personal` | Personal | (lista de empleados) |
| `eventos` | Eventos | ID, Evento, Fecha, Tipo |
| `vehiculos` | Vehiculos | ID, Vehículo, Marca, Modelo, Año, Patente |
| `viajes` | Viajes | ID, Empleado, Destino, Fecha salida, Fecha regreso, Estado |
| `viajes_updates` | ViajesUpdates | ID, Updates de viajes |
| `destinos` | Destinos | ID, Destino, Descripción |
| `feriados` | Feriados_Manuales | ID, Fecha, Descripción |
| `comentarios` | Comentarios | ID_Tarea, Fecha, Comentario |

---

## 2. Pasos de Migración

### Paso 1: Análisis de Estructura (COMPLETO)
- [x] Identificar todas las hojas usadas
- [x] Documentar columnas de cada hoja

### Paso 2: Crear Esquema SQLite (EN PROGRESO)
- [ ] Definir CREATE TABLE para cada entidad
- [ ] Agregar PRIMARY KEY (id)
- [ ] Agregar FOREIGN KEY donde corresponda
- [ ] Definir tipos de datos apropiados

### Paso 3: Implementar Capa de Acceso a Datos
- [ ] Crear `database.py` con funciones:
  - `init_db()` — crear tablas
  - `get_data(table_name)` → DataFrame
  - `update_data(table_name, id, column, value)` → bool
  - `insert_data(table_name, data)` → bool
  - `delete_data(table_name, id)` → bool

### Paso 4: Script de Migración
- [ ] Exportar datos desde Google Sheets
- [ ] Importar a SQLite
- [ ] Verificar integridad

### Paso 5: Tests
- [ ] Test de migración (datos == datos)
- [ ] Test de integración (CRUD completo)
- [ ] Test de Performance (tiempo de carga)

### Paso 6: Integración con la App
- [ ] Modificar `app.py` para usar SQLite
- [ ] Eliminar dependencia de `credenciales.json`
- [ ] Configurar variable de entorno para DB path

---

## 3. Estructura de Archivos

```
gestor_proyectos_streamlit/
├── database.py              # Capa de abstracción SQLite (NUEVO)
├── migrations/
│   └── migrate_from_sheets.py  # Script de migración (NUEVO)
├── tests/
│   ├── test_database.py    # Tests CRUD (NUEVO)
│   └── test_migration.py # Tests de migración (NUEVO)
└── data/
    └── gestor.db         # Archivo SQLite (generado)
```

---

## 4. Cambios en Código Existente

| Archivo | Cambio |
|---------|-------|
| `app.py` | Importar database, no google_sheets_client |
| `google_sheets_client.py` | Se mantiene para migración |
| `ui_sections/*.py` | Sin cambios (usan st.session_state) |

---

## 5. Consideraciones de Desarrollo vs Producción

### Desarrollo (laptop)
- DB: `data/gestor.db` (local)
- Git: ignore `*.db`

### Producción (VPS)
- DB: `/var/lib/gestor/gestor.db`
- Variable: `export DATABASE_PATH=/var/lib/gestor/gestor.db`

### Primer Deploy
1. En VPS: crear DB vacía o importar desde export
2. Sin sincronización automática con Sheets

---

## 6. Tests Requeridos

### Test 1: Migración de Datos
```python
def test_migration_data_integrity():
    # Exportar de Sheets
    # Importar a SQLite
    # Comparar: len(gs) == len(sqlite)
    # Comparar: columnas == columnas
```

### Test 2: CRUD Básico
```python
def test_crud_operations():
    # INSERT → SELECT
    # UPDATE → SELECT (verificar cambio)
    # DELETE → SELECT (verificar ausencia)
```

### Test 3: Rendimiento
```python
def test_load_time():
    # SELECT * FROM tareas → DataFrame
    # Medir tiempo < 1 segundo
```

---

## 7. Rollback Plan

Si algo falla:
1. Mantener archivo `credenciales.json`
2. Revertir cambios en `app.py`
3. Volver a Google Sheets temporalmente

---

## 8. Estado de Ejecución

- [x] Análisis de estructura (COMPLETO)
- [x] Definir esquema SQLite (COMPLETO)
- [x] Implementar database.py (COMPLETO)
- [x] Crear script de migración (COMPLETO)
- [x] Tests de migración (COMPLETO)
- [x] Tests de integración (COMPLETO)
- [x] Modificar app.py (COMPLETO)
- [x] Tests de integración de app (COMPLETO)
- [ ] Deploy a producción