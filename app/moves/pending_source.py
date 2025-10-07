from __future__ import annotations
import csv, io, hashlib, json, urllib.request, time
from pathlib import Path
from typing import List, Tuple, Dict, Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PENDING_JSON = DATA_DIR / "pending.json"

def _num(x) -> float:
    if x is None: return 0.0
    s = str(x).strip().replace(" ", "").replace(",", ".")
    if not s: return 0.0
    try:
        return float(s)
    except Exception:
        try: return float(int(s))
        except Exception: return 0.0

def _row_id(d: Dict[str, Any]) -> str:
    basis = "|".join([
        str(d.get("date","")).strip(),
        str(d.get("fraction","")).strip(),
        str(d.get("note","")).strip(),
        str(d.get("unit","")).strip(),
        str(d.get("fact_s1","")).strip(),
        str(d.get("fact_s2","")).strip(),
        str(d.get("fact_s3","")).strip(),
        str(d.get("fact_s4","")).strip(),
        str(d.get("fact_total","")).strip(),
    ])
    h = hashlib.md5(basis.encode("utf-8")).hexdigest()[:10]
    return f"MR-{h}"

def pull_from_csv(base_url: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Тянем /mining-report/export.csv и нормализуем строки
    -> rows: [{id,date,product_name,unit,qty,note,src:csv, _raw:...}]
    -> dbg: {'http_ok':bool, 'count':int, 'err':str}
    """
    dbg = {"http_ok": False, "count": 0, "err": ""}
    rows: List[Dict[str, Any]] = []
    try:
        url = base_url.rstrip("/") + "/mining-report/export.csv"
        with urllib.request.urlopen(url, timeout=6) as r:
            data = r.read().decode("utf-8", errors="ignore")
        rdr = csv.DictReader(io.StringIO(data))
        for r in rdr:
            # qty = fact_total (если есть), иначе сумма fact_s1..fact_s4
            ft = _num(r.get("fact_total"))
            if ft <= 0:
                ft = (_num(r.get("fact_s1")) + _num(r.get("fact_s2"))
                      + _num(r.get("fact_s3")) + _num(r.get("fact_s4")))
            d = {
                "date": (r.get("date") or "").strip(),
                "fraction": (r.get("fraction") or "").strip(),
                "product_name": (r.get("fraction") or "").strip(),
                "unit": (r.get("unit") or "т").strip() or "т",
                "note": (r.get("note") or "").strip(),
                "fact_s1": r.get("fact_s1",""),
                "fact_s2": r.get("fact_s2",""),
                "fact_s3": r.get("fact_s3",""),
                "fact_s4": r.get("fact_s4",""),
                "fact_total": r.get("fact_total",""),
            }
            qty = max(0.0, ft)
            if qty <= 0:
                continue
            d_norm = {
                "id": _row_id(d),
                "date": d["date"],
                "product_name": d["product_name"] or "Продукт",
                "unit": d["unit"],
                "qty": round(qty, 3),
                "note": d["note"],
                "src": "csv",
            }
            rows.append(d_norm)
        dbg["http_ok"] = True
        dbg["count"] = len(rows)
    except Exception as e:
        dbg["err"] = str(e)
    return rows, dbg

def _load_local() -> Dict[str, Any]:
    if not PENDING_JSON.exists(): return {"rows": [], "ts": 0}
    try:
        return json.loads(PENDING_JSON.read_text("utf-8"))
    except Exception:
        return {"rows": [], "ts": 0}

def _save_local(payload: Dict[str, Any]) -> None:
    PENDING_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def merge_refresh(base_url: str) -> Tuple[List[Dict[str,Any]], Dict[str,Any]]:
    """
    Локальное состояние 'нераспределённой'. Если пусто — подтянем CSV и сохраним.
    Если не пусто — вернём как есть (без дерганья сети).
    """
    st = _load_local()
    dbg = {"src":"internal", "local_count": len(st.get("rows",[])), "refreshed": False}
    if st.get("rows"):
        return st["rows"], dbg
    csv_rows, http_dbg = pull_from_csv(base_url)
    dbg.update({"refreshed": True, "csv": http_dbg})
    st = {"rows": csv_rows, "ts": int(time.time())}
    _save_local(st)
    return st["rows"], dbg

def consume(row_id: str, action: str) -> Dict[str, Any]:
    """
    action ∈ {'accept','discard'} — удаляем из pending.
    Возвращаем удалённый элемент (если был).
    """
    st = _load_local()
    rows = st.get("rows", [])
    keep, removed = [], None
    for r in rows:
        if r.get("id") == row_id and removed is None:
            removed = r
            continue
        keep.append(r)
    st["rows"] = keep
    _save_local(st)
    return {"removed": removed, "left": len(keep), "action": action}

def debug_snapshot() -> Dict[str, Any]:
    st = _load_local()
    return {"src":"internal", "count": len(st.get("rows",[])), "file": str(PENDING_JSON)}
