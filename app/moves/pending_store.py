import os, csv, datetime as _dt

DATA_PATH = os.environ.get("PENDING_CSV_PATH", "data/pending_mine_output.csv")
FIELDS = ["id","dt","shift","warehouse","product","qty","unit","source","doc","note","status"]

def _ensure_file():
    if not os.path.exists(DATA_PATH):
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            demo = [
                {"id":"P-1001","dt":"2025-10-06 08:10","shift":"A","warehouse":"Шахта","product":"Сырец ДГ","qty":"35.0","unit":"т","source":"shift","doc":"Наряд #A-061","note":"рампа 1","status":"pending"},
                {"id":"P-1002","dt":"2025-10-06 19:45","shift":"B","warehouse":"Шахта","product":"Сырец ДГ","qty":"28.5","unit":"т","source":"weigh","doc":"Талон 443","note":"весовая","status":"pending"},
                {"id":"P-1003","dt":"2025-10-07 04:20","shift":"C","warehouse":"Шахта","product":"Сырец ДГ","qty":"22.0","unit":"т","source":"shift","doc":"Наряд #C-012","note":"рампа 2","status":"pending"},
            ]
            for r in demo: w.writerow(r)

def list_rows(warehouse="Шахта", status="pending"):
    _ensure_file()
    out=[]
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (not warehouse or r.get("warehouse")==warehouse) and (not status or r.get("status")==status):
                out.append(r)
    return out

def total_qty(rows):
    try: 
        return sum(float(r.get("qty") or 0) for r in rows)
    except Exception:
        return 0.0

def bulk_update(ids, op):
    _ensure_file()
    changed=0
    rows=[]
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["id"]: r for r in rows}
    for i in ids:
        r = by_id.get(i)
        if not r: continue
        if op=="accept" and r["status"]=="pending":
            r["status"]="accepted"; changed+=1
        elif op=="cancel" and r["status"]=="pending":
            r["status"]="canceled"; changed+=1
    # перезапись
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in rows: w.writerow(r)
    return changed
