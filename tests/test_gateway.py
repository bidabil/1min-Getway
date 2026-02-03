import pytest
import json
from main import app

@pytest.fixture
def client():
    """Crée un client de test Flask."""
    app.config['TESTING'] = True
    # Désactiver le limiteur pendant les tests pour éviter les erreurs 429
    app.config['RATELIMIT_ENABLED'] = False 
    with app.test_client() as client:
        yield client

def test_models_route(client):
    """Vérifie la récupération de la liste des modèles."""
    response = client.get('/v1/models')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "data" in data
    # On vérifie la présence d'un modèle que tu as mis dans ton .env
    assert any("gpt-4o" in m["id"] for m in data["data"])
    assert data["object"] == "list"

def test_chat_completion_unauthorized(client):
    """Vérifie le blocage sans API Key (Erreur 1021)."""
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    # Envoi sans headers d'auth
    response = client.post('/v1/chat/completions', json=payload)
    
    # Ton service d'erreur renvoie 401 pour 1021
    assert response.status_code == 401
    data = json.loads(response.data)
    assert "error" in data
    assert "message" in data["error"]

def test_options_method(client):
    """Vérifie la gestion des requêtes CORS OPTIONS (indispensable pour TypingMind)."""
    response = client.options('/v1/chat/completions')
    # Les requêtes OPTIONS renvoient souvent 200 ou 204 selon handle_options_request
    assert response.status_code in [200, 204]
    assert 'Access-Control-Allow-Origin' in response.headers
    assert 'Access-Control-Allow-Methods' in response.headers

def test_payload_validation_missing_messages(client):
    """Vérifie que le gateway rejette les requêtes sans messages (Erreur 1412)."""
    headers = {"Authorization": "Bearer fake_key"}
    payload = {"model": "gpt-4o"} # 'messages' manquant
    response = client.post('/v1/chat/completions', json=payload, headers=headers)
    assert response.status_code == 400 
    data = json.loads(response.data)
    assert "error" in data