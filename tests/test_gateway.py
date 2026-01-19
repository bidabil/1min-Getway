import pytest
import json
from main import app

@pytest.fixture
def client():
    """Crée un client de test Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Vérifie le Health Check."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"1min-Gateway is running" in response.data

def test_models_route(client):
    """Vérifie la récupération de la liste des modèles 2026."""
    response = client.get('/v1/models')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "data" in data
    assert any(m["id"] == "gpt-5" for m in data["data"]) # Vérifie la présence d'un modèle 2026
    assert data["object"] == "list"

def test_chat_completion_unauthorized(client):
    """Vérifie le blocage sans Bearer Token."""
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
    assert response.status_code == 204
    assert 'Access-Control-Allow-Origin' in response.headers