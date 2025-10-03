from flask import Blueprint, render_template, request, abort, redirect, url_for, flash

cabinet_bp = Blueprint("cabinet", __name__, template_folder="templates")

# ===== СПРАВОЧНИКИ (вкладка refs) =====
REFS = {
    "1": ("Нормы и расценки",        "pickers/norms.html"),
    "2": ("Перечень ТМЦ",             "pickers/tmc.html"),
    "3": ("Перечень услуг",           "pickers/services.html"),
}

# ===== РАБОЧИЕ ДОКУМЕНТЫ (вкладка docs) =====
DOCS = {
    "1": ("Книга нарядов",               "pickers/workbook.html"),
    "2": ("Заявка на ТМЦ",               "pickers/generic.html"),
    "3": ("Заявка на оказание услуг",    "pickers/generic.html"),
    "4": ("Табель выходов",              "pickers/generic.html"),
    "5": ("Отчет о добыче",              "pickers/generic.html"),
    "6": ("Отчет об отгрузке",           "pickers/generic.html"),
    "7": ("Баланс ТМЦ",                  "pickers/generic.html"),
    "8": ("Баланс товара",               "pickers/generic.html"),
    "9": ("Отчет об оказанных услугах",  "pickers/generic.html"),
}

def _items_for(tab:str):
    return REFS if tab == "refs" else DOCS

@cabinet_bp.get("/")
def index():
    tab = request.args.get("tab", "docs")  # 'docs' или 'refs'
    ITEMS = _items_for(tab)
    items = [{"key": k, "label": v[0]} for k, v in ITEMS.items()]
    return render_template("cabinet.html", title="Кабинет участка", tab=tab, items=items)

@cabinet_bp.get("/picker/<key>")
def picker(key: str):
    tab = request.args.get("tab", "docs")
    ITEMS = _items_for(tab)
    info = ITEMS.get(key)
    if not info:
        abort(404)
    label, tpl = info
    # передаём текущую вкладку, чтобы после submit вернуться туда же
    return render_template(tpl, key=key, label=label, tab=tab)

@cabinet_bp.post("/run/<key>")
def run_action(key: str):
    tab = request.args.get("tab", "docs")
    ITEMS = _items_for(tab)
    if key not in ITEMS:
        abort(404)
    # пример чтения параметров формы
    period = request.form.get("period", "")
    site = request.form.get("site", "")
    shift = request.form.get("shift", "")
    flash(f"[{ 'Справочники' if tab=='refs' else 'Рабочие документы' }] {ITEMS[key][0]} → период={period}, участок={site}, смена={shift}", "ok")
    return redirect(url_for("cabinet.index", tab=tab))
