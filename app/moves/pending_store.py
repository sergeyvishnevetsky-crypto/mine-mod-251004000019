import os, csv, datetime as _dt

DATA_PATH = os.environ.get("PENDING_CSV_PATH", "data/pending_mine_output.csv")
FIELDS = ["id","dt","shift","warehouse","product","qty","unit","source","doc","note","status"]

MINING_PATH = "data/mining_report.csv"
def _read_csv_rows(path, fields_expected=None):
    import csv, os
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        rows = [ {k.strip(): (v.strip() if isinstance(v,str) else v) for k,v in r.items()} for r in rdr ]
    return rows

def _try_float(x):
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        return 0.0

def _mining_qty(row):
    # 1) Явное поле итога
    for key in ("Факт/сутки","Факт сут","Факт за сутки","fact_day","fact_per_day","fact_total"):
        v = row.get(key)
        if v is not None and str(v).strip() != "":
            try:
                return float(str(v).replace(",", "."))
            except Exception:
                pass
    # 2) Сумма смен: Факт I..IV или fact_s1..fact_s4
    total = 0.0
    for k, v in row.items():
        ks = str(k).strip().lower()
        if ks.startswith("факт "):
            try: total += float(str(v).replace(",", ".")); 
            except: pass
        if ks in ("fact_s1","fact_s2","fact_s3","fact_s4"):
            try: total += float(str(v).replace(",", ".")); 
            except: pass
    return total

def _mining_product(row):
    for key in ("Фракция","Фракция/марка","fraction","grade"):
        if key in row and str(row[key]).strip():
            return str(row[key]).strip()
    return "Сырец ДГ"

def _load_mining_csv():
    rows = _read_csv_rows(MINING_PATH)
    out = []
    for i, r in enumerate(rows, start=1):
        dt = r.get("Дата") or r.get("date") or r.get("DT") or ""
        qty = _mining_qty(r)
        if qty <= 0:
            continue
        out.append({
            "id": f"MR-{dt}-{i}",
            "dt": f"{(r.get("date") or r.get("Дата") or dt)} 00:00",
            "shift": r.get("Смена") or r.get("shift") or "",
            "warehouse": "Шахта",
            "product": _mining_product(r),
            "qty": f"{qty}",
            "unit": (r.get("unit") or "т"),
            "source": "mining",
            "doc": "Отчёт о добыче",
            "note": r.get("Качество") or r.get("quality") or "",
            "status": "pending",
        })
    return out


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

def list_rows(warehouse="Шахта", status="pending", mining_url: str | None = None):
    _ensure_file()
    import csv
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        manual = list(csv.DictReader(f))
    man_filtered = [r for r in manual if (not warehouse or r.get("warehouse")==warehouse) and (not status or r.get("status")==status)]
    mining = []
    try:
        mining = _load_mining_csv()
    except Exception:
        mining = []
    if mining_url:
        try:
            mining.extend(load_mining_from_url(mining_url))
        except Exception:
            pass
    man_ids = {r.get("id") for r in manual}
    mining = [r for r in mining if r.get("id") not in man_ids]
    out=[]
    if status == "pending":
        out.extend([r for r in mining if (not warehouse or r.get("warehouse")==warehouse)])
    out.extend(man_filtered)
    return out

def total_qty(rows):
    try: 
        return sum(float(r.get("qty") or 0) for r in rows)
    except Exception:
        return 0.0

def bulk_update(ids, op):
    try:
        from csv import DictWriter
        virt_to_add=[]
        try:
            base = _load_mining_csv()
        except Exception:
            base = []
        by_id = {r.get("id"): r for r in base}
        for vid in list(ids):
            vid=str(vid)
            if vid.startswith("MR-"):
                r = by_id.get(vid)
                if r:
                    rc=dict(r); rc["status"] = "accepted" if op=="accept" else "canceled"
                    virt_to_add.append(rc)
        if virt_to_add:
            _ensure_file()
            import csv
            with open(DATA_PATH, newline="", encoding="utf-8") as f:
                curr = list(csv.DictReader(f))
            curr.extend(virt_to_add)
            with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
                w = DictWriter(f, fieldnames=FIELDS); w.writeheader()
                for r in curr: w.writerow(r)
        # смена статусов для обычных строк
        _ensure_file()
        import csv
        with open(DATA_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ids_set=set(map(str,ids))
        for r in rows:
            if r.get("id") in ids_set and not str(r.get("id","")).startswith("MR-"):
                r["status"] = "accepted" if op=="accept" else "canceled"
        with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
            w = DictWriter(f, fieldnames=FIELDS); w.writeheader()
            for r in rows: w.writerow(r)
    except Exception:
        pass
