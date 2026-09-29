def test_list_products(client):
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 10
    assert any(p["id"] == "prod_01" for p in products)

def test_filter_products_by_category(client):
    res = client.get("/api/products?category=Electronics")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0
    assert all(p["category"] == "Electronics" for p in products)

def test_search_products(client):
    res = client.get("/api/products?q=Headphones")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 1
    assert "Headphones" in products[0]["title"]

def test_get_product_by_id(client):
    res = client.get("/api/products/prod_01")
    assert res.status_code == 200
    prod = res.json()
    assert prod["id"] == "prod_01"
    assert "ProFlow" in prod["title"]
    assert "specs" in prod

def test_get_categories(client):
    res = client.get("/api/categories")
    assert res.status_code == 200
    cats = res.json()
    assert "Electronics" in cats
    assert "Apparel" in cats
    assert "Home & Living" in cats
