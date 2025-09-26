#!/bin/bash
# Script simplificado para VPS con PM2 ya configurado
# Como ya tienes PM2 + ecosystem.config.js, solo necesitamos actualizar el código

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

log "🔧 Configurando deployment simplificado para PM2"

# 1. Verificar si PM2 está instalado
if ! command -v pm2 &> /dev/null; then
    warning "PM2 no está instalado. Instalando..."
    npm install -g pm2 || error "Error instalando PM2"
fi

# 2. Verificar si ya existe un repositorio
PROJECT_DIR="/home/nleal/gestor_proyectos_streamlit"
if [ ! -d "$PROJECT_DIR/.git" ]; then
    error "No se encontró repositorio git en $PROJECT_DIR"
fi

# 3. Actualizar repositorio
log "📥 Actualizando repositorio..."
cd "$PROJECT_DIR"
git pull origin main || error "Error actualizando repositorio"

# 4. Verificar si existe ecosystem.config.js
if [ ! -f "ecosystem.config.js" ]; then
    warning "No se encontró ecosystem.config.js"
    warning "Asegúrate de tener tu configuración de PM2 en la VPS"
fi

# 5. Verificar si PM2 está corriendo
if pm2 list | grep -q "gestor-proyectos"; then
    log "🔄 PM2 ya está gestionando la aplicación"

    # Reiniciar para aplicar cambios
    pm2 restart ecosystem.config.js || {
        warning "Error reiniciando PM2, intentando reload"
        pm2 reload ecosystem.config.js || warning "Error con PM2"
    }
else
    log "🚀 Iniciando aplicación con PM2..."
    pm2 start ecosystem.config.js || error "Error iniciando con PM2"
fi

# 6. Limpiar archivos temporales
log "🧹 Limpiando archivos temporales..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 7. Mostrar información final
log "✅ ¡Configuración completada!"
echo
echo -e "${BLUE}📋 Estado actual:${NC}"
echo "   📁 Directorio: $PROJECT_DIR"
echo "   🔧 PM2: $(pm2 list | grep gestor-proyectos | awk '{print $2, $4, $6}')"
echo "   🌐 Puerto: (verificar en tu ecosystem.config.js)"
echo "   📜 Último commit: $(git rev-parse --short HEAD)"
echo
echo -e "${GREEN}💡 Comandos útiles:${NC}"
echo "   # Ver estado de PM2"
echo "   pm2 status"
echo
echo "   # Ver logs de PM2"
echo "   pm2 logs gestor-proyectos"
echo
echo "   # Reiniciar aplicación"
echo "   pm2 restart ecosystem.config.js"
echo
echo "   # Actualizar código"
echo "   git pull origin main"
echo "   pm2 restart ecosystem.config.js"
echo
echo -e "${GREEN}✅ ¡Tu aplicación está lista con PM2!${NC}"

# Verificar que PM2 esté corriendo
if pm2 list | grep -q "gestor-proyectos.*online"; then
    log "🎉 Aplicación funcionando correctamente con PM2"
else
    warning "⚠️ Verificar que PM2 esté funcionando correctamente"
fi
