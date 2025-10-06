#!/usr/bin/env bash
set -euo pipefail

### --- ПАРАМЕТРЫ (правь при необходимости) ---
REPO_DIR="${REPO_DIR:-$HOME/mine-mod-251004000019}"
APP="${APP:-mine-mod-251004000019}"
BR="${BR:-main}"
TEMPLATE="app/revexp_items/templates/revexp_items/index.html"
### -------------------------------------------

echo "== 0) Перехожу в репозиторий =="
cd "$REPO_DIR"

if [ ! -d .git ]; then
  echo "❌ Тут нет .git — укажи правильный REPO_DIR"; exit 1
fi

echo "== 1) Обновляю ветку $BR =="
git fetch origin || true
git checkout "$BR"
git reset --hard "origin/$BR"

echo "== 2) Бэкап текущего шаблона =="
mkdir -p "$(dirname "$TEMPLATE")"
if [ -f "$TEMPLATE" ]; then
  cp -f "$TEMPLATE" "$TEMPLATE.bak"
fi

echo "== 3) Записываю новый шаблон ($TEMPLATE) =="
cat > "$TEMPLATE" <<'HTML'
{% extends "base.html" %}
{% block title %}Статьи доходов и расходов{% endblock %}

{% block content %}
<div class="container my-4" id="revexp-app">
  <h1 class="mb-3">Статьи доходов и расходов</h1>
  <p class="text-muted">
    Единый формат: <code>код</code>, <code>тип</code>, <code>статья</code>, <code>цфо</code>, <code>группа</code>, <code>активна</code>,
    <code>счет_бух</code>, <code>ндс</code>, <code>ед_изм</code>, <code>действует_с</code>, <code>действует_по</code>, <code>проект</code>, <code>комментарий</code>.
  </p>

  <!-- Панель действий -->
  <div class="d-flex flex-wrap gap-2 align-items-center mb-3">
    <form method="post" action="/dict/revexp-items/import" enctype="multipart/form-data" class="d-flex gap-2">
      <input type="file" name="file" class="form-control" style="max-width: 360px;" />
      <button class="btn btn-primary" type="submit">Импортировать</button>
      <a class="btn btn-outline-secondary" href="/dict/revexp-items/template.xlsx">Шаблон XLSX</a>
    </form>

    <div class="vr mx-2"></div>

    <a class="btn btn-success" href="/dict/revexp-items/export.csv">Экспорт CSV</a>
    <a class="btn btn-success" href="/dict/revexp-items/export.xlsx">Экспорт XLSX</a>

    <div class="vr mx-2"></div>

    <div class="btn-group" role="group" aria-label="view-modes">
      <button id="btnTable" class="btn btn-outline-dark active" type="button">Таблица</button>
      <button id="btnTree"  class="btn btn-outline-dark" type="button">Дерево</button>
    </div>

    <div class="ms-auto d-flex flex-wrap gap-2">
      <input id="q" type="search" class="form-control" placeholder="Поиск (код/статья/ЦФО/группа)" style="min-width:280px">
      <div class="dropdown">
        <button class="btn btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">Колонки</button>
        <ul class="dropdown-menu p-2" id="colMenu" style="width:280px; max-height: 50vh; overflow:auto"></ul>
      </div>
    </div>
  </div>

  <!-- Табличный вид -->
  <div id="view-table">
    <div class="table-responsive">
      <table class="table table-sm table-hover align-middle" id="grid">
        <thead class="table-light">
          <tr id="thead"></tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="d-flex justify-content-between align-items-center">
      <small class="text-muted" id="countHint">0 записей</small>
      <div class="btn-group btn-group-sm" role="group">
        <button id="prev" class="btn btn-outline-secondary">&laquo;</button>
        <button id="next" class="btn btn-outline-secondary">&raquo;</button>
      </div>
    </div>
  </div>

  <!-- Иерархический вид -->
  <div id="view-tree" class="d-none">
    <div id="tree" class="list-group"></div>
  </div>
</div>

