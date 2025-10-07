import csv, io, urllib.request

# Нормализация числа: "78", "78.0", "78,0", " 78 " → float
def _num(x):
    if x is None:
        return 0.0
    s = str(x).strip().replace(" ", "").replace(",", ".")
    if s == "":
        return 0.0
    try:
        return float(s)
    except Exception:
        try:
            return float(int(s))
        except Exception:
            return 0.0

def fetch_pending_from_mining(base_url: str):
    """
    Тянем CSV с /mining-report/export.csv и превращаем строки
    в «нераспределённую добычу» для нижней карточки в /moves.

    Ожидаемые поля CSV (без регистра):
      date,fraction,quality,plan_total,fact_s1,fact_s2,fact_s3,fact_s4,note,fact_total,unit
    Если fact_total пуст — считаем sum(fact_s1..fact_s4).
    Берём только записи, где итог > 0.
    """
    url = (base_url.rstrip("/") + "/mining-report/export.csv")
    dbg = {"url": url, "rows": 0, "used": 0, "sum": 0.0, "err": ""}

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        rdr = csv.DictReader(io.StringIO(data))
        out = []
        i = 0
        for r in rdr:
            i += 1
            # заголовки без регистра
            row = { (k or "").strip().lower(): (v or "").strip() for k, v in r.items() }

            s1 = _num(row.get("fact_s1"))
            s2 = _num(row.get("fact_s2"))
            s3 = _num(row.get("fact_s3"))
            s4 = _num(row.get("fact_s4"))
            total = _num(row.get("fact_total"))
            if total <= 0:
                total = s1 + s2 + s3 + s4

            if total > 0:
                item = {
                    "id": f"MR-{i}-{row.get('date','')}",
                    "date": row.get("date", ""),
                    "product_name": row.get("fraction", "") or "Добыча",
                    "qty": total,
                    "unit": row.get("unit", "т") or "т",
                    "source": "mining",
                    "doc": "",
                    "note": row.get("note", ""),
                }
                out.append(item)
                dbg["used"] += 1
                dbg["sum"] += total

        dbg["rows"] = i
        return out, dbg

    except Exception as e:
        dbg["err"] = str(e)
        return [], dbg
