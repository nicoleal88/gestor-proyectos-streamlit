#!/usr/bin/env python3
"""
Módulo simplificado para mostrar información de versión del proyecto.
Solo muestra fecha y hora del último commit, sin scripts complejos.
"""

import subprocess
import os
from datetime import datetime
from typing import Dict, Optional

class SimpleVersionManager:
    """Gestor simplificado de versiones - solo fecha del commit"""

    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()

    def _run_git_command(self, command: list) -> str:
        """Ejecutar comando git de manera segura"""
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""

    def get_simple_version_info(self) -> Dict[str, str]:
        """
        Obtener información simplificada del repositorio.
        Solo fecha del último commit y hash corto.
        """
        # Obtener información del último commit
        commit_info = self._run_git_command([
            'git', 'log', '-1',
            '--format=%H|%h|%ad|%an|%s',
            '--date=format:%d/%m/%Y %H:%M'
        ])

        if not commit_info:
            return {
                'commit_hash': 'unknown',
                'short_hash': 'unknown',
                'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'author': 'unknown',
                'message': 'No git repository found'
            }

        parts = commit_info.split('|', 4)
        if len(parts) >= 5:
            return {
                'commit_hash': parts[0],
                'short_hash': parts[1],
                'date': parts[2],
                'author': parts[3],
                'message': parts[4][:30] + '...' if len(parts[4]) > 30 else parts[4]
            }

        return {
            'commit_hash': 'unknown',
            'short_hash': 'unknown',
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'author': 'unknown',
            'message': 'Error reading git info'
        }

def get_simple_version_string() -> str:
    """Obtener string simple de versión"""
    vm = SimpleVersionManager()
    info = vm.get_simple_version_info()

    # Formato simple: fecha y hora del commit
    return f"Última actualización: {info['date']}"

def get_detailed_version_string() -> str:
    """Obtener información detallada"""
    vm = SimpleVersionManager()
    info = vm.get_simple_version_info()

    return f"""**Último commit:** {info['short_hash']}
**Fecha:** {info['date']}
**Autor:** {info['author']}
**Mensaje:** {info['message']}"""

def display_simple_version_sidebar(user_role: str = 'invitado'):
    """
    Mostrar información simplificada en el sidebar.
    Solo fecha del último commit.
    Los detalles solo se muestran a usuarios con rol admin.
    """
    import streamlit as st

    vm = SimpleVersionManager()
    info = vm.get_simple_version_info()

    # Mostrar versión simple para todos los usuarios
    st.caption(f"📅 {get_simple_version_string()}")

    # Mostrar información detallada solo para admins
    if user_role == 'admin':
        with st.expander("ℹ️ Detalles del commit"):
            st.markdown(get_detailed_version_string())

            # Botón para copiar hash (solo para admins)
            if st.button("📋 Copiar Hash del Commit"):
                st.code(info['commit_hash'], language=None)
                st.success("Hash copiado!")

def main():
    """Función principal para pruebas"""
    print("📅 Información Simplificada de Versión")
    print("=" * 40)

    vm = SimpleVersionManager()
    info = vm.get_simple_version_info()

    print(f"Última actualización: {info['date']}")
    print(f"Commit: {info['short_hash']}")
    print(f"Autor: {info['author']}")
    print(f"Mensaje: {info['message']}")

    print(f"\nVersión simple: {get_simple_version_string()}")
    print(f"Versión detallada: {get_detailed_version_string()}")

if __name__ == "__main__":
    main()
