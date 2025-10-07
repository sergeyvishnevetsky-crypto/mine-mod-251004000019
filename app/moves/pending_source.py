import csv, io, urllib.request, hashlib

# Множества ID, «съеденных» из карточки (живут в памяти dyno)
CONSUMED_IDS: set[str] = set()
DISCARDED_IDS: set[str] = set()

def _to_float(v, default=0.0):
    if v is None: return default
    s = str(v).strip().replace(" ", "").replace(",", ".")
    if s == "": return default
    try:
        return float(s)
    except Exception:
        return default

def _make_row_id(date_s: str, product: str, qty: float, i: int) -> str:
    sig = f"{date_s}|{product}|{qty}|{i}"
    return "MR-" + hashlib.sha1(sig.encode("utf-8")).hexdigest()[:10]

def fetch_pending_from_mining(base_url: str):
    """
    Тянем CSV /mining-report/export.csv, строим список pending-строк и
    отфильтровываем уже принятые/списанные по стабильному id.
    """
    rows, dbg = [], {"mining_http": 0, "filtered": 0}
    try:
        url = base_url.rstrip("/") + "/mining-report/export.csv"
        data = urllib.request.urlopen(url, timeout=4).read().decode("utf-8", errors="ignore")
        rdr = csv.DictReader(io.StringIO(data))
        i = 0
        for r in rdr:
            i += 1
            # поля CSV допускаем как EN, так и RU заголовки
            date_s = (r.get("date") or r.get("дата") or "").strip()
            product = (r.get("fraction") or r.get("фракция") or "Добыча").strip() or "Добыча"
            qty = _to_float(r.get("fact_total") or r.get("Факт/сутки") or r.get("qty") or r.get("факт"))
            if qty <= 0:
                continue
            rid = _make_row_id(date_s, product, qty, i)
            if rid in CONSUMED_IDS or rid in DISCARDED_IDS:
                dbg["filtered"] += 1
                continue
            rows.append({
                "id": rid,
                "date": date_s,
                "product_name": product,
                "qty": qty,
                "unit": (r.get("unit") or r.get("ед.") or "т"),
                "note": (r.get("note") or r.get("примечание") or ""),
            })
        dbg["mining_http"] = len(rows)
    except Exception as e:
        dbg["err"] = str(e)
    return rows, dbg

def consume(ids: list[str], action: str = "accept"):
    """
    Пометить строки как обработанные:
      action="accept"  -> скрыть как принятые
      action="discard" -> скрыть как списанные
    """
    bucket = CONSUMED_IDS if action == "accept" else DISCARDED_IDS
    for x in ids:
        bucket.add(str(x))
