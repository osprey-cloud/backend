from app.helpers.admin import create_default_roles
import pytest

from app.models.user import User
from server import create_app, db


@pytest.fixture(scope='function')
def new_user(test_client):
    user = User(
        email='test_email@testdomain.com', password='test_password', name='test_name')
    user.verified=True
    user.save()
    return user


@pytest.fixture(scope='function')
def test_client(monkeypatch):
    flask_app = create_app(config_name='testing')
    monkeypatch.setenv("SECRET_KEY", "192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf")
    # create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        # Establish an application context
        with flask_app.app_context():
            # create the database and database tables
            db.engine.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            db.create_all()
            create_default_roles()

            yield testing_client  # this is where the testing happens
            db.session.remove()
            db.drop_all()


@pytest.fixture(scope='function')
def login_default_user(test_client):
    test_client.post('/users/login',
                     data=dict(email='test_email@testdomain.com', password='test_password'),
                     content_type='application/json',
                     follow_redirects=True,
                     )

    yield  # testing happens
