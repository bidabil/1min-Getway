# run_tests.py
"""
Script pour exécuter facilement les tests.
"""
import os
import sys

import pytest


def main():
    """Exécute tous les tests."""
    print("=" * 60)
    print("🚀 Démarrage des tests 1min-Gateway...")
    print("=" * 60)

    # Options par défaut
    args = [
        "tests/",
        "-v",  # Mode verbeux
        "--tb=short",  # Traceback court
        "--disable-warnings",  # Désactiver les warnings
        "--no-header",  # Pas d'en-tête pytest
        "-q",  # Mode silencieux pour les succès
    ]

    # Vérifier les arguments de ligne de commande
    if len(sys.argv) > 1:
        user_args = sys.argv[1:]
        if "--cov" in user_args:
            args.extend(["--cov=src", "--cov-report=term", "--cov-report=html"])
            print("📊 Mode coverage activé")
        else:
            args.extend(["--no-cov"])  # Désactiver coverage par défaut

        # Ajouter les autres arguments de l'utilisateur
        for arg in user_args:
            if arg not in ["--cov"]:
                args.append(arg)
    else:
        args.append("--no-cov")  # Pas de coverage par défaut

    print(f"📁 Répertoire de tests: {os.path.abspath('tests')}")
    print(f"🔧 Arguments: {' '.join(args)}")
    print("-" * 60)

    # Exécuter les tests
    try:
        exit_code = pytest.main(args)

        if exit_code == 0:
            print("✅ Tous les tests ont réussi !")
        else:
            print(f"❌ Certains tests ont échoué (code: {exit_code})")

        return exit_code

    except Exception as e:
        print(f"💥 Erreur lors de l'exécution des tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
