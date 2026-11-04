
/* =========================================================
   ConsultFlow — учебный интерактивный прототип
   Три экрана: «Заявки», «Карточка заявки», «Кабинет клиента».
   Данные загружаются из общего API /api/prototype и сохраняются в БД.
   ========================================================= */

const ICONS = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.2-3.2"></path></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"></path></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5m6-6-6 6 6 6"></path></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z"></path><path d="M14 2v5h5"></path></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m20 6-11 11-5-5"></path></svg>',
  checkCircle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"></circle><path d="m8.5 12.5 2.4 2.4 4.6-5"></path></svg>',
  paperclip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m21 11.5-8.5 8.5a5 5 0 0 1-7-7L14 4.5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L16 6.5"></path></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"></circle><path d="M12 11v5"></path><path d="M12 8h.01"></path></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>'
};

const STATUS = {
  new:            { label: 'Новая',          cls: 'st-new' },
  clarification:  { label: 'На уточнении',   cls: 'st-clarification' },
  sent:           { label: 'КП отправлено',  cls: 'st-sent' },
  revision:       { label: 'На доработке',   cls: 'st-revision' },
  in_progress:    { label: 'В работе',       cls: 'st-in_progress' },
  done:           { label: 'Завершена',      cls: 'st-done' }
};

const STATUS_OPTIONS = [
  ['all', 'Все статусы'],
  ['new', 'Новая'],
  ['clarification', 'На уточнении'],
  ['sent', 'КП отправлено'],
  ['revision', 'На доработке'],
  ['in_progress', 'В работе'],
  ['done', 'Завершена']
];

const PRACTICES = [
  ['management', 'Управленческий консалтинг'],
  ['finance', 'Финансовый консалтинг'],
  ['legal', 'Юридический консалтинг'],
  ['it', 'IT-консалтинг']
];

const CONSULTANTS = [
  'Анна Смирнова',
  'Дмитрий Орлов',
  'Мария Ковалёва'
];

const API_BASE = window.CONSULTFLOW_API || '/api/prototype';

const state = {
  role: 'staff',
  view: 'list',
  activeId: null,
  tab: 'request',
  search: '',
  filter: 'all',
  modal: null,
  remarkOpen: false,
  ready: false,
  error: null,
  practices: PRACTICES,
  consultants: CONSULTANTS,
  requests: [],
  detail: null
};

/* ---------- helpers ---------- */
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[ch]));

const money = (value) => `${new Intl.NumberFormat('ru-RU').format(Number(value) || 0)} ₽`;
const active = () => state.detail || state.requests[0] || null;
const statusPill = (status) => {
  const meta = STATUS[status] || STATUS.new;
  return `<span class="status ${meta.cls}"><span class="status-dot"></span>${meta.label}</span>`;
};
const practiceLabel = (key) => (state.practices.find(([value]) => value === key) || state.practices[0] || ['management', 'Управленческий консалтинг'])[1];
const initials = (name) => String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();

function apiErrorText(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
  }
  return fallback;
}

async function api(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = null; }
  if (!response.ok) {
    throw new Error(apiErrorText(payload && payload.detail, `Ошибка API (${response.status})`));
  }
  return payload;
}

async function load(orderId) {
  const query = orderId ? `?order_id=${encodeURIComponent(orderId)}` : '';
  const data = await api(`/bootstrap${query}`);
  state.requests = data.orders || [];
  state.practices = (data.practices || []).map((item) => [item.value, item.label]);
  state.consultants = data.consultants || CONSULTANTS;
  state.detail = data.current || state.requests[0] || null;
  state.activeId = state.detail ? state.detail.id : null;
  state.ready = true;
  state.error = null;
}

async function reload(orderId = state.activeId) {
  try {
    await load(orderId);
    render();
  } catch (error) {
    toast(error.message);
  }
}

async function refreshAfter(promise, message, { closeModal = false } = {}) {
  try {
    const result = await promise;
    if (closeModal) {
      state.modal = null;
      state.remarkOpen = false;
    }
    await load(result && result.id ? result.id : state.activeId);
    render();
    toast(message);
  } catch (error) {
    toast(error.message);
  }
}
function toast(message) {
  const node = document.getElementById('toast');
  node.innerHTML = `${ICONS.checkCircle}<span>${esc(message)}</span>`;
  node.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => node.classList.remove('show'), 3200);
}

/* ---------- header ---------- */
function renderHeader() {
  const staff = state.role === 'staff';
  return `
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <div class="brand-mark">CF</div>
        <div>
          <div class="brand-name">ConsultFlow</div>
          <div class="brand-slogan">От заявки до акта — один процесс</div>
        </div>
      </div>
      <div class="topbar-right">
        <span class="proto-badge">Прототип</span>
        <div class="role-switch" aria-label="Демонстрационная роль">
          <button class="role-btn ${staff ? 'active' : ''}" data-action="role" data-role="staff">Сотрудник</button>
          <button class="role-btn ${staff ? '' : 'active'}" data-action="role" data-role="client">Клиент</button>
        </div>
        <div class="avatar" title="${staff ? 'Алексей Иванов' : 'Иван Петров'}">${staff ? 'АИ' : 'ИП'}</div>
      </div>
    </div>
  </header>`;
}

