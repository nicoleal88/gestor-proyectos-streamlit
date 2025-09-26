const path = require('path');

module.exports = {
  apps: [
    {
      name: 'gestor-proyectos',
      script: 'app.py',

      // Usar rutas relativas para mayor portabilidad
      cwd: __dirname,

      // Habilitar watch para reinicio automático (¡IMPORTANTE!)
      watch: true,
      watch_delay: 1000,
      ignore_watch: [
        'node_modules',
        '.git',
        '*.log',
        'logs/',
        '*.pyc',
        '__pycache__/',
        '.streamlit/secrets.toml',
        'ToDo.md'
      ],

      // Configuración de reinicio automático
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      max_memory_restart: '1G',

      // Logs combinados para facilitar debugging
      combine_logs: true,
      log_file: path.join(__dirname, 'logs', 'combined.log'),
      out_file: path.join(__dirname, 'logs', 'out.log'),
      error_file: path.join(__dirname, 'logs', 'err.log'),
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Variables de entorno optimizadas
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: __dirname,
        // Streamlit en modo headless para servidores
        STREAMLIT_SERVER_HEADLESS: 'true',
        STREAMLIT_SERVER_ENABLECORS: 'false',
        STREAMLIT_SERVER_ENABLEXSRSFPROTECTION: 'true'
      },

      // Configuración específica para Streamlit
      interpreter: 'python3',
      args: '--server.port=8502 --server.address=0.0.0.0',

      // Tiempo de gracia para apagado limpio
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 10000,

      // Reiniciar si se cae
      restart_delay: 4000,

      // Health check opcional
      health_check: {
        enabled: false
        // Si quieres health check:
        // enabled: true,
        // url: 'http://localhost:8502/_stcore/health',
        // timeout: 3000
      }
    }
  ]
};
