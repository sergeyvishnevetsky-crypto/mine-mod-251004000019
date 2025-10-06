from flask import Blueprint, render_template, request, send_file, jsonify
import io
import pandas as pd

revexp_bp = Blueprint("revexp_items", __name__, template_folder="templates")

# Единый набор колонок
REQUIRED = ["код", "тип", "статья", "ЦФО"]
# «Память» в процессе (как в других справочниках). Для прод — обычно БД.
_DATA = pd.DataFrame(columns=REQUIRED)

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    # Приведём имена колонок
    df = df.rename(columns={c: str(c).strip() for c in df.columns})
    # Кейс 1: уже единый формат
    if set(REQUIRED).issubset(df.columns):
        out = df[REQUIRED].copy()
    # Кейс 2: «доходы» отдельно
    elif {"код", "статья_дохода", "ЦФО"}.issubset(df.columns):
        out = pd.DataFrame({
            "код": df["код"], "тип": "Доход",
            "статья": df["статья_дохода"], "ЦФО": df["ЦФО"]
        })
    # Кейс 3: «расходы» отдельно
    elif {"код", "статья_расхода", "ЦФО"}.issubset(df.columns):
        out = pd.DataFrame({
            "код": df["код"], "тип": "Расход",
            "статья": df["статья_расхода"], "ЦФО": df["ЦФО"]
        })
    else:
        raise ValueError("Ожидаю колонки: (код, тип, статья, ЦФО) ИЛИ (код, статья_дохода, ЦФО) ИЛИ (код, статья_расхода, ЦФО)")
    # Нормализуем значения «тип»
    out["тип"] = (
        out["тип"].fillna("").astype(str).str.strip().str.title()
        .replace({"Доходы": "Доход", "Расходы": "Расход"})
    )
    if out.isna().any().any():
        raise ValueError("Пустые значения в обязательных полях")
    return out[REQUIRED]

@revexp_bp.get("/dict/revexp-items/")
def index():
    return render_template("revexp_items/index.html")

@revexp_bp.get("/dict/revexp-items/params")
def params():
    return jsonify({
        "columns_unified": REQUIRED,
        "columns_income": ["код", "статья_дохода", "ЦФО"],
        "columns_expense": ["код", "статья_расхода", "ЦФО"],
        "count": int(_DATA.shape[0]),
    })

@revexp_bp.get("/dict/revexp-items/template.xlsx")
def template_xlsx():
    # Дадим вкладки: «единый», «доходы», «расходы»
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame(columns=REQUIRED).to_excel(xw, sheet_name="единый", index=False)
        pd.DataFrame(columns=["код", "статья_дохода", "ЦФО"]).to_excel(xw, sheet_name="доходы", index=False)
        pd.DataFrame(columns=["код", "статья_расхода", "ЦФО"]).to_excel(xw, sheet_name="расходы", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="revexp-items-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@revexp_bp.post("/dict/revexp-items/import")
def import_():
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "Файл не передан"}), 400
    name = (f.filename or "").lower()
    try:
        if name.endswith((".xlsx", ".xlsm", ".xls")):
            df = pd.read_excel(f)
        else:
            df = pd.read_csv(f)
        use = _normalize(df)
        global _DATA
        _DATA = use.reset_index(drop=True)
        return jsonify({"ok": True, "rows": int(_DATA.shape[0])})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@revexp_bp.get("/dict/revexp-items/export.csv")
def export_csv():
    if _DATA.empty:
        return jsonify({"ok": False, "error": "Нет данных — загрузите файл"}), 400
    buf = io.StringIO()
    _DATA.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8")),
                     as_attachment=True, download_name="revexp-items.csv",
                     mimetype="text/csv; charset=utf-8")

@revexp_bp.get("/dict/revexp-items/export.xlsx")
def export_xlsx():
    if _DATA.empty:
        return jsonify({"ok": False, "error": "Нет данных — загрузите файл"}), 400
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        _DATA.to_excel(xw, sheet_name="данные", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="revexp-items.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
