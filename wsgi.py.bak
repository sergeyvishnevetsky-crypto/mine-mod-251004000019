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

# === auto-register fgwh blueprint ===
try:
    from fgwh import bp as fgwh_bp  # noqa
    app.register_blueprint(fgwh_bp)  # доступно по /fgwh/
except Exception as _e:
    # Лог ошибки при импорте блюпринта не валит приложение
    print("fgwh blueprint register error:", _e)
