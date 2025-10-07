import csv, io, urllib.request
from typing import List, Dict

# Файл для «материализации» (чтобы скрыть обработанные MR-строки)
PENDING_FILE = "data/pending_mine_output.csv"
FIELDS = ["id","dt","shift","warehouse","product","qty","unit","source","doc","note","status"]

def _try_float(x)->float:
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return 0.0

def _mining_qty(row: Dict)->float:
    # сначала факт-итого, иначе сумма по сменам
    for k in ("fact_total","Факт/сутки","fact_day","fact_per_day"):
        if k in row and str(row[k]).strip():
            v=_try_float(row[k])
            if v>0: return v
    total=0.0
    for k in ("fact_s1","fact_s2","fact_s3","fact_s4"):
        total+=_try_float(row.get(k))
    return total

def _product(row: Dict)->str:
    for k in ("fraction","Фракция","Фракция/марка","grade"):
        v=row.get(k,"")
        if str(v).strip(): return str(v).strip()
    return "Сырец ДГ"

def _read_materialized_ids()->set:
    try:
        with open(PENDING_FILE, newline="", encoding="utf-8") as f:
            rdr=csv.DictReader(f)
            return { r.get("id") for r in rdr }
    except FileNotFoundError:
        return set()
    except Exception:
        return set()

def _append_materialized(rows: List[Dict]):
    # rows уже содержат поля FIELDS
    try:
        existed = []
        try:
            with open(PENDING_FILE, newline="", encoding="utf-8") as f:
                existed = list(csv.DictReader(f))
        except FileNotFoundError:
            pass
        with open(PENDING_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
            for r in existed: w.writerow(r)
            for r in rows:   w.writerow(r)
    except Exception:
        # не валим журнал при ошибках файла
        pass

def fetch_from_export(base_url: str)->List[Dict]:
    """Читает /mining-report/export.csv и возвращает pending-строки MR-* (которые ещё не материализованы)."""
    url = base_url.rstrip("/") + "/mining-report/export.csv"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    rdr = csv.DictReader(io.StringIO(text))
    out=[]
    for i, r in enumerate(rdr, start=1):
        qty=_mining_qty(r)
        if qty<=0: 
            continue
        date = (r.get("date") or r.get("Дата") or "").strip()
        pid  = f"MR-{date}-{i}"
        out.append({
            "id": pid,
            "dt": f"{date} 00:00",
            "shift": r.get("shift") or r.get("Смена") or "",
            "warehouse": "Шахта",
            "product": _product(r),
            "qty": f"{qty}",
            "unit": r.get("unit") or "т",
            "source": "mining",
            "doc": "Отчёт о добыче",
            "note": r.get("quality") or r.get("Качество") or r.get("note") or "",
            "status": "pending",
        })
    # отфильтруем уже материализованные
    mat = _read_materialized_ids()
    return [r for r in out if r["id"] not in mat]

def mark_processed(ids: List[str], op: str):
    """Материализует MR-* как accepted/canceled, чтобы они больше не появлялись из отчёта."""
    rows=[]
    for pid in ids:
        if not str(pid).startswith("MR-"): 
            continue
        rows.append({
            "id": pid, "dt":"", "shift":"", "warehouse":"Шахта", "product":"", "qty":"0",
            "unit":"т","source":"mining","doc":"Отчёт о добыче","note":"",
            "status": "accepted" if op=="accept" else "canceled"
        })
    if rows:
        _append_materialized(rows)
