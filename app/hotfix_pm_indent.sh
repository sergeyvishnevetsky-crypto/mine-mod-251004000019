#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-mine-mod-251004000019}"
REPO_DIR="${REPO_DIR:-$HOME/mine-mod-251004000019}"
BR="${BR:-main}"
HREF="/dict/product-metrics"

echo "→ REPO_DIR=$REPO_DIR"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "❌ Тут нет git-репозитория: $REPO_DIR"
  echo "   Укажи путь: export REPO_DIR=/путь/к/репо"
  exit 1
fi

cd "$REPO_DIR"
git fetch origin "$BR" || true
git checkout "$BR"
git reset --hard "origin/$BR"

python3 - <<'PY'
import re
from pathlib import Path

p = Path("app/__init__.py")
txt = p.read_text(encoding="utf-8")

# 1) Удалим кривые импорты/регистрации product-metrics
txt = re.sub(r'^\s*from\s+\.product_metrics\s+import\s+prod_bp\s*\n', '', txt, flags=re.M)
txt = re.sub(r'^\s*app\.register_blueprint\(\s*prod_bp\s*,[^\n]*\)\s*\n', '', txt, flags=re.M)
txt = re.sub(r'^\s*app\.register_blueprint\(\s*product_metrics_bp\s*,[^\n]*\)\s*\n', '', txt, flags=re.M)

# 2) Вставим корректный импорт, если его нет
if not re.search(r'from\s+\.product_metrics\s+import\s+product_metrics_bp', txt):
    # вставим рядом с другими импортами из внутренних модулей
    ins_at = 0
    m = list(re.finditer(r'^\s*from\s+\.[\w_]+\s+import\s+.*$', txt, flags=re.M))
    if m:
        ins_at = m[-1].end()
        txt = txt[:ins_at] + "\nfrom .product_metrics import product_metrics_bp" + txt[ins_at:]
    else:
        txt = "from .product_metrics import product_metrics_bp\n" + txt

# 3) Найдём строку 'return app' и возьмём её отступ
m_ret = re.search(r'^[ \t]*return\s+app\b', txt, flags=re.M)
if not m_ret:
    raise SystemExit("Не нашёл 'return app' в app/__init__.py")
indent = re.match(r'^[ \t]*', m_ret.group(0)).group(0)

# 4) Добавим корректную регистрацию прямо перед return app
reg_line = f'{indent}app.register_blueprint(product_metrics_bp, url_prefix="/dict/product-metrics")\n'
txt = txt[:m_ret.start()] + reg_line + txt[m_ret.start():]

p.write_text(txt, encoding="utf-8")
print("✓ app/__init__.py: импорт/регистрация product_metrics исправлены")
PY

git add app/__init__.py
git commit -m "fix(product-metrics): правильный импорт/регистрация + отступ" || true

# Деплой
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null || true

# Проверка
BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "BASE=$BASE"
for p in "$HREF/" "$HREF/params" "$HREF/template.xlsx" "$HREF/export.csv" "/"; do
  printf "%-32s -> " "$p"
  curl -sS -I "${BASE%/}${p}" | sed -n '1p'
done

echo
echo "Если всё ещё 503 — смотри логи:"
echo "  heroku logs -a \"$APP\" --tail"
