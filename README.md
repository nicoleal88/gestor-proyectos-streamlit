# Gestor de Proyectos con Streamlit y Google Sheets

Esta es una aplicación web simple creada con Streamlit que sirve como un frontend para gestionar proyectos, tareas, vacaciones y notas. Utiliza una hoja de cálculo de Google Sheets como backend para almacenar todos los datos.

---

## 🚀 Cómo Ejecutar la Aplicación

### 1. Requisitos Previos

- Python 3.7 o superior.
- Una cuenta de Google.

### 2. Instalación

```bash
pip install -r requirements.txt
```

### 3. Configuración de las Credenciales de Google Sheets

Esta es la parte más importante. La aplicación necesita acceso a tu Google Drive y Google Sheets a través de una **Cuenta de Servicio (Service Account)**.

**Paso 1: Habilitar las APIs**

1.  Ve a la [Consola de Google Cloud](https://console.cloud.google.com/).
2.  Crea un nuevo proyecto o selecciona uno existente.
3.  En el buscador, busca y habilita las siguientes dos APIs:
    *   **Google Drive API**
    *   **Google Sheets API**

**Paso 2: Crear la Cuenta de Servicio**

1.  En el menú de navegación de la izquierda, ve a `IAM y administración` > `Cuentas de servicio`.
2.  Haz clic en `+ CREAR CUENTA DE SERVICIO`.
3.  Dale un nombre (ej. "gestor-proyectos-streamlit") y una descripción. Haz clic en `CREAR Y CONTINUAR`.
4.  En el paso de "roles", no es necesario añadir ninguno. Haz clic en `CONTINUAR`.
5.  En el último paso, haz clic en `HECHO`.

**Paso 3: Generar la Clave JSON**

1.  En la lista de cuentas de servicio, busca la que acabas de crear. Haz clic en los tres puntos bajo "Acciones" y selecciona `Administrar claves`.
2.  Haz clic en `AGREGAR CLAVE` > `Crear nueva clave`.
3.  Selecciona `JSON` como tipo de clave y haz clic en `CREAR`.
4.  Se descargará un archivo JSON. **Este archivo es tu credencial.**

**Paso 4: Mover y Renombrar la Clave**

1.  Busca el archivo JSON que descargaste.
2.  Muévelo a la raíz de este proyecto (la misma carpeta donde está `app.py`).
3.  **Renombra el archivo a `credenciales.json`**.

**Paso 5: Crear y Compartir el Google Sheet**

1.  Ve a [Google Sheets](https://sheets.google.com) y crea una nueva hoja de cálculo.
2.  **Renómbrala a `GestorProyectosStreamlit`**. El nombre debe ser exacto.
3.  Abre tu archivo `credenciales.json` con un editor de texto. Busca el valor asociado a la clave `"client_email"`. Será algo como `nombre-cuenta@...gserviceaccount.com`. Cópialo.
4.  Vuelve a tu Google Sheet, haz clic en el botón `Compartir` (arriba a la derecha).
5.  Pega el email de la cuenta de servicio en el campo de texto, asegúrate de que tenga el rol de **Editor**, y haz clic en `Compartir`.

### 4. Configurar las Pestañas y Columnas del Google Sheet

Dentro de tu Google Sheet `GestorProyectosStreamlit`, crea **7 pestañas**. Asegúrate de que la primera fila de cada pestaña contenga exactamente los siguientes encabezados:

-   **Pestaña `Personal`**
    -   `Apellido, Nombres`

-   **Pestaña `Tareas`**
    -   `ID`, `Título Tarea`, `Tarea`, `Responsable`, `Fecha límite`, `Estado`

-   **Pestaña `Comentarios`**
    -   `ID_Tarea`, `Fecha`, `Comentario`

-   **Pestaña `Vacaciones`**
    -   `Apellido, Nombres`, `Fecha solicitud`, `Tipo`, `Fecha inicio`, `Fecha fin`, `Observaciones`

-   **Pestaña `Compensados`**
    -   `Apellido, Nombre`, `Fecha Solicitud`, `Tipo`, `Desde fecha`, `Desde hora`, `Hasta fecha`, `Hasta hora`

-   **Pestaña `Notas`**
    -   `Fecha`, `Remitente`, `DNI`, `Teléfono`, `Motivo`, `Responsable`, `Estado`

-   **Pestaña `Recordatorios`**
    -   `Fecha`, `Mensaje`, `Responsable`

### 5. Ejecutar la Aplicación

```bash
streamlit run app.py
```