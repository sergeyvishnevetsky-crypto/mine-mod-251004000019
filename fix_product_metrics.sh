#!/usr/bin/env bash
set -euo pipefail

# === НАСТРОЙКИ ===
REPO_DIR="${REPO_DIR:-$HOME/mine-mod-251004000019}"
APP="${APP:-mine-mod-251004000019}"
BR="${BR:-main}"
HREF="/dict/product-metrics"

echo "→ REPO_DIR=$REPO_DIR"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "❌ Не нашёл git-репозиторий по пути: $REPO_DIR"
  echo "   Укажи правильный путь:  export REPO_DIR=/путь/к/репо  и повтори запуск."
  exit 1
fi

# === 0) Подчистим случайно созданный ~/app (если есть и это НЕ git) ===
if [[ -d "$HOME/app" && ! -d "$HOME/app/.git" ]]; then
  TS="$(date +%s)"
  mv "$HOME/app" "$HOME/app._wrong_${TS}"
  echo "🔧 Перенёс «случайный» $HOME/app -> $HOME/app._wrong_${TS}"
fi

# === 1) Обновляем рабочую ветку ===
cd "$REPO_DIR"
git fetch origin "$BR" || true
git checkout "$BR"
git reset --hard "origin/$BR"

# === 2) Бэкапим важные файлы ===
mkdir -p .backup_pm
cp -n app/__init__.py .backup_pm/__init__.py.bak || true
cp -n app/cabinet/templates/cabinet.html .backup_pm/cabinet.html.bak 2>/dev/null || true

# === 3) Создаём/обновляем модуль product_metrics ===
mkdir -p app/product_metrics/templates/product_metrics

cat > app/product_metrics/__init__.py <<'PY'
from flask import Blueprint, render_template, jsonify, send_file
from io import BytesIO
import csv

try:
    import pandas as pd
except Exception:
    pd = None

product_metrics_bp = Blueprint(
    "product_metrics",
    __name__,
    template_folder="templates",
)

COLUMNS = [
    {"key":"code",     "title":"Код",        "type":"str",  "required":True},
    {"key":"brand",    "title":"Марка",      "type":"str",  "required":True},
    {"key":"fraction", "title":"Фракция",    "type":"str",  "required":True},
    {"key":"ash",      "title":"Зола,%",     "type":"num",  "required":False},
    {"key":"moist",    "title":"Влага,%",    "type":"num",  "required":False},
    {"key":"sulfur",   "title":"Сера,%",     "type":"num",  "required":False},
    {"key":"status",   "title":"Статус",     "type":"str",  "required":False, "enum":["активен","архив"]},
]

@product_metrics_bp.get("/")
def index():
    return render_template("product_metrics/index.html",
                           title="Показатели готовой продукции", columns=COLUMNS)

@product_metrics_bp.get("/params")
def params():
    return jsonify({
        "title": "Показатели готовой продукции",
        "columns": COLUMNS,
        "import": {"accept": [".csv", ".xlsx"]},
        "export": {"csv": True, "xlsx": True},
        "notes": "Импорт: code,brand,fraction,ash,moist,sulfur,status",
    })

@product_metrics_bp.get("/template.xlsx")
def template_xlsx():
    headers = [c["key"] for c in COLUMNS]
    buf = BytesIO()
    if pd is not None:
        pd.DataFrame(columns=headers).to_excel(buf, index=False)
    else:
        tmp = BytesIO()
        cw = csv.writer(tmp); cw.writerow(headers)
        buf.write(tmp.getvalue())
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name="product-metrics-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@product_metrics_bp.get("/export.csv")
def export_csv():
    headers = [c["key"] for c in COLUMNS]
    buf = BytesIO()
    cw = csv.writer(buf); cw.writerow(headers)
    return send_file(BytesIO(buf.getvalue()), as_attachment=True,
                     download_name="product-metrics.csv", mimetype="text/csv")
PY

