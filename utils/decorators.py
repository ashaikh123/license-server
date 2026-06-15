"""Custom decorators
====================

Defines decorators used to protect views for authenticated
administrators and organisation administrators. These ensure that
unauthorised users are redirected to the appropriate login page.
"""

from functools import wraps
from flask import session, redirect, url_for, g

from models.admin import Admin
from models.organization_admin import OrganizationAdmin


def admin_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        admin_id = session.get("admin_id")
        if not admin_id:
            return redirect(url_for("admin.login"))

        admin = Admin.query.get(admin_id)
        if not admin:
            session.pop("admin_id", None)
            return redirect(url_for("admin.login"))

        g.current_admin = admin
        return func(*args, **kwargs)

    return wrapper


def org_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        org_admin_id = session.get("org_admin_id")
        if not org_admin_id:
            return redirect(url_for("org.login"))

        org_admin = OrganizationAdmin.query.get(org_admin_id)
        if not org_admin or not org_admin.is_active:
            session.pop("org_admin_id", None)
            return redirect(url_for("org.login"))

        g.current_org_admin = org_admin
        return func(*args, **kwargs)

    return wrapper