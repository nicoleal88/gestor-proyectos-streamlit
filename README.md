# 📊 Gestor de Proyectos - Streamlit

Una aplicación web moderna para gestión integral de proyectos, tareas, vacaciones y recursos empresariales, construida con Streamlit y Google Sheets.

## 🚀 Características Principales

- ✅ **Gestión de Tareas**: Sistema completo con estados, prioridades y seguimiento
- 📅 **Control de Vacaciones**: Registro y seguimiento de licencias y días libres
- ⏱️ **Compensatorios**: Gestión de horas compensatorias y días adicionales
- 📝 **Sistema de Notas**: Registro de solicitudes y comunicaciones
- 🔔 **Recordatorios**: Sistema de alertas y notificaciones
- 📆 **Calendario**: Vista integrada de eventos y fechas importantes
- 👥 **Gestión de Horarios**: Control de turnos y horarios del personal
- 🌤️ **Información Adicional**: Clima, cotizaciones y datos útiles

## 📁 Estructura del Proyecto

```
gestor_proyectos_streamlit/
├── app.py                    # 🏠 Aplicación principal con navegación multipágina
├── google_sheets_client.py   # 🔗 Cliente para integración con Google Sheets
├── requirements.txt          # 📦 Dependencias del proyecto
├── pytest.ini               # ⚙️ Configuración de pruebas
├── README.md                 # 📖 Documentación principal
├── ToDo.md                   # 📋 Estado del proyecto y tareas pendientes
│
├── pages/                    # 📄 Páginas de la aplicación
│   ├── 00_Inicio.py          # 🏠 Página de bienvenida
│   ├── 01_Tareas.py          # ✅ Gestión de tareas
│   ├── 02_Vacaciones.py      # 📅 Registro de vacaciones
│   ├── 03_Compensados.py     # ⏱️ Control de horas compensadas
│   ├── 04_Notas.py           # 📝 Sistema de notas
│   ├── 05_Recordatorios.py   # 🔔 Recordatorios
│   ├── 06_Calendario.py      # 📆 Calendario de eventos
│   └── 07_Horarios.py        # 👥 Gestión de horarios
│
├── ui_sections/              # 🧩 Módulos de la interfaz de usuario
│   ├── bienvenida.py         # Funciones de la página de inicio
│   ├── tareas.py             # Lógica de gestión de tareas
│   ├── vacaciones.py         # Funciones de vacaciones
│   ├── compensados.py        # Lógica de compensatorios
│   ├── notas.py              # Sistema de notas
│   ├── recordatorios.py      # Funciones de recordatorios
│   ├── calendario.py         # Lógica del calendario
│   ├── horarios.py           # Gestión de horarios
│   ├── eventos.py            # Sistema de eventos
│   └── pronostico.py         # Información meteorológica
│
├── tests/                    # 🧪 Suite de pruebas
│   ├── __init__.py           # Inicialización del paquete de tests
│   ├── conftest.py           # Fixtures y configuración de pytest
│   ├── test_app.py           # Tests de la aplicación principal
│   ├── test_google_sheets.py # Tests de integración con Google Sheets
│   ├── test_notas_filter.py  # Tests específicos de filtros en Notas
│   ├── test_vacaciones_filter.py # Tests específicos de filtros en Vacaciones
│   └── test_compensados_filter.py # Tests específicos de filtros en Compensados
│
├── scripts/                  # 🔧 Scripts de utilidad y herramientas
│   ├── __init__.py           # Inicialización del paquete de scripts
│   ├── run_tests.sh          # Script para ejecutar pruebas
│   ├── verify_structure.py   # Verificación de estructura del proyecto
│   ├── update_colors.py      # Actualización de colores para modo oscuro
│   └── color_selector.py     # Selector interactivo de temas de color
│
├── docs/                     # 📚 Documentación adicional
│   ├── __init__.py           # Inicialización del paquete de docs
│   └── AGENTS.md             # Información sobre agentes y desarrollo
│
└── backups/                  # 💾 Archivos de respaldo
    ├── __init__.py           # Inicialización del paquete de backups
    └── ToDo.md.backup        # Copia de seguridad del archivo ToDo
```

