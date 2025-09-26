#!/usr/bin/env python3
"""
Script para gestionar tags de versión del proyecto.
Facilita el workflow de desarrollo a producción con versionado semántico.
"""

import sys
import os
import subprocess
import re
from datetime import datetime
from typing import List, Optional, Tuple

class VersionTagger:
    """Gestor de tags de versión semántica"""

    def __init__(self, repo_path: str = None):
        """
        Inicializar el gestor de tags.

        Args:
            repo_path: Ruta al repositorio git
        """
        self.repo_path = repo_path or os.getcwd()

    def _run_git_command(self, command: list) -> Tuple[str, int]:
        """Ejecutar comando git de manera segura"""
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip(), result.returncode
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return "", 1

    def get_current_version(self) -> str:
        """Obtener la versión actual del proyecto"""
        output, code = self._run_git_command(['git', 'describe', '--tags', '--abbrev=0'])
        if code == 0:
            return output
        return "v0.0.0"

    def get_next_version(self, version_type: str = 'patch') -> str:
        """
        Calcular la siguiente versión semántica.

        Args:
            version_type: 'major', 'minor', o 'patch'

        Returns:
            Nueva versión semántica
        """
        current = self.get_current_version()

        # Extraer números de versión
        match = re.match(r'v(\d+)\.(\d+)\.(\d+)', current)
        if not match:
            # Si no hay versión válida, empezar desde v1.0.0
            major, minor, patch = 1, 0, 0
        else:
            major, minor, patch = map(int, match.groups())

        # Incrementar según el tipo
        if version_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif version_type == 'minor':
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        return f"v{major}.{minor}.{patch}"

    def create_tag(self, version: str, message: str = None) -> bool:
        """
        Crear un nuevo tag de versión.

        Args:
            version: Versión a crear (ej: v1.2.3)
            message: Mensaje del tag (opcional)

        Returns:
            True si se creó exitosamente
        """
        if not message:
            message = f"Release {version} - {datetime.now().strftime('%Y-%m-%d')}"

        # Verificar que no existe el tag
        output, code = self._run_git_command(['git', 'tag', '-l', version])
        if code == 0 and output.strip() == version:
            print(f"❌ El tag {version} ya existe")
            return False

        # Crear el tag anotado
        cmd = ['git', 'tag', '-a', version, '-m', message]
        output, code = self._run_git_command(cmd)

        if code == 0:
            print(f"✅ Tag {version} creado exitosamente")
            print(f"   Mensaje: {message}")
            return True
        else:
            print(f"❌ Error al crear tag {version}")
            print(f"   Error: {output}")
            return False

    def push_tag(self, version: str, remote: str = 'origin') -> bool:
        """
        Hacer push del tag al repositorio remoto.

        Args:
            version: Versión a hacer push
            remote: Repositorio remoto

        Returns:
            True si se subió exitosamente
        """
        cmd = ['git', 'push', remote, version]
        output, code = self._run_git_command(cmd)

        if code == 0:
            print(f"✅ Tag {version} subido a {remote}")
            return True
        else:
            print(f"❌ Error al subir tag {version}")
            print(f"   Error: {output}")
            return False

    def deploy_to_production(self, version: str) -> bool:
        """
        Simular deployment a producción.

        Args:
            version: Versión a desplegar

        Returns:
            True si el deployment sería exitoso
        """
        print(f"🚀 Simulando deployment de {version} a producción...")

        # Verificar que el tag existe
        output, code = self._run_git_command(['git', 'tag', '-l', version])
        if not (code == 0 and output.strip() == version):
            print(f"❌ El tag {version} no existe")
            return False

        # Verificar que estamos en main/master
        branch, _ = self._run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        if branch not in ['main', 'master']:
            print(f"⚠️ No estás en la rama principal ({branch})")
            print("   Recomendación: hacer merge a main/master antes del deployment")
            return False

        # Verificar que no hay cambios sin commitear
        status, _ = self._run_git_command(['git', 'status', '--porcelain'])
        if status.strip():
            print("⚠️ Hay cambios sin commitear")
            print("   Recomendación: commitear cambios antes del deployment")
            return False

        print(f"✅ {version} está lista para producción")
        print("   📋 Pasos para deployment manual:")
        print(f"   1. git checkout {version}")
        print("   2. Deploy to production server")
        print("   3. Update production branch pointer")

        return True

    def show_version_history(self, limit: int = 10) -> None:
        """Mostrar historial de versiones"""
        print(f"\n📋 Historial de Versiones (últimas {limit}):")
        print("=" * 50)

        cmd = ['git', 'tag', '--sort=-version:refname', f'--format=%(refname:short) | %(creatordate) | %(subject)']
        if limit:
            cmd.insert(-1, f'-n{limit}')

        output, code = self._run_git_command(cmd)

        if code == 0 and output:
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split(' | ', 2)
                    if len(parts) == 3:
                        tag, date, message = parts
                        print(f"   🏷️ {tag}")
                        print(f"   📅 {date}")
                        print(f"   💬 {message}")
                        print()
        else:
            print("   ℹ️ No se encontraron tags de versión")

