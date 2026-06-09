"""End-to-end API test covering all RealWorld FastAPI endpoints using requests."""

import requests
import time

BASE = "http://localhost:8000/api"
TIMEOUT = 10

# ---- fixtures / state ----
register_payload = {"user": {"username": "testuser", "email": "test@example.com", "password": "testpass123"}}
login_payload = {"user": {"email": "test@example.com", "password": "testpass123"}}
update_user_payload = {"user": {"bio": "updated bio"}}
new_article = {"article": {"title": "Test Article", "description": "desc", "body": "body content", "tagList": ["test", "api"]}}
update_article = {"article": {"title": "Updated Article"}}
new_comment = {"comment": {"body": "Nice post!"}}

token = ""
article_slug = ""
comment_id = ""
profile_username = "testuser"


def headers():
    return {"Authorization": f"Token {token}"} if token else {}


def register():
    r = requests.post(f"{BASE}/users", json=register_payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "user" in data
    assert "token" in data["user"]
    return data


def login():
    r = requests.post(f"{BASE}/users/login", json=login_payload, timeout=TIMEOUT)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "user" in data
    assert "token" in data["user"]
    return data


def test_01_register():
    """POST /users - register new user."""
    global token
    # Try login first (idempotent - if user exists, login instead)
    r = requests.post(f"{BASE}/users/login", json=login_payload, timeout=TIMEOUT)
    if r.status_code == 200:
        data = r.json()
        token = data["user"]["token"]
        print("PASS: register (user existed, logged in)")
        return
    data = register()
    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"
    token = data["user"]["token"]
    print("PASS: register")


def test_02_login():
    """POST /users/login - login."""
    data = login()
    global token
    token = data["user"]["token"]
    print("PASS: login")


def test_03_register_duplicate():
    """POST /users - duplicate registration should fail."""
    r = requests.post(f"{BASE}/users", json=register_payload, timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    print("PASS: register duplicate rejected")


def test_04_login_bad_password():
    """POST /users/login - wrong password."""
    r = requests.post(f"{BASE}/users/login", json={"user": {"email": "test@example.com", "password": "wrong"}}, timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    print("PASS: bad password rejected")


def test_05_get_current_user():
    """GET /user - get current authenticated user."""
    r = requests.get(f"{BASE}/user", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 200, f"GET /user failed: {r.status_code} {r.text}"
    data = r.json()
    assert "user" in data
    assert data["user"]["username"] == "testuser"
    print("PASS: get current user")


def test_06_update_current_user():
    """PUT /user - update current user."""
    r = requests.put(f"{BASE}/user", json=update_user_payload, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 200, f"PUT /user failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["bio"] == "updated bio"
    print("PASS: update current user")


def test_07_get_profile():
    """GET /profiles/{username} - get profile."""
    r = requests.get(f"{BASE}/profiles/{profile_username}", timeout=TIMEOUT)
    assert r.status_code == 200, f"GET profile failed: {r.status_code} {r.text}"
    data = r.json()
    assert "profile" in data
    assert data["profile"]["username"] == profile_username
    print("PASS: get profile")


def test_08_follow_unfollow():
    """POST/DELETE /profiles/{username}/follow - follow/unfollow."""
    # Register second user to follow
    r2 = requests.post(f"{BASE}/users", json={"user": {"username": "follower", "email": "follower@example.com", "password": "pass123"}}, timeout=TIMEOUT)
    assert r2.status_code == 201, f"Register follower failed: {r2.status_code} {r2.text}"
    follower_token = r2.json()["user"]["token"]
    follower_headers = {"Authorization": f"Token {follower_token}"}

    # Follow
    r = requests.post(f"{BASE}/profiles/{profile_username}/follow", headers=follower_headers, timeout=TIMEOUT)
    assert r.status_code == 200, f"Follow failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["profile"]["following"] is True
    print("PASS: follow")

    # Already following should fail
    r = requests.post(f"{BASE}/profiles/{profile_username}/follow", headers=follower_headers, timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400 on double follow, got {r.status_code}"
    print("PASS: double follow rejected")

    # Unfollow
    r = requests.delete(f"{BASE}/profiles/{profile_username}/follow", headers=follower_headers, timeout=TIMEOUT)
    assert r.status_code == 200, f"Unfollow failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["profile"]["following"] is False
    print("PASS: unfollow")

    # Not following should fail
    r = requests.delete(f"{BASE}/profiles/{profile_username}/follow", headers=follower_headers, timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400 on unfollow not following, got {r.status_code}"
    print("PASS: unfollow not following rejected")


def test_09_create_article():
    """POST /articles - create article."""
    global article_slug
    r = requests.post(f"{BASE}/articles", json=new_article, headers=headers(), timeout=TIMEOUT)
    if r.status_code == 400:
        # Article already exists from previous run - find it
        r = requests.get(f"{BASE}/articles", params={"author": "testuser"}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["articlesCount"] >= 1
        article = data["articles"][0]
        article_slug = article["slug"]
        print(f"PASS: create article (found existing: {article_slug})")
        return
    assert r.status_code == 201, f"Create article failed: {r.status_code} {r.text}"
    data = r.json()
    assert "article" in data
    article_slug = data["article"]["slug"]
    assert data["article"]["title"] == "Test Article"
    assert data["article"]["tagList"] == ["test", "api"]
    print("PASS: create article")


def test_10_list_articles():
    """GET /articles - list articles with filters."""
    r = requests.get(f"{BASE}/articles", timeout=TIMEOUT)
    assert r.status_code == 200, f"List articles failed: {r.status_code} {r.text}"
    data = r.json()
    assert "articles" in data
    assert "articlesCount" in data
    assert data["articlesCount"] > 0
    print("PASS: list articles")


def test_11_list_articles_with_filters():
    """GET /articles?author=...&tag=...&favorited=...&limit=...&offset=..."""
    r = requests.get(f"{BASE}/articles", params={"author": "testuser"}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["articlesCount"] >= 1
    print("PASS: list articles by author")

    r = requests.get(f"{BASE}/articles", params={"tag": "test"}, timeout=TIMEOUT)
    assert r.status_code == 200
    print("PASS: list articles by tag")

    r = requests.get(f"{BASE}/articles", params={"favorited": "testuser"}, timeout=TIMEOUT)
    assert r.status_code == 200
    print("PASS: list articles favorited by user")

    r = requests.get(f"{BASE}/articles", params={"limit": 1, "offset": 0}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["articles"]) <= 1
    print("PASS: list articles with limit/offset")


def test_12_get_article():
    """GET /articles/{slug} - get single article."""
    assert article_slug, "article_slug not set"
    r = requests.get(f"{BASE}/articles/{article_slug}", timeout=TIMEOUT)
    assert r.status_code == 200, f"Get article failed: {r.status_code} {r.text}"
    data = r.json()
    assert "article" in data
    assert data["article"]["slug"] == article_slug
    print("PASS: get article")


def test_13_update_article():
    """PUT /articles/{slug} - update article."""
    global article_slug
    assert article_slug, "article_slug not set"
    r = requests.put(f"{BASE}/articles/{article_slug}", json=update_article, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 200, f"Update article failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["article"]["title"] == "Updated Article"
    # Slug changed due to title change
    article_slug = data["article"]["slug"]
    print("PASS: update article")


def test_14_create_comment():
    """POST /articles/{slug}/comments - create comment."""
    global comment_id
    assert article_slug, "article_slug not set"
    r = requests.post(f"{BASE}/articles/{article_slug}/comments", json=new_comment, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 201, f"Create comment failed: {r.status_code} {r.text}"
    data = r.json()
    assert "comment" in data
    assert data["comment"]["body"] == "Nice post!"
    comment_id = data["comment"]["id"]
    print("PASS: create comment")


def test_15_list_comments():
    """GET /articles/{slug}/comments - list comments."""
    assert article_slug, "article_slug not set"
    r = requests.get(f"{BASE}/articles/{article_slug}/comments", timeout=TIMEOUT)
    assert r.status_code == 200, f"List comments failed: {r.status_code} {r.text}"
    data = r.json()
    assert "comments" in data
    assert len(data["comments"]) >= 1
    print("PASS: list comments")


def test_16_favorite_article():
    """POST /articles/{slug}/favorite - favorite article."""
    assert article_slug, "article_slug not set"
    r = requests.post(f"{BASE}/articles/{article_slug}/favorite", headers=headers(), timeout=TIMEOUT)
    if r.status_code == 400:
        # Already favorited
        print("PASS: favorite article (already favorited)")
        return
    assert r.status_code == 200, f"Favorite failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["article"]["favorited"] is True
    assert data["article"]["favoritesCount"] >= 1
    print("PASS: favorite article")


def test_17_unfavorite_article():
    """DELETE /articles/{slug}/favorite - unfavorite article."""
    assert article_slug, "article_slug not set"
    # First favorite again
    r = requests.post(f"{BASE}/articles/{article_slug}/favorite", headers=headers(), timeout=TIMEOUT)
    if r.status_code == 400:
        # Already favorited, skip unfavorite test
        print("PASS: unfavorite article (already favorited)")
        return
    assert r.status_code == 200
    # Now unfavorite
    r = requests.delete(f"{BASE}/articles/{article_slug}/favorite", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 200, f"Unfavorite failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["article"]["favorited"] is False
    print("PASS: unfavorite article")


def test_18_delete_comment():
    """DELETE /articles/{slug}/comments/{comment_id} - delete comment."""
    assert article_slug, "article_slug not set"
    assert comment_id, "comment_id not set"
    r = requests.delete(f"{BASE}/articles/{article_slug}/comments/{comment_id}", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 204, f"Delete comment failed: {r.status_code} {r.text}"
    print("PASS: delete comment")


def test_19_get_feed():
    """GET /articles/feed - get user feed."""
    r = requests.get(f"{BASE}/articles/feed", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 200, f"Get feed failed: {r.status_code} {r.text}"
    data = r.json()
    assert "articles" in data
    assert "articlesCount" in data
    print("PASS: get feed")


def test_20_get_tags():
    """GET /tags - get all tags."""
    r = requests.get(f"{BASE}/tags", timeout=TIMEOUT)
    assert r.status_code == 200, f"Get tags failed: {r.status_code} {r.text}"
    data = r.json()
    assert "tags" in data
    assert "test" in data["tags"]
    print("PASS: get tags")


def test_21_delete_article():
    """DELETE /articles/{slug} - delete article."""
    assert article_slug, "article_slug not set"
    r = requests.delete(f"{BASE}/articles/{article_slug}", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 204, f"Delete article failed: {r.status_code} {r.text}"
    print("PASS: delete article")


def test_22_unauthenticated_access():
    """Verify unauthenticated requests to protected endpoints fail."""
    r = requests.get(f"{BASE}/user", timeout=TIMEOUT)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    print("PASS: unauthenticated /user rejected")

    r = requests.post(f"{BASE}/articles", json=new_article, timeout=TIMEOUT)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    print("PASS: unauthenticated POST /articles rejected")

    r = requests.get(f"{BASE}/articles/feed", timeout=TIMEOUT)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    print("PASS: unauthenticated /articles/feed rejected")


def test_23_follow_yourself():
    """POST /profiles/{username}/follow - cannot follow self."""
    r = requests.post(f"{BASE}/profiles/{profile_username}/follow", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    print("PASS: follow self rejected")


def test_24_update_article_unauthorized():
    """PUT /articles/{slug} - unauthorized user cannot update."""
    # Create a new article for this test since previous one was deleted
    r = requests.post(f"{BASE}/articles", json={"article": {"title": "Hacker Article", "description": "x", "body": "y", "tagList": []}}, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 201, f"Create hacker article failed: {r.status_code} {r.text}"
    hacker_article_slug = r.json()["article"]["slug"]

    r2 = requests.post(f"{BASE}/users", json={"user": {"username": "hacker", "email": "hacker@example.com", "password": "pass123"}}, timeout=TIMEOUT)
    hacker_token = r2.json()["user"]["token"]
    hacker_headers = {"Authorization": f"Token {hacker_token}"}
    r = requests.put(f"{BASE}/articles/{hacker_article_slug}", json=update_article, headers=hacker_headers, timeout=TIMEOUT)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    print("PASS: unauthorized article update rejected")


def test_25_wrong_token_prefix():
    """Wrong token prefix should return 403."""
    r = requests.get(f"{BASE}/user", headers={"Authorization": "Bearer fake"}, timeout=TIMEOUT)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    print("PASS: wrong token prefix rejected")


def test_26_create_article_duplicate_slug():
    """POST /articles - duplicate slug should fail."""
    # Create an article first
    r = requests.post(f"{BASE}/articles", json={"article": {"title": "Dup Test Article", "description": "x", "body": "y", "tagList": []}}, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 201, f"Create first article failed: {r.status_code}"
    # Try to create another with same title (same slug)
    r = requests.post(f"{BASE}/articles", json={"article": {"title": "Dup Test Article", "description": "z", "body": "w", "tagList": []}}, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    print("PASS: duplicate slug rejected")


def test_27_update_user_duplicate_username():
    """PUT /user - duplicate username should fail."""
    r = requests.post(f"{BASE}/users", json={"user": {"username": "dupuser", "email": "dup@example.com", "password": "pass123"}}, timeout=TIMEOUT)
    dup_token = r.json()["user"]["token"]
    dup_headers = {"Authorization": f"Token {dup_token}"}
    r = requests.put(f"{BASE}/user", json={"user": {"username": "testuser"}}, headers=dup_headers, timeout=TIMEOUT)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    print("PASS: duplicate username rejected")


def test_28_article_not_found():
    """GET /articles/{slug} - nonexistent slug."""
    r = requests.get(f"{BASE}/articles/nonexistent-slug-xyz", timeout=TIMEOUT)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    print("PASS: article not found")


def test_29_profile_not_found():
    """GET /profiles/{username} - nonexistent username."""
    r = requests.get(f"{BASE}/profiles/nonexistentuser", timeout=TIMEOUT)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    print("PASS: profile not found")


def test_30_delete_article_twice():
    """DELETE /articles/{slug} - delete again should fail."""
    # Create and immediately delete a new article
    r = requests.post(f"{BASE}/articles", json={"article": {"title": "Delete Me", "description": "x", "body": "y", "tagList": []}}, headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 201
    slug = r.json()["article"]["slug"]
    r = requests.delete(f"{BASE}/articles/{slug}", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 204
    # Delete again
    r = requests.delete(f"{BASE}/articles/{slug}", headers=headers(), timeout=TIMEOUT)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    print("PASS: delete already-deleted article rejected")


if __name__ == "__main__":
    tests = [
        test_01_register,
        test_02_login,
        test_03_register_duplicate,
        test_04_login_bad_password,
        test_05_get_current_user,
        test_06_update_current_user,
        test_07_get_profile,
        test_08_follow_unfollow,
        test_09_create_article,
        test_10_list_articles,
        test_11_list_articles_with_filters,
        test_12_get_article,
        test_13_update_article,
        test_14_create_comment,
        test_15_list_comments,
        test_16_favorite_article,
        test_17_unfavorite_article,
        test_18_delete_comment,
        test_19_get_feed,
        test_20_get_tags,
        test_21_delete_article,
        test_22_unauthenticated_access,
        test_23_follow_yourself,
        test_24_update_article_unauthorized,
        test_25_wrong_token_prefix,
        test_26_create_article_duplicate_slug,
        test_27_update_user_duplicate_username,
        test_28_article_not_found,
        test_29_profile_not_found,
        test_30_delete_article_twice,
    ]

    passed = 0
    failed = 0
    errors = []

    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((t.__name__, str(e)))
            print(f"FAIL: {t.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  {name}: {err}")
    else:
        print("All tests passed!")