cat > app/product_metrics/templates/product_metrics/index.html <<'HTML'
{% extends "base.html" %}
{% block content %}
  <h3 class="mb-3">{{ title }}</h3>

  <p class="text-secondary">
    Единый формат: <code>code, brand, fraction, ash, moist, sulfur, status</code>.
    Импорт CSV/XLSX и ручное добавление строк.
  </p>

  <!-- Импорт -->
  <form class="row g-2 align-items-center mb-3" method="post" enctype="multipart/form-data">
    <div class="col-12 col-md-6">
      <input class="form-control" type="file" name="file" accept=".csv,.xlsx">
    </div>
    <div class="col-auto">
      <button type="button" class="btn btn-primary">Импортировать</button>
    </div>
    <div class="col-auto">
      <a class="btn btn-outline-secondary" href="{{ url_for('product_metrics.template_xlsx') }}">Шаблон XLSX</a>
    </div>
  </form>

  <!-- Ручное добавление -->
  <details class="mb-3">
    <summary class="mb-2">Параметры / Ручное добавление</summary>
    <form class="row g-2 align-items-end" id="add-form" onsubmit="return false;">
      {% for c in columns %}
        <div class="col-6 col-md-3 col-lg-2">
          <label class="form-label small">{{ c.title }}</label>
          {% if c.enum %}
            <select class="form-select form-select-sm" name="{{ c.key }}">
              <option value="" selected>—</option>
              {% for v in c.enum %}<option>{{ v }}</option>{% endfor %}
            </select>
          {% else %}
            <input class="form-control form-control-sm" name="{{ c.key }}"
                   {% if c.type=='num' %}type="number" step="any"{% else %}type="text"{% endif %}>
          {% endif %}
        </div>
      {% endfor %}
      <div class="col-12 col-md-auto">
        <button class="btn btn-success btn-sm" id="btn-add">Добавить</button>
      </div>
    </form>
  </details>

  <!-- Таблица -->
  <div class="table-responsive">
    <table class="table table-sm align-middle">
      <thead>
        <tr>
          {% for c in columns %}<th>{{ c.title }}</th>{% endfor %}
          <th class="text-end" style="width:64px">Действия</th>
        </tr>
      </thead>
      <tbody id="grid">
        <tr class="text-secondary"><td colspan="{{ columns|length + 1 }}">Данных пока нет. Импортируйте или добавьте вручную.</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Экспорт -->
  <div class="d-flex gap-2">
    <a class="btn btn-success btn-sm" href="{{ url_for('product_metrics.export_csv') }}">Экспорт CSV</a>
    <a class="btn btn-success btn-sm" href="{{ url_for('product_metrics.template_xlsx') }}">Экспорт XLSX</a>
    <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('product_metrics.params') }}">Параметры (JSON)</a>
  </div>

  <script>
    const grid = document.getElementById('grid');
    const addBtn = document.getElementById('btn-add');
    const addForm = document.getElementById('add-form');

    function rowTemplate(){
      return `<tr>` +
        `{% for c in columns %}<td data-k="{{ c.key }}"></td>{% endfor %}` +
        `<td class="text-end"><button class="btn btn-outline-danger btn-sm js-del">Удалить</button></td>` +
        `</tr>`;
    }
    function fill(tr, rec){
      {% for c in columns %}
      tr.querySelector('[data-k="{{ c.key }}"]').textContent = rec['{{ c.key }}'] ?? '';
      {% endfor %}
    }

    addBtn.addEventListener('click', ()=>{
      const fd = new FormData(addForm); const rec={}; for (const [k,v] of fd.entries()) rec[k]=v;
      const tr = document.createElement('tr'); tr.innerHTML = rowTemplate(); grid.appendChild(tr); fill(tr, rec);
    });
    grid.addEventListener('click', (e)=>{ if (e.target.matches('.js-del')) e.target.closest('tr')?.remove(); });
  </script>
{% endblock %}
HTML

# === 4) Регистрация блюпринта корректно ===
python3 - "$REPO_DIR" <<'PY'
import re, sys
from pathlib import Path
root = Path(sys.argv[1])
p = root/"app/__init__.py"
t = p.read_text(encoding="utf-8")

if not re.search(r'from\s+\.product_metrics\s+import\s+product_metrics_bp', t):
    m = list(re.finditer(r'^\s*from\s+\.[\w_]+\s+import\s+.*$', t, re.M))
    if m:
        i = m[-1].end()
        t = t[:i] + "\nfrom .product_metrics import product_metrics_bp" + t[i:]
    else:
        t = "from .product_metrics import product_metrics_bp\n" + t

if "app.register_blueprint(product_metrics_bp" not in t:
    t = re.sub(r'(return\s+app)',
               'app.register_blueprint(product_metrics_bp, url_prefix="/dict/product-metrics")\n        \\1',
               t, count=1)

p.write_text(t, encoding="utf-8")
print("✓ __init__.py обновлён")
PY

# === 5) Карточка в Кабинете ===
CAB="app/cabinet/templates/cabinet.html"
if [[ -f "$CAB" ]] && ! grep -q "/dict/product-metrics/" "$CAB"; then
  awk -v card='\
      <div class="col-12 col-sm-6 col-md-4 col-lg-3">\
        <div class="card h-100">\
          <div class="card-body d-flex flex-column">\
            <div class="fw-semibold mb-2">Показатели готовой продукции</div>\
            <div class="text-secondary small mb-3">Фракция, марка и показатели (зола/влага/сера). Импорт XLSX/CSV, экспорт CSV.</div>\
            <div class="mt-auto"><a class="btn btn-primary w-100" href="/dict/product-metrics/">Открыть</a></div>\
          </div>\
        </div>\
      </div>' \
      '1;/<\/div>[[:space:]]*<!-- Универсальная модалка -->/{print card}' "$CAB" > "$CAB.new" && mv "$CAB.new" "$CAB"
  echo "✓ Карточка добавлена"
else
  echo "ℹ️ Карточка уже есть или файл не найден"
fi

# === 6) Коммит/пуш ===
git add app/product_metrics app/__init__.py "$CAB" 2>/dev/null || true
git commit -m "feat(product-metrics): страница + регистрация + карточка" || true
git push origin "$BR" || true

# === 7) Деплой на Heroku ===
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null || true

# === 8) Проверка ===
BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "BASE=$BASE"
for p in "$HREF/" "$HREF/params" "$HREF/template.xlsx" "$HREF/export.csv"; do
  printf "%-30s -> " "$p"
  curl -sS -I "${BASE%/}${p}" | sed -n '1p'
done

echo
echo "Если что-то упало — смотри логи:"
echo "  heroku logs -a \"$APP\" --tail"
