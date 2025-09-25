# Gestor de Proyectos con Streamlit y Google Sheets

Esta es una aplicación web moderna creada con Streamlit que sirve como un frontend para gestionar proyectos, tareas, vacaciones y notas. Utiliza una hoja de cálculo de Google Sheets como backend para almacenar todos los datos.

La aplicación utiliza la nueva arquitectura de aplicaciones multipágina de Streamlit con `st.Page` y `st.navigation` para una mejor organización y experiencia de usuario.

---

## ✨ Características Principales

- **Arquitectura Moderna**: Aplicación multipágina con navegación moderna usando `st.Page` y `st.navigation`
- Gestión de personal y tareas
- Registro de vacaciones con cálculo automático de fechas
- Control de horas compensadas
- Sistema de notas y recordatorios
- Calendario integrado con visualización de eventos
- Autenticación de usuarios con roles de administrador, empleado e invitado
- Integración con Google Sheets para almacenamiento de datos
- Visualización de datos con gráficos interactivos
- Control de acceso basado en roles

---

## 🚀 Cómo Ejecutar la Aplicación

### 📋 Requisitos Previos

- Python 3.9 o superior
- Una cuenta de Google
- Acceso a Google Cloud Console

### 🛠️ Instalación

1. **Clona el repositorio:**

   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd gestor_proyectos_streamlit
   ```

2. **Crea y activa un entorno virtual (recomendado):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instala las dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

### 🔑 Configuración de Google Sheets

#### 1. Habilitar las APIs de Google

- Ve a la [Consola de Google Cloud](https://console.cloud.google.com/)
- Crea un nuevo proyecto o selecciona uno existente
- Habilita las siguientes APIs:
  - Google Drive API
  - Google Sheets API

#### 2. Crear una Cuenta de Servicio

1. Navega a `IAM y administración` > `Cuentas de servicio`
2. Haz clic en `+ CREAR CUENTA DE SERVICIO`
3. Completa la información solicitada y haz clic en `CREAR Y CONTINUAR`
4. Haz clic en `CONTINUAR` sin asignar roles
5. Haz clic en `HECHO`

#### 3. Generar y Configurar las Credenciales

1. En la lista de cuentas de servicio, busca la que acabas de crear
2. Haz clic en los tres puntos y selecciona `Administrar claves`
3. Haz clic en `AGREGAR CLAVE` > `Crear nueva clave`
4. Selecciona `JSON` y haz clic en `CREAR`
5. Mueve el archivo descargado a la raíz del proyecto y renómbralo a `credenciales.json`

#### 4. Configurar la Hoja de Cálculo

1. Crea una nueva hoja de cálculo en [Google Sheets](https://sheets.google.com)
2. Nómbrala `GestorProyectosStreamlit`
3. Comparte la hoja con el email de la cuenta de servicio (encontrado en `credenciales.json` como `client_email`)
4. Asegúrate de dar permisos de **Editor**

#### 5. Estructura de la Hoja de Cálculo

La aplicación espera que la hoja de cálculo de Google Sheets contenga las siguientes pestañas con sus respectivas columnas:

**Pestaña `Personal`:**
- `Apellido, Nombres`

**Pestaña `Tareas`:**
- `ID`, `Título Tarea`, `Tarea`, `Responsable`, `Fecha límite`, `Estado`

**Pestaña `Comentarios`:**
- `ID_Tarea`, `Fecha`, `Comentario`

**Pestaña `Vacaciones`:**
- `Apellido, Nombres`, `Fecha solicitud`, `Tipo`, `Fecha inicio`, `Fecha regreso`, `Observaciones`

**Pestaña `Compensados`:**
- `Apellido, Nombre`, `Fecha Solicitud`, `Tipo`, `Desde fecha`, `Desde hora`, `Hasta fecha`, `Hasta hora`

**Pestaña `Notas`:**
- `Fecha`, `Remitente`, `DNI`, `Teléfono`, `Motivo`, `Responsable`, `Estado`

**Pestaña `Recordatorios`:**
- `Fecha`, `Mensaje`, `Responsable`

### 6. Ejecutar la Aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá en tu navegador web. La navegación aparecerá en la barra lateral con las páginas disponibles según tu rol de usuario.

---

## 📁 Estructura del Proyecto

```
gestor_proyectos_streamlit/
├── app.py                    # Archivo principal con la lógica de navegación
├── google_sheets_client.py   # Cliente para integración con Google Sheets
├── requirements.txt          # Dependencias del proyecto
├── pages/                    # Directorio con las páginas de la aplicación
│   ├── 00_🏠_Inicio.py       # Página de bienvenida
│   ├── 01_✅_Tareas.py       # Gestión de tareas
│   ├── 02_📅_Vacaciones.py   # Registro de vacaciones
│   ├── 03_⏱️_Compensados.py # Control de horas compensadas
│   ├── 04_📝_Notas.py        # Sistema de notas
│   ├── 05_🔔_Recordatorios.py # Recordatorios
│   ├── 06_📆_Calendario.py   # Calendario de eventos
│   └── 07_👥_Horarios.py     # Gestión de horarios
├── ui_sections/              # Módulos de la interfaz de usuario
│   ├── bienvenida.py
│   ├── tareas.py
│   ├── vacaciones.py
│   ├── compensados.py
│   ├── notas.py
│   ├── recordatorios.py
│   ├── calendario.py
│   ├── horarios.py
│   └── eventos.py
├── credenciales.json         # Credenciales de Google (no subir a git)
└── README.md
```

---

## 🔐 Sistema de Roles

La aplicación implementa un sistema de control de acceso basado en roles:

- **Administrador**: Acceso completo a todas las secciones
- **Empleado**: Acceso a tareas, vacaciones y su información personal
- **Invitado**: Acceso solo a la página de inicio

Los roles se configuran en el archivo `.streamlit/secrets.toml` con las listas de emails de cada rol.

---

## 🛠️ Comandos Útiles

```bash
# Ejecutar la aplicación
streamlit run app.py

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests
pytest

# Formatear código
black .

# Linting
flake8 .

# Type checking
mypy .
```

---

## 📝 Notas Importantes

- La aplicación utiliza la nueva arquitectura de Streamlit con `st.Page` y `st.navigation`
- Cada página se ejecuta de forma independiente y carga sus propios datos
- El control de acceso se realiza tanto a nivel de navegación como de funcionalidad
- Los datos se almacenan en Google Sheets y se sincronizan automáticamente
- La aplicación es responsive y funciona en dispositivos móviles

> **Nota:** Asegúrate de configurar correctamente las credenciales de Google y los permisos de la hoja de cálculo antes de ejecutar la aplicación.
