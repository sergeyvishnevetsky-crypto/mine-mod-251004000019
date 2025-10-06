#!/usr/bin/env bash
set -euo pipefail

APP="mine-mod-251004000019"
BR="main"
INI="app/__init__.py"

echo "== 0) Проверяю наличие модуля =="
test -f app/revexp_items/__init__.py || { echo "❌ нет app/revexp_items/__init__.py"; exit 1; }

echo "== 1) Обновляю локальную $BR и забираю свежий __init__.py =="
git fetch origin || true
git checkout -B "$BR" origin/"$BR" || git checkout -B "$BR"
git pull --ff-only origin "$BR" || true

echo "== 2) Патчу $INI (импорт + регистрация) =="
# 2.1 Импорт
if ! grep -q 'from \.revexp_items import revexp_bp' "$INI"; then
  # вставим импорт перед def create_app
  awk '
    BEGIN{added=0}
    /^def[[:space:]]+create_app/ && !added { print "from .revexp_items import revexp_bp"; added=1 }
    { print }
  ' "$INI" > "$INI.new" && mv "$INI.new" "$INI"
  echo "✅ Добавлен импорт revexp_bp"
else
  echo "ℹ️ Импорт уже есть"
fi

# 2.2 Регистрация блюпринта
if ! grep -q 'app\.register_blueprint(revexp_bp, url_prefix="/dict/revexp-items")' "$INI"; then
  # вставим ПЕРЕД 'return app' в create_app с нужным отступом
  awk '
    BEGIN{infunc=0}
    /^def[[:space:]]+create_app/ {infunc=1}
    {/return[[:space:]]+app/ && infunc==1}{
      print "    app.register_blueprint(revexp_bp, url_prefix=\"/dict/revexp-items\")"
    }
    { print }
  ' "$INI" > "$INI.new" && mv "$INI.new" "$INI"
  echo "✅ Добавлена регистрация revexp_bp"
else
  echo "ℹ️ Регистрация уже есть"
fi

echo "== 3) Коммит → GitHub =="
git add "$INI"
git commit -m "fix: register revexp_items blueprint in app/__init__.py (import + url_prefix)" || true
git push origin "$BR"

echo "== 4) Деплой на Heroku =="
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null

BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "URL: $BASE"

echo "== 5) Проверяю эндпоинты =="
curl -sS -I "${BASE%/}/dict/revexp-items/" | head -n 5 || true
curl -sS -I "${BASE%/}/dict/revexp-items/params" | head -n 5 || true
curl -sS -I "${BASE%/}/dict/revexp-items/template.xlsx" | head -n 5 || true

echo "== 6) Карта маршрутов на живом dyno (фильтр по revexp) =="
heroku run -a "$APP" python - <<'PY'
from wsgi import app
with app.app_context():
    for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
        methods=','.join(sorted(m for m in r.methods if m not in ('HEAD','OPTIONS')))
        if 'revexp-items' in r.rule or r.rule == '/cabinet/':
            print(f"{r.rule:35} {methods:10} {r.endpoint}")
PY

echo "✅ Готово."
