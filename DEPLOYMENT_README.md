# 🚀 Deployment Simplificado - Gestor de Proyectos

Guía simplificada para deployment con PM2 ya configurado.

## 📋 Tu Configuración Actual

✅ **PM2 configurado** con `ecosystem.config.js` en la VPS
✅ **Aplicación corriendo** automáticamente
✅ **Solo necesitas** hacer `git pull` para actualizar

---

## 🔄 Deployment Manual (Lo que necesitas)

### En tu VPS:
```bash
# 1. Ir al directorio del proyecto
cd /home/nleal/gestor_proyectos_streamlit

# 2. Hacer pull de los cambios
git pull origin main

# 3. Reiniciar con PM2 (si es necesario)
pm2 restart ecosystem.config.js

# 4. ¡Listo! La aplicación se actualiza automáticamente
```

### Script de Deployment Automático:
```bash
# Ejecutar el script simplificado
./deploy.sh

# El script hace:
# - git pull origin main
# - pm2 restart ecosystem.config.js
# - Limpia archivos temporales
# - Muestra logs de lo que se actualizó
```

---

## 🛠️ Comandos Útiles para PM2

### Gestión de la Aplicación
```bash
# Ver estado de PM2
pm2 status

# Ver logs en tiempo real
pm2 logs gestor-proyectos

# Ver información detallada
pm2 show gestor-proyectos

# Reiniciar aplicación
pm2 restart ecosystem.config.js

# Recargar configuración
pm2 reload ecosystem.config.js

# Parar aplicación
pm2 stop ecosystem.config.js

# Ver historial de logs
pm2 logs gestor-proyectos --lines 50
```

### Monitoreo
```bash
# Monitor en tiempo real
pm2 monit

# Ver uso de recursos
pm2 jlist

# Ver métricas
pm2 metrics
```

---

## 🔧 Configuración de PM2

### Si necesitas modificar ecosystem.config.js:
```javascript
const path = require('path');

module.exports = {
  apps: [{
    name: 'gestor-proyectos',
    script: 'app.py',
    cwd: __dirname,                    // ← Ruta relativa (¡IMPORTANTE!)
    interpreter: 'python3',

    // Watch para auto-restart (¡MEJORADO!)
    watch: true,                       // ← Reinicia automáticamente
    watch_delay: 1000,
    ignore_watch: [
      'node_modules', '.git', '*.log', 'logs/',
      '*.pyc', '__pycache__/', 'ToDo.md'
    ],

    // Configuración robusta
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    max_memory_restart: '1G',

    // Logs optimizados
    combine_logs: true,
    log_file: path.join(__dirname, 'logs', 'combined.log'),
    out_file: path.join(__dirname, 'logs', 'out.log'),
    error_file: path.join(__dirname, 'logs', 'err.log'),
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

    // Variables de entorno
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: __dirname
    }
  }]
};
```

### Opciones útiles para ecosystem.config.js:
```javascript
{
  // Reiniciar automáticamente si se cae
  autorestart: true,

  // Número máximo de reinicios
  max_restarts: 10,

  // Delay entre reinicios
  restart_delay: 4000,

  // Memoria máxima antes de reiniciar
  max_memory_restart: '1G',

  // Watch específico de archivos
  watch: ['app.py', 'ui_sections/', 'pages/'],
  ignore_watch: ['node_modules', 'logs']
}
```

---

## 🚀 Workflow de Desarrollo a Producción

### En tu máquina local (Desarrollo)
```bash
# Hacer cambios
git add .
git commit -m "Nueva funcionalidad"
git push origin main
```

### En VPS (Producción)
```bash
# Con PM2 configurado para watch: Se actualiza automáticamente 🚀
# O manualmente:
git pull origin main
pm2 restart ecosystem.config.js
```

---

## 📊 Monitoreo y Debugging

### Ver Logs
```bash
# Logs de PM2
pm2 logs gestor-proyectos

# Logs del sistema (nueva ubicación)
tail -f logs/deploy.log

# Logs de la aplicación
tail -f logs/combined.log
```

### Debugging
```bash
# Ver variables de entorno
pm2 env 0

# Ver detalles del proceso
pm2 describe 0

# Profiling de performance
pm2 install pm2-profiling
pm2 start ecosystem.config.js --profiling
```

---

## 🔒 Backup y Seguridad

### Backup antes de actualizar
```bash
# Crear backup
cp -r /home/nleal/gestor_proyectos_streamlit /backup/gestor_proyectos_$(date +%Y%m%d_%H%M%S)
```

### Revertir si hay problemas
```bash
# Si algo sale mal, restaurar backup
cd /home/nleal/gestor_proyectos_streamlit
git reset --hard HEAD~1  # Revertir último commit
pm2 restart ecosystem.config.js
```

---

## 🎯 Configuración Recomendada para PM2

Para que PM2 reinicie automáticamente cuando cambien archivos:

```javascript
const path = require('path');

module.exports = {
  apps: [{
    name: 'gestor-proyectos',
    script: 'app.py',
    cwd: __dirname,                    // ← Ruta relativa (¡IMPORTANTE!)
    interpreter: 'python3',

    // Watch habilitado para auto-restart
    watch: true,
    watch_delay: 1000,
    ignore_watch: [
      'node_modules', '.git', '*.log', 'logs/',
      '*.pyc', '__pycache__/', 'ToDo.md'
    ],

    // Configuración robusta
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    max_memory_restart: '1G',

    // Logs con timestamps
    combine_logs: true,
    log_file: path.join(__dirname, 'logs', 'combined.log'),
    out_file: path.join(__dirname, 'logs', 'out.log'),
    error_file: path.join(__dirname, 'logs', 'err.log'),
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

    // Variables de entorno
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: __dirname
    }
  }]
};
```

---

## 📞 Troubleshooting

### Si la aplicación no reinicia automáticamente:
```bash
# Verificar que ecosystem.config.js existe
ls -la ecosystem.config.js

# Verificar configuración de watch
cat ecosystem.config.js

# Reiniciar manualmente
pm2 restart ecosystem.config.js

# Ver logs para errores
pm2 logs gestor-proyectos --err
```

### Si hay errores de dependencias:
```bash
# Instalar requirements
pip install -r requirements.txt

# Reiniciar PM2
pm2 restart ecosystem.config.js
```

---

**¡Tu aplicación ya está configurada para deployment automático con PM2! 🚀**

Solo necesitas hacer `git pull` en la VPS y PM2 se encarga del resto.
