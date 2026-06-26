"""Application configuration
=============================

This module defines the configuration settings for the Flask
application. It reads values from environment variables where
possible to allow easy configuration in different environments,
including local development, testing and production. When an
environment variable is not provided, a reasonable default is used.

Environment variables expected:

- ``DATABASE_URL``: SQLAlchemy database URL. If not set, a local
  SQLite database is used. For production, set this to your
  Supabase PostgreSQL connection string.
- ``SECRET_KEY``: Secret key used to secure sessions and other
  cryptographic features. In production, this should be a long
  random string.
- ``ADMIN_EMAIL`` and ``ADMIN_PASSWORD``: Credentials for the
  super‑administrator account created automatically on startup.
- ``API_SECRET_KEY``: Optional secret key that can be used to
  authenticate API requests from clients. The API does not enforce
  this by default but it can be enabled in the API routes if
  desired.

See ``.env.example`` for sample values.
"""

import os


class Config:
    """Base configuration class.

    Attributes defined here are loaded from environment variables
    where possible, otherwise default values are used. These
    settings are read by the Flask application via ``app.config``.
    """

    # Secret key for session signing. Overridden via environment
    # variable in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")

    # Database connection string. Supabase provides a PostgreSQL URL
    # which can be used here directly. When not provided a SQLite
    # database in the project directory is used for development.
    db_url = os.environ.get("DATABASE_URL")

    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url or \
        f"sqlite:///{os.path.join(os.getcwd(), 'license_server.db')}"

    # Disable SQLAlchemy event notifications (recommended).
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default administrator credentials. These values are used to
    # automatically create a super administrator on first launch.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Optional secret key for authenticating API calls. Clients can
    # include this value in their requests to prove authenticity.
    API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "api-secret-key")

    OFFLINE_GRACE_MINUTES = int(os.environ.get("OFFLINE_GRACE_MINUTES", 10))