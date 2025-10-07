from flask import Blueprint, render_template, request, redirect, url_for, flash
import csv, io, urllib.request

bp = Blueprint("moves", __name__, template_folder="templates")

def _fetch_pending_from_mining(base_url: str):
    """Тянем строки из /mining-report/export.csv, формируем MR-* элементы."""
    rows, dbg = [], {"mining_http": 0, "err": ""}
    try:
        url = (base_url.rstrip("/") + "/mining-report/export.csv")
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        rdr = csv.DictReader(io.StringIO(data))
        i = 0
        for r in rdr:
            i += 1
            qty = 0.0
            try:
                qty = float(str(r.get("fact_total","0")).replace(",", "."))
            except Exception:
                qty = 0.0
            rows.append({
                "id": f"MR-{i}-{r.get('date','')}",
                "date": r.get("date",""),
                "fraction": r.get("fraction",""),
                "product_name": r.get("fraction",""),
                "qty": qty,
                "unit": r.get("unit","т"),
                "note": r.get("note",""),
            })
        dbg["mining_http"] = len(rows)
    except Exception as e:
        dbg["err"] = str(e)
    return rows, dbg

@bp.get("/")
def index():
    # Основной журнал (если нужен) — пока пустой список, чтобы шаблон не падал
    rows = []

    # Безопасные дефолты для «нераспределённой добычи»
    _pending_rows = []
    _pending_total = 0.0
    _pending_dbg = {"mining_http": 0}

    try:
        base = request.url_root
        _pending_rows, _pending_dbg = _fetch_pending_from_mining(base)
        _pending_total = sum(float(x.get("qty") or 0) for x in _pending_rows)
    except Exception:
        # Не роняем страницу — просто оставим пустой блок
        pass

    return render_template(
        "moves/index.html",
        rows=rows,
        pending_rows=_pending_rows,
        pending_total=_pending_total,
        pending_dbg=_pending_dbg,
    )

@bp.post("/pending_action")
def pending_action():
    """Обработчик кнопок из карточки.
       Прототип: просто возвращаемся назад; интеграцию с хранилищем можно добавить позже.
    """
    act = (request.form.get("act") or "").strip().lower()
    # act ∈ {"accept","discard"} — пока без побочных эффектов (мягкий прототип)
    flash("Действие обработано" if act in ("accept","discard") else "Нет действия", "ok")
    return redirect(url_for("moves.index"))

@bp.get("/receipt")
def receipt():
    """Форма приёма (заглушка: только рендер шаблона)."""
    return render_template("moves/receipt_form.html")

@bp.get("/process")
def process():
    """Форма переработки (заглушка: только рендер шаблона)."""
    return render_template("moves/process_form.html")
