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

