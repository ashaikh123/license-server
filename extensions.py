"""Extensions module to hold reusable Flask extensions.

This module creates and exposes instances of extensions such as
SQLAlchemy. Keeping these objects in a dedicated file helps avoid
circular imports when they need to be referenced in models or
elsewhere across the application.
"""

from flask_sqlalchemy import SQLAlchemy

# The database instance used across the application. It is initialised
# in the application factory in ``app.py``. Other modules should
# import this object rather than creating their own SQLAlchemy
# instances to ensure all models share the same database connection.
db = SQLAlchemy()