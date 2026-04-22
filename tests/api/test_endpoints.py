from fastapi.testclient import TestClient
from app.core.config import get_settings

settings = get_settings()

def test_read_root(client: TestClient):
    """
    测试 API 根路径或 openapi.json 是否可访问
    """
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == settings.APP_NAME

def test_list_agents_empty(client: TestClient):
    """
    测试在空数据库中列出 Agents
    """
    response = client.get(f"{settings.API_V1_STR}/agents")
    assert response.status_code == 200
    assert response.json() == []
