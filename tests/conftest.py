"""Pytest fixtures and configuration for SolutionBridge test suites."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

# Explicitly use in-memory SQLite with StaticPool for isolated testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.config import settings
from app.db.database import Base, get_db
from app.db.seed import seed_database
from app.main import app


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    return test_engine


@pytest.fixture(scope="function")
def db(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
