# Agent Guidelines for Gestor de Proyectos Streamlit

This file provides guidelines and reference information for AI agents working in this repository.

---

## 1. Project Overview

- **Type**: Streamlit Web Application (Python 3.12+)
- **Purpose**: Employee management system with Google Sheets backend
- **Main Features**: Tasks, vacation tracking, absences (compensados), notes, calendar, schedules, travel management
- **Data Storage**: Google Sheets via gspread API
- **Authentication**: Google OAuth via Streamlit's built-in login

---

## 2. Build/Test/Lint Commands

### Running the Application
```bash
streamlit run app.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Running Tests
```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest -m "not slow"      # Skip slow tests
pytest --collect-only     # List available tests without running
```

### Running Single Test
```bash
pytest -k test_name              # By name pattern
pytest path/to/test_file.py::test_function  # Specific function
pytest path/to/test_file.py -v  # Single file with verbose
```

### Code Quality Tools
```bash
black .           # Format code (auto-fix)
flake8 .          # Linter (show issues)
flake8 . --select=E9,F63,F7,F82  # Critical errors only
mypy .            # Type checker
mypy --strict .   # Strict type checking
```

---

## 3. Code Style Guidelines

### Language & Version
- Python 3.12+ required
- Use type hints for all function signatures

### Import Order (with blank lines between groups)
1. Standard library (os, sys, datetime, etc.)
2. Third-party packages (streamlit, pandas, gspread, etc.)
3. Local application imports (google_sheets_client, ui_sections, utils)

### Naming Conventions
- **Functions/variables**: snake_case (e.g., `get_sheet_data`, `personal_list`)
- **Classes**: PascalCase (e.g., `GoogleSheetsClient`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `PAGE_PERMISSIONS`)
- **Private functions**: prefix with underscore (e.g., `_internal_function`)

### Formatting
- Line length: 88 characters (Black default)
- Use f-strings for string formatting
- Use f"{var}" over f"{var}" if already a string

### Type Hints
```python
from typing import Dict, List, Optional, Callable

def function(arg1: str, arg2: Optional[int] = None) -> Dict[str, List[str]]:
    ...
```

### Error Handling
- Use try/except blocks with specific exception types
- Display errors to users via `st.error()`
- Use `st.warning()` for non-critical issues
- Log errors to console for debugging

### Docstrings
- Use Google-style docstrings for public functions
- Keep docstrings concise but complete
- Include args, returns, and raises sections when needed

---

## 4. Streamlit-Specific Patterns

### Caching
```python
@st.cache_resource          # For connections (Google Sheets, API clients)
@st.cache_data(ttl=3600)    # For expensive data computations
```

### Session State
```python
# Initialize if not exists
if "key" not in st.session_state:
    st.session_state["key"] = default_value

# Access data
data = st.session_state["key"]
```

### Page Configuration
```python
st.set_page_config(
    page_title="Title",
    layout="wide",
    page_icon="icon"
)
```

### Forms
```python
with st.form("form_key"):
    input1 = st.text_input("Label")
    if st.form_submit_button("Submit"):
        # Process data
```

---

## 5. Project Structure

```
gestor_proyectos_streamlit/
├── app.py                    # Main entry point, auth, navigation, roles
├── google_sheets_client.py   # Google Sheets CRUD operations
├── credenciales.json         # Google API credentials (DO NOT COMMIT)
├── version_manager.py       # Version management utilities
├── requirements.txt         # Python dependencies
├── pytest.ini               # Pytest configuration
│
├── utils/                   # Utility functions
│   └── date_utils.py        # Date handling, holidays API
│
├── pages/                   # Streamlit pages (navigation)
│   ├── 00_Inicio.py
│   ├── 01_Tareas.py
│   ├── 02_Vacaciones.py
│   ├── 03_Compensados.py
│   ├── 04_Notas.py
│   ├── 06_Calendario.py
│   ├── 07_Horarios.py
│   ├── 08_Viajes.py
│   └── 10_Utilidades_Carga_y_Merge.py
│
├── ui_sections/             # UI logic (reusable across pages)
│   ├── tareas.py
│   ├── vacaciones.py
│   ├── compensados.py
│   ├── notas.py
│   ├── calendario.py
│   ├── horarios.py
│   ├── viajes.py
│   └── ...
│
├── tests/                  # Test files
│   ├── conftest.py         # Pytest fixtures
│   ├── test_app.py
│   └── ...
│
└── .streamlit/
    └── secrets.toml        # App secrets (DO NOT COMMIT)
```

---

## 6. Google Sheets Integration

### Reading Data
```python
from google_sheets_client import get_sheet_data, get_sheet

# Get as DataFrame
df = get_sheet_data(client, "SheetName")

# Get worksheet object
sheet = get_sheet(client, "SheetName")
```

### Writing Data
```python
from google_sheets_client import refresh_data

# Append row
sheet.append_row([col1, col2, col3])
refresh_data(client, "SheetName")

# Update cell by ID
from google_sheets_client import update_cell_by_id
update_cell_by_id(client, "SheetName", row_id, "ColumnName", new_value)
```

### Session State Initialization
```python
from google_sheets_client import init_session_state

# Initialize all sheets at app start
init_session_state(client)

# Access data
df = st.session_state.df_tareas  # df_{sheetname.lower()}
```

---

## 7. Role-Based Access Control

Defined in `app.py`:

| Role       | Permissions                                      |
|------------|--------------------------------------------------|
| admin      | Full access (all pages)                         |
| empleado   | inicio, tareas, vacaciones                      |
| secretaria | inicio, vacaciones, compensados, horarios        |
| invitado   | inicio only                                     |

### Adding New Pages
1. Create page in `pages/` directory (e.g., `05_Ejemplo.py`)
2. Add entry to `PAGE_PERMISSIONS` dict in `app.py`
3. Add icon mapping in `PAGE_ICONS` dict in `app.py`
4. Add permission to appropriate roles in `ROLES_PERMISOS` dict

---

## 8. Security Guidelines

- **NEVER commit**: `credenciales.json`, `.streamlit/secrets.toml`, `.env` files
- **Use st.secrets** for sensitive configuration
- **Validate user input** before processing
- **Sanitize data** before displaying (especially user-generated content)
- **Use HTTPS** in production

---

## 9. Testing Guidelines

### Test Naming
- Files: `test_*.py`
- Functions: `test_*`
- Classes: `Test*`

### Fixtures (see `tests/conftest.py`)
- `sample_user_data`: Mock user roles
- `sample_dataframe`: Test DataFrame
- `mock_streamlit_secrets`: Mock st.secrets

### Markers
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Tests that take significant time

---

## 10. Common Patterns

### Adding Date Picker with Format
```python
st.date_input("Label", value=datetime.now(), format="DD/MM/YYYY")
```

### Creating Tabs
```python
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])
with tab1:
    # Tab content
```

### Data Editor with Updates
```python
if "df_display" not in st.session_state:
    st.session_state.df_display = df.copy()

edited_df = st.data_editor(df, key="editor_key")

if not edited_df.equals(st.session_state.df_display):
    # Detect changes and update Google Sheets
    st.session_state.df_display = edited_df.copy()
```

### Error-Safe Date Parsing
```python
df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True, format='mixed')
```

---

## 11. Useful Resources

- Streamlit Docs: https://docs.streamlit.io
- gspread Docs: https://docs.gspread.org
- Pandas Docs: https://pandas.pydata.org/docs/
- Google Calendar API: https://developers.google.com/calendar/api
- Argentina Holidays API: https://api.argentinadatos.com/

---

*Last Updated: 2026-03-31*