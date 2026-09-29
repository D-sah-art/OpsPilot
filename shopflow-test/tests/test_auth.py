def test_demo_users_list(client):
    res = client.get("/api/auth/users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 2
    emails = [u["email"] for u in users]
    assert "alex@shopflow.dev" in emails
    assert "sarah@shopflow.dev" in emails

def test_login_successful(client):
    payload = {
        "email": "alex@shopflow.dev",
        "password": "demo123"
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alex@shopflow.dev"

def test_login_invalid_credentials(client):
    payload = {
        "email": "alex@shopflow.dev",
        "password": "wrongpassword"
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 401

def test_verify_token(client):
    # Login first
    login_res = client.post("/api/auth/login", json={"email": "sarah@shopflow.dev", "password": "demo123"})
    token = login_res.json()["access_token"]

    verify_res = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert verify_res.status_code == 200
    assert verify_res.json()["email"] == "sarah@shopflow.dev"
