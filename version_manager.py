#!/usr/bin/env python3
"""
Módulo para obtener información de versión del proyecto desde git.
Proporciona información detallada sobre el estado del repositorio.
"""

import subprocess
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
import re

class VersionManager:
    """Gestor de versiones basado en información de git"""

    def __init__(self, repo_path: str = None):
        """
        Inicializar el gestor de versiones.

        Args:
            repo_path: Ruta al repositorio git (por defecto, directorio actual)
        """
        self.repo_path = repo_path or os.getcwd()

    def _run_git_command(self, command: list) -> Tuple[str, int]:
        """
        Ejecutar un comando git de manera segura.

        Args:
            command: Lista con el comando git a ejecutar

        Returns:
            Tupla con (output, return_code)
        """
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip(), result.returncode
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return "", 1

    def get_git_info(self) -> Dict[str, str]:
        """
        Obtener información completa del repositorio git.

        Returns:
            Diccionario con información de git
        """
        git_info = {
            'branch': 'unknown',
            'commit_hash': 'unknown',
            'short_hash': 'unknown',
            'last_commit_date': 'unknown',
            'last_commit_author': 'unknown',
            'last_commit_message': 'unknown',
            'is_dirty': False,
            'tag': None,
            'version': 'dev'
        }

        # Obtener rama actual
        branch_output, branch_code = self._run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        if branch_code == 0:
            git_info['branch'] = branch_output

        # Obtener hash completo del commit
        commit_output, commit_code = self._run_git_command(['git', 'rev-parse', 'HEAD'])
        if commit_code == 0:
            git_info['commit_hash'] = commit_output
            git_info['short_hash'] = commit_output[:8]

        # Obtener información del último commit
        log_output, log_code = self._run_git_command(['git', 'log', '-1', '--format=%H|%ad|%an|%s', '--date=short'])
        if log_code == 0:
            parts = log_output.split('|', 3)
            if len(parts) == 4:
                git_info['commit_hash'] = parts[0]
                git_info['last_commit_date'] = parts[1]
                git_info['last_commit_author'] = parts[2]
                git_info['last_commit_message'] = parts[3][:50] + '...' if len(parts[3]) > 50 else parts[3]

        # Verificar si hay cambios sin commitear
        status_output, status_code = self._run_git_command(['git', 'status', '--porcelain'])
        git_info['is_dirty'] = bool(status_output.strip())

        # Obtener tag más reciente
        tag_output, tag_code = self._run_git_command(['git', 'describe', '--tags', '--abbrev=0'])
        if tag_code == 0:
            git_info['tag'] = tag_output

        # Determinar versión basada en branch y tag
        git_info['version'] = self._determine_version(git_info)

        return git_info

    def _determine_version(self, git_info: Dict[str, str]) -> str:
        """
        Determinar la versión basada en la información de git.

        Args:
            git_info: Diccionario con información de git

        Returns:
            String con la versión formateada
        """
        branch = git_info['branch']
        tag = git_info['tag']
        short_hash = git_info['short_hash']

        # Si hay un tag, usar ese como versión base
        if tag:
            if branch == 'main' or branch == 'master':
                return tag  # v1.0.0 (ya incluye la 'v')
            else:
                return f"{tag}-{branch}"  # v1.0.0-feature

        # Si no hay tag, usar branch + commit
        if branch == 'main' or branch == 'master':
            return f"dev-{short_hash}"
        elif branch == 'develop' or branch == 'development':
            return f"dev-{short_hash}"
        else:
            return f"{branch}-{short_hash}"

    def get_version_string(self, format_type: str = 'full') -> str:
        """
        Obtener string de versión formateado.

        Args:
            format_type: Tipo de formato ('full', 'short', 'compact', 'badge')

        Returns:
            String con la versión formateada
        """
        git_info = self.get_git_info()

        if format_type == 'full':
            version_parts = []

            # Versión base
            version_parts.append(f"**Versión:** {git_info['version']}")

            # Información adicional
            if git_info['is_dirty']:
                version_parts.append("⚠️ *Cambios sin commitear*")

            version_parts.append(f"**Branch:** {git_info['branch']}")
            version_parts.append(f"**Commit:** `{git_info['short_hash']}`")

            if git_info['last_commit_date'] != 'unknown':
                version_parts.append(f"**Fecha:** {git_info['last_commit_date']}")

            if git_info['last_commit_author'] != 'unknown':
                version_parts.append(f"**Autor:** {git_info['last_commit_author']}")

            return '\n\n'.join(version_parts)

        elif format_type == 'short':
            dirty_indicator = "⚠️" if git_info['is_dirty'] else ""
            return f"{git_info['version']} {dirty_indicator}"

        elif format_type == 'compact':
            dirty_indicator = "⚠️" if git_info['is_dirty'] else ""
            return f"v{git_info['short_hash']}{dirty_indicator}"

        elif format_type == 'badge':
            if git_info['is_dirty']:
                return "🔴 **DEV** (con cambios)"
            elif git_info['branch'] in ['main', 'master']:
                return "🟢 **PROD**"
            else:
                return "🟡 **DEV**"

        return git_info['version']

    def is_production_ready(self) -> bool:
        """
        Verificar si la versión actual está lista para producción.

        Returns:
            True si está en main/master y no tiene cambios sin commitear
        """
        git_info = self.get_git_info()
        return (git_info['branch'] in ['main', 'master'] and
                not git_info['is_dirty'] and
                git_info['tag'] is not None)

