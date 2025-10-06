#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$HOME/mine-mod-251004000019"
APP="mine-mod-251004000019"
BR="main"
REMOTE="origin"

cd "$PROJECT_DIR"
[ -f wsgi.py ] || { echo "❌ Запускай из корня проекта (нет wsgi.py)"; exit 1; }

PYBIN="$(command -v python3 || command -v python)"
echo "== Python: $PYBIN =="

echo "== 1) Обновляю $BR =="
git fetch "$REMOTE" || true
git checkout -B "$BR" "${REMOTE}/${BR}" || git checkout -B "$BR"
git pull --ff-only "$REMOTE" "$BR" || true

echo "== 2) Создаю/обновляю модуль app/revexp_items =="
mkdir -p app/revexp_items/templates/revexp_items

# __init__.py (идемпотентно перезапишем той же версией)
cat > app/revexp_items/__init__.py <<'PY'
from flask import Blueprint, render_template, request, send_file, jsonify
import io
import pandas as pd

revexp_bp = Blueprint("revexp_items", __name__, template_folder="templates")

REQUIRED = ["код", "тип", "статья", "ЦФО"]
_DATA = pd.DataFrame(columns=REQUIRED)

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: str(c).strip() for c in df.columns})
    if set(REQUIRED).issubset(df.columns):
        out = df[REQUIRED].copy()
    elif {"код", "статья_дохода", "ЦФО"}.issubset(df.columns):
        out = pd.DataFrame({"код": df["код"], "тип": "Доход", "статья": df["статья_дохода"], "ЦФО": df["ЦФО"]})
    elif {"код", "статья_расхода", "ЦФО"}.issubset(df.columns):
        out = pd.DataFrame({"код": df["код"], "тип": "Расход", "статья": df["статья_расхода"], "ЦФО": df["ЦФО"]})
    else:
        raise ValueError("Ожидаю: (код, тип, статья, ЦФО) ИЛИ (код, статья_дохода, ЦФО) ИЛИ (код, статья_расхода, ЦФО)")
    out["тип"] = out["тип"].fillna("").astype(str).str.strip().str.title().replace({"Доходы":"Доход","Расходы":"Расход"})
    if out.isna().any().any():
        raise ValueError("Пустые значения в обязательных полях")
    return out[REQUIRED]

@revexp_bp.get("/dict/revexp-items/")
def index():
    return render_template("revexp_items/index.html")

@revexp_bp.get("/dict/revexp-items/params")
def params():
    return jsonify({
        "columns_unified": REQUIRED,
        "columns_income": ["код","статья_дохода","ЦФО"],
        "columns_expense": ["код","статья_расхода","ЦФО"],
        "count": int(_DATA.shape[0]),
    })

@revexp_bp.get("/dict/revexp-items/template.xlsx")
def template_xlsx():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame(columns=REQUIRED).to_excel(xw, sheet_name="единый", index=False)
        pd.DataFrame(columns=["код","статья_дохода","ЦФО"]).to_excel(xw, sheet_name="доходы", index=False)
        pd.DataFrame(columns=["код","статья_расхода","ЦФО"]).to_excel(xw, sheet_name="расходы", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="revexp-items-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@revexp_bp.post("/dict/revexp-items/import")
def import_():
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error":"Файл не передан"}), 400
    name = (f.filename or "").lower()
    try:
        if name.endswith((".xlsx",".xlsm",".xls")):
            df = pd.read_excel(f)
        else:
            df = pd.read_csv(f)
        use = _normalize(df)
        global _DATA
        _DATA = use.reset_index(drop=True)
        return jsonify({"ok": True, "rows": int(_DATA.shape[0])})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@revexp_bp.get("/dict/revexp-items/export.csv")
def export_csv():
    if _DATA.empty:
        return jsonify({"ok": False, "error":"Нет данных — загрузите файл"}), 400
    buf = io.StringIO(); _DATA.to_csv(buf, index=False); buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8")), as_attachment=True,
                     download_name="revexp-items.csv", mimetype="text/csv; charset=utf-8")

@revexp_bp.get("/dict/revexp-items/export.xlsx")
def export_xlsx():
    if _DATA.empty:
        return jsonify({"ok": False, "error":"Нет данных — загрузите файл"}), 400
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        _DATA.to_excel(xw, sheet_name="данные", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="revexp-items.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
PY

# шаблон страницы
cat > app/revexp_items/templates/revexp_items/index.html <<'HTML'
{% extends "base.html" %}
{% block title %}Справочник · Статьи доходов и расходов{% endblock %}
{% block content %}
<div class="container py-4">
  <h1 class="mb-3">Статьи доходов и расходов</h1>
  <p class="text-muted">Единый формат: <code>код, тип, статья, ЦФО</code>. Можно грузить «доходы» или «расходы» — конвертируется автоматически.</p>

  <div class="card mb-3">
    <div class="card-body">
      <form id="uploadForm">
        <input class="form-control mb-2" type="file" name="file" accept=".csv,.xlsx,.xlsm,.xls" required>
        <button class="btn btn-primary">Импортировать</button>
        <a class="btn btn-outline-secondary" href="/dict/revexp-items/template.xlsx">Шаблон XLSX</a>
      </form>
      <div id="result" class="mt-2 small text-muted"></div>
    </div>
  </div>

  <div class="d-flex gap-2">
    <a class="btn btn-success" href="/dict/revexp-items/export.csv">Экспорт CSV</a>
    <a class="btn btn-success" href="/dict/revexp-items/export.xlsx">Экспорт XLSX</a>
    <a class="btn btn-outline-secondary" href="/dict/revexp-items/params">Параметры</a>
  </div>
</div>
<script>
const form = document.getElementById('uploadForm');
const result = document.getElementById('result');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const r = await fetch('/dict/revexp-items/import', { method:'POST', body:new FormData(form) });
  const j = await r.json(); result.textContent = j.ok ? `✅ Строк: ${j.rows}` : `❌ ${j.error||'Ошибка'}`;
});
</script>
{% endblock %}
HTML

echo "== 3) Жёстко пропишу импорт и регистрацию в app/__init__.py =="
"$PYBIN" - <<'PY'
from pathlib import Path
p = Path("app/__init__.py")
t = p.read_text(encoding="utf-8")

if "from .revexp_items import revexp_bp" not in t:
    lines = t.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("def create_app"):
            lines.insert(i, "from .revexp_items import revexp_bp")
            break
    t = "\n".join(lines)

if 'app.register_blueprint(revexp_bp, url_prefix="/dict/revexp-items")' not in t:
    lines = t.splitlines()
    for i in range(len(lines)-1, -1, -1):
        if lines[i].strip().startswith("return app"):
            lines.insert(i, '    app.register_blueprint(revexp_bp, url_prefix="/dict/revexp-items")')
            break
    t = "\n".join(lines)

p.write_text(t, encoding="utf-8")
PY

echo "== 4) Карточка в Кабинете (если нет) =="
CAB="app/cabinet/templates/cabinet.html"
if ! grep -q '/dict/revexp-items/' "$CAB"; then
  # Добавим простую карточку в секцию "Справочники"
  /usr/bin/awk '
    {print}
    /id="dicts"/ && /tab-pane/ {inb=1}
    inb && /<\/div>/ && !added { 
      print "        <div class=\"col-md-3\">"
      print "          <div class=\"card h-100\"><div class=\"card-body\">"
      print "            <div class=\"fw-semibold mb-1\">Статьи доходов и расходов</div>"
      print "            <div class=\"text-muted small mb-3\">Импорт/экспорт CSV/XLSX</div>"
      print "            <a class=\"btn btn-primary\" href=\"/dict/revexp-items/\">Открыть</a>"
      print "          </div></div>"
      print "        </div>"
      added=1
    }
  ' "$CAB" > "$CAB.new" && mv "$CAB.new" "$CAB"
fi

echo "== 5) Коммит и пуш =="
git add -A
git commit -m "feat: /dict/revexp-items (единый справочник «Статьи доходов и расходов»)" || true
git push "$REMOTE" "$BR"

echo "== 6) Деплой на Heroku =="
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null

BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "URL: $BASE"

echo "-- Проверяю эндпоинты (ожидаю 200):"
curl -sS -I "${BASE%/}/dict/revexp-items/" | head -n 5 || true
curl -sS -I "${BASE%/}/dict/revexp-items/params" | head -n 5 || true
curl -sS -I "${BASE%/}/dict/revexp-items/template.xlsx" | head -n 5 || true

echo "-- Маршруты на живом dyno:"
heroku run -a "$APP" python - <<'PY'
from wsgi import app
with app.app_context():
    routes=[(r.rule,','.join(sorted(m for m in r.methods if m not in ('HEAD','OPTIONS'))),r.endpoint)
            for r in app.url_map.iter_rules()]
    for rule,methods,ep in sorted(routes):
        if 'revexp-items' in rule or rule=='/cabinet/':
            print(f"{rule:35} {methods:10} {ep}")
PY

echo "✅ Готово."
