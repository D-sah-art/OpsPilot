import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
TEST_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = TEST_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Also ensure shopflow-test is in sys.path for end-to-end integration testing
PROJECT_ROOT = BACKEND_ROOT.parent
SHOPFLOW_ROOT = PROJECT_ROOT / "shopflow-test"
if str(SHOPFLOW_ROOT) not in sys.path:
    sys.path.insert(0, str(SHOPFLOW_ROOT))

from app.database.session import Base, get_db
from app.database.repository import TelemetryRepository
from app.topology.graph import dependency_graph
from app.main import app

# In-memory test SQLite engine
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
