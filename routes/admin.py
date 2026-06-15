"""Admin routes
===============

Defines all views for super administrators. Admin users can log in
using the email and password set in the environment. Once logged
in they can manage organisations, users, licences, devices and
inspection logs. These routes are protected by the
``admin_login_required`` decorator to ensure only authenticated
administrators can access them.
"""

import secrets
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from extensions import db
from models.organization import Organization
from models.user import User
from models.license import License
from models.device import Device
from models.usage_log import UsageLog
from models.admin import Admin
from utils.auth import check_password_hash
from utils.auth import generate_password_hash
from utils.decorators import admin_login_required
from utils.license_utils import generate_license_key


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Display the admin login form and authenticate the administrator."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            flash("Logged in successfully", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
@admin_login_required
def logout():
    """Log out the current admin."""
    session.pop("admin_id", None)
    flash("You have been logged out", "info")
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@admin_login_required
def dashboard():
    """Show a summary of the system, including counts of objects."""
    org_count = Organization.query.count()
    user_count = User.query.count()
    license_count = License.query.count()
    device_count = Device.query.count()
    return render_template(
        "admin/dashboard.html",
        org_count=org_count,
        user_count=user_count,
        license_count=license_count,
        device_count=device_count,
    )


@admin_bp.route("/organizations", methods=["GET", "POST"])
@admin_login_required
def organizations():
    if request.method == "POST":
        name = request.form.get("name")
        contact_person = request.form.get("contact_person")
        contact_email = request.form.get("contact_email")
        is_active = True if request.form.get("is_active") == "on" else False

        if not name:
            flash("Organization name is required", "danger")
        else:
            org = Organization(
                name=name,
                contact_person=contact_person,
                contact_email=contact_email,
                is_active=is_active,
                dashboard_token=secrets.token_urlsafe(32),
                dashboard_enabled=True,
            )
            db.session.add(org)
            db.session.commit()
            flash("Organization created successfully", "success")
            return redirect(url_for("admin.organizations"))

    orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    return render_template("admin/organizations.html", orgs=orgs)


@admin_bp.route("/organizations/add", methods=["GET", "POST"])
@admin_login_required
def add_organization():
    """Create a new organisation."""
    if request.method == "POST":
        name = request.form.get("name")
        contact_person = request.form.get("contact_person")
        contact_email = request.form.get("contact_email")
        is_active = True if request.form.get("is_active") == "on" else False
        if not name:
            flash("Organisation name is required", "danger")
        else:
            org = Organization(
                name=name,
                contact_person=contact_person,
                contact_email=contact_email,
                is_active=is_active,
                dashboard_token=secrets.token_urlsafe(32),
                dashboard_enabled=True,
            )
            db.session.add(org)
            db.session.commit()
            flash("Organisation created", "success")
            return redirect(url_for("admin.organizations"))
    return render_template("admin/add_organization.html")

@admin_bp.route("/organizations/deactivate/<int:org_id>", methods=["POST"])
@admin_login_required
def deactivate_organization(org_id):
    org = Organization.query.get_or_404(org_id)

    org.is_active = False
    org.dashboard_enabled = False

    db.session.commit()

    flash("Organization deactivated successfully", "success")
    return redirect(url_for("admin.organizations"))

@admin_bp.route("/organizations/regenerate-token/<int:org_id>", methods=["POST"])
@admin_login_required
def regenerate_org_token(org_id):
    org = Organization.query.get_or_404(org_id)

    org.dashboard_token = secrets.token_urlsafe(32)
    org.dashboard_enabled = True

    db.session.commit()

    flash("Dashboard link regenerated successfully", "success")
    return redirect(url_for("admin.organizations"))

@admin_bp.route("/organizations/edit/<int:org_id>", methods=["GET", "POST"])
@admin_login_required
def edit_organization(org_id):
    """Edit an existing organisation."""
    org = Organization.query.get_or_404(org_id)
    if request.method == "POST":
        org.name = request.form.get("name")
        org.contact_person = request.form.get("contact_person")
        org.contact_email = request.form.get("contact_email")
        org.is_active = True if request.form.get("is_active") == "on" else False
        db.session.commit()
        flash("Organisation updated", "success")
        return redirect(url_for("admin.organizations"))
    return render_template("admin/edit_organization.html", org=org)


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_login_required
def users():
    orgs = Organization.query.filter_by(is_active=True).all()

    if request.method == "POST":
        organization_id = request.form.get("organization_id")
        name = request.form.get("name")
        email = request.form.get("email")
        is_active = True if request.form.get("is_active") == "on" else False

        if not organization_id or not name or not email:
            flash("Organization, user name and email are required", "danger")
        else:
            user = User(
                organization_id=int(organization_id),
                name=name,
                email=email,
                is_active=is_active,
            )
            db.session.add(user)
            db.session.commit()

            flash("User created successfully", "success")
            return redirect(url_for("admin.users"))

    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users, orgs=orgs)

