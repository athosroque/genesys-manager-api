import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_reactivate_user():
    with patch("auth.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        
        with patch("httpx.AsyncClient.patch", new_callable=AsyncMock) as mock_patch:
            # Simula sucesso da Genesys (200)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "123", "state": "active"}
            mock_patch.return_value = mock_response
            
            # Testa sanitização tb ({userid} com restritores JSON)
            response = client.post("/users/{user123}/reactivate", json={"version": 5})
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            # Verifica envio correto dos campos
            mock_patch.assert_called_once()
            args, kwargs = mock_patch.call_args
            assert "user123" in args[0]
            assert kwargs["json"] == {"state": "active", "version": 5}

@pytest.mark.asyncio
async def test_delete_user_from_all_queues():
    mock_queues = {"entities": [
        {"id": "q1", "name": "Fila 1", "joined": True},
        {"id": "q2", "name": "Fila 2", "joined": True}
    ]}
    
    with patch("auth.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = mock_queues
            mock_get.return_value = mock_get_response
            
            with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
                # Simular: q1 removido com sucesso, q2 retorna 404 (já não era membro)
                def side_effect(*args, **kwargs):
                    mock_resp = MagicMock()
                    if "q1" in args[0]:
                        mock_resp.status_code = 200
                    else:
                        mock_resp.status_code = 404
                    return mock_resp
                
                mock_delete.side_effect = side_effect
                
                response = client.delete("/queues/user/{user123}/all")
                
                assert response.status_code == 200
                results = response.json()["results"]
                assert len(results) == 2
                assert results[0]["queue_id"] == "q1"
                assert results[0]["status"] == "removed"
                assert results[1]["queue_id"] == "q2"
                assert results[1]["status"] == "skip"
                
@pytest.mark.asyncio
async def test_remove_user_from_group():
    with patch("auth.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        
        with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 204 # Genesys group delete OK
            mock_delete.return_value = mock_response
            
            response = client.delete("/groups/{g123}/members/{user456}")
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            # Validar URL
            args, _ = mock_delete.call_args
            assert "g123/members?ids=user456" in args[0]
