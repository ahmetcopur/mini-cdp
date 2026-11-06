def test_dashboard_origin_allowed(client):
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
    response = client.options("/segments", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_other_origin_not_allowed(client):
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers
