# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, abort

cabinet_bp = Blueprint("cabinet", __name__, template_folder="templates")

DOCS = {
    '1': ('Книга нарядов', 'pickers/workbook.html'),
    '2': ('Заявка на ТМЦ', 'pickers/req_tmc.html'),
    '3': ('Заявка на оказание услуг', 'pickers/req_services.html'),
    '4': ('Табель выходов', 'pickers/generic.html'),
    '7': ('Баланс ТМЦ', 'pickers/generic.html'),
    '9': ('Отчет об оказанных услугах', 'pickers/generic.html'),
}


REFS = {
    '1': ('Нормы и расценки', 'pickers/norms.html'),
    '2': ('Перечень ТМЦ', 'pickers/tmc.html'),
    '3': ('Перечень услуг', 'pickers/services.html'),
    '4': ('Статьи доходов и расходов', 'pickers/revexp_items.html'),
    'fgwh': ('Склады готовой продукции', 'pickers/fgwh.html'),
    'products': ('Номенклатура продукции', 'pickers/products.html'),
    'recipes': ('Рецепты переработки', 'pickers/recipes.html'),
}
# Движение продукции — отдельная вкладка
MOV = {    'journal': ('Журнал движения продукции', 'pickers/moves_journal.html'),

    '90': ('Отчёт о переработке', 'pickers/proc.html'),
    '5': ('Отчет о добыче', 'pickers/report_mining.html'),
    '6': ('Отчет об отгрузке', 'pickers/generic.html'),
    '8': ('Баланс товара', 'pickers/generic.html'),
}


# Карта вкладок и общий индекс
TAB_MAP = {
    "docs": DOCS,
    "refs": REFS,
    "moves": MOV,
}
ALL_MAP = {**DOCS, **REFS, **MOV}

@cabinet_bp.route("/")
def index():
    tab = request.args.get("tab", "docs")
    items_map = TAB_MAP.get(tab, DOCS)
    items = [{"key": k, "label": v[0], "tpl": v[1]} for k, v in sorted(items_map.items())]
    return render_template("cabinet.html", title="Кабинет участка", tab=tab, items=items)

@cabinet_bp.route("/picker/<key>")
def picker(key):
    tab = request.args.get("tab", "docs")
    tab = (tab or "docs").strip().lower()
    TAB_MAP = {
        "docs": DOCS,
        "refs": REFS,
        "moves": MOV,
    }
    items_map = TAB_MAP.get(tab)
    if not items_map:
        abort(404)
    rec = items_map.get(key) or items_map.get(str(key))
    if not rec:
        abort(404)
    label, tpl = rec
    return render_template(tpl, key=key, tab=tab, label=label)