/* ---------- screen 1: list ---------- */
function filteredRequests() {
  const query = state.search.trim().toLowerCase();
  return state.requests.filter((request) => {
    if (state.filter !== 'all' && request.status !== state.filter) return false;
    if (!query) return true;
    return [request.number, request.company, request.contact, request.service]
      .join(' ')
      .toLowerCase()
      .includes(query);
  });
}

function renderTable() {
  const items = filteredRequests();
  if (!items.length) {
    return `<div class="card"><div class="empty"><b>Ничего не найдено</b>Измените поисковый запрос или фильтр статуса.</div></div>`;
  }
  const rows = items.map((request) => `
    <tr data-action="open" data-id="${request.id}">
      <td><span class="num">№${esc(request.number)}</span></td>
      <td>
        <div class="client-cell">
          <span class="avatar-sm">${esc(initials(request.company.replace(/[«»]/g, '')))}</span>
          <div>
            <b>${esc(request.company)}</b>
            <span>${esc(request.contact)}</span>
          </div>
        </div>
      </td>
      <td><div class="service" title="${esc(request.service)}">${esc(request.service)}</div></td>
      <td class="responsible">${esc(request.manager)}</td>
      <td>${statusPill(request.status)}</td>
      <td><div class="due">${esc(request.due)}<small>${request.status === 'done' ? 'завершена' : 'рабочий день'}</small></div></td>
    </tr>`).join('');

  return `
  <div class="card">
    <div class="table-wrap">
      <table class="requests">
        <thead>
          <tr>
            <th>Номер</th>
            <th>Клиент</th>
            <th>Услуга</th>
            <th>Ответственный</th>
            <th>Статус</th>
            <th>Срок ответа</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  </div>`;
}

