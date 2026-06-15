"""Authentication helpers
=========================

Provides convenience wrappers around Werkzeug's password hashing
functions and helper methods for verifying user credentials.
"""

from werkzeug.security import generate_password_hash as _generate_password_hash, check_password_hash as _check_password_hash


def generate_password_hash(password: str) -> str:
    """Return a secure hash for the given password.

    Args:
        password: The plaintext password to hash.

    Returns:
        A salted hash which can be stored safely in the database.
    """
    return _generate_password_hash(password)


def check_password_hash(pwhash: str, password: str) -> bool:
    """Check a password against an existing hash.

    Args:
        pwhash: The stored password hash.
        password: The candidate plaintext password.

    Returns:
        ``True`` if the password matches the hash, else ``False``.
    """
    return _check_password_hash(pwhash, password)