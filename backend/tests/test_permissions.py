def test_viewer_cannot_create_provider_account(client, viewer_headers):
    response = client.post("/api/provider-accounts", headers=viewer_headers, json={"provider": "render", "name": "render-x", "product_id": "00000000-0000-0000-0000-000000000001", "credential_ref": "RENDER_API_KEY_X"})
    assert response.status_code == 403


def test_admin_reaches_admin_route(client, admin_headers):
    response = client.get("/api/users", headers=admin_headers)
    assert response.status_code == 200


def test_direct_access_reaches_admin_route_without_token(client):
    response = client.get("/api/users")
    assert response.status_code == 200