def interactive_version_manager():
    """Modo interactivo para gestionar versiones"""
    tagger = VersionTagger()

    print("🏷️ Gestor de Versiones Interactivo")
    print("=" * 40)

    while True:
        print("\n📋 Opciones disponibles:")
        print("1. 📋 Ver versión actual")
        print("2. 🚀 Crear nueva versión (patch)")
        print("3. ⬆️ Crear nueva versión (minor)")
        print("4. 🎯 Crear nueva versión (major)")
        print("5. 📤 Subir tag a repositorio remoto")
        print("6. 🚀 Simular deployment a producción")
        print("7. 📜 Ver historial de versiones")
        print("8. ❌ Salir")

        try:
            choice = input("\nElige una opción (1-8): ").strip()

            if choice == "1":
                current = tagger.get_current_version()
                next_patch = tagger.get_next_version('patch')
                next_minor = tagger.get_next_version('minor')
                next_major = tagger.get_next_version('major')

                print(f"\n📋 Información de Versiones:")
                print(f"   Actual: {current}")
                print(f"   Siguiente patch: {next_patch}")
                print(f"   Siguiente minor: {next_minor}")
                print(f"   Siguiente major: {next_major}")

            elif choice in ["2", "3", "4"]:
                version_types = {"2": "patch", "3": "minor", "4": "major"}
                v_type = version_types[choice]

                next_version = tagger.get_next_version(v_type)
                message = input(f"\n💬 Mensaje para {next_version}: ").strip()

                if not message:
                    message = f"Release {next_version}"

                if tagger.create_tag(next_version, message):
                    print(f"✅ Tag {next_version} creado localmente")
                    print("💡 Para subir al repositorio remoto:")
                    print(f"   git push origin {next_version}")

            elif choice == "5":
                version = input("🏷️ Versión a subir: ").strip()
                if version:
                    tagger.push_tag(version)

            elif choice == "6":
                version = input("🏷️ Versión a desplegar: ").strip()
                if version:
                    tagger.deploy_to_production(version)

            elif choice == "7":
                limit = input("🔢 Número de versiones a mostrar (Enter para 10): ").strip()
                limit = int(limit) if limit.isdigit() else 10
                tagger.show_version_history(limit)

            elif choice == "8":
                print("👋 ¡Hasta luego!")
                break

            else:
                print("❌ Opción no válida")

        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Función principal"""
    print("🏷️ Gestor de Tags de Versión")
    print("=" * 30)

    if len(sys.argv) > 1:
        # Modo comando
        tagger = VersionTagger()

        if sys.argv[1] == "current":
            print(tagger.get_current_version())
        elif sys.argv[1] == "next":
            v_type = sys.argv[2] if len(sys.argv) > 2 else "patch"
            print(tagger.get_next_version(v_type))
        elif sys.argv[1] == "create":
            if len(sys.argv) < 3:
                print("❌ Uso: python version_tagger.py create <version> [message]")
                return
            version = sys.argv[2]
            message = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
            tagger.create_tag(version, message)
        elif sys.argv[1] == "push":
            if len(sys.argv) < 3:
                print("❌ Uso: python version_tagger.py push <version>")
                return
            version = sys.argv[2]
            tagger.push_tag(version)
        elif sys.argv[1] == "deploy":
            if len(sys.argv) < 3:
                print("❌ Uso: python version_tagger.py deploy <version>")
                return
            version = sys.argv[2]
            tagger.deploy_to_production(version)
        elif sys.argv[1] == "history":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            tagger.show_version_history(limit)
        else:
            print("❌ Comando no reconocido")
    else:
        # Modo interactivo
        interactive_version_manager()

if __name__ == "__main__":
    main()
