from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
import io
import os
import pandas as pd

bp = Blueprint("cost_items", __name__, template_folder="templates")
DATA_PATH = os.getenv("COST_ITEMS_CSV", os.path.join("data", "cost_items.csv"))

COLUMNS = ["code", "name", "cfo", "archived"]
HUMAN = {"code": "Код статьи", "name": "Статья затрат", "cfo": "ЦФО", "archived": "archived"}

def _ensure_file():
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)

def _read():
    _ensure_file()
    df = pd.read_csv(DATA_PATH, dtype=str).fillna("")
    if "archived" not in df.columns: df["archived"] = ""
    # нормализуем порядок колонок
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    # генерируем id = индекс
    df = df.reset_index().rename(columns={"index": "id"})
    df["id"] = df["id"].astype(int)
    return df

def _write(df: pd.DataFrame):
    out = df[[c for c in COLUMNS if c in df.columns]].copy()
    out.to_csv(DATA_PATH, index=False)

@bp.route("/")
def index():
    df = _read()
    q = (request.args.get("q") or "").strip().lower()
    cfo = (request.args.get("cfo") or "").strip()
    if q:
        df = df[df["code"].str.lower().str.contains(q) | df["name"].str.lower().str.contains(q)]
    if cfo:
        df = df[df["cfo"] == cfo]
    # список ЦФО для фильтра
    cfo_values = sorted(v for v in df["cfo"].unique() if v)
    # отображаем
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id": int(r["id"]),
            "code": r["code"],
            "name": r["name"],
            "cfo": r["cfo"],
            "archived": (str(r["archived"]).strip().lower() in ("1","true","yes","y","да"))
        })
    return render_template("cost_items/index.html", rows=rows, cfo_values=cfo_values)

@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        name = (request.form.get("name") or "").strip()
        cfo  = (request.form.get("cfo") or "").strip()
        if not code or not name:
            flash("Код статьи и Статья затрат — обязательны", "danger")
            return redirect(url_for("cost_items.new"))
        df = _read()
        if (df["code"] == code).any():
            flash("Запись с таким кодом уже существует", "danger")
            return redirect(url_for("cost_items.new"))
        new_row = pd.DataFrame([{"code": code, "name": name, "cfo": cfo, "archived": ""}])
        df = pd.concat([df[COLUMNS], new_row], ignore_index=True)
        _write(df)
        flash("Добавлено", "success")
        return redirect(url_for("cost_items.index"))
    return render_template("cost_items/form.html", title="Добавить статью", data={"code":"","name":"","cfo":""})

@bp.route("/<int:rid>/edit", methods=["GET", "POST"])
def edit(rid: int):
    df = _read()
    if rid < 0 or rid >= len(df):
        flash("Запись не найдена", "danger")
        return redirect(url_for("cost_items.index"))
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        name = (request.form.get("name") or "").strip()
        cfo  = (request.form.get("cfo") or "").strip()
        if not code or not name:
            flash("Код статьи и Статья затрат — обязательны", "danger")
            return redirect(url_for("cost_items.edit", rid=rid))
        # проверка уникальности кода
        if (df.index != rid).any() and (df.loc[df.index != rid, "code"] == code).any():
            flash("Запись с таким кодом уже существует", "danger")
            return redirect(url_for("cost_items.edit", rid=rid))
        df.loc[rid, "code"] = code
        df.loc[rid, "name"] = name
        df.loc[rid, "cfo"] = cfo
        _write(df)
        flash("Сохранено", "success")
        return redirect(url_for("cost_items.index"))
    data = {c: df.loc[rid, c] for c in ["code","name","cfo"]}
    return render_template("cost_items/form.html", title="Редактировать статью", data=data, rid=rid)

@bp.route("/<int:rid>/archive")
def archive(rid: int):
    df = _read()
    if 0 <= rid < len(df):
        df.loc[rid, "archived"] = "1"
        _write(df)
        flash("Запись архивирована", "warning")
    return redirect(url_for("cost_items.index"))

@bp.route("/<int:rid>/restore")
def restore(rid: int):
    df = _read()
    if 0 <= rid < len(df):
        df.loc[rid, "archived"] = ""
        _write(df)
        flash("Запись восстановлена", "success")
    return redirect(url_for("cost_items.index"))

@bp.route("/export.csv")
def export_csv():
    df = _read()
    buf = io.StringIO()
    df_out = df[["code","name","cfo"]].rename(columns={"code":"Код статьи","name":"Статья затрат","cfo":"ЦФО"})
    df_out.to_csv(buf, index=False)
    mem = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name="cost_items.csv", mimetype="text/csv")

@bp.route("/export.xlsx")
def export_xlsx():
    df = _read()
    df_out = df[["code","name","cfo"]].rename(columns={"code":"Код статьи","name":"Статья затрат","cfo":"ЦФО"})
    mem = io.BytesIO()
    with pd.ExcelWriter(mem, engine="openpyxl") as w:
        df_out.to_excel(w, index=False, sheet_name="Статьи затрат")
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name="cost_items.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@bp.route("/import", methods=["POST"])
def import_post():
    file = request.files.get("file")
    if not file:
        flash("Файл не выбран", "danger")
        return redirect(url_for("cost_items.index"))
    try:
        df_in = pd.read_excel(file)
    except Exception as e:
        flash(f"Ошибка чтения файла: {e}", "danger")
        return redirect(url_for("cost_items.index"))
    # ожидаемые заголовки
    # допускаем русские/английские варианты
    cols = {c.lower().strip(): c for c in df_in.columns}
    need = ["код статьи","статья затрат","цфо"]
    for n in need:
        if n not in cols:
            flash(f"Нет колонки '{n}' в заголовке", "danger")
            return redirect(url_for("cost_items.index"))
    df_in = df_in.rename(columns={
        cols["код статьи"]: "code",
        cols["статья затрат"]: "name",
        cols["цфо"]: "cfo"
    })[["code","name","cfo"]]
    df_in = df_in.fillna("").astype(str)

    base = _read()
    # upsert по code
    up = 0
    ins = 0
    for _, r in df_in.iterrows():
        code = r["code"].strip()
        if not code:
            continue
        mask = (base["code"] == code)
        if mask.any():
            idx = base[mask].index[0]
            base.loc[idx, "name"] = r["name"]
            base.loc[idx, "cfo"]  = r["cfo"]
            up += 1
        else:
            base = pd.concat([base, pd.DataFrame([{"code":code,"name":r["name"],"cfo":r["cfo"],"archived":""}])], ignore_index=True)
            ins += 1
    _write(base)
    flash(f"Импорт завершён: обновлено {up}, добавлено {ins}", "success")
    return redirect(url_for("cost_items.index"))

@bp.route("/template.xlsx")
def template_xlsx():
    df = pd.DataFrame([{"Код статьи":"","Статья затрат":"","ЦФО":""}])
    mem = io.BytesIO()
    with pd.ExcelWriter(mem, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Статьи затрат")
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name="template_cost_items.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
