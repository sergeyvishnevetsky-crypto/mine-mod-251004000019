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
    # 1) Явный total
    for key in ("Факт/сутки","Факт сут","Факт за сутки","fact_day","fact_per_day","fact_total"):
        if key in row and str(row[key]).strip():
            try:
                return float(str(row[key]).replace(",", "."))
            except Exception:
                pass
    # 2) Сумма смен: Факт I..IV или fact_s1..fact_s4
    total = 0.0
    for k in row.keys():
        ks = k.strip().lower()
        if ks.startswith("факт "):
            try: total += float(str(row[k]).replace(",", "."))
            except Exception: pass
        if ks in ("fact_s1","fact_s2","fact_s3","fact_s4"):
            try: total += float(str(row[k]).replace(",", "."))
            except Exception: pass
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
    # base manual rows
    _ensure_file()
    manual = []
    import csv
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        manual = list(csv.DictReader(f))
    # filter manual
    man_filtered = [r for r in manual if (not warehouse or r.get("warehouse")==warehouse) and (not status or r.get("status")==status)]
    # mining virtual rows
    mining = _load_mining_csv()
    # выкидываем те mining-id, которые уже материализованы в manual (любой статус, чтобы не задваивать)
    man_ids = {r.get("id") for r in manual}
    mining = [r for r in mining if r["id"] not in man_ids]
    # итоговый список: сначала mining, затем manual (pending)
    out = []
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
    # материализация MR-* (если есть) и безопасная смена статусов
    try:
        from csv import DictWriter
        virt_to_add = []
        # материализация MR-* из файл/URL
        try:
            mining_all = _load_mining_csv()
        except Exception:
            mining_all = []
        def find_mr(vid):
            for r in mining_all:
                if r.get("id")==vid:
                    return r
            return None
        for vid in list(ids):
            if str(vid).startswith("MR-"):
                virt = find_mr(vid)
                if virt:
                    vc = dict(virt)
                    vc["status"] = "accepted" if op=="accept" else "canceled"
                    virt_to_add.append(vc)
        if virt_to_add:
            _ensure_file()
            import csv
            with open(DATA_PATH, newline="", encoding="utf-8") as f:
                curr = list(csv.DictReader(f))
            curr.extend(virt_to_add)
            with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
                w = DictWriter(f, fieldnames=FIELDS); w.writeheader()
                for r in curr: w.writerow(r)
        # обычная смена статусов для manual-строк ниже
    except Exception:
        pass

    except Exception:
        pass

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


def load_mining_from_url(url: str):
    """Скачать /mining-report/export.csv и вернуть список виртуальных pending-строк."""
    import csv, io, urllib.request
    if not url:
        return []
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read()
        text = data.decode("utf-8", errors="replace")
        rdr = csv.DictReader(io.StringIO(text))
        rows = []
        for i, r in enumerate(rdr, start=1):
            qty = _mining_qty(r)
            if qty <= 0:
                continue
            dt = r.get("Дата") or r.get("date") or r.get("DT") or ""
            rows.append({
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
        return rows
    except Exception:
        return []


def debug_counts(mining_url=None):
    man, mfile, mhttp = 0, 0, 0
    try:
        _ensure_file()
        import csv
        with open(DATA_PATH, newline="", encoding="utf-8") as f:
            man = sum(1 for _ in csv.DictReader(f))
    except Exception:
        man = -1
    try:
        mfile = len(_load_mining_csv())
    except Exception:
        mfile = -1
    if mining_url:
        try:
            mhttp = len(load_mining_from_url(mining_url))
        except Exception:
            mhttp = -1
    return {"manual": man, "mining_file": mfile, "mining_http": mhttp}
