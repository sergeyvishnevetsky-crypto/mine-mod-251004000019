"""
Package shim for FGWH blueprint:
- some code imports "from app.fgwh import bp"
- our actual blueprint is defined in app.fgwh.routes as fgwh_bp
This file exports bp -> fgwh_bp if available.
"""
try:
    from .routes import fgwh_bp as bp  # noqa: F401
except Exception as e:
    # Keep a clear message but don't crash app import
    print(f"fgwh register error: {e}")
    bp = None
