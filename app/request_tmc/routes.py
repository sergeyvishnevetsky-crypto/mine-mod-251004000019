from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
import io, csv, datetime as dt

try:
    import pandas as pd
except Exception:
    pd = None

request_tmc_bp = Blueprint("request_tmc", __name__, template_folder="templates")

STATUSES = ["draft", "submitted", "approved", "fulfilled", "closed"]

# временные справочники/данные (подключим к реальным позже)
EMPLOYEES = [
    {"id":1,"tab_no":"0001","name":"Иванов И.И."},
    {"id":2,"tab_no":"0002","name":"Петров П.П."},
]
# Хранилище заявок в памяти
REQS = []   # [{id, date, requester_id, department, priority, need_by, status, comment, items:[{code,name,unit,qty}] }]

def _next_id(): return (max((r["id"] for r in REQS), default=0) + 1)
def _today(): return dt.date.today().isoformat()
def _find_emp(eid): return next((e for e in EMPLOYEES if str(e["id"])==str(eid)), None)

@request_tmc_bp.get("/")
def index():
    q=(request.args.get("q","") or "").lower().strip()
    status=request.args.get("status","")
    rows=REQS
    if q:
        def hay(r):
            parts=[r.get("department",""), r.get("comment","")]
            for it in r.get("items",[]):
                parts += [it.get("code",""), it.get("name","")]
            return " ".join(parts).lower()
        rows=[r for r in rows if q in hay(r)]
    if status: rows=[r for r in rows if r.get("status")==status]
    return render_template("tmc_req_index.html", title="Заявки на ТМЦ", rows=rows, STATUSES=STATUSES)

@request_tmc_bp.get("/new")
def new():
    r={"date":_today(),"priority":"Обычная","need_by":_today(),"status":"draft","items":[]}
    return render_template("tmc_req_form.html", title="Новая заявка на ТМЦ", r=r, employees=EMPLOYEES, mode="create")

@request_tmc_bp.post("/new")
def create():
    f=request.form
    items=[]
    # строки из формы (повторяющиеся поля)
    codes=request.form.getlist("code[]")
    names=request.form.getlist("name[]")
    units=request.form.getlist("unit[]")
    qtys =request.form.getlist("qty[]")
    for i in range(len(codes)):
        if codes[i] or names[i]:
            items.append({"code":codes[i].strip(), "name":names[i].strip(), "unit":units[i].strip(), "qty":float(qtys[i] or 0)})
    REQS.append({
        "id":_next_id(),
        "date":f.get("date") or _today(),
        "requester_id":int(f.get("requester_id")),
        "department":f.get("department","").strip(),
        "priority":f.get("priority","Обычная"),
        "need_by":f.get("need_by") or _today(),
        "status":"draft",
        "comment":f.get("comment","").strip(),
        "items":items
    })
    flash("Заявка создана (черновик)","ok")
    return redirect(url_for("request_tmc.index"))

