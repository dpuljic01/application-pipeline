import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.core.security.deps import CurrentUser, get_current_user
from app.db.base import Base
from app.db.models import User
from app.db.session import engine, get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _tables():
    # checkfirst=True (the default) means this is a no-op against a DB that
    # already has the schema applied via Alembic - safe to run every session.
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session():
    """Give each test its own transaction, rolled back at teardown.

    App code calls db.commit() inside services (see CLAUDE.md's layering
    rules), which would normally end the transaction early. Binding the
    session to a connection that already has an outer transaction open, and
    re-opening a SAVEPOINT every time the session ends one, means those
    commits only release the savepoint - the outer transaction (and
    everything in it) is still rolled back when the test finishes.
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if not connection.in_nested_transaction():
            connection.begin_nested()

    try:
        yield session
    finally:
        event.remove(session, "after_transaction_end", _restart_savepoint)
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def test_user(db_session):
    user = User(cognito_sub=uuid.uuid4(), email="test@example.com")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def client(db_session, test_user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=test_user.id,
        cognito_sub=test_user.cognito_sub,
        email=test_user.email,
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
