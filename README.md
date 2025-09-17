# Gestor de Proyectos con Streamlit y Google Sheets

Esta es una aplicación web simple creada con Streamlit que sirve como un frontend para gestionar proyectos, tareas, vacaciones y notas. Utiliza una hoja de cálculo de Google Sheets como backend para almacenar todos los datos.

---

## ✨ Características Principales

- Gestión de personal y tareas
- Registro de vacaciones con cálculo automático de fechas
- Control de horas compensadas
- Sistema de notas y recordatorios
- Calendario integrado con visualización de eventos
- Autenticación de usuarios con roles de administrador, empleado e invitado
- Integración con Google Sheets para almacenamiento de datos
- Visualización de datos con gráficos interactivos

## 🚀 Cómo Ejecutar la Aplicación

## 📋 Requisitos Previos

- Python 3.7 o superior
- Una cuenta de Google
- Acceso a Google Cloud Console

## 🛠️ Instalación

1. Clona el repositorio:

   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd gestor_proyectos_streamlit
   ```

2. Crea y activa un entorno virtual (recomendado):

   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

## 🔑 Configuración de Google Sheets

### 1. Habilitar las APIs de Google

- Ve a la [Consola de Google Cloud](https://console.cloud.google.com/)
- Crea un nuevo proyecto o selecciona uno existente
- Habilita las siguientes APIs:
  - Google Drive API
  - Google Sheets API

### 2. Crear una Cuenta de Servicio

1. Navega a `IAM y administración` > `Cuentas de servicio`
2. Haz clic en `+ CREAR CUENTA DE SERVICIO`
3. Completa la información solicitada y haz clic en `CREAR Y CONTINUAR`
4. Haz clic en `CONTINUAR` sin asignar roles
5. Haz clic en `HECHO`

### 3. Generar y Configurar las Credenciales

1. En la lista de cuentas de servicio, busca la que acabas de crear
2. Haz clic en los tres puntos y selecciona `Administrar claves`
3. Haz clic en `AGREGAR CLAVE` > `Crear nueva clave`
4. Selecciona `JSON` y haz clic en `CREAR`
5. Mueve el archivo descargado a la raíz del proyecto y renómbralo a `credenciales.json`

### 4. Configurar la Hoja de Cálculo

1. Crea una nueva hoja de cálculo en [Google Sheets](https://sheets.google.com)
2. Nómbrala `GestorProyectosStreamlit`
3. Comparte la hoja con el email de la cuenta de servicio (encontrado en `credenciales.json` como `client_email`)
4. Asegúrate de dar permisos de **Editor**

### 4. Configurar las Pestañas y Columnas del Google Sheet

Dentro de tu Google Sheet `GestorProyectosStreamlit`, crea **7 pestañas**. Asegúrate de que la primera fila de cada pestaña contenga exactamente los siguientes encabezados:

### Estructura de la Hoja de Cálculo

La aplicación espera que la hoja de cálculo de Google Sheets contenga las siguientes pestañas con sus respectivas columnas:

#### Pestaña `Personal`

- `Apellido, Nombres`

#### Pestaña `Tareas`

- `ID`
- `Título Tarea`
- `Tarea`
- `Responsable`
- `Fecha límite`
- `Estado`

#### Pestaña `Comentarios`

- `ID_Tarea`
- `Fecha`
- `Comentario`

#### Pestaña `Vacaciones`

- `Apellido, Nombres`
- `Fecha solicitud`
- `Tipo`
- `Fecha inicio`
- `Fecha regreso`
- `Observaciones`

> **Nota:** La fecha de regreso es el día en que la persona vuelve al trabajo. Las vacaciones terminan el día anterior a la fecha de regreso.

#### Pestaña `Compensados`

- `Apellido, Nombre`
- `Fecha Solicitud`
- `Tipo`
- `Desde fecha`
- `Desde hora`
- `Hasta fecha`
- `Hasta hora`

#### Pestaña `Notas`

- `Fecha`
- `Remitente`
- `DNI`
- `Teléfono`
- `Motivo`
- `Responsable`
- `Estado`

#### Pestaña `Recordatorios`

- `Fecha`
- `Mensaje`
- `Responsable`

### 5. Ejecutar la Aplicación

```bash
streamlit run app.py
```