## 🛠️ Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone <url-del-repositorio>
cd gestor_proyectos_streamlit
```

### 2. Crear Entorno Virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Google Sheets
- Crear un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
- Habilitar la Google Sheets API
- Crear credenciales de tipo "Cuenta de servicio"
- Descargar el archivo `credenciales.json` y colocarlo en la raíz del proyecto
- Crear una hoja de cálculo en Google Sheets llamada "GestorProyectosStreamlit"
- Configurar las pestañas necesarias según la documentación

### 5. Configurar Secrets de Streamlit
Crear el archivo `.streamlit/secrets.toml`:
```toml
[roles]
admin_emails = ["admin@empresa.com"]
empleado_emails = ["empleado@empresa.com"]

[api_keys]
openweather = "tu_clave_api_aqui"
exchangerate = "tu_clave_api_aqui"
```

## 🚀 Ejecución

### Desarrollo
```bash
streamlit run app.py
```

### Pruebas
```bash
# Ejecutar todas las pruebas
python -m pytest tests/ -v

# Ejecutar script de pruebas
./scripts/run_tests.sh

# Verificar estructura del proyecto
python scripts/verify_structure.py
```

### Utilidades
```bash
# Actualizar colores para modo oscuro
python scripts/update_colors.py

# Selector interactivo de colores
python scripts/color_selector.py
```

## 🎨 Características de la Interfaz

### 🎯 Navegación Moderna
- **Sidebar limpio** con información del usuario y navegación
- **Páginas dinámicas** basadas en permisos de usuario
- **Navegación fluida** con indicadores visuales
- **Responsive design** para diferentes dispositivos

### 📊 Filtros Inteligentes
- **Notas**: Filtro por estado con "Pendiente" por defecto
- **Vacaciones**: Filtros por estado de licencias (En Curso, Próximas, Transcurridas)
- **Compensados**: Filtros por estado de compensatorios
- **Tareas**: Filtros por estado y responsable

### 🌙 Optimización para Modo Oscuro
- **Colores optimizados** para excelente contraste
- **Legibilidad mejorada** con texto blanco
- **Paleta coherente** en todas las secciones
- **Fácil alternancia** entre temas

### 📱 Métricas en Tiempo Real
- **Indicadores visuales** del estado de cada módulo
- **Contadores automáticos** de registros
- **Información contextual** sobre el estado de los datos

## 🔐 Seguridad y Permisos

### 👤 Roles de Usuario
- **Admin**: Acceso completo a todas las funciones
- **Empleado**: Acceso limitado a funciones relevantes
- **Invitado**: Acceso de solo lectura

### 🔒 Características de Seguridad
- Autenticación con Google OAuth
- Control de acceso basado en roles
- Validación de datos en cliente y servidor
- Protección contra inyección de código

## 🧪 Testing

### Suite de Pruebas Completa
```bash
# Tests unitarios
python -m pytest tests/test_app.py -v

# Tests de integración
python -m pytest tests/test_google_sheets.py -v

# Tests específicos de funcionalidad
python -m pytest tests/test_notas_filter.py -v
python -m pytest tests/test_vacaciones_filter.py -v
python -m pytest tests/test_compensados_filter.py -v
```

### Cobertura de Pruebas
- ✅ Autenticación y autorización
- ✅ Navegación y permisos
- ✅ Integración con Google Sheets
- ✅ Filtros y búsqueda
- ✅ Validación de datos
- ✅ Manejo de errores

## 📈 Estado del Proyecto

### ✅ Completado
- [x] Arquitectura multipágina moderna
- [x] Sistema de autenticación y permisos
- [x] Integración completa con Google Sheets
- [x] Filtros inteligentes en todas las secciones
- [x] Optimización para modo oscuro
- [x] Suite completa de pruebas
- [x] Documentación exhaustiva

### 🚀 Próximas Mejoras
- [ ] API REST para integración externa
- [ ] Notificaciones push
- [ ] Exportación avanzada de reportes
- [ ] Dashboard ejecutivo
- [ ] Módulo de proyectos colaborativos

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo `LICENSE` para más detalles.

## 👥 Equipo de Desarrollo

- **Desarrollador Principal**: [Tu Nombre]
- **Arquitectura**: Streamlit + Google Sheets API
- **Frontend**: Streamlit Components
- **Backend**: Google Apps Script / Python

## 📞 Soporte

Para soporte técnico o consultas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo
- Revisar la documentación en `docs/`

---

**🎉 ¡Gracias por usar Gestor de Proyectos Streamlit!**  
*Una solución moderna y eficiente para la gestión empresarial.*
