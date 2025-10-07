import csv, io, urllib.request

def _f(x):
    try:
        return float(str(x).replace(" ", "").replace(",", "."))
    except Exception:
        return 0.0

def _parse_rows(text: str):
    rdr = csv.DictReader(io.StringIO(text))
    rows = []
    for i, r in enumerate(rdr, 1):
        qty = _f(r.get("fact_total", "0"))
        if qty <= 0:
            continue
        rows.append({
            "id": f"MR-{i}-{r.get('date','')}",
            "date": r.get("date", ""),
            "product_name": (r.get("fraction") or "Добыча"),
            "qty": qty,
            "unit": r.get("unit", "т"),
            "source": "mining",
            "doc": "",
            "note": r.get("note",""),
        })
    return rows

def fetch_pending_from_mining(base_url: str, timeout: int = 4):
    """
    Возвращает (rows, dbg), где rows — список MR-* записей,
    dbg — отладочная инфа: {'url':..., 'rows': N} или {'url':..., 'err': ...}
    """
    url = (base_url.rstrip("/") + "/mining-report/export.csv")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
        rows = _parse_rows(text)
        return rows, {"url": url, "rows": len(rows)}
    except Exception as e:
        return [], {"url": url, "err": str(e)}
