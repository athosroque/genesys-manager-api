import pytest
import time
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from auth import get_token, h

@pytest.mark.asyncio
async def test_get_token_success():
    # Mock do objeto de resposta
    mock_response = MagicMock()
    mock_response.status_code = 200
    # O .json() no httpx NÃO é uma corrotina, é um método normal que retorna o dict
    mock_response.json.return_value = {
        "access_token": "fake_token_123",
        "expires_in": 3600
    }
    mock_response.raise_for_status = MagicMock()

    # Patchear o AsyncClient.post para retornar o mock_response (como se fosse awaitado)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        import auth
        auth._token = None
        auth._expires_at = 0.0
        
        token = await get_token()
        assert token == "fake_token_123"
        assert auth._token == "fake_token_123"

@pytest.mark.asyncio
async def test_get_token_cache_usage():
    import auth
    auth._token = "cached_token"
    auth._expires_at = time.time() + 1000
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        token = await get_token()
        mock_post.assert_not_called()
        assert token == "cached_token"

@pytest.mark.asyncio
async def test_get_token_error_handling():
    import auth
    auth._token = None
    auth._expires_at = 0.0
    
    # Simular erro de HTTP lançando a exceção que o código espera capturar
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection Error")
        
        with pytest.raises(HTTPException) as excinfo:
            await get_token()
        assert excinfo.value.status_code == 502
        assert "Falha na autenticação" in excinfo.value.detail

def test_headers_helper():
    headers = h("my_token")
    assert headers["Authorization"] == "Bearer my_token"
    assert headers["Content-Type"] == "application/json"
