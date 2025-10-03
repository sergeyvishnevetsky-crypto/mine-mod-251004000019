from flask import Blueprint, render_template, request, abort, redirect, url_for, flash

cabinet_bp = Blueprint("cabinet", __name__, template_folder="templates")

# Конфиг пунктов (можешь менять подписи)
ITEMS = {
    "1": ("Пункт 1", "pickers/p1.html"),
    "2": ("Пункт 2", "pickers/p2.html"),
    "3": ("Пункт 3", "pickers/p3.html"),
    "4": ("Пункт 4", "pickers/p4.html"),
    "5": ("Пункт 5", "pickers/p5.html"),
    "6": ("Пункт 6", "pickers/p6.html"),
    "7": ("Пункт 7", "pickers/p7.html"),
    "8": ("Пункт 8", "pickers/p8.html"),
}

@cabinet_bp.get("/")
def index():
    tab = request.args.get("tab", "docs")  # 'docs' или 'refs'
    items = [{"key": k, "label": v[0]} for k, v in ITEMS.items()]
    return render_template("cabinet.html", title="Кабинет участка", tab=tab, items=items)

@cabinet_bp.get("/picker/<key>")
def picker(key: str):
    info = ITEMS.get(key)
    if not info:
        abort(404)
    label, tpl = info
    return render_template(tpl, key=key, label=label)

@cabinet_bp.post("/run/<key>")
def run_action(key: str):
    if key not in ITEMS:
        abort(404)
    # пример чтения выбранных параметров
    period = request.form.get("period", "")
    site = request.form.get("site", "")
    shift = request.form.get("shift", "")
    flash(f"Запущено действие {key}: период={period}, участок={site}, смена={shift}", "ok")
    return redirect(url_for("cabinet.index", tab=request.args.get("tab", "docs")))
