from flask import Blueprint, render_template, request, redirect, url_for, flash
import io, csv, urllib.request

bp = Blueprint("moves", __name__, template_folder="templates")

def _inline_fetch_from_csv(base_url: str):
    """Fallback: тянем /mining-report/export.csv и строим MR-* строки."""
    rows, dbg = [], {"src": "inline_csv", "http_rows": 0}
    try:
        url = base_url.rstrip("/") + "/mining-report/export.csv"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        rdr = csv.DictReader(io.StringIO(data))
        i = 0
        for r in rdr:
            i += 1
            # qty = fact_total (если пусто — сумма fact_s1..s4)
            def _num(x):
                try:
                    return float(str(x).replace(",", ".").strip())
                except Exception:
                    return 0.0
            qty = _num(r.get("fact_total")) or (_num(r.get("fact_s1")) + _num(r.get("fact_s2")) + _num(r.get("fact_s3")) + _num(r.get("fact_s4")))
            if qty <= 0:
                continue
            rid = f"MR-{i}-{r.get('date','')}"
            rows.append({
                "id": rid,
                "date": (r.get("date") or "").strip(),
                "product_name": (r.get("fraction") or "").strip(),
                "fraction": (r.get("fraction") or "").strip(),
                "qty": qty,
                "unit": (r.get("unit") or "т").strip(),
                "note": (r.get("note") or "").strip(),
            })
        dbg["http_rows"] = len(rows)
    except Exception as e:
        dbg["err"] = str(e)
    return rows, dbg

def _load_pending(base_url: str):
    """Best-effort: сначала пробуем app.moves.pending_source, иначе inline CSV."""
    # Попытка использовать кастомный источник, если он есть
    try:
        from app.moves import pending_source as ps
        if hasattr(ps, "merge_refresh"):
            rows, dbg = ps.merge_refresh(base_url); dbg = dict(dbg or {}); dbg["src"] = "merge_refresh"
            return rows, dbg
        if hasattr(ps, "fetch_pending_from_mining"):
            rows, dbg = ps.fetch_pending_from_mining(base_url); dbg = dict(dbg or {}); dbg["src"] = "fetch_pending_from_mining"
            return rows, dbg
        if hasattr(ps, "refresh_pending"):
            rows, dbg = ps.refresh_pending(base_url); dbg = dict(dbg or {}); dbg["src"] = "refresh_pending"
            return rows, dbg
    except Exception as e:
        # Падает импорт? пойдём во встроенный CSV-парсер.
        pass
    # Fallback: тянем напрямую CSV отчёта
    return _inline_fetch_from_csv(base_url)

def _consume_pending(row_id: str, act: str):
    """Best-effort: зовём pending_source.consume, если есть; иначе тихо игнорируем."""
    try:
        from app.moves import pending_source as ps
        if hasattr(ps, "consume"):
            ps.consume(row_id, act)
    except Exception:
        pass

@bp.get("/")
def index():
    rows = []  # основной журнал пока не используем
    pending_rows, pending_dbg = _load_pending(request.url_root)
    try:
        pending_total = sum(float(x.get("qty") or 0) for x in pending_rows)
    except Exception:
        pending_total = 0.0
    return render_template(
        "moves/index.html",
        rows=rows,
        pending_rows=pending_rows,
        pending_total=pending_total,
        pending_dbg=pending_dbg,
    )

@bp.get("/receipt")
def receipt():
    return render_template("moves/receipt_form.html")

@bp.get("/process")
def process():
    return render_template("moves/process_form.html")

@bp.post("/pending_action")
def pending_action():
    row_id = (request.form.get("id") or "").strip()
    act = (request.form.get("act") or "").strip().lower()  # accept|discard
    _consume_pending(row_id, act)
    if act == "accept":
        flash("Принято на склад", "success")
    elif act == "discard":
        flash("Списано", "warning")
    else:
        flash("Нет действия", "secondary")
    return redirect(url_for("moves.index"))
