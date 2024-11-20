import os


class Base:
    """ base config """

    # main
    SECRET_KEY = os.getenv("FLASK_APP_SECRET")
    PASSWORD_SALT = os.getenv("FLASK_APP_SALT")
    VERIFICATION_SALT = os.getenv("FLASK_VERIFY_SALT")

    # mail settings
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True

    # gmail authentication
    MAIL_USERNAME = os.getenv("APP_MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("APP_MAIL_PASSWORD")

    # mail accounts
    MAIL_DEFAULT_SENDER = "no-reply@cranecloud.io"

    # EXCEPTIONS
    PROPAGATE_EXCEPTIONS = True

    # Github auth
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

    # celery
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Log level
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

    KUBE_SERVICE_PORT = int(os.getenv("KUBE_SERVICE_PORT", "80"))

    # Docker logins (optional)
    SYSTEM_DOCKER_EMAIL = os.getenv("SYSTEM_DOCKER_EMAIL")
    SYSTEM_DOCKER_PASSWORD = os.getenv("SYSTEM_DOCKER_PASSWORD")
    SYSTEM_DOCKER_SERVER = os.getenv("SYSTEM_DOCKER_SERVER", 'docker.io')

    # logger app url
    LOGGER_APP_URL = os.getenv('LOGGER_APP_URL', None)

    # mlops api
    MLOPS_API_URL = os.getenv('MLOPS_API_URL', None)


class Development(Base):
    """ development config """

    DEBUG = True
    # SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@database/cranecloud"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI", "postgresql:///cranecloud")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/cranecloud")


class Testing(Base):
    """ test environment config """

    TESTING = True
    DEBUG = True
    # use a separate db

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URI") or "postgresql:///cranecloud_test_db"
    MONGO_URI = os.getenv(
        "TEST_MONGO_URI", "mongodb://localhost:27017/cranecloud_test_db")


class Staging(Base):
    """ Staging config """

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    MONGO_URI = os.getenv("MONGO_URI")


class Production(Base):
    """ production config """

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    MONGO_URI = os.getenv("MONGO_URI")


app_config = {"development": Development, "testing": Testing,
              "staging": Staging, "production": Production}
