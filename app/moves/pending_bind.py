from flask import request, redirect, url_for
try:
    # Импортируем существующий блюпринт журнала
    from .routes import bp as moves_bp
except Exception:
    # На некоторых сборках имя может быть moves_bp — пытаемся по-другому
    from .routes import moves_bp  # type: ignore

from .pending_store import list_rows, total_qty, bulk_update

# Включаем pending-данные в контекст index через before_request-hook (мягко)
@moves_bp.before_app_request
def _inject_pending_to_moves_index():
    # Ничего не рендерим здесь; логику подтянем в маршруте index через g/_ctx, если надо.
    pass

# Маршрут действий над pending (на том же префиксе /moves)
@moves_bp.route("/pending_action", methods=["POST"])
def pending_action():
    ids = request.form.getlist("ids")
    op  = request.form.get("op")
    if ids and op in ("accept","cancel"):
        bulk_update(ids, op)
    return redirect(url_for("moves.index"))
