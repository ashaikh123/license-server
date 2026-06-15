"""API routes
==============

Exposes endpoints for client applications to activate and validate
licences. These endpoints are designed to be called by desktop
applications packaged as executables. They return JSON responses
indicating whether the licence is valid and any relevant messages.
"""

from datetime import datetime, date

from flask import Blueprint, request, jsonify, current_app

from extensions import db
from models.license import License
from models.user import User
from models.device import Device
from models.usage_log import UsageLog
from models.organization import Organization

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _log_usage(action: str, licence: License | None, user: User | None, org: Organization | None, system_id: str | None, ip: str | None, app_version: str | None, result: str, reason: str | None) -> None:
    """Helper to record API usage attempts."""
    log = UsageLog(
        license_id=licence.id if licence else None,
        user_id=user.id if user else None,
        organization_id=org.id if org else None,
        system_id=system_id,
        ip_address=ip,
        app_version=app_version,
        action=action,
        result=result,
        reason=reason,
        timestamp=datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()


@api_bp.route("/activate", methods=["POST"])
def activate():
    """Activate a licence on a new or existing device."""
    data = request.get_json() or request.form
    license_key = data.get("license_key")
    system_id = data.get("system_id")
    machine_name = data.get("machine_name")
    app_version = data.get("app_version")
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # Optionally enforce API secret key
    api_secret_required = current_app.config.get("API_SECRET_KEY")
    api_secret_received = request.headers.get("X-API-SECRET") or data.get("api_secret_key")
    if api_secret_required and api_secret_received != api_secret_required:
        return jsonify({"valid": False, "reason": "Invalid API secret"}), 401

    if not license_key or not system_id:
        return jsonify({"valid": False, "reason": "Missing required parameters"}), 400

    licence = License.query.filter_by(key=license_key).first()
    if not licence:
        _log_usage(
            action="activate",
            licence=None,
            user=None,
            org=None,
            system_id=system_id,
            ip=client_ip,
            app_version=app_version,
            result="fail",
            reason="License not found",
        )
        return jsonify({"valid": False, "reason": "License not found"}), 404

    # Validate licence status
    if licence.status in ("revoked", "suspended"):
        _log_usage("activate", licence, licence.user, licence.user.organization, system_id, client_ip, app_version, "fail", f"License {licence.status}")
        return jsonify({"valid": False, "reason": f"License {licence.status}"}), 403
    # Check expiry
    if licence.expiry_date and date.today() > licence.expiry_date:
        # Mark as expired if not already
        licence.status = "expired"
        db.session.commit()
        _log_usage("activate", licence, licence.user, licence.user.organization, system_id, client_ip, app_version, "fail", "License expired")
        return jsonify({"valid": False, "reason": "License expired"}), 403

    user = licence.user
    org = user.organization

    if not org.is_active:
        _log_usage("activate", licence, user, org, system_id, client_ip, app_version, "fail", "Organization inactive")
        return jsonify({"valid": False, "reason": "Organization inactive"}), 403

    if not user.is_active:
        _log_usage("activate", licence, user, org, system_id, client_ip, app_version, "fail", "User inactive")
        return jsonify({"valid": False, "reason": "User inactive"}), 403

    # Check existing device
    device = Device.query.filter_by(license_id=licence.id, system_id=system_id).first()
    if device:
        # update last_check and ip
        device.last_check = datetime.utcnow()
        device.ip_address = client_ip
        device.app_version = app_version
        db.session.commit()
        _log_usage("activate", licence, user, org, system_id, client_ip, app_version, "success", None)
        return jsonify({"valid": True, "message": "License valid", "expires_on": licence.expiry_date.isoformat() if licence.expiry_date else None})

    # Check device limit
    active_devices = Device.query.filter_by(license_id=licence.id, is_active=True).count()
    if active_devices >= licence.max_devices:
        _log_usage("activate", licence, user, org, system_id, client_ip, app_version, "fail", "Device limit reached")
        return jsonify({"valid": False, "reason": "Device limit reached"}), 403

    # Register new device
    new_device = Device(
        license_id=licence.id,
        user_id=user.id,
        organization_id=org.id,
        system_id=system_id,
        machine_name=machine_name,
        activation_timestamp=datetime.utcnow(),
        last_check=datetime.utcnow(),
        ip_address=client_ip,
        app_version=app_version,
        is_active=True,
    )
    db.session.add(new_device)
    db.session.commit()
    _log_usage("activate", licence, user, org, system_id, client_ip, app_version, "success", None)
    return jsonify({"valid": True, "message": "License valid", "expires_on": licence.expiry_date.isoformat() if licence.expiry_date else None}), 200


@api_bp.route("/validate", methods=["POST"])
def validate():
    """Validate an existing device and licence."""
    data = request.get_json() or request.form
    license_key = data.get("license_key")
    system_id = data.get("system_id")
    app_version = data.get("app_version")
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    api_secret_required = current_app.config.get("API_SECRET_KEY")
    api_secret_received = request.headers.get("X-API-SECRET") or data.get("api_secret_key")
    if api_secret_required and api_secret_received != api_secret_required:
        return jsonify({"valid": False, "reason": "Invalid API secret"}), 401

    if not license_key or not system_id:
        return jsonify({"valid": False, "reason": "Missing required parameters"}), 400

    licence = License.query.filter_by(key=license_key).first()
    if not licence:
        _log_usage("validate", None, None, None, system_id, client_ip, app_version, "fail", "License not found")
        return jsonify({"valid": False, "reason": "License not found"}), 404

    # Check status
    if licence.status in ("revoked", "suspended"):
        _log_usage("validate", licence, licence.user, licence.user.organization, system_id, client_ip, app_version, "fail", f"License {licence.status}")
        return jsonify({"valid": False, "reason": f"License {licence.status}"}), 403
    if licence.expiry_date and date.today() > licence.expiry_date:
        licence.status = "expired"
        db.session.commit()
        _log_usage("validate", licence, licence.user, licence.user.organization, system_id, client_ip, app_version, "fail", "License expired")
        return jsonify({"valid": False, "reason": "License expired"}), 403

    user = licence.user
    org = user.organization
    if not org.is_active:
        _log_usage("validate", licence, user, org, system_id, client_ip, app_version, "fail", "Organization inactive")
        return jsonify({"valid": False, "reason": "Organization inactive"}), 403
    if not user.is_active:
        _log_usage("validate", licence, user, org, system_id, client_ip, app_version, "fail", "User inactive")
        return jsonify({"valid": False, "reason": "User inactive"}), 403

    # Check device exists
    device = Device.query.filter_by(license_id=licence.id, system_id=system_id).first()
    if not device or not device.is_active:
        _log_usage("validate", licence, user, org, system_id, client_ip, app_version, "fail", "Device not registered")
        return jsonify({"valid": False, "reason": "Device not registered"}), 403

    # Update last_check and metadata
    device.last_check = datetime.utcnow()
    device.ip_address = client_ip
    device.app_version = app_version
    db.session.commit()
    _log_usage("validate", licence, user, org, system_id, client_ip, app_version, "success", None)
    return jsonify({"valid": True, "message": "License valid", "expires_on": licence.expiry_date.isoformat() if licence.expiry_date else None}), 200