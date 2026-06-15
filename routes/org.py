"""Organisation routes
======================

Defines views accessible to organisation administrators. Each
organisation admin can only see and manage data associated with their
own organisation. These routes are protected by the
``org_login_required`` decorator.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g,
)

from extensions import db
from models.organization import Organization
from models.organization_admin import OrganizationAdmin
from models.user import User
from models.license import License
from models.device import Device
from utils.auth import check_password_hash, generate_password_hash
from utils.decorators import org_login_required
from utils.license_utils import generate_license_key


org_bp = Blueprint("org", __name__, url_prefix="/org")


@org_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log in an organisation administrator."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        admin = OrganizationAdmin.query.filter_by(email=email).first()
        if admin and admin.is_active and check_password_hash(admin.password_hash, password):
            session.clear()
            session["org_admin_id"] = admin.id
            flash("Logged in successfully", "success")
            return redirect(url_for("org.dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("org/login.html")


@org_bp.route("/logout")
@org_login_required
def logout():
    session.pop("org_admin_id", None)
    flash("Logged out", "info")
    return redirect(url_for("org.login"))

@org_bp.route("/view/<token>")
def view_org_dashboard(token):
    org = Organization.query.filter_by(
        dashboard_token=token,
        dashboard_enabled=True,
        is_active=True
    ).first_or_404()

    users = User.query.filter_by(organization_id=org.id).all()
    devices = Device.query.filter_by(organization_id=org.id).all()
    licenses = License.query.join(User).filter(User.organization_id == org.id).all()

    return render_template(
        "org/public_dashboard.html",
        org=org,
        users=users,
        devices=devices,
        licenses=licenses,
        user_count=len(users),
        device_count=len(devices),
        license_count=len(licenses),
    )

@org_bp.route("/dashboard")
@org_login_required
def dashboard():
    """Show organisation overview."""
    org_admin = g.current_org_admin
    org = org_admin.organization
    user_count = User.query.filter_by(organization_id=org.id).count()
    license_count = License.query.join(User).filter(User.organization_id == org.id).count()
    device_count = Device.query.filter_by(organization_id=org.id).count()
    return render_template(
        "org/dashboard.html",
        organization=org,
        user_count=user_count,
        license_count=license_count,
        device_count=device_count,
    )


@org_bp.route("/users")
@org_login_required
def users():
    org_admin = g.current_org_admin
    users = User.query.filter_by(organization_id=org_admin.organization_id).all()
    return render_template("org/users.html", users=users, org=org_admin.organization)


@org_bp.route("/users/add", methods=["GET", "POST"])
@org_login_required
def add_user():
    org_admin = g.current_org_admin
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        is_active = True if request.form.get("is_active") == "on" else False
        if not name or not email:
            flash("Name and email are required", "danger")
        else:
            user = User(
                organization_id=org_admin.organization_id,
                name=name,
                email=email,
                is_active=is_active,
            )
            db.session.add(user)
            db.session.commit()
            flash("User created", "success")
            return redirect(url_for("org.users"))
    return render_template("org/add_user.html")


@org_bp.route("/licenses")
@org_login_required
def licenses():
    org_admin = g.current_org_admin
    licences = License.query.join(User).filter(User.organization_id == org_admin.organization_id).all()
    return render_template("org/licenses.html", licenses=licences)


@org_bp.route("/licenses/add", methods=["GET", "POST"])
@org_login_required
def add_license():
    org_admin = g.current_org_admin
    users = User.query.filter_by(organization_id=org_admin.organization_id).all()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date = request.form.get("start_date")
        expiry_date = request.form.get("expiry_date")
        max_devices = request.form.get("max_devices")
        user = User.query.get(int(user_id)) if user_id else None
        if not user or user.organization_id != org_admin.organization_id:
            flash("Invalid user", "danger")
        else:
            licence_key = generate_license_key()[:16]
            licence = License(
                user_id=user.id,
                key=licence_key,
                status="active",
                start_date=start_date or None,
                expiry_date=expiry_date or None,
                max_devices=int(max_devices) if max_devices else 1,
            )
            db.session.add(licence)
            db.session.commit()
            flash(f"Licence {licence_key} created", "success")
            return redirect(url_for("org.licenses"))
    return render_template("org/add_license.html", users=users)


@org_bp.route("/devices")
@org_login_required
def devices():
    org_admin = g.current_org_admin
    devices = Device.query.filter_by(organization_id=org_admin.organization_id).all()
    return render_template("org/devices.html", devices=devices)