@admin_bp.route("/users/deactivate/<int:user_id>", methods=["POST"])
@admin_login_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)

    user.is_active = False

    # Revoke all active licenses for this user
    for lic in user.licenses:
        if lic.status == "active":
            lic.status = "revoked"

    db.session.commit()

    flash("User deactivated and active licenses revoked", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/activate/<int:user_id>", methods=["POST"])
@admin_login_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)

    user.is_active = True
    db.session.commit()

    flash("User activated successfully", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/licenses", methods=["GET", "POST"])
@admin_login_required
def licenses():
    users = User.query.filter_by(is_active=True).all()

    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date_raw = request.form.get("start_date")
        expiry_date_raw = request.form.get("expiry_date")
        max_devices = request.form.get("max_devices")

        start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date() if start_date_raw else None
        expiry_date = datetime.strptime(expiry_date_raw, "%Y-%m-%d").date() if expiry_date_raw else None

        user = User.query.get(int(user_id)) if user_id else None

        if not user:
            flash("User is required", "danger")
        else:
            licence_key = generate_license_key()[:16]

            licence = License(
                user_id=user.id,
                key=licence_key,
                status="active",
                start_date=start_date,
                expiry_date=expiry_date,
                max_devices=int(max_devices) if max_devices else 1,
            )

            db.session.add(licence)
            db.session.commit()

            flash(f"License {licence_key} created successfully", "success")
            return redirect(url_for("admin.licenses"))

    all_licenses = License.query.order_by(License.created_at.desc()).all()
    return render_template("admin/licenses.html", licenses=all_licenses, users=users)

@admin_bp.route("/licenses/revoke/<int:license_id>", methods=["POST"])
@admin_login_required
def revoke_license(license_id):
    lic = License.query.get_or_404(license_id)

    lic.status = "revoked"

    # Deactivate linked devices
    for device in lic.devices:
        device.is_active = False

    db.session.commit()

    flash("License revoked successfully", "success")
    return redirect(url_for("admin.licenses"))

@admin_bp.route("/licenses/grant/<int:license_id>", methods=["POST"])
@admin_login_required
def grant_license(license_id):
    lic = License.query.get_or_404(license_id)

    lic.status = "active"
    db.session.commit()

    flash("License granted again successfully", "success")
    return redirect(url_for("admin.licenses"))

@admin_bp.route("/licenses/add", methods=["GET", "POST"])
@admin_login_required
def add_license():
    """Assign a new licence to a user."""
    users = User.query.all()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date_raw = request.form.get("start_date")
        expiry_date_raw = request.form.get("expiry_date")

        start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date() if start_date_raw else None
        expiry_date = datetime.strptime(expiry_date_raw, "%Y-%m-%d").date() if expiry_date_raw else None
        max_devices = request.form.get("max_devices")
        user = User.query.get(int(user_id)) if user_id else None
        if not user:
            flash("User is required", "danger")
        else:
            licence_key = generate_license_key()[:16]
            licence = License(
                user_id=user.id,
                key=licence_key,
                status="active",
                start_date=start_date,
                expiry_date=expiry_date,
                max_devices=int(max_devices) if max_devices else 1,
            )
            db.session.add(licence)
            db.session.commit()
            flash(f"Licence {licence_key} created for {user.email}", "success")
            return redirect(url_for("admin.licenses"))
    return render_template("admin/add_license.html", users=users)

@admin_bp.route("/users/add", methods=["GET", "POST"])
@admin_login_required
def add_user():
    orgs = Organization.query.all()

    if request.method == "POST":
        organization_id = request.form.get("organization_id")
        name = request.form.get("name")
        email = request.form.get("email")
        is_active = True if request.form.get("is_active") == "on" else False

        if not organization_id or not name or not email:
            flash("Organization, name and email are required", "danger")
        else:
            user = User(
                organization_id=int(organization_id),
                name=name,
                email=email,
                is_active=is_active,
            )
            db.session.add(user)
            db.session.commit()
            flash("User created successfully", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/add_user.html", orgs=orgs)

@admin_bp.route("/devices")
@admin_login_required
def devices():
    """List all devices."""
    all_devices = Device.query.all()
    return render_template("admin/devices.html", devices=all_devices)


@admin_bp.route("/logs")
@admin_login_required
def logs():
    """Display usage logs."""
    logs = UsageLog.query.order_by(UsageLog.timestamp.desc()).limit(100).all()
    return render_template("admin/logs.html", logs=logs)