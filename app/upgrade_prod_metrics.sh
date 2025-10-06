#!/usr/bin/env bash
set -euo pipefail

# === 0) Настройки проекта ===
REPO_DIR="${REPO_DIR:-$HOME/mine-mod-251004000019}"
APP="${APP:-mine-mod-251004000019}"
BR="${BR:-main}"
GITHUB_REMOTE="${GITHUB_REMOTE:-origin}"

echo "== Python =="
PY="$(command -v python3 || true)"; echo "${PY:-python3 not found}"

echo "== 1) Перехожу в репозиторий =="
cd "$REPO_DIR"

echo "== 2) Обновляю $BR =="
git fetch --all -p
git reset --hard
git checkout "$BR"
git reset --hard "origin/$BR"
git pull --rebase --autostash || true

echo "== 3) Определяю URL карточки «Показатели готовой продукции» из cabinet.html =="
CARD_HREF="$(awk 'BEGIN{RS="</div>";FS="\n"} /Показатели готовой продукции/ {print $0}' app/cabinet/templates/cabinet.html 2>/dev/null \
  | sed -n 's/.*href="\([^"]*\)".*/\1/p' | head -n1 || true)"
if [[ -z "${CARD_HREF:-}" ]]; then
  CARD_HREF="/dict/prod-metrics/"
fi
echo "➡️  CARD_HREF=${CARD_HREF}"

echo "== 4) Создаю модуль app/prod_metrics (блюпринт, шаблон, статика) =="

mkdir -p app/prod_metrics/templates/prod_metrics

# --- app/prod_metrics/__init__.py ---
cat > app/prod_metrics/__init__.py <<'PY'
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, Response
import io, csv
import pandas as pd

prod_bp = Blueprint("prod_metrics", __name__, template_folder="templates")

# Память процесса для быстрого старта
_STATE = {
    "rows": []  # list of dicts
}

# Колонки (порядок отображения и экспорта)
COLUMNS = [
    ("fraction", "Фракция"),
    ("grade",    "Марка"),
    ("ash",      "Зола (%)"),
    ("moist",    "Влага (%)"),
    ("sulfur",   "Сера (%)"),
    ("note",     "Примечание"),
    ("status",   "Статус"),  # active/archived
]

def _normalize_row(d):
    return {
        "fraction": str(d.get("fraction","")).strip(),
        "grade":    str(d.get("grade","")).strip(),
        "ash":      str(d.get("ash","")).strip(),
        "moist":    str(d.get("moist","")).strip(),
        "sulfur":   str(d.get("sulfur","")).strip(),
        "note":     str(d.get("note","")).strip(),
        "status":   (str(d.get("status","active")).strip() or "active"),
    }

@prod_bp.route("/", methods=["GET"])
def index():
    return render_template("prod_metrics/index.html", rows=_STATE["rows"], columns=COLUMNS)

@prod_bp.route("/params", methods=["GET"])
def params():
    return jsonify({
        "title": "Показатели готовой продукции",
        "columns": [{"key":k, "title": t} for k,t in COLUMNS],
        "count": len(_STATE["rows"])
    })

@prod_bp.route("/add", methods=["POST"])
def add_row():
    row = _normalize_row(request.form.to_dict())
    _STATE["rows"].append(row)
    return redirect(url_for("prod_metrics.index"))

@prod_bp.route("/delete/<int:idx>", methods=["POST"])
def delete_row(idx):
    if 0 <= idx < len(_STATE["rows"]):
        del _STATE["rows"][idx]
    return redirect(url_for("prod_metrics.index"))

@prod_bp.route("/import", methods=["POST"])
def import_data():
    f = request.files.get("file")
    if not f or not f.filename:
        return redirect(url_for("prod_metrics.index"))
    # XLSX или CSV
    if f.filename.lower().endswith(".xlsx"):
        df = pd.read_excel(f)
    else:
        df = pd.read_csv(f)
    # ожидаем колонки по ключам
    wanted = [k for k,_ in COLUMNS]
    cols = [c for c in df.columns]
    # попытка сопоставить русские заголовки
    rus_to_key = {title:key for key,title in COLUMNS}
    mapped = []
    for c in cols:
        k = rus_to_key.get(str(c).strip())
        mapped.append(k if k else str(c).strip())
    df.columns = mapped
    df = df[[k for k in wanted if k in df.columns]].copy()
    rows = [ _normalize_row(m) for m in df.to_dict(orient="records") ]
    _STATE["rows"] = rows
    return redirect(url_for("prod_metrics.index"))

@prod_bp.route("/template.xlsx", methods=["GET"])
def template_xlsx():
    df = pd.DataFrame([{k:t} for k,t in COLUMNS]).T.iloc[1:].T
    df.columns = [title for _,title in COLUMNS]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return Response(buf.getvalue(),
        headers={
            "Content-Disposition":"attachment; filename=prod-metrics-template.xlsx",
            "Cache-Control":"no-cache"
        },
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@prod_bp.route("/export.csv")
def export_csv():
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([title for _,title in COLUMNS])
    for r in _STATE["rows"]:
        writer.writerow([r.get(k,"") for k,_ in COLUMNS])
    return Response(si.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=prod-metrics.csv"})

@prod_bp.route("/export.xlsx")
def export_xlsx():
    df = pd.DataFrame([[r.get(k,"") for k,_ in COLUMNS] for r in _STATE["rows"]],
                      columns=[title for _,title in COLUMNS])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return Response(buf.getvalue(),
        headers={"Content-Disposition":"attachment; filename=prod-metrics.xlsx"},
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
PY

# --- app/prod_metrics/templates/prod_metrics/index.html ---
cat > app/prod_metrics/templates/prod_metrics/index.html <<'HTML'
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
  <h2 class="mb-3">Показатели готовой продукции</h2>
  <p class="text-muted">Импорт колонок: <code>Фракция, Марка, Зола (%), Влага (%), Сера (%), Примечание, Статус</code>.
     Ручное добавление — ниже. Шаблон можно скачать кнопкой.</p>

  <form class="row g-2 align-items-center" method="post" action="./import" enctype="multipart/form-data">
    <div class="col-md-6">
      <input type="file" name="file" class="form-control">
    </div>
    <div class="col-auto">
      <button class="btn btn-primary">Импортировать</button>
    </div>
    <div class="col-auto">
      <a class="btn btn-outline-secondary" href="./template.xlsx">Шаблон XLSX</a>
    </div>
  </form>

  <details class="mt-3">
    <summary class="h6">Ручное добавление</summary>
    <form class="row gy-2 gx-3 align-items-end mt-2" method="post" action="./add">
      <div class="col-md-2">
        <label class="form-label">Фракция</label>
        <input name="fraction" class="form-control" placeholder="0–25 мм">
      </div>
      <div class="col-md-2">
        <label class="form-label">Марка</label>
        <input name="grade" class="form-control" placeholder="ДГ/Г/СС...">
      </div>
      <div class="col-md-2">
        <label class="form-label">Зола (%)</label>
        <input name="ash" class="form-control" placeholder="≤ 12">
      </div>
      <div class="col-md-2">
        <label class="form-label">Влага (%)</label>
        <input name="moist" class="form-control" placeholder="≤ 8">
      </div>
      <div class="col-md-2">
        <label class="form-label">Сера (%)</label>
        <input name="sulfur" class="form-control" placeholder="≤ 1.2">
      </div>
      <div class="col-md-2">
        <label class="form-label">Статус</label>
        <select name="status" class="form-select">
          <option value="active" selected>active</option>
          <option value="archived">archived</option>
        </select>
      </div>
      <div class="col-12">
        <label class="form-label">Примечание</label>
        <input name="note" class="form-control" placeholder="любая пометка">
      </div>
      <div class="col-12">
        <button class="btn btn-success mt-2">Добавить</button>
      </div>
    </form>
  </details>

  <div class="d-flex gap-2 mt-4">
    <a class="btn btn-outline-success" href="./export.csv">Экспорт CSV</a>
    <a class="btn btn-outline-success" href="./export.xlsx">Экспорт XLSX</a>
    <a class="btn btn-outline-secondary" href="./params">Параметры (JSON)</a>
  </div>

  <div class="table-responsive mt-3">
    <table class="table align-middle">
      <thead>
        <tr>
          {% for key,title in columns %}
            <th>{{ title }}</th>
          {% endfor %}
          <th style="width:100px;">Действия</th>
        </tr>
      </thead>
      <tbody>
        {% if rows and rows|length %}
          {% for r in rows %}
            <tr>
              {% for key,title in columns %}
                <td>{{ r.get(key,"") }}</td>
              {% endfor %}
              <td>
                <form method="post" action="./delete/{{ loop.index0 }}">
                  <button class="btn btn-sm btn-outline-danger">Удалить</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        {% else %}
          <tr><td colspan="{{ columns|length + 1 }}" class="text-muted">
            Данных пока нет. Импортируйте файл или добавьте запись вручную.
          </td></tr>
        {% endif %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
HTML

echo "== 5) Регистрирую блюпринт в app/__init__.py =="
# Импорт
if ! grep -q "from \.prod_metrics import prod_bp" app/__init__.py; then
  awk '1; END{print "from .prod_metrics import prod_bp"}' app/__init__.py > app/__init__.py.new && mv app/__init__.py.new app/__init__.py
fi
# Регистрация (перед return app)
if ! grep -q "app.register_blueprint(prod_bp" app/__init__.py; then
  python3 - <<'PY'
from pathlib import Path, re
p = Path("app/__init__.py")
t = p.read_text()
t = re.sub(r'(return\s+app)', "    app.register_blueprint(prod_bp, url_prefix=\"/dict/prod-metrics\")\n    \\1", t, count=1)
p.write_text(t)
print("ok")
PY
fi

echo "== 6) Коммит → GitHub =="
git add app/prod_metrics app/__init__.py
git commit -m "feat(prod-metrics): таблица + ручное добавление + импорт/экспорт CSV/XLSX" || true
git push "$GITHUB_REMOTE" "$BR"

echo "== 7) Деплой на Heroku ($APP) =="
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null

BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "== 8) Проверка эндпоинтов =="
echo "BASE: $BASE"
for path in "$CARD_HREF" "${CARD_HREF%/}/params" "${CARD_HREF%/}/template.xlsx" "${CARD_HREF%/}/export.csv"; do
  printf -- "-- HEAD %s -> " "$path"
  curl -sS -I "${BASE%/}${path}" | sed -n '1p'
done

echo "== Готово. Открой ${BASE%/}${CARD_HREF} =="
