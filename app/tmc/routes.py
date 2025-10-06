from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv
try:
    import pandas as pd
except Exception:
    pd = None

tmc_bp = Blueprint("tmc", __name__, template_folder="templates")

ROWS = [
    {"id":1,"code":"MT-1001","name":"Болт М16х50 DIN933","unit":"шт","group":"Крепёж","stock":250,"price":12.5,"currency":"грн","supplier":"ТОВ «ПромСнаб»","status":"Активен"},
    {"id":2,"code":"MT-2001","name":"Масло индустриальное И-20А","unit":"л","group":"Смазки","stock":120,"price":56.0,"currency":"грн","supplier":"ТОВ «ОйлМаркет»","status":"Активен"},
]
def _next_id(): return (max(r["id"] for r in ROWS)+1) if ROWS else 1

COLUMNS = ["code","name","unit","group","stock","price","currency","supplier","status"]

def _filter(rows):
    q=(request.args.get("q","") or "").strip().lower()
    group=(request.args.get("group","") or "").strip()
    supplier=(request.args.get("supplier","") or "").strip()
    status=(request.args.get("status","") or "").strip()
    res=rows
    if q:
        def hay(r): return " ".join([str(r.get(k,"")) for k in ["code","name","unit","group","supplier"]]).lower()
        res=[r for r in res if q in hay(r)]
    if group: res=[r for r in res if r.get("group","")==group]
    if supplier: res=[r for r in res if r.get("supplier","")==supplier]
    if status: res=[r for r in res if r.get("status","")==status]
    return res

@tmc_bp.get("/")
def index():
    rows=_filter(ROWS)
    return render_template("tmc_index.html", title="Перечень ТМЦ", rows=rows, total=len(rows), page=1, pages=1)

@tmc_bp.get("/add")
def add(): return render_template("tmc_form.html", title="Добавить ТМЦ", r=None)

@tmc_bp.post("/add")
def add_post():
    f=request.form
    ROWS.append({
        "id":_next_id(),
        "code":f.get("code","").strip(),
        "name":f.get("name","").strip(),
        "unit":f.get("unit","").strip(),
        "group":f.get("group","").strip(),
        "stock":float(f.get("stock","0") or 0),
        "price":float(f.get("price","0") or 0),
        "currency":f.get("currency","грн").strip() or "грн",
        "supplier":f.get("supplier","").strip(),
        "status":f.get("status","Активен").strip() or "Активен",
    })
    flash("ТМЦ добавлен","ok"); return redirect(url_for("tmc.index"))

@tmc_bp.get("/<int:rid>/edit")
def edit(rid:int):
    r=next((x for x in ROWS if x["id"]==rid), None)
    if not r: flash("Запись не найдена","err"); return redirect(url_for("tmc.index"))
    return render_template("tmc_form.html", title=f"Редактирование: {r['code']}", r=r)

@tmc_bp.post("/<int:rid>/edit")
def edit_post(rid:int):
    r=next((x for x in ROWS if x["id"]==rid), None)
    if not r: flash("Запись не найдена","err"); return redirect(url_for("tmc.index"))
    f=request.form
    r.update({
        "code":f.get("code",r["code"]).strip(),
        "name":f.get("name",r["name"]).strip(),
        "unit":f.get("unit",r["unit"]).strip(),
        "group":f.get("group",r["group"]).strip(),
        "stock":float(f.get("stock",r["stock"]) or 0),
        "price":float(f.get("price",r["price"]) or 0),
        "currency":f.get("currency",r["currency"]).strip(),
        "supplier":f.get("supplier",r["supplier"]).strip(),
        "status":f.get("status",r["status"]).strip(),
    })
    flash("Изменения сохранены","ok"); return redirect(url_for("tmc.index"))

@tmc_bp.get("/<int:rid>/archive")
def archive(rid:int):
    r=next((x for x in ROWS if x["id"]==rid), None)
    if not r: flash("Запись не найдена","err")
    else: r["status"]="Архив"; flash("Перенесено в архив","ok")
    return redirect(url_for("tmc.index"))

@tmc_bp.get("/<int:rid>/delete")
def delete(rid:int):
    idx=next((i for i,x in enumerate(ROWS) if x["id"]==rid), None)
    if idx is None: flash("Запись не найдена","err")
    else: del ROWS[idx]; flash("Удалено","ok")
    return redirect(url_for("tmc.index"))

# ---- Import/Export ----
@tmc_bp.get("/template.xlsx")
def template_xlsx():
    if pd is None:
        buf=io.StringIO(); csv.writer(buf).writerow(COLUMNS)
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition":"attachment; filename=tmc_template.csv"})
    import pandas as pd
    df=pd.DataFrame(columns=COLUMNS); buf=io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="tmc")
    return Response(buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=tmc_template.xlsx"})

@tmc_bp.post("/import")
def import_post():
    f=request.files.get("file")
    if not f: flash("Файл не выбран","err"); return redirect(url_for("tmc.index"))
    name=(f.filename or "").lower(); count=0
    try:
        if name.endswith(".csv"):
            reader=csv.DictReader(io.StringIO(f.read().decode("utf-8",errors="ignore")))
            for row in reader:
                ROWS.append({
                    "id":_next_id(),
                    "code":(row.get("code","") or "").strip(),
                    "name":(row.get("name","") or "").strip(),
                    "unit":(row.get("unit","") or "").strip(),
                    "group":(row.get("group","") or "").strip(),
                    "stock":float(row.get("stock","0") or 0),
                    "price":float(row.get("price","0") or 0),
                    "currency":(row.get("currency","грн") or "грн").strip(),
                    "supplier":(row.get("supplier","") or "").strip(),
                    "status":(row.get("status","Активен") or "Активен").strip(),
                }); count+=1
        else:
            if pd is None: flash("Для XLSX нужен pandas/openpyxl","err"); return redirect(url_for("tmc.index"))
            df=pd.read_excel(f, dtype=str).fillna("")
            for _,row in df.iterrows():
                ROWS.append({
                    "id":_next_id(),
                    "code":row.get("code","").strip(),
                    "name":row.get("name","").strip(),
                    "unit":row.get("unit","").strip(),
                    "group":row.get("group","").strip(),
                    "stock":float(row.get("stock","0") or 0),
                    "price":float(row.get("price","0") or 0),
                    "currency":row.get("currency","грн").strip() or "грн",
                    "supplier":row.get("supplier","").strip(),
                    "status":(row.get("status","Активен") or "Активен").strip(),
                }); count+=1
        flash(f"Импортировано: {count}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("tmc.index"))

@tmc_bp.get("/export.csv")
def export_csv():
    rows=_filter(ROWS); buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(["id"]+COLUMNS)
    for r in rows: w.writerow([r.get("id")]+[r.get(k,"") for k in COLUMNS])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=tmc_export.csv"})

@tmc_bp.get("/export.xlsx")
def export_xlsx():
    rows=_filter(ROWS)
    if pd is None: return export_csv()
    import pandas as pd
    df=pd.DataFrame([{k:r.get(k,"") for k in ["id"]+COLUMNS} for r in rows])
    buf=io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="tmc")
    return Response(buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=tmc_export.xlsx"})
