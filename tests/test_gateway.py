import pytest
import json
from main import app

@pytest.fixture
def client():
    """Crée un client de test Flask pour envoyer des requêtes."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Vérifie que le point d'entrée principal répond (Health Check)."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"1min-Gateway is running" in response.data

def test_models_route(client):
    """Vérifie que la route /v1/models répond avec du JSON."""
    response = client.get('/v1/models')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "data" in data
    assert data["object"] == "list"

def test_chat_completion_unauthorized(client):
    """Vérifie que l'API répond 401 (Unauthorized) si on n'envoie pas de clé API."""
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    response = client.post('/v1/chat/completions', 
                           json=payload)
    
    # Ton code dans main.py renvoie get_error_response(1021) -> 401
    assert response.status_code == 401
    data = json.loads(response.data)
    assert "error" in data