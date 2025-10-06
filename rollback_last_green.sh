#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-mine-mod-251004000019}"

echo "→ Показываю последние релизы:"
heroku releases -a "$APP" -n 10

# Возьмём третий сверху релиз (обычно до двух неудачных)
REL="${REL:-$(heroku releases -a "$APP" -n 3 | awk 'NR==3{print $1}')}"

if [[ -z "${REL:-}" ]]; then
  echo "❌ Не смог определить релиз. Укажи вручную: REL=v55 ./rollback_last_green.sh"
  exit 1
fi

echo "→ Откатываюсь к $REL"
heroku releases:rollback -a "$APP" "$REL"

echo "→ Жду перезапуск и проверяю корень…"
BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
for i in {1..10}; do
  code=$(curl -sI -o /dev/null -w '%{http_code}' "${BASE%/}/")
  echo "  попытка $i: / -> $code"
  [[ "$code" == "200" || "$code" == "302" ]] && break
  sleep 2
done

echo "Готово. Текущая версия:"
heroku releases -a "$APP" -n 1