<script>
(() => {
  const COLUMNS = [
    {key:'код',       title:'Код',         w:'10ch'},
    {key:'тип',       title:'Тип',         w:'10ch'},
    {key:'статья',    title:'Статья',      w:'32ch'},
    {key:'цфо',       title:'ЦФО',         w:'18ch'},
    {key:'группа',    title:'Группа',      w:'18ch'},
    {key:'активна',   title:'Активна',     w:'10ch'},
    {key:'счет_бух',  title:'Счёт бух.',   w:'12ch'},
    {key:'ндс',       title:'НДС',         w:'8ch'},
    {key:'ед_изм',    title:'Ед. изм.',    w:'10ch'},
    {key:'действует_с',title:'Действует с',w:'12ch'},
    {key:'действует_по',title:'Действует по',w:'12ch'},
    {key:'проект',    title:'Проект',      w:'14ch'},
    {key:'комментарий',title:'Комментарий',w:'28ch'},
  ];

  const state = {
    rows: [],
    filtered: [],
    page: 0,
    pageSize: 50,
    visible: new Set(COLUMNS.map(c=>c.key)),
  };

  const el = (id)=>document.getElementById(id);

  // UI init
  function buildHeader(){
    const tr = el('thead'); tr.innerHTML='';
    COLUMNS.forEach(c=>{
      const th = document.createElement('th');
      th.textContent = c.title;
      th.dataset.key = c.key;
      th.style.whiteSpace='nowrap';
      th.style.width=c.w;
      if(!state.visible.has(c.key)) th.classList.add('d-none');
      th.role='button';
      th.onclick = ()=>sortBy(c.key);
      tr.appendChild(th);
    });
  }
  function buildColMenu(){
    const menu = el('colMenu'); menu.innerHTML='';
    COLUMNS.forEach(c=>{
      const li = document.createElement('li');
      li.className='form-check';
      li.innerHTML = \`
        <input class="form-check-input" type="checkbox" value="\${c.key}" id="col_\${c.key}" \${state.visible.has(c.key)?'checked':''}>
        <label class="form-check-label" for="col_\${c.key}">\${c.title}</label>\`;
      li.querySelector('input').addEventListener('change', e=>{
        if(e.target.checked) state.visible.add(c.key); else state.visible.delete(c.key);
        buildHeader(); renderPage();
      });
      menu.appendChild(li);
    });
  }

  function renderPage(){
    const start = state.page*state.pageSize;
    const pageRows = state.filtered.slice(start, start+state.pageSize);
    const tb = el('tbody'); tb.innerHTML='';
    pageRows.forEach(r=>{
      const tr = document.createElement('tr');
      COLUMNS.forEach(c=>{
        const td = document.createElement('td');
        td.textContent = r[c.key]??'';
        if(!state.visible.has(c.key)) td.classList.add('d-none');
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
    el('countHint').textContent = \`\${state.filtered.length} записей • страница \${state.page+1}\`;
  }

  function applyFilter(){
    const q = el('q').value.trim().toLowerCase();
    state.filtered = !q ? state.rows : state.rows.filter(r=>{
      return ['код','статья','цфо','группа','тип'].some(k=>String(r[k]??'').toLowerCase().includes(q));
    });
    state.page=0; renderPage(); buildTree();
  }

  function sortBy(key){
    state.filtered.sort((a,b)=>String(a[key]??'').localeCompare(String(b[key]??''), 'ru'));
    renderPage();
  }

  function buildTree(){
    const tree = el('tree'); tree.innerHTML='';
    // Группы -> ЦФО -> статьи (доход/расход по "тип")
    const byGroup = groupBy(state.filtered, 'группа');
    Object.entries(byGroup).forEach(([grp, items])=>{
      const groupNode = mkNode(grp||'Без группы', 'list-group-item active');
      const byCfo = groupBy(items, 'цфо');
      Object.entries(byCfo).forEach(([cfo, items2])=>{
        const cfoNode = mkNode('ЦФО: '+(cfo||'—'), 'list-group-item');
        const ul = document.createElement('ul'); ul.className='list-group list-group-flush ms-3 my-2';
        items2.forEach(r=>{
          const li = document.createElement('li');
          li.className='list-group-item d-flex justify-content-between align-items-center';
          li.innerHTML = \`
            <span><span class="badge bg-secondary me-2">\${r['тип']||'—'}</span>\${r['код']||''} — \${r['статья']||''}</span>
            <small class="text-muted">\${r['счет_бух']||''}</small>\`;
          ul.appendChild(li);
        });
        cfoNode.appendChild(ul);
        groupNode.appendChild(cfoNode);
      });
      tree.appendChild(groupNode);
    });
  }
  function groupBy(arr, key){ return arr.reduce((acc, x)=>((acc[x[key]??'']??=[]).push(x), acc), {}); }
  function mkNode(text, cls){
    const div = document.createElement('div'); div.className=cls; div.style.cursor='pointer';
    const caret = document.createElement('span'); caret.className='me-2'; caret.textContent='▸';
    const title = document.createElement('strong'); title.textContent = text;
    div.append(caret, title);
    let expanded=false;
    const toggle = ()=>{
      expanded=!expanded; caret.textContent = expanded?'▾':'▸';
      Array.from(div.children).forEach((ch,i)=>{ if(i>=2) ch.classList.toggle('d-none', !expanded); });
    };
    div.addEventListener('click', (e)=>{ if(e.target===div || e.target===title || e.target===caret) toggle(); });
    return div;
  }

  // Пагинация
  el('prev').onclick = ()=>{ if(state.page>0){ state.page--; renderPage(); } };
  el('next').onclick = ()=>{ if((state.page+1)*state.pageSize < state.filtered.length){ state.page++; renderPage(); } };
  el('q').addEventListener('input', ()=>applyFilter());

  // Переключатели вида
  el('btnTable').onclick = ()=>{
    el('btnTable').classList.add('active'); el('btnTree').classList.remove('active');
    el('view-table').classList.remove('d-none'); el('view-tree').classList.add('d-none');
  };
  el('btnTree').onclick = ()=>{
    el('btnTree').classList.add('active'); el('btnTable').classList.remove('active');
    el('view-tree').classList.remove('d-none'); el('view-table').classList.add('d-none');
  };

  // Загрузка CSV (используем экспорт бекенда, чтоб не трогать API)
  fetch('/dict/revexp-items/export.csv',{cache:'no-store'})
    .then(r=>r.text())
    .then(text=>{
      const rows = parseCSV(text);
      // первая строка — заголовки
      const hdr = rows.shift()?.map(x=>x.trim().toLowerCase()) || [];
      const mapRow = (arr) => {
        const obj = {};
        hdr.forEach((h,i)=>obj[h] = arr[i] ?? '');
        return obj;
      };
      state.rows = rows.map(mapRow);
      state.filtered = [...state.rows];
      buildHeader(); buildColMenu(); renderPage(); buildTree();
    })
    .catch(e=>{
      console.error(e);
      document.getElementById('tbody').innerHTML =
        '<tr><td class="text-danger" colspan="12">Не удалось загрузить export.csv</td></tr>';
    });

  // Небольшой CSV-парсер (RFC4180-light)
  function parseCSV(s){
    const out=[]; let row=[], cell='', inQ=false;
    for(let i=0;i<s.length;i++){
      const ch=s[i], nx=s[i+1];
      if(inQ){
        if(ch=='"' && nx=='"'){ cell+='"'; i++; continue; }
        if(ch=='"'){ inQ=false; continue; }
        cell+=ch; continue;
      }
      if(ch=='"'){ inQ=true; continue; }
      if(ch==','){ row.push(cell); cell=''; continue; }
      if(ch=='\n'){ row.push(cell); out.push(row); row=[]; cell=''; continue; }
      if(ch=='\r'){ continue; }
      cell+=ch;
    }
    row.push(cell); out.push(row);
    // убираем возможную пустую последнюю строку
    return out.filter(r=>r.some(x=>String(x).trim()!==''));
  }
})();
</script>
{% endblock %}
HTML

echo "== 4) Коммит → GitHub =="
git add "$TEMPLATE"
git commit -m "revexp(UI): таблица/дерево, колонки, поиск; не трогаем backend" || true
git push origin "$BR"

echo "== 5) Деплой → Heroku ($APP) =="
heroku git:remote -a "$APP" -r heroku >/dev/null 2>&1 || true
git push heroku "$BR":main --force
heroku ps:restart -a "$APP" >/dev/null

echo "== 6) Проверка =="
BASE="$(heroku info -a "$APP" | sed -n 's/^Web URL:[[:space:]]*//p' | tr -d '\r\n')"
echo "URL: $BASE"
echo "-- HEAD /dict/revexp-items/:"
curl -sS -I "${BASE%/}/dict/revexp-items/" | head -n 5
echo "-- Ищу элементы таблицы в HTML:"
curl -sS "${BASE%/}/dict/revexp-items/" | grep -nE "Колонки|Таблица|Дерево|table" | head -n 5 || true

echo "✅ Готово. Открой ${BASE%/}/dict/revexp-items/"
