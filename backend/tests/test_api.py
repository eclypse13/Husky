import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

def test_placeholder(api_client):
    """Базовый тест"""
    response = api_client.get('/api/')
    assert response.status_code in [200, 404]
