import pytest
import json
from unittest.mock import patch
from main import app

@pytest.fixture
def client():
    """Configuration du client de test Flask."""
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False 
    with app.test_client() as client:
        yield client

def test_models_route(client):
    """Vérifie la récupération de la liste des modèles avec mocking des arguments."""
    # On simule un retour propre de la fonction de domaine
    mock_models = [{"id": "gpt-4o", "object": "model", "owned_by": "1min.ai"}]
    
    with patch('main.get_formatted_models_list') as mock_get:
        mock_get.return_value = mock_models
        
        response = client.get('/v1/models')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "data" in data
        assert any("gpt-4o" in m["id"] for m in data["data"])
        assert data["object"] == "list"
        # On vérifie que le main a bien appelé la fonction avec ses paramètres
        mock_get.assert_called_once()

def test_chat_completion_unauthorized(client):
    """Vérifie le blocage sans API Key (Erreur 401)."""
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    response = client.post('/v1/chat/completions', json=payload)
    assert response.status_code == 401
    data = json.loads(response.data)
    assert "error" in data

def test_options_method(client):
    """Vérifie la gestion des requêtes CORS OPTIONS."""
    response = client.options('/v1/chat/completions')
    assert response.status_code in [200, 204]
    assert 'Access-Control-Allow-Origin' in response.headers

def test_payload_validation_missing_messages(client):
    """Vérifie le rejet des requêtes sans messages (Erreur 400)."""
    headers = {"Authorization": "Bearer fake_key"}
    payload = {"model": "gpt-4o"}
    response = client.post('/v1/chat/completions', json=payload, headers=headers)
    assert response.status_code == 400 
    data = json.loads(response.data)
    assert "error" in data