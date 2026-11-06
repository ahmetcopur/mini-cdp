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


def search(client, q, **params):
    response = client.get("/users/search", params={"q": q, **params})
    assert response.status_code == 200
    return [u["external_id"] for u in response.json()]


def create_users(client, *users):
    for external_id, email in users:
        client.post("/users", json={"external_id": external_id, "email": email})


def test_search_by_email_or_external_id_prefix(client):
    create_users(
        client,
        ("cust-001", "alice@example.com"),
        ("cust-002", "bob@example.com"),
        ("alina-7", None),
        ("cust-003", "carol@alice.dev"),
    )

    # carol only contains "ali" in the middle of her email, so she is not a prefix match.
    assert search(client, "ali") == ["alina-7", "cust-001"]
    assert search(client, "cust-00") == ["cust-001", "cust-002", "cust-003"]
    assert search(client, "cust-00", limit=2) == ["cust-001", "cust-002"]


def test_search_is_case_insensitive(client):
    create_users(client, ("Cust-001", "Alice@Example.com"))
    assert search(client, "ALICE@ex") == ["Cust-001"]
    assert search(client, "cUsT") == ["Cust-001"]


def test_search_without_matches(client):
    create_users(client, ("cust-001", "alice@example.com"))
    assert search(client, "zed") == []


def test_search_treats_wildcards_as_text(client):
    create_users(client, ("cust-001", "a_b@example.com"), ("cust-002", "axb@example.com"))
    assert search(client, "a_") == ["cust-001"]
    assert search(client, "%") == []


def test_search_needs_a_query(client):
    assert client.get("/users/search", params={"q": ""}).status_code == 422
