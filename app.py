from __future__ import annotations

from flask import Flask, request

from meetingai_api.auth.routes import auth_bp
from meetingai_api.routes.dashboard import register_dashboard_routes
from meetingai_api.routes.mobile_api import register_mobile_api_routes
from meetingai_shared.config import SECRET_KEY


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.register_blueprint(auth_bp)

    @app.after_request
    def disable_cache(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    register_dashboard_routes(app)
    register_mobile_api_routes(app)
    return app


__all__ = ["create_app"]
