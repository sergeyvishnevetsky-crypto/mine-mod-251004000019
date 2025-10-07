import csv, io, time
from urllib.request import urlopen, Request
from urllib.error import URLError
from typing import List, Tuple, Dict, Any

def _to_float(x) -> float:
    s = str(x or "").strip().replace(" ", "").replace(",", ".")
    if not s:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def _rows_from_internal() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Читаем прямо из модуля отчёта о добыче, без сети."""
    dbg = {"src": "internal", "count": 0, "err": ""}
    rows = []
    try:
        from app.mining_report.routes import ROWS as MR_ROWS  # type: ignore
        # MR_ROWS = [{date,fraction,quality,plan_total,fact_s1..s4,fact_total,unit,note}, ...]
        i = 0
        for r in (MR_ROWS or []):
            i += 1
            s1=_to_float(r.get("fact_s1")); s2=_to_float(r.get("fact_s2"))
            s3=_to_float(r.get("fact_s3")); s4=_to_float(r.get("fact_s4"))
            total = _to_float(r.get("fact_total"))
            if total <= 0:
                total = s1 + s2 + s3 + s4
            if total <= 0:
                continue
            rows.append({
                "id": f"MR-{i}-{r.get('date','')}",
                "date": r.get("date",""),
                "product_name": r.get("fraction") or "Добыча",
                "qty": total,
                "unit": r.get("unit","т"),
                "source": "mining",
                "doc": "",
                "note": r.get("note",""),
            })
        dbg["count"] = len(rows)
    except Exception as e:
        dbg["err"] = str(e)
    return rows, dbg

def _rows_from_http(base_url: str, timeout_sec: float = 7.5, retries: int = 1) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Фолбэк: тянем CSV по HTTP, но с увеличенным таймаутом и 1 ретраем."""
    dbg = {"src": "http", "count": 0, "err": ""}
    url = base_url.rstrip("/") + "/mining-report/export.csv"
    last_err = ""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "moves-pending/1.0"})
            with urlopen(req, timeout=timeout_sec) as resp:
                data = resp.read().decode("utf-8", errors="ignore")
            rdr = csv.DictReader(io.StringIO(data))
            rows = []
            i = 0
            for r in rdr:
                i += 1
                s1=_to_float(r.get("fact_s1")); s2=_to_float(r.get("fact_s2"))
                s3=_to_float(r.get("fact_s3")); s4=_to_float(r.get("fact_s4"))
                total = _to_float(r.get("fact_total"))
                if total <= 0:
                    total = s1 + s2 + s3 + s4
                if total <= 0:
                    continue
                rows.append({
                    "id": f"MR-{i}-{r.get('date','')}",
                    "date": r.get("date",""),
                    "product_name": r.get("fraction") or "Добыча",
                    "qty": total,
                    "unit": r.get("unit","т"),
                    "source": "mining",
                    "doc": "",
                    "note": r.get("note",""),
                })
            dbg["count"] = len(rows)
            return rows, dbg
        except Exception as e:
            last_err = str(e)
            time.sleep(0.2)
            continue
    dbg["err"] = last_err or "unknown http error"
    return [], dbg

def fetch_pending(base_url: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Главная точка: сначала пробуем internal, если нет — http."""
    rows, dbg = _rows_from_internal()
    if dbg.get("count", 0) > 0 or not dbg.get("err"):  # даже при err, но с данными — считаем успехом
        return rows, dbg
    # фолбэк: http
    rows2, dbg2 = _rows_from_http(base_url)
    # слей дебаг
    return (rows2, dbg2 if rows2 else {"src":"http", "count":0, "err": dbg2.get("err","")})
