
# --- stable registration for moves blueprint ---
def _register_moves(app):
    try:
        from app.moves import routes as _moves_routes
        register_bp_once(app, _moves_routes.bp, \"/moves\")
        app.logger.info("moves blueprint registered")
    except Exception as e:
        # не проглатываем тихо — логируем, чтобы не было 404 незаметно
        app.logger.error("moves register error: %s", e)
        raise

from flask import Flask

def _safe_import(module_path, attr=None):
    """
    Пытаемся импортировать блюпринт из module_path.
    Если нет — молча пропускаем, чтобы приложение грузилось.
    """
    try:
        mod = __import__(module_path, fromlist=['*'])
        return getattr(mod, attr) if attr else mod
    except Exception as e:
        # Можно логировать в stdout, но не валим импорт
        print(f"[WARN] skip {module_path} ({e})")
        return None

def create_app():
    # ensure /moves is registered
    from flask import current_app as _ca

    app = Flask(__name__)

    # stable moves registration
    try:
        _register_moves(app)
    except Exception:
        pass
    modules = [
        ("app.main.routes", "main_bp", None),
        ("app.cabinet.routes", "cabinet_bp", "/cabinet"),
        ("app.employees.routes", "employees_bp", "/employees"),
        ("app.access_control.routes", "access_bp", "/access"),

        # Справочники
        ("app.norms.routes", "norms_bp", "/dict/norms"),
        ("app.tmc.routes", "tmc_bp", "/dict/tmc"),
        ("app.services.routes", "services_bp", "/dict/services"),
        ("app.revexp_items", "revexp_bp", "/dict/revexp-items"),
        ("app.cost_items", "bp", "/dict/cost-items"),

        # Прочее
        ("app.fgwh.routes", "bp", "/fgwh"),
        ("app.products.routes", "bp", "/products"),
        ("app.recipes.routes", "bp", "/recipes"),
        ("app.moves.routes", "bp", "/moves"),
        ("app.workbook.routes", "workbook_bp", "/workbook"),
        ("app.mining_report.routes", "mining_bp", "/mining-report"),
        ("app.request_tmc.routes", "request_tmc_bp", "/requests/tmc"),
        ("app.request_services.routes", "request_services_bp", "/requests/services"),        ("app.fg_warehouse", "fgwh_bp", "/fg-warehouse"),        ("app.processing_report", "proc_bp", "/processing-report"),


    ]

    for module_path, attr, prefix in modules:
        bp = _safe_import(module_path, attr)
        if bp:
            register_bp_once(app, bp, prefix)

    return app

# --- auto-registered by script: moves blueprint ---
try:
    from app.moves.routes import bp as moves_bp
    register_bp_once(app, moves_bp, url_prefix="/moves")
except Exception as e:
    print("moves register error:", e)
# --- end moves blueprint block ---


def register_bp_once(app, bp, prefix=None):
    """Регистрирует блюпринт только если его имя ещё не зарегистрировано."""
    try:
        name = getattr(bp, "name", None) or getattr(bp, "blueprint", getattr(bp, "__name__", ""))
        if name and name in app.blueprints:
            # уже есть — молча выходим
            return
    except Exception:
        pass
    register_bp_once(app, bp, prefix)
