# Agent Guidelines for Gestor de Proyectos Streamlit

## Build/Test/Lint Commands
- **Run app**: `streamlit run app.py`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run tests**: `pytest` (pytest available in requirements.txt)
- **Lint**: `black .` (code formatter), `flake8 .` (linter), `mypy .` (type checker)
- **Run single test**: `pytest -k test_name` or `pytest path/to/test_file.py::test_function`

## Code Style Guidelines
- **Language**: Python 3.12+
- **Framework**: Streamlit with Google Sheets integration via gspread
- **Imports**: Standard library first, third-party, then local imports with blank lines between groups
- **Formatting**: Use snake_case for functions/variables, PascalCase for classes
- **Type hints**: Use typing module (Dict, List, Optional) for function signatures
- **Error handling**: Use try/except blocks with specific error messages via st.error()
- **Comments**: Use docstrings for functions, minimal inline comments
- **Streamlit patterns**: Use st.cache_resource for connections, st.session_state for data
- **File structure**: UI sections in ui_sections/ directory, main logic in app.py
- **Google Sheets**: Use get_sheet_data() and refresh_data() helpers for data operations
- **Security**: Never expose credentials, use st.secrets for configuration