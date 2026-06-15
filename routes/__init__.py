"""Blueprint registrations
=========================

This module exposes the blueprints used by the application. Importing
these here allows the application factory to register all routes
easily without importing each file individually in ``app.py``.
"""

from .admin import admin_bp  # noqa: F401
from .org import org_bp  # noqa: F401
from .api import api_bp  # noqa: F401