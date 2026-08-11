import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND_ROOT / 'test_drdoom.db'}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def registered_client(client, request):
    # Unique email per test — the DB persists across the whole test session,
    # so a fixed address would 409 (already registered) on the second test
    # that uses this fixture and silently leave the client unauthenticated.
    import hashlib

    short_hash = hashlib.sha1(f"{request.node.name}-{id(client)}".encode()).hexdigest()[:12]
    unique_email = f"pytestuser-{short_hash}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "TestPassword123", "full_name": "Pytest User"},
    )
    assert resp.status_code == 201, f"fixture registration failed: {resp.status_code} {resp.text}"
    return client