@request_tmc_bp.get("/<int:rid>")
def view(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Заявка не найдена","err"); return redirect(url_for("request_tmc.index"))
    emp=_find_emp(r["requester_id"])
    return render_template("tmc_req_view.html", title=f"Заявка ТМЦ №{rid}", r=r, emp=emp, STATUSES=STATUSES)

@request_tmc_bp.get("/<int:rid>/edit")
def edit(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Заявка не найдена","err"); return redirect(url_for("request_tmc.index"))
    if r["status"]!="draft": flash("Редактирование возможно только в черновике","err"); return redirect(url_for("request_tmc.view", rid=rid))
    return render_template("tmc_req_form.html", title=f"Редактирование заявки №{rid}", r=r, employees=EMPLOYEES, mode="edit")

@request_tmc_bp.post("/<int:rid>/edit")
def edit_post(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Заявка не найдена","err"); return redirect(url_for("request_tmc.index"))
    if r["status"]!="draft": flash("Редактировать можно только черновик","err"); return redirect(url_for("request_tmc.view", rid=rid))
    f=request.form
    r.update({
        "date":f.get("date") or r["date"],
        "requester_id":int(f.get("requester_id")),
        "department":f.get("department","").strip(),
        "priority":f.get("priority","Обычная"),
        "need_by":f.get("need_by") or r["need_by"],
        "comment":f.get("comment","").strip(),
    })
    items=[]
    codes=request.form.getlist("code[]"); names=request.form.getlist("name[]"); units=request.form.getlist("unit[]"); qtys=request.form.getlist("qty[]")
    for i in range(len(codes)):
        if codes[i] or names[i]:
            items.append({"code":codes[i].strip(),"name":names[i].strip(),"unit":units[i].strip(),"qty":float(qtys[i] or 0)})
    r["items"]=items
    flash("Сохранено","ok")
    return redirect(url_for("request_tmc.view", rid=rid))

@request_tmc_bp.post("/<int:rid>/submit")
def submit(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Не найдено","err")
    elif r["status"]!="draft": flash("Уже подана/обработана","err")
    else: r["status"]="submitted"; flash("Заявка подана","ok")
    return redirect(url_for("request_tmc.view", rid=rid))

@request_tmc_bp.post("/<int:rid>/approve")
def approve(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Не найдено","err")
    elif r["status"]!="submitted": flash("Неверная стадия","err")
    else: r["status"]="approved"; flash("Заявка утверждена","ok")
    return redirect(url_for("request_tmc.view", rid=rid))

@request_tmc_bp.post("/<int:rid>/fulfill")
def fulfill(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Не найдено","err")
    elif r["status"]!="approved": flash("Неверная стадия","err")
    else: r["status"]="fulfilled"; flash("Заявка исполнена (ТМЦ выданы/заказаны)","ok")
    return redirect(url_for("request_tmc.view", rid=rid))

@request_tmc_bp.post("/<int:rid>/close")
def close(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Не найдено","err")
    else: r["status"]="closed"; flash("Заявка закрыта","ok")
    return redirect(url_for("request_tmc.view", rid=rid))

# ---- Импорт/Экспорт ----
COLUMNS = ["code","name","unit","qty"]
@request_tmc_bp.get("/template.xlsx")
def template_xlsx():
    if pd is None:
        buf=io.StringIO(); csv.writer(buf).writerow(COLUMNS)
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition":"attachment; filename=tmc_request_template.csv"})
    import pandas as pd
    df=pd.DataFrame(columns=COLUMNS); buf=io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="items")
    return Response(buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=tmc_request_template.xlsx"})

@request_tmc_bp.post("/import_items/<int:rid>")
def import_items(rid:int):
    r=next((x for x in REQS if x["id"]==rid), None)
    if not r: flash("Заявка не найдена","err"); return redirect(url_for("request_tmc.index"))
    if r["status"]!="draft": flash("Импорт возможен только в черновике","err"); return redirect(url_for("request_tmc.view", rid=rid))
    f=request.files.get("file")
    if not f: flash("Файл не выбран","err"); return redirect(url_for("request_tmc.view", rid=rid))
    name=(f.filename or "").lower()
    try:
        items=[]
        if name.endswith(".csv"):
            reader=csv.DictReader(io.StringIO(f.read().decode("utf-8",errors="ignore")))
            for row in reader:
                if row.get("code") or row.get("name"):
                    items.append({"code":row.get("code","").strip(),"name":row.get("name","").strip(),
                                  "unit":row.get("unit","").strip(),"qty":float(row.get("qty","0") or 0)})
        else:
            if pd is None: flash("Для XLSX нужен pandas/openpyxl","err"); return redirect(url_for("request_tmc.view", rid=rid))
            df=pd.read_excel(f, dtype=str).fillna("")
            for _,row in df.iterrows():
                if row.get("code") or row.get("name"):
                    items.append({"code":row.get("code","").strip(),"name":row.get("name","").strip(),
                                  "unit":row.get("unit","").strip(),"qty":float(row.get("qty","0") or 0)})
        r["items"].extend(items)
        flash(f"Импортировано позиций: {len(items)}","ok")
    except Exception as e:
        flash(f"Ошибка импорта: {e}","err")
    return redirect(url_for("request_tmc.view", rid=rid))

@request_tmc_bp.get("/export.csv")
def export_csv():
    # экспорт списка заявок (шапки)
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(["id","date","status","requester","department","priority","need_by","items_count"])
    for r in REQS:
        emp=_find_emp(r["requester_id"])
        w.writerow([r["id"],r["date"],r["status"], emp["name"] if emp else "", r["department"], r["priority"], r["need_by"], len(r["items"])])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=tmc_requests.csv"})
