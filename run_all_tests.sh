# run_all_tests.sh
echo "🧪 Exécution de tous les tests..."

echo "1. Tests de l'infrastructure..."
python -m pytest tests/test_infrastructure/ -v --tb=short

echo "2. Tests du domaine..."
python -m pytest tests/test_domain/ -v --tb=short

echo "3. Tests principaux..."
python -m pytest tests/test_main.py -v --tb=short

echo "4. Tests du service d'erreurs..."
python -m pytest tests/test_error_service_fixed.py -v --tb=short

echo "5. Tous les tests ensemble..."
python -m pytest tests/ -v --tb=short

echo "✅ Tous les tests terminés !"
