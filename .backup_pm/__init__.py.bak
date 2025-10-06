from app.cost_items import bp as cost_items_bp
from flask import Flask
from .main.routes import main_bp
from .employees.routes import employees_bp
from .access_control.routes import access_bp
from .cabinet.routes import cabinet_bp
from .norms.routes import norms_bp
from .tmc.routes import tmc_bp
from .services.routes import services_bp
from .workbook.routes import workbook_bp
from .mining_report.routes import mining_bp
from .request_tmc.routes import request_tmc_bp
from .request_services.routes import request_services_bp
from .revexp_items import revexp_bp
def create_app():
    app=Flask(__name__)
    app.config["SECRET_KEY"]="change-me"
    app.register_blueprint(main_bp)
    app.register_blueprint(employees_bp, url_prefix="/employees")
    app.register_blueprint(access_bp, url_prefix="/access")
    app.register_blueprint(cabinet_bp, url_prefix="/cabinet")
    app.register_blueprint(norms_bp, url_prefix="/norms")
    app.register_blueprint(tmc_bp, url_prefix="/tmc")
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(workbook_bp, url_prefix="/workbook")
    app.register_blueprint(mining_bp, url_prefix="/mining_report")
    app.register_blueprint(request_tmc_bp, url_prefix="/request_tmc")
    app.register_blueprint(request_services_bp, url_prefix="/request_services")
        # Product Metrics: основной и совместимый пути

        # -- Product Metrics (dict) --
    try:
        from .product_metrics import bp as product_metrics_bp, compat_bp as product_metrics_compat_bp
        if 'product_metrics' not in app.blueprints:
            app.register_blueprint(product_metrics_bp, url_prefix="/dict/product-metrics")
        if 'product_metrics_compat' not in app.blueprints:
            app.register_blueprint(product_metrics_compat_bp, url_prefix="/dict/r")
    except Exception as e:
        app.logger.warning(f'product_metrics init failed: {e}')

    app.register_blueprint(revexp_bp, url_prefix="/dict/revexp-items")
        app.register_blueprint(prod_bp, url_prefix="/dict/prod-metrics")
return app
from .prod_metrics import prod_bp
