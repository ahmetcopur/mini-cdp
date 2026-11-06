def test_create_and_get_user(client):
    response = client.post("/users", json={"external_id": "abc", "email": "a@example.com", "country": "TR"})
    assert response.status_code == 201
    user_id = response.json()["id"]

    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["external_id"] == "abc"


def test_duplicate_external_id(client):
    client.post("/users", json={"external_id": "abc"})
    response = client.post("/users", json={"external_id": "abc"})
    assert response.status_code == 409


def test_bad_country_code(client):
    response = client.post("/users", json={"external_id": "abc", "country": "TUR"})
    assert response.status_code == 422


def test_missing_user(client):
    assert client.get("/users/999").status_code == 404


def test_list_products_by_category(client, make_product):
    make_product(category="shoes")
    make_product(category="bags")
    make_product(category="shoes")

    response = client.get("/products", params={"category": "shoes"})
    assert len(response.json()) == 2


def test_negative_price(client):
    body = {"sku": "x", "name": "X", "category": "shoes", "price_cents": -5}
    assert client.post("/products", json=body).status_code == 422
