from app import create_app
app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


# --- [auto] ensure SECRET_KEY after app is created ---
try:
    _ = app.config['SECRET_KEY']
    if not _:
        raise KeyError
except Exception:
    import os as _os
    app.config['SECRET_KEY'] = _os.environ.get('SECRET_KEY') or 'qwerty123'
# --- [/auto] ---

# --- [auto-fix] ensure SECRET_KEY at the very end of module ---
try:
    import os as _os
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = _os.environ.get('SECRET_KEY') or 'qwerty123'
except Exception as _e:
    # last resort: if app not yet defined or something odd, just ignore
    pass
# --- [/auto-fix] ---

try:
except Exception as _e:
    # Лог ошибки при импорте блюпринта не валит приложение

try:
except Exception as _e:
    pass

# === fgwh blueprint registration (canonical) ===
try:
    from app.fgwh import bp as fgwh_bp
    app.register_blueprint(fgwh_bp)  # /fgwh/
except Exception as e:
    print("fgwh register error:", e)
