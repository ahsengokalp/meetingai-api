from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from meetingai_api.services.ldap_service import LdapService


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Kullanici adi ve sifre zorunludur.")
            return render_template("auth_login.html")

        user = LdapService.authenticate(username, password)

        if user:
            session["user"] = user["username"]
            session["user_dn"] = user["user_dn"]
            return redirect(url_for("dashboard"))

        flash("Kullanici adi veya sifre hatali.")
        return render_template("auth_login.html")

    return render_template("auth_login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
