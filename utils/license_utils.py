"""Licence utility functions
===========================

Contains helper functions for generating unique licence keys and
checking activation limits.
"""

import uuid
from datetime import datetime

from extensions import db
from models.device import Device


def generate_license_key() -> str:
    """Generate a random 16‑character licence key.

    The key is derived from a UUID4 and uppercased.  Hyphens are
    removed to create a compact string. The resulting key is 32
    characters; if you need a shorter key you can slice the result.

    Returns:
        A unique licence key.
    """
    return str(uuid.uuid4()).replace("-", "").upper()


def count_active_devices(license_obj) -> int:
    """Return the number of active devices associated with a licence.

    Args:
        license_obj: A ``License`` instance.

    Returns:
        The count of devices where ``is_active`` is ``True``.
    """
    return Device.query.filter_by(license_id=license_obj.id, is_active=True).count()


def register_device(license_obj, user, system_id: str, machine_name: str | None, ip_address: str | None, app_version: str | None) -> Device:
    """Create and persist a new device record for an activation.

    Args:
        license_obj: The licence being activated.
        user: The user owning the licence.
        system_id: Unique identifier for the client machine.
        machine_name: Optional human friendly name of the machine.
        ip_address: IP address from which the activation originated.
        app_version: Version of the desktop application.

    Returns:
        The newly created ``Device`` object.
    """
    device = Device(
        license_id=license_obj.id,
        user_id=user.id,
        organization_id=user.organization_id,
        system_id=system_id,
        machine_name=machine_name,
        activation_timestamp=datetime.utcnow(),
        last_check=datetime.utcnow(),
        ip_address=ip_address,
        app_version=app_version,
        is_active=True,
    )
    db.session.add(device)
    db.session.commit()
    return device