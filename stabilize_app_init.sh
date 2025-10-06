#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-mine-mod-251004000019}"
BR="${BR:-main}"
HREF="/dict/product-metrics"

echo "→ Проверяю, что это git-репозиторий…"
test -d .git || { echo "❌ Тут нет .git. Выполни: cd ~/mine-mod-251004000019"; exit 1; }

echo "→ Обновляю ветку $BR"
git fetch origin "$BR" || true
git checkout "$BR"
git reset --hard "origin/$BR"

echo "→ Чиню app/__init__.py"
python3 - <<'PY'
import re
from pathlib import Path

p = Path("app/__init__.py")
txt = p.read_text(encoding="utf-8")

# 1) Выпилим мусор/ошибочные строки
patterns = [
    r"^\s*if\s+'product_metrics_compat'\s+not\s+in\s+app\.blueprints\s*:\s*$",  # пустой if
    r"^\s*from\s+\.product_metrics\s+import\s+prod_bp\s*$",                     # кривой импорт
    r"^\s*app\.register_blueprint\(\s*prod_bp\s*,.*$",                          # кривое имя bp
    r'^\s*app\.register_blueprint\(\s*product_metrics_bp\s*,\s*url_prefix\s*=\s*"/dict/prod-metrics"\s*\)\s*$', # кривой префикс
]
for pat in patterns:
    txt = re.sub(pat, "", txt, flags=re.M)

# 2) Добавим корректный импорт, если отсутствует
if not re.search(r'^\s*from\s+\.product_metrics\s+import\s+product_metrics_bp\s*$', txt, flags=re.M):
    # Вставим рядом с другими внутренними импортами
    imps = list(re.finditer(r'^\s*(?:from\s+\.[\w_]+\s+import\s+.*|import\s+\.[\w_]+.*)\s*$', txt, flags=re.M))
    ins_at = imps[-1].end() if imps else 0
    ins = ("\n" if ins_at else "") + "from .product_metrics import product_metrics_bp\n"
    txt = txt[:ins_at] + ins + txt[ins_at:]

# 3) Найдём 'return app' и его отступ
m_ret = re.search(r'^[ \t]*return\s+app\b', txt, flags=re.M)
if not m_ret:
    raise SystemExit("Не нашёл 'return app' в app/__init__.py — проверь фабрику приложения.")
indent = re.match(r'^[ \t]*', m_ret.group(0)).group(0)

# 4) Убедимся, что перед return есть корректная регистрация /dict/product-metrics
reg_line = f'{indent}app.register_blueprint(product_metrics_bp, url_prefix="/dict/product-metrics")'
has_good = re.search(r'^\s*app\.register_blueprint\(\s*product_metrics_bp\s*,\s*url_prefix\s*=\s*"/dict/product-metrics"\s*\)\s*$', txt, flags=re.M)

if not has_good:
    txt = txt[:m_ret.start()] + reg_line + "\n" + txt[m_ret.start():]

# 5) Сжать лишние пустые строки (но бережно)
txt = re.sub(r'\n{3,}', '\n\n', txt)

p.write_text(txt, encoding="utf-8")
print("✓ app/__init__.py — приведён в порядок")
PY

echo "→ Коммит и пуш"
git add app/__init__.py
git commit -m "fix(product-metrics): убрать пустой if, нормализовать импорт/регистрацию" || true

echo "→ Деплой на Heroku"
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null || true

echo "→ Проверка эндпоинтов"
BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "BASE=$BASE"
for p in "$HREF/" "$HREF/params" "$HREF/template.xlsx" "$HREF/export.csv" "/"; do
  printf "%-34s -> " "$p"
  curl -sS -I "${BASE%/}${p}" | sed -n '1p'
done

echo
echo "Если всё ещё 503 — сразу дай 20–30 последних строк логов:"
echo "  heroku logs -a \"$APP\" --tail"
