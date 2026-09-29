import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure shopflow-test root is in sys.path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.api_gateway.main import app
from chaos.engine import chaos_engine
from telemetry.engine import telemetry_engine

@pytest.fixture(autouse=True)
def clean_state():
    chaos_engine.reset()
    yield
    chaos_engine.reset()

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