function renderList() {
  const count = filteredRequests().length;
  const options = STATUS_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${state.filter === value ? 'selected' : ''}>${label}</option>`).join('');

  return `${renderHeader()}
  <div class="container">
    <div class="page-head">
      <div>
        <h1 class="page-title">Заявки</h1>
        <p class="page-sub">Рабочее место сотрудника: обработка обращений и подготовка документов.</p>
      </div>
      <button class="btn btn-primary" data-action="modal-new">${ICONS.plus}Новая заявка</button>
    </div>

    <div class="toolbar">
      <div class="search">
        ${ICONS.search}
        <input id="search" type="search" placeholder="Поиск по номеру, клиенту или услуге" value="${esc(state.search)}" autocomplete="off">
      </div>
      <select class="select" id="status-filter" aria-label="Фильтр по статусу">${options}</select>
      <span class="toolbar-count" id="list-count">${count} из ${state.requests.length} заявок</span>
    </div>

    <div id="table-area">${renderTable()}</div>
  </div>`;
}

/* ---------- screen 2: card ---------- */
function renderCard() {
  const request = active();
  return `${renderHeader()}
  <div class="container">
    <a class="back-link" data-action="back">${ICONS.back}Назад к заявкам</a>

    <div class="page-head card-head">
      <div>
        <div class="eyebrow">Заявка</div>
        <h1>Заявка №${esc(request.number)}</h1>
        <p class="company">${esc(request.company)} · ${esc(request.contact)}</p>
      </div>
      <div>${statusPill(request.status)}</div>
    </div>

    <div class="meta-strip">
      <div class="meta-item">
        <div class="meta-label">Ответственный менеджер</div>
        <div class="meta-value">${esc(request.manager)}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Срок ответа клиенту</div>
        <div class="meta-value">${esc(request.due)}</div>
      </div>
      <div class="meta-item" style="flex:1">
        <div class="meta-label">Услуга</div>
        <div class="meta-value">${esc(request.service)}</div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab ${state.tab === 'request' ? 'active' : ''}" data-action="tab" data-tab="request">Заявка</button>
      <button class="tab ${state.tab === 'docs' ? 'active' : ''}" data-action="tab" data-tab="docs">КП и документы</button>
      <button class="tab ${state.tab === 'history' ? 'active' : ''}" data-action="tab" data-tab="history">История<span class="tab-count">${request.history.length}</span></button>
    </div>

    <div>${renderTab(request)}</div>
  </div>`;
}

function renderTab(request) {
  if (state.tab === 'docs') return renderDocsTab(request);
  if (state.tab === 'history') return renderHistoryTab(request);
  return renderRequestTab(request);
}

function renderRequestTab(request) {
  const practiceOptions = state.practices.map(([value, label]) =>
    `<option value="${value}" ${request.practice === value ? 'selected' : ''}>${label}</option>`).join('');
  const consultantOptions = state.consultants.map((name) =>
    `<option value="${esc(name)}" ${request.consultant === name ? 'selected' : ''}>${esc(name)}</option>`).join('');

  return `
  <div class="grid-2">
    <section class="panel">
      <div class="panel-head"><h2>Данные клиента</h2></div>
      <dl class="kv">
        <dt>Контактное лицо</dt><dd>${esc(request.contact)}</dd>
        <dt>Email</dt><dd>${esc(request.email)}</dd>
        <dt>Компания</dt><dd>${esc(request.company)}</dd>
      </dl>
      <p class="description">${esc(request.description)}</p>
      <div class="file-chip">${ICONS.file}${esc(request.file || 'Техническое задание.pdf')}</div>
    </section>

    <section class="panel">
      <div class="panel-head"><h2>Автоматическая обработка</h2></div>
      <div class="auto-box">
        <div class="auto-item">${ICONS.checkCircle}<span>Данные из заявки извлечены</span></div>
        <div class="auto-item">${ICONS.checkCircle}<span>Дубликаты не найдены</span></div>
        <div class="auto-item">${ICONS.checkCircle}<span>Предложенная практика: <b>${practiceLabel(request.practice).toLowerCase()}</b></span></div>
        <div class="auto-item">${ICONS.checkCircle}<span>Рекомендуемый консультант: <b>${esc(request.consultant)}</b></span></div>
        <p class="auto-note">Рекомендации системы. Решение подтверждает сотрудник.</p>
      </div>

      <div class="auto-controls">
        <div class="field">
          <label for="practice-select">Практика</label>
          <select class="select" id="practice-select">${practiceOptions}</select>
        </div>
        <div class="field">
          <label for="consultant-select">Консультант</label>
          <select class="select" id="consultant-select">${consultantOptions}</select>
        </div>
      </div>

      <p class="kb-line">Похожие работы из базы знаний: <a href="#" onclick="return false">оптимизация продаж</a>, <a href="#" onclick="return false">аудит бизнес-процессов</a></p>
    </section>
  </div>

  <section class="panel">
    <div class="panel-head">
      <h2>Уточнение требований</h2>
      ${request.status === 'clarification' ? statusPill('clarification') : ''}
    </div>

    ${request.clarification ? `
      <div class="qa">
        <div class="qa-head">Вопрос клиенту</div>
        <div class="qa-body">${esc(request.clarification)}</div>
      </div>` : ''}

    ${request.answer ? `
      <div class="qa">
        <div class="qa-head">Ответ клиента</div>
        <div class="qa-body">${esc(request.answer)}</div>
      </div>` : ''}

    <div class="clarify-box">
      <div class="field">
        <label for="clarify-input">Вопрос клиенту</label>
        <input class="input" id="clarify-input" placeholder="Например: уточните количество сотрудников в процессе">
      </div>
      <button class="btn btn-secondary" data-action="clarify">Запросить уточнение</button>
    </div>
    <p class="client-hint">После отправки заявка перейдёт в статус «На уточнении», а вопрос появится в кабинете клиента.</p>
  </section>`;
}

function docCard(name, meta = 'PDF · демонстрационный документ', tag = '') {
  return `
  <div class="doc">
    <div class="doc-icon">${ICONS.file}</div>
    <div>
      <div class="doc-name">${esc(name)}</div>
      <div class="doc-meta">${esc(meta)}</div>
    </div>
    ${tag ? `<span class="doc-tag">${esc(tag)}</span>` : ''}
  </div>`;
}

function renderDocsTab(request) {
  const locked = request.signed || request.status === 'sent' || request.status === 'in_progress' || request.status === 'done';
  const canSend = !locked && request.status !== 'sent';
  const sendLabel = request.proposalVersion > 0 ? 'Отправить обновлённое КП' : 'Сформировать и отправить КП';

  const remarks = request.remarks && request.status === 'revision' ? `
    <div class="notice notice-amber">
      <b>Замечания клиента</b>
      <p>${esc(request.remarks)}</p>
      <p class="notice-note">Изучите заявку, ТЗ и предыдущую версию КП, затем скорректируйте предложение.</p>
    </div>` : '';

  return `
  <section class="panel">
    <div class="panel-head">
      <h2>Коммерческое предложение</h2>
      ${request.proposalVersion ? `<span class="version">Версия ${request.proposalVersion}</span>` : ''}
    </div>

    ${remarks}

    <p class="client-hint" style="margin-top:-4px">Стоимость и срок рассчитаны системой. Проверьте значения и при необходимости измените их.</p>

    <div class="form-grid">
      <div class="field span-2">
        <label for="solution">Описание решения</label>
        <textarea class="textarea" id="solution" ${locked ? 'disabled' : ''} placeholder="Что именно получит клиент">${esc(request.solution)}</textarea>
      </div>
      <div class="field">
        <label for="cost">Стоимость, ₽</label>
        <input class="input" id="cost" type="number" min="0" step="1000" value="${Number(request.cost) || 0}" ${locked ? 'disabled' : ''}>
      </div>
      <div class="field">
        <label for="days">Срок выполнения, рабочих дней</label>
        <input class="input" id="days" type="number" min="1" step="1" value="${Number(request.days) || 1}" ${locked ? 'disabled' : ''}>
      </div>
      <div class="field">
        <label for="sla">SLA / условия взаимодействия</label>
        <input class="input" id="sla" value="${esc(request.sla)}" ${locked ? 'disabled' : ''}>
      </div>
      <div class="field">
        <label for="kp-consultant">Консультант</label>
        <select class="select" id="kp-consultant" ${locked ? 'disabled' : ''}>
          ${state.consultants.map((name) => `<option value="${esc(name)}" ${request.consultant === name ? 'selected' : ''}>${esc(name)}</option>`).join('')}
        </select>
      </div>
    </div>

    <div class="approvals">
      <span class="approval">${ICONS.checkCircle}Стоимость согласована финансовым отделом</span>
      <span class="approval">${ICONS.checkCircle}Условия согласованы юридическим отделом</span>
    </div>

    ${canSend ? `<div class="actions-row"><button class="btn btn-primary" data-action="send-kp">${sendLabel}</button></div>` : ''}
    ${request.status === 'sent' && !request.signed ? `<p class="client-hint">КП отправлено клиенту. Ожидаем подписание или замечания.</p>` : ''}
  </section>

  ${request.proposalVersion ? `
    <section class="panel">
      <div class="panel-head"><h2>Документы по заявке</h2></div>
      ${docCard(`КП — версия ${request.proposalVersion}.pdf`, 'Коммерческое предложение · демонстрационный документ')}
      ${request.signed ? docCard('Подписанное КП.pdf', 'Подписано клиентом · демонстрационный документ', 'подписано') : ''}
      ${request.contract ? docCard('Договор.pdf', 'Договор на оказание услуг · демонстрационный документ') : ''}
      ${request.act ? docCard('Акт выполненных работ.pdf', 'Закрывающий документ · демонстрационный документ') : ''}
    </section>` : ''}

  ${request.signed ? `
    <div class="notice notice-green">
      <b>КП подписано клиентом</b>
      <p>Можно переходить к договору и выполнению заказа.</p>
      <p class="notice-note">Сохранено в базе подписанных КП.</p>
    </div>` : ''}

  ${renderExecution(request)}
  ${request.status === 'done' ? `
    <div class="notice notice-green">
      <b>Заказ завершён</b>
      <p>Акт подтверждён клиентом. Заявка переведена в статус «Завершена».</p>
    </div>` : ''}`;
}

function renderExecution(request) {
  if (!request.signed) return '';

  const contractRow = request.contract
    ? `${docCard('Договор.pdf', 'Договор на оказание услуг · демонстрационный документ')}`
    : `<button class="btn btn-secondary" data-action="contract">Сформировать договор</button>`;

  const workRow = request.workStarted
    ? `<span class="muted small">Работа начата</span>`
    : `<button class="btn btn-secondary" data-action="start" ${request.contract ? '' : 'disabled'}>Начать работу</button>`;

  const actRow = request.act
    ? `${docCard('Акт выполненных работ.pdf', 'Демонстрационный документ', request.actConfirmed ? 'подтверждён' : 'ожидает клиента')}`
    : `<button class="btn btn-secondary" data-action="act" ${request.workStarted ? '' : 'disabled'}>Сформировать акт</button>`;

  return `
  <section class="panel">
    <div class="panel-head"><h2>Выполнение заказа</h2></div>
    <div class="exec-row">
      <div><div class="exec-title">Договор</div><div class="exec-sub">Формируется после подписания КП</div></div>
      <div class="exec-right">${contractRow}</div>
    </div>
    <div class="exec-row">
      <div><div class="exec-title">Работа</div><div class="exec-sub">Старт после подписания договора</div></div>
      <div class="exec-right">${workRow}</div>
    </div>
    <div class="exec-row">
      <div><div class="exec-title">Акт</div><div class="exec-sub">Клиент подтверждает закрытие заказа</div></div>
      <div class="exec-right">${actRow}</div>
    </div>
  </section>`;
}

function renderHistoryTab(request) {
  const items = request.history.slice().reverse().map((item, index) => {
    const color = index === 0 ? 'blue' : 'green';
    return `
    <div class="tl-item ${color}">
      <div class="tl-text">${esc(item.text)}</div>
      <div class="tl-time">${esc(item.time)}</div>
    </div>`;
  }).join('');

  return `
  <section class="panel">
    <div class="panel-head"><h2>История заявки</h2></div>
    <div class="timeline">${items}</div>
  </section>`;
}

/* ---------- screen 3: client ---------- */
function clientStage(request) {
  if (request.actConfirmed || request.status === 'done') return 4;
  if (request.workStarted || request.status === 'in_progress') return 3;
  if (request.proposalVersion > 0) return 2;
  return 1;
}

function renderStepper(request) {
  const stage = clientStage(request);
  const steps = ['Заявка', 'Согласование КП', 'Работа', 'Акт'];
  return `<div class="stepper">${steps.map((label, index) => {
    const number = index + 1;
    const cls = number < stage ? 'done' : number === stage ? 'active' : '';
    const content = number < stage ? ICONS.check : number;
    return `<div class="step ${cls}">
      <div class="step-dot">${content}</div>
      <div class="step-label">${label}</div>
    </div>`;
  }).join('')}</div>`;
}

function renderClient() {
  const request = active();
  const firstName = (request.contact || '').split(' ')[0] || 'клиент';

  return `${renderHeader()}
  <div class="container narrow">
    <div class="page-head">
      <div>
        <div class="eyebrow">Кабинет клиента</div>
        <h1 class="page-title">Здравствуйте, ${esc(firstName)}</h1>
        <p class="page-sub">Здесь можно следить за заявкой, отвечать на вопросы и согласовывать документы.</p>
      </div>
      <button class="btn btn-primary" data-action="modal-new">${ICONS.plus}Оставить заявку</button>
    </div>

    <section class="client-hero">
      <div class="summary-top">
        <div>
          <div class="eyebrow">Текущая заявка</div>
          <h2>Заявка №${esc(request.number)}</h2>
          <p>${esc(request.service)}</p>
        </div>
        ${statusPill(request.status)}
      </div>
      ${renderStepper(request)}
    </section>

    ${renderClientClarification(request)}
    ${renderClientProposal(request)}
    ${renderClientAct(request)}

    <p class="client-hint" style="text-align:center;margin-top:18px!important">
      Это демонстрационный прототип. Заявка, статусы и документы сохраняются в общей базе ConsultFlow, электронная подпись имитируется.
    </p>
  </div>`;
}

function renderClientClarification(request) {
  if (!request.clarification) return '';

  if (request.answer) {
    return `
    <section class="panel">
      <div class="panel-head"><h2>Уточнение требований</h2>${statusPill('clarification')}</div>
      <div class="qa">
        <div class="qa-head">Вопрос менеджера</div>
        <div class="qa-body">${esc(request.clarification)}</div>
      </div>
      <div class="qa">
        <div class="qa-head">Ваш ответ</div>
        <div class="qa-body">${esc(request.answer)}</div>
      </div>
    </section>`;
  }

  return `
  <section class="panel">
    <div class="panel-head"><h2>Уточнение требований</h2>${statusPill('clarification')}</div>
    <div class="qa">
      <div class="qa-head">Вопрос менеджера</div>
      <div class="qa-body">${esc(request.clarification)}</div>
    </div>
    <div class="field" style="margin-top:14px">
      <label for="answer-text">Ваш ответ</label>
      <textarea class="textarea" id="answer-text" placeholder="Напишите ответ на вопрос менеджера"></textarea>
    </div>
    <div class="actions-row" style="margin-top:0">
      <button class="btn btn-primary" data-action="answer">Отправить ответ</button>
    </div>
  </section>`;
}

function renderClientProposal(request) {
  if (!request.proposalVersion) {
    return `
    <section class="panel">
      <div class="panel-head"><h2>Коммерческое предложение</h2></div>
      <p class="muted small">КП ещё не подготовлено. Мы сообщим, когда менеджер отправит предложение.</p>
    </section>`;
  }

  const signed = request.signed;
  const revision = request.status === 'revision';

  const actions = signed ? `
    <div class="notice notice-green" style="margin-bottom:0">
      <b>КП подписано</b>
      <p>Подписанный документ сохранён и доступен менеджеру.</p>
    </div>` : revision ? `
    <div class="notice notice-amber">
      <b>Замечания отправлены</b>
      <p>${esc(request.remarks || '')}</p>
      <p class="notice-note">Ожидайте обновлённую версию КП от менеджера.</p>
    </div>` : `
    <div class="actions-row">
      <button class="btn btn-primary" data-action="modal-sign">Подписать КП</button>
      <button class="btn btn-secondary" data-action="toggle-remarks">Отправить замечания</button>
    </div>
    ${state.remarkOpen ? `
      <div class="field" style="margin-top:14px">
        <label for="remarks-text">Что необходимо изменить?</label>
        <textarea class="textarea" id="remarks-text" placeholder="Опишите, что добавить или скорректировать в предложении"></textarea>
      </div>
      <div class="actions-row" style="margin-top:0">
        <button class="btn btn-primary" data-action="submit-remarks">Отправить</button>
      </div>` : ''}`;

  return `
  <section class="panel">
    <div class="panel-head">
      <h2>Коммерческое предложение</h2>
      <span class="version">Версия ${request.proposalVersion}</span>
    </div>

    <p class="solution">${esc(request.solution)}</p>

    <div class="proposal-grid">
      <div class="metric">
        <div class="metric-label">Стоимость</div>
        <div class="metric-value">${money(request.cost)}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Срок</div>
        <div class="metric-value">${Number(request.days) || 0} раб. дн.</div>
      </div>
      <div class="metric">
        <div class="metric-label">SLA</div>
        <div class="metric-value small-value">${esc(request.sla)}</div>
      </div>
    </div>

    ${docCard('Коммерческое предложение.pdf', `КП — версия ${request.proposalVersion} · демонстрационный документ`)}
    ${signed ? docCard('Подписанное КП.pdf', 'Подписано клиентом · демонстрационный документ', 'подписано') : ''}

    ${actions}
  </section>`;
}

function renderClientAct(request) {
  if (!request.act) return '';
  return `
  <section class="panel">
    <div class="panel-head"><h2>Акт выполненных работ</h2>${request.actConfirmed ? statusPill('done') : ''}</div>
    ${docCard('Акт выполненных работ.pdf', 'Закрывающий документ · демонстрационный документ', request.actConfirmed ? 'подтверждён' : 'ожидает подтверждения')}
    ${request.actConfirmed ? `
      <div class="notice notice-green" style="margin-bottom:0">
        <b>Заказ завершён</b>
        <p>Спасибо! Акт подтверждён, заявка переведена в статус «Завершена».</p>
      </div>` : `
      <div class="actions-row">
        <button class="btn btn-primary" data-action="confirm-act">Подтвердить акт</button>
      </div>`}
  </section>`;
}

/* ---------- modals ---------- */
function renderModal() {
  const root = document.getElementById('modal-root');
  if (!state.modal) {
    root.innerHTML = '';
    return;
  }
  if (state.modal === 'new') {
    root.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="new-title">
        <div class="modal-head">
          <div>
            <h3 id="new-title">Новая заявка</h3>
            <p>Заполните данные — заявка появится в реестре со статусом «Новая».</p>
          </div>
          <button class="modal-close" data-action="close-modal" aria-label="Закрыть">×</button>
        </div>
        <form id="new-request-form">
          <div class="modal-body">
            <div class="field">
              <label for="company">Название компании</label>
              <input class="input" id="company" name="company" required placeholder="ООО «Пример»">
            </div>
            <div class="field">
              <label for="contact">Контактное лицо</label>
              <input class="input" id="contact" name="contact" required placeholder="Имя и фамилия">
            </div>
            <div class="field">
              <label for="email">Email</label>
              <input class="input" id="email" name="email" type="email" required placeholder="name@company.ru">
            </div>
            <div class="field">
              <label for="description">Описание задачи</label>
              <textarea class="textarea" id="description" name="description" required placeholder="Коротко опишите задачу и ожидаемый результат"></textarea>
            </div>
            <div class="field">
              <label>Прикрепить ТЗ</label>
              <label class="file-drop" for="file-input">
                ${ICONS.paperclip}
                <span id="file-name"><b>Выберите файл</b> · PDF, DOC или DOCX</span>
              </label>
              <input id="file-input" name="file" type="file" accept=".pdf,.doc,.docx" hidden>
            </div>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" data-action="close-modal">Отмена</button>
            <button type="submit" class="btn btn-primary">Создать заявку</button>
          </div>
        </form>
      </div>
    </div>`;
    return;
  }

  if (state.modal === 'sign') {
    const request = active();
    root.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal small" role="dialog" aria-modal="true" aria-labelledby="sign-title">
        <div class="modal-head">
          <div>
            <h3 id="sign-title">Подписать КП?</h3>
            <p>Заявка №${esc(request.number)} · ${money(request.cost)} · ${Number(request.days) || 0} раб. дн.</p>
          </div>
          <button class="modal-close" data-action="close-modal" aria-label="Закрыть">×</button>
        </div>
        <div class="modal-body">
          <div class="notice notice-blue" style="margin-top:0">
            <b>Демонстрационное действие</b>
            <p>Настоящая электронная подпись не используется. Подпись имитируется и сохраняется в базе ConsultFlow.</p>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" data-action="close-modal">Отмена</button>
          <button class="btn btn-primary" data-action="confirm-sign">Подписать</button>
        </div>
      </div>
    </div>`;
  }
}

/* ---------- actions ---------- */
function orderPath(request) {
  return `/orders/${request.id}`;
}

function orderAction(request, action, body, message, options = {}) {
  return refreshAfter(
    api(`${orderPath(request)}/${action}`, { method: 'POST', body }),
    message,
    options
  );
}

async function handleAction(action, dataset) {
  const request = active();

  switch (action) {
    case 'role':
      state.role = dataset.role;
      state.remarkOpen = false;
      render();
      break;

    case 'open':
      state.activeId = Number(dataset.id);
      state.detail = state.requests.find((item) => item.id === state.activeId) || state.detail;
      state.view = 'card';
      state.tab = 'request';
      state.remarkOpen = false;
      render();
      break;

    case 'back':
      state.view = 'list';
      state.remarkOpen = false;
      render();
      break;

    case 'tab':
      state.tab = dataset.tab;
      render();
      break;

    case 'reload':
      state.ready = false;
      state.error = null;
      render();
      try {
        await load(state.activeId);
        render();
      } catch (error) {
        state.error = error.message;
        render();
      }
      break;

    case 'modal-new':
      state.modal = 'new';
      renderModal();
      bindForm();
      break;

    case 'close-modal':
      state.modal = null;
      renderModal();
      break;

    case 'clarify': {
      if (!request) return;
      const value = (document.getElementById('clarify-input')?.value || '').trim();
      if (!value) {
        toast('Введите вопрос клиенту');
        document.getElementById('clarify-input')?.focus();
        return;
      }
      await orderAction(request, 'clarify', { question: value }, 'Уточнение отправлено клиенту');
      break;
    }

    case 'answer': {
      if (!request) return;
      const value = (document.getElementById('answer-text')?.value || '').trim();
      if (!value) {
        toast('Введите ответ');
        document.getElementById('answer-text')?.focus();
        return;
      }
      await orderAction(request, 'answer', { answer: value }, 'Ответ отправлен менеджеру');
      break;
    }

    case 'send-kp': {
      if (!request) return;
      const solution = (document.getElementById('solution')?.value || '').trim();
      if (!solution) {
        toast('Заполните описание решения');
        return;
      }
      const sla = (document.getElementById('sla')?.value || '').trim();
      if (!sla) {
        toast('Заполните условия SLA');
        return;
      }
      const body = {
        solution,
        cost: Number(document.getElementById('cost')?.value) || 0,
        days: Number(document.getElementById('days')?.value) || 1,
        sla,
        consultant: document.getElementById('kp-consultant')?.value || request.consultant
      };
      const message = request.proposalVersion > 0
        ? 'Обновлённое КП отправлено клиенту'
        : 'КП отправлено клиенту';
      await orderAction(request, 'proposal', body, message);
      break;
    }

    case 'toggle-remarks':
      state.remarkOpen = !state.remarkOpen;
      render();
      break;

    case 'submit-remarks': {
      if (!request) return;
      const value = (document.getElementById('remarks-text')?.value || '').trim();
      if (!value) {
        toast('Опишите, что необходимо изменить');
        return;
      }
      state.remarkOpen = false;
      await orderAction(request, 'remarks', { text: value }, 'Замечания отправлены менеджеру');
      break;
    }

    case 'modal-sign':
      state.modal = 'sign';
      renderModal();
      break;

    case 'confirm-sign': {
      if (!request) return;
      await orderAction(request, 'sign', undefined, 'КП подписано', { closeModal: true });
      break;
    }

    case 'contract':
      if (!request) return;
      await orderAction(request, 'contract', undefined, 'Договор сформирован');
      break;

    case 'start':
      if (!request) return;
      await orderAction(request, 'start', undefined, 'Работа начата');
      break;

    case 'act':
      if (!request) return;
      await orderAction(request, 'act', undefined, 'Акт выполненных работ сформирован');
      break;

    case 'confirm-act':
      if (!request) return;
      await orderAction(request, 'confirm-act', undefined, 'Акт подтверждён. Заказ завершён', { closeModal: true });
      break;

    default:
      break;
  }
}

/* ---------- form ---------- */
function bindForm() {
  const form = document.getElementById('new-request-form');
  if (!form) return;

  const fileInput = document.getElementById('file-input');
  const fileName = document.getElementById('file-name');
  fileInput?.addEventListener('change', () => {
    const file = fileInput.files && fileInput.files[0];
    if (file && fileName) {
      fileName.innerHTML = `${ICONS.file}<span style="margin-left:6px"><b>${esc(file.name)}</b></span>`;
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const company = String(data.get('company') || '').trim();
    const contact = String(data.get('contact') || '').trim();
    const email = String(data.get('email') || '').trim();
    const description = String(data.get('description') || '').trim();
    if (!company || !contact || !email || !description) {
      toast('Заполните обязательные поля');
      return;
    }

    const file = fileInput?.files && fileInput.files[0];
    const submit = form.querySelector('button[type="submit"]');
    if (submit) submit.disabled = true;
    try {
      const created = await api('/orders', {
        method: 'POST',
        body: {
          company,
          contact,
          email,
          description,
          file_name: file ? file.name : null
        }
      });
      state.modal = null;
      state.remarkOpen = false;
      if (state.role === 'staff') {
        state.view = 'card';
        state.tab = 'request';
      }
      await load(created.id);
      render();
      toast('Заявка создана');
    } catch (error) {
      toast(error.message);
      if (submit) submit.disabled = false;
    }
  });
}

/* ---------- wiring ---------- */
function bindListControls() {
  const search = document.getElementById('search');
  const filter = document.getElementById('status-filter');

  search?.addEventListener('input', () => {
    state.search = search.value;
    const area = document.getElementById('table-area');
    if (area) area.innerHTML = renderTable();
    const count = document.getElementById('list-count');
    if (count) count.textContent = `${filteredRequests().length} из ${state.requests.length} заявок`;
  });

  filter?.addEventListener('change', () => {
    state.filter = filter.value;
    const area = document.getElementById('table-area');
    if (area) area.innerHTML = renderTable();
    const count = document.getElementById('list-count');
    if (count) count.textContent = `${filteredRequests().length} из ${state.requests.length} заявок`;
  });
}

function bindCardControls() {
  const request = active();
  if (!request) return;

  const practice = document.getElementById('practice-select');
  practice?.addEventListener('change', async () => {
    const consultant = document.getElementById('consultant-select')?.value || request.consultant;
    await refreshAfter(
      api(`${orderPath(request)}/practice`, {
        method: 'POST',
        body: { practice: practice.value, consultant }
      }),
      'Практика обновлена'
    );
  });

  const consultant = document.getElementById('consultant-select');
  consultant?.addEventListener('change', async () => {
    const practiceValue = document.getElementById('practice-select')?.value || request.practice;
    await refreshAfter(
      api(`${orderPath(request)}/practice`, {
        method: 'POST',
        body: { practice: practiceValue, consultant: consultant.value }
      }),
      'Консультант обновлён'
    );
  });

  const kpConsultant = document.getElementById('kp-consultant');
  kpConsultant?.addEventListener('change', () => {
    request.consultant = kpConsultant.value;
  });
}

function renderLoading() {
  const app = document.getElementById('app');
  app.innerHTML = `${renderHeader()}
  <div class="container">
    <div class="card"><div class="empty"><b>Загружаем данные</b>Подключаемся к базе ConsultFlow…</div></div>
  </div>`;
}

function renderError() {
  const app = document.getElementById('app');
  app.innerHTML = `${renderHeader()}
  <div class="container">
    <div class="card">
      <div class="empty">
        <b>Не удалось загрузить данные</b>
        <p>${esc(state.error || 'Проверьте соединение с бэкендом.')}</p>
        <p class="client-hint">Запустите backend на <code>127.0.0.1:8000</code> и откройте прототип через frontend: <code>/prototype/</code>.</p>
        <button class="btn btn-primary" data-action="reload">Повторить</button>
      </div>
    </div>
  </div>`;
}

function renderEmpty() {
  const app = document.getElementById('app');
  app.innerHTML = `${renderHeader()}
  <div class="container">
    <div class="page-head">
      <div><h1 class="page-title">Заявки</h1><p class="page-sub">В демо-базе пока нет заявок.</p></div>
      <button class="btn btn-primary" data-action="modal-new">${ICONS.plus}Новая заявка</button>
    </div>
    <div class="card"><div class="empty"><b>Список пуст</b>Создайте первую заявку.</div></div>
  </div>`;
}

function render() {
  if (!state.ready && !state.error) {
    renderLoading();
    return;
  }
  if (state.error) {
    renderError();
    return;
  }
  if (!active()) {
    renderEmpty();
    bindListControls();
    renderModal();
    bindForm();
    return;
  }

  const app = document.getElementById('app');
  app.innerHTML = state.role === 'client'
    ? renderClient()
    : state.view === 'card'
      ? renderCard()
      : renderList();

  bindListControls();
  bindCardControls();
  renderModal();
  bindForm();

  window.scrollTo({ top: 0, behavior: 'auto' });
}

/* ---------- global listeners ---------- */
document.addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-action]');
  if (trigger) {
    handleAction(trigger.dataset.action, trigger.dataset);
    return;
  }
  if (event.target.classList.contains('modal-backdrop')) {
    state.modal = null;
    renderModal();
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && state.modal) {
    state.modal = null;
    renderModal();
  }
});

(async function init() {
  try {
    await load();
    render();
  } catch (error) {
    state.ready = true;
    state.error = error.message;
    render();
  }
})();
