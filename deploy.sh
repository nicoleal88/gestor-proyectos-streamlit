#!/bin/bash
# Script simplificado para deployment con PM2
# Como ya tienes PM2 configurado, solo necesitamos git pull
# PM2 se encarga de reiniciar automáticamente si monitorea archivos

set -e  # Salir si hay error

BRANCH=${1:-main}
LOG_FILE="/var/log/gestor_proyectos_deploy.log"

echo "$(date): 🚀 Iniciando deployment simplificado con PM2..." | tee -a "$LOG_FILE"

# Función para loguear
log() {
    echo "$(date): $1" | tee -a "$LOG_FILE"
}

# Verificar si estamos en un repositorio git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log "❌ No es un repositorio git"
    exit 1
fi

# Verificar si PM2 está corriendo
if ! pm2 list | grep -q "gestor-proyectos"; then
    log "⚠️ PM2 no está gestionando la aplicación"
    log "💡 Si tienes ecosystem.config.js, ejecuta: pm2 start ecosystem.config.js"
    exit 1
fi

# Hacer fetch de los cambios remotos
log "📥 Verificando cambios remotos..."
git fetch origin || {
    log "❌ Error en git fetch"
    exit 1
}

# Verificar si hay cambios en el branch remoto
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "✅ No hay cambios nuevos en $BRANCH"
    exit 0
fi

log "🔄 Cambios detectados, actualizando..."

# Hacer backup del estado actual (opcional)
if [ -d ".git" ]; then
    log "💾 Creando backup del estado actual..."
    cp -r . ../backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
fi

# Hacer pull de los cambios
log "⬇️ Bajando cambios..."
git pull origin $BRANCH || {
    log "❌ Error en git pull"
    exit 1
}

# PM2 debería reiniciar automáticamente si está configurado para monitorear archivos
# Si no, podemos forzar un reinicio
log "🔄 Verificando si PM2 reinicia automáticamente..."

# Verificar si el proceso sigue corriendo
sleep 2
if pm2 list | grep -q "gestor-proyectos.*online"; then
    log "✅ PM2 reinició automáticamente"
else
    log "🔄 Forzando reinicio de PM2..."
    pm2 restart ecosystem.config.js || {
        log "⚠️ Error reiniciando con PM2, intentando reload"
        pm2 reload ecosystem.config.js || log "❌ Error con PM2"
    }
fi

# Limpiar archivos temporales
log "🧹 Limpiando archivos temporales..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

log "✅ Deployment completado exitosamente"
log "🌐 Nuevos cambios disponibles: $(git rev-parse --short HEAD)"
log "📊 Estado de PM2: $(pm2 jlist | grep -o '"name":"[^"]*"' | head -1)"

echo "$(date): ✅ Deployment completado" | tee -a "$LOG_FILE"
