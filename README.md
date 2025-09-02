
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

(Los pasos para generar el `credenciales.json` son los mismos que antes...)

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

-   **Pestaña `Notas` (¡ESTRUCTURA ACTUALIZADA!)**
    -   `Fecha`, `Remitente`, `DNI`, `Teléfono`, `Motivo`, `Responsable`, `Estado`

-   **Pestaña `Recordatorios`**
    -   `Fecha`, `Mensaje`, `Responsable`

### 5. Ejecutar la Aplicación

```bash
streamlit run app.py
```