def get_version_info() -> Dict[str, str]:
    """
    Función de conveniencia para obtener información de versión.

    Returns:
        Diccionario con información de versión
    """
    vm = VersionManager()
    return vm.get_git_info()

def get_version_string(format_type: str = 'short') -> str:
    """
    Función de conveniencia para obtener string de versión.

    Args:
        format_type: Tipo de formato

    Returns:
        String con la versión formateada
    """
    vm = VersionManager()
    return vm.get_version_string(format_type)

def display_version_sidebar():
    """
    Mostrar información de versión en el sidebar de Streamlit.
    Esta función está diseñada para ser llamada desde el sidebar.
    """
    import streamlit as st

    vm = VersionManager()
    git_info = vm.get_git_info()

    # Mostrar versión principal
    st.caption(f"📦 Versión: {vm.get_version_string('short')}")

    # Mostrar badge de estado
    badge = vm.get_version_string('badge')
    st.caption(badge)

    # Mostrar información detallada en expander
    with st.expander("ℹ️ Detalles de versión"):
        st.markdown(vm.get_version_string('full'))

        # Botones de acción
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Actualizar Git Info"):
                st.rerun()

        with col2:
            if st.button("📋 Copiar Commit Hash"):
                st.code(git_info['commit_hash'], language=None)
                st.success("Hash copiado al portapapeles!")

def main():
    """Función principal para pruebas"""
    vm = VersionManager()

    print("🚀 Información de Versión del Proyecto")
    print("=" * 40)

    git_info = vm.get_git_info()
    print(f"Versión: {vm.get_version_string('short')}")
    print(f"Branch: {git_info['branch']}")
    print(f"Commit: {git_info['short_hash']}")
    print(f"Estado: {'⚠️ Dirty' if git_info['is_dirty'] else '✅ Clean'}")
    print(f"Producción Ready: {'✅ Sí' if vm.is_production_ready() else '❌ No'}")

    print("\n📋 Versiones disponibles:")
    print(f"  Full: {vm.get_version_string('full')}")
    print(f"  Short: {vm.get_version_string('short')}")
    print(f"  Compact: {vm.get_version_string('compact')}")
    print(f"  Badge: {vm.get_version_string('badge')}")

if __name__ == "__main__":
    main()
