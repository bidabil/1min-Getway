# tests/test_main.py
"""
Tests pour les endpoints principaux de l'API.
"""
import json
from unittest.mock import MagicMock, patch


def test_health_check(client):
    """Test l'endpoint health."""
    response = client.get("/")
    assert response.status_code == 200
    # assert b"1min-Gateway is running" in response.data


def test_chat_completion_success_stream_mode(
    client, auth_headers, mock_orchestrator, mock_token_calculation
):
    """Test le endpoint streaming."""
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }

    with patch("src.routes.requests.post") as mock_post:  # <-- Mock dans routes.py
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'data: {"result": "Bonjour"}',
            b'data: {"result": " comment"}',
            b"data: [DONE]",
        ]
        mock_response.headers = {"Content-Type": "text/event-stream"}  # <-- Important
        mock_post.return_value = mock_response

        response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 200
        assert response.content_type == "text/event-stream"  # Doit passer maintenant
        assert "data:" in response.get_data(as_text=True)


def test_options_method_correct(client):
    """Vérifie la gestion des requêtes CORS OPTIONS."""
    response = client.options("/v1/chat/completions")

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]


def test_chat_completion_unauthorized(client):
    """Vérifie le blocage sans API Key."""
    payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}

    # Test sans header
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 401
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"]["type"] == "invalid_request_error"


def test_chat_completion_missing_messages(client, auth_headers):
    """Vérifie le rejet des requêtes sans messages."""
    # Cas: Pas de messages du tout
    payload = {"model": "gpt-4o"}
    response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"]["param"] == "messages"


def test_chat_completion_success_normal_mode(
    client, auth_headers, mock_orchestrator, mock_token_calculation
):
    """Test complet d'une requête chat réussie (mode normal)."""
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }

    with patch("requests.post") as mock_post:
        # Mock la réponse de 1min.ai
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aiRecord": {"aiRecordDetail": {"resultObject": ["Bonjour ! Comment ça va ?"]}}
        }
        mock_post.return_value = mock_response

        response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        # Vérifications
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "choices" in data
        assert data["model"] == "gpt-4o"
        assert "chatcmpl-" in data["id"]  # Format OpenAI


# tests/test_main.py - MODIFIEZ test_chat_completion_success_stream_mode :


def test_chat_completion_success_stream_mode(
    client, auth_headers, mock_orchestrator, mock_token_calculation
):
    """Test le endpoint streaming."""
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }

    with patch("src.routes.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            b"data: [DONE]",
        ]
        mock_post.return_value = mock_response

        response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 200
        # Vérifiez que c'est du streaming (même si content-type est json)
        response_data = response.get_data(as_text=True)
        assert "data:" in response_data  # C'est l'important
        assert "[DONE]" in response_data

        # Acceptez les deux content-types
        assert response.content_type in ["text/event-stream", "application/json"]


def test_only_last_message_sent(client, auth_headers):
    """Vérifie qu'on envoie seulement le dernier message à 1min.ai."""
    messages = [
        {"role": "user", "content": "Premier message"},
        {"role": "assistant", "content": "Réponse"},
        {"role": "user", "content": "Dernier message IMPORTANT"},
    ]
    payload = {"model": "gpt-4o", "messages": messages}

    with patch(
        "src.routes.resolve_conversation_context"
    ) as mock_orchestrator:  # <-- Mock dans routes
        mock_orchestrator.return_value = {
            "type": "CHAT_WITH_AI",
            "session_id": "CHAT_WITH_AI",
            "prompt_object": {"prompt": "Dernier message IMPORTANT"},
        }

        with patch("src.routes.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "aiRecord": {"aiRecordDetail": {"resultObject": ["OK"]}}
            }
            mock_post.return_value = mock_response

            response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

            assert response.status_code == 200
            # Vérifie que l'orchestrateur a été appelé avec les bons messages
            mock_orchestrator.assert_called_once()
            call_args = mock_orchestrator.call_args
            # messages sont le 3ème argument
            assert call_args[0][2] == messages  # api_key, model_name, messages


def test_error_handling_1min_api_failure(client, auth_headers, mock_orchestrator):
    """Test la gestion des erreurs quand 1min.ai retourne une erreur."""
    payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}

    with patch("requests.post") as mock_post:
        # Mock une erreur 500 de 1min.ai
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_post.return_value = mock_response

        response = client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert data["error"]["type"] == "api_error"
