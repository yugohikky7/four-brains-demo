// ============================================================
// FB Cashflow & HR Suite - Single-page app with hash router
// ============================================================

const yen = (n) => {
  if (n === null || n === undefined || isNaN(n)) return '--';
  const v = Math.round(Number(n));
  return '¥' + v.toLocaleString('ja-JP');
};
const num = (n) => (n == null || isNaN(n) ? '--' : Number(n).toLocaleString('ja-JP'));
const pct = (n, digits = 1) => (n == null || isNaN(n) ? '--' : Number(n).toFixed(digits) + '%');
const dateJP = (iso) => {
  if (!iso) return '--';
  const [y, m, d] = iso.split('-');
  return `${y}/${m}/${d}`;
};
const monthJP = (ym) => {
  if (!ym) return '--';
  const [y, m] = ym.split('-');
  return `${y}年${parseInt(m)}月`;
};
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => root.querySelectorAll(s);

const PAGE_META = {
  home: { title: 'ホーム', subtitle: '全体サマリーと重要アラート' },
  pl: { title: '損益計算書 (P/L)', subtitle: 'freee取引データに基づく当期損益' },
  bs: { title: '貸借対照表 (B/S)', subtitle: 'freee取引データに基づく財政状態' },
  monthly: { title: '月次キャッシュフロー予測', subtitle: '向こう12ヶ月、3シナリオ並行表示' },
  daily: { title: '日次キャッシュフロー予測', subtitle: '向こう30日、日別の入出金と残高' },
  receivables: { title: '入金予定（売掛）', subtitle: '請求書ごとの入金スケジュール' },
  'receivables-forecast': { title: '入金予測', subtitle: '取引先別パターン分析に基づく将来12ヶ月の入金予測' },
  payables: { title: '支払予定（買掛）', subtitle: 'ベンダー請求書ごとの支払スケジュール' },
  'payables-forecast': { title: '支払予測', subtitle: '取引先別パターン分析に基づく将来12ヶ月の支払予測' },
  tax: { title: '税金カレンダー', subtitle: '法人税・消費税・源泉・住民税・社保・固定資産税' },
  banks: { title: '銀行口座', subtitle: '口座別残高と合計' },
  loans: { title: '借入金管理', subtitle: '元利返済スケジュールと残高' },
  'org-chart': { title: '組織図', subtitle: 'freee人事労務マスタ連携 - 部門ごとの所属・役職' },
  employees: { title: '従業員一覧', subtitle: '在籍メンバーと基本情報' },
  payroll: { title: '給与推移', subtitle: '月次給与・社保・源泉・住民税・手取り' },
  bonus: { title: '賞与カレンダー', subtitle: '夏季・冬季賞与の支給予定' },
  'labor-cost': { title: '人件費分析', subtitle: '対売上比率・一人当たり生産性' },
  scenarios: { title: 'シナリオ設定', subtitle: '楽観／中立／悲観の倍率調整' },
  adjustments: { title: '手動調整', subtitle: 'API外の月別収支調整（賞与・税金・設備投資など）' },
  preferences: { title: 'サイト・期首設定', subtitle: '売掛/買掛サイト、期首残高など' },
  diagnostics: { title: 'freee連携診断', subtitle: 'どのAPIが取得できているか確認' },
};

const state = {
  status: null,
  forecast: null,
  settings: null,
  loans: [],
  adjustments: {},
  bankAccounts: null,
  arSchedule: null,
  apSchedule: null,
  taxCalendar: null,
  dailyForecast: null,
  employees: null,
  payrollHistory: null,
  bonusCalendar: null,
  laborAnalysis: null,
  selectedScenario: 'neutral',
  currentRoute: 'home',
  charts: {},
};

// ============================================================
// Init & router
// ============================================================

async function bootstrap() {
  try {
    state.status = await fetch('/api/status').then(r => r.json());
    renderModeBadge();
    bindTopbar();
    // 会社名をサイドバーに表示 (デモでも実モードでも)
    try {
      const ci = await fetch('/api/company-info').then(r => r.json());
      if (ci && ci.data && ci.data.name) {
        const span = document.getElementById('company-name');
        if (span) span.textContent = ci.data.name;
      }
    } catch (e) {}
    window.addEventListener('hashchange', handleRoute);
    handleRoute();
  } catch (e) {
    showWarning('initialization error: ' + e.message);
  }
}

function handleRoute() {
  const route = (location.hash || '#home').replace('#', '');
  const valid = PAGE_META[route] ? route : 'home';
  state.currentRoute = valid;
  // Update sidebar active state
  $$('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.route === valid));
  // Update topbar
  $('#page-title').textContent = PAGE_META[valid].title;
  $('#page-subtitle').textContent = PAGE_META[valid].subtitle;
  // Show only the active page
  $$('.page').forEach(el => el.classList.toggle('active', el.dataset.page === valid));
  // Lazy-load + render
  renderPage(valid);
}

async function renderPage(route) {
  const container = $(`.page[data-page="${route}"]`);
  if (!container) return;
  container.innerHTML = '<div class="empty-state"><div class="icon">⌛</div><div>読込中...</div></div>';
  try {
    switch (route) {
      case 'home': await renderHome(container); break;
      case 'pl': await renderPL(container); break;
      case 'bs': await renderBS(container); break;
      case 'monthly': await renderMonthly(container); break;
      case 'daily': await renderDaily(container); break;
      case 'receivables': await renderReceivables(container); break;
      case 'receivables-forecast': await renderReceivablesForecast(container); break;
      case 'payables': await renderPayables(container); break;
      case 'payables-forecast': await renderPayablesForecast(container); break;
      case 'tax': await renderTax(container); break;
      case 'banks': await renderBanks(container); break;
      case 'loans': await renderLoans(container); break;
      case 'org-chart': await renderOrgChart(container); break;
      case 'employees': await renderEmployees(container); break;
      case 'payroll': await renderPayroll(container); break;
      case 'bonus': await renderBonus(container); break;
      case 'labor-cost': await renderLaborCost(container); break;
      case 'scenarios': await renderScenarios(container); break;
      case 'adjustments': await renderAdjustments(container); break;
      case 'preferences': await renderPreferences(container); break;
      case 'diagnostics': await renderDiagnostics(container); break;
    }
  } catch (e) {
    container.innerHTML = `<div class="alert danger">ページ読込エラー: ${e.message}</div>`;
    console.error(e);
  }
}

// ============================================================
// Data loaders (cached)
// ============================================================

async function getForecast() {
  if (!state.forecast) {
    const r = await fetch('/api/forecast').then(x => x.json());
    state.forecast = r;
    if (r.company_name) $('#company-name').textContent = r.company_name;
    if (r.warning) showWarning(r.warning); else hideWarning();
  }
  return state.forecast;
}
async function getSettings() {
  if (!state.settings) state.settings = await fetch('/api/settings').then(r => r.json());
  return state.settings;
}
async function getLoans() {
  if (state.loans.length === 0) state.loans = await fetch('/api/loans').then(r => r.json());
  return state.loans;
}
async function getAdjustments() {
  if (!state.adjustments || Object.keys(state.adjustments).length === 0)
    state.adjustments = await fetch('/api/adjustments').then(r => r.json());
  return state.adjustments;
}
async function getBankAccounts() {
  if (!state.bankAccounts) {
    const r = await fetch('/api/bank-accounts').then(x => x.json());
    state.bankAccounts = r.data || [];
    state.bankAccountsSource = r.source;
    state.bankAccountsWarning = r.warning;
  }
  return state.bankAccounts;
}
async function getAR() {
  if (!state.arSchedule) {
    const r = await fetch('/api/ar-schedule').then(x => x.json());
    state.arSchedule = r.data || [];
    state.arSource = r.source;
    state.arWarning = r.warning;
  }
  return state.arSchedule;
}
async function getAP() {
  if (!state.apSchedule) {
    const r = await fetch('/api/ap-schedule').then(x => x.json());
    state.apSchedule = r.data || [];
    state.apSource = r.source;
    state.apWarning = r.warning;
  }
  return state.apSchedule;
}
async function getTax() {
  if (!state.taxCalendar) {
    const r = await fetch('/api/tax-calendar').then(x => x.json());
    state.taxCalendar = r.data || [];
    state.taxSource = r.source;
    state.taxWarning = r.warning;
  }
  return state.taxCalendar;
}
async function getDaily() {
  if (!state.dailyForecast) {
    const r = await fetch('/api/daily-forecast?days=60').then(x => x.json());
    state.dailyForecast = r.data || [];
    state.dailySource = r.source;
    state.dailyWarning = r.warning;
  }
  return state.dailyForecast;
}
async function getEmployees() {
  if (!state.employees) {
    const r = await fetch('/api/employees').then(x => x.json());
    state.employees = r.data || [];
    state.employeesSource = r.source;
    state.employeesWarning = r.warning;
  }
  return state.employees;
}
async function getPayrollHistory() {
  if (!state.payrollHistory) {
    const r = await fetch('/api/payroll-history').then(x => x.json());
    state.payrollHistory = r.data || [];
    state.payrollSource = r.source;
    state.payrollWarning = r.warning;
  }
  return state.payrollHistory;
}
async function getBonusCalendar() {
  if (!state.bonusCalendar) {
    const r = await fetch('/api/bonus-calendar').then(x => x.json());
    state.bonusCalendar = r.data || [];
    state.bonusSource = r.source;
    state.bonusWarning = r.warning;
  }
  return state.bonusCalendar;
}
async function getLaborAnalysis() {
  if (!state.laborAnalysis) {
    const r = await fetch('/api/labor-analysis').then(x => x.json());
    state.laborAnalysis = r.data || {};
    state.laborSource = r.source;
    state.laborWarning = r.warning;
  }
  return state.laborAnalysis;
}

function reloadAll() {
  Object.assign(state, {
    forecast: null, settings: null, loans: [], adjustments: {},
    bankAccounts: null, arSchedule: null, apSchedule: null,
    taxCalendar: null, dailyForecast: null, employees: null,
    payrollHistory: null, bonusCalendar: null, laborAnalysis: null,
  });
  Object.values(state.charts).forEach(c => c?.destroy && c.destroy());
  state.charts = {};
  renderPage(state.currentRoute);
}

// ============================================================
// Top bar
// ============================================================

function renderModeBadge() {
  const badge = $('#mode-badge');
  if (state.status.mock_mode) { badge.textContent = 'Mockモード'; badge.className = 'badge mock'; }
  else if (state.status.connected) { badge.textContent = '● freee連携中'; badge.className = 'badge live'; }
  else { badge.textContent = '未連携'; badge.className = 'badge'; }
  $('#btn-connect').hidden = state.status.mock_mode || state.status.connected;
  $('#btn-disconnect').hidden = !state.status.connected;
}

function bindTopbar() {
  $('#btn-connect').addEventListener('click', () => { location.href = '/oauth/start'; });
  $('#btn-disconnect').addEventListener('click', async () => {
    if (!confirm('freeeとの連携を解除しますか？')) return;
    await fetch('/api/disconnect', { method: 'POST' });
    location.reload();
  });
  $('#btn-reload').addEventListener('click', reloadAll);
}

function showWarning(msg) {
  const el = $('#warning-banner');
  el.textContent = '⚠️ ' + msg; el.hidden = false;
}
function hideWarning() { $('#warning-banner').hidden = true; }
function flash(msg) {
  const el = document.createElement('div');
  el.textContent = msg; el.className = 'toast';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

// ============================================================
// Chart helper
// ============================================================

function makeChart(canvasEl, key, config) {
  if (state.charts[key]) state.charts[key].destroy();
  state.charts[key] = new Chart(canvasEl, config);
  return state.charts[key];
}

// ============================================================
// Page: Home
// ============================================================

async function renderHome(c) {
  const [fc, banks, ar, ap, tax, daily, labor] = await Promise.all([
    getForecast(), getBankAccounts(), getAR(), getAP(), getTax(),
    getDaily(), getLaborAnalysis(),
  ]);
  const neutral = fc.scenarios.neutral;
  const totalBank = banks.reduce((s, b) => s + (b.balance || 0), 0);
  const today = new Date();
  const next30 = new Date(today.getTime() + 30 * 86400000);

  const arNext30 = ar.filter(x => {
    const d = new Date(x.due_date);
    return x.status === 'scheduled' && d >= today && d <= next30;
  });
  const apNext30 = ap.filter(x => {
    const d = new Date(x.due_date);
    return x.status === 'scheduled' && d >= today && d <= next30;
  });
  const taxNext30 = tax.filter(x => {
    const d = new Date(x.due_date);
    return d >= today && d <= next30;
  });

  const arSum = arNext30.reduce((s, x) => s + x.amount, 0);
  const apSum = apNext30.reduce((s, x) => s + x.amount, 0);
  const taxSum = taxNext30.reduce((s, x) => s + x.amount, 0);
  const minBalance30d = Math.min(...daily.slice(0, 30).map(d => d.ending_balance));
  const minDay = daily.slice(0, 30).find(d => d.ending_balance === minBalance30d);

  // Alerts
  const alerts = [];
  if (minBalance30d < 5_000_000) {
    alerts.push({ level: 'danger', msg: `30日以内に残高が ${yen(minBalance30d)} まで低下します（${dateJP(minDay.date)}）` });
  } else if (minBalance30d < 15_000_000) {
    alerts.push({ level: 'warn', msg: `30日以内の最低残高は ${yen(minBalance30d)}（${dateJP(minDay.date)}）。注意水準です` });
  }
  if (neutral.totals.min_balance < 0) {
    alerts.push({ level: 'danger', msg: `中立シナリオで12ヶ月以内に残高がマイナスになります（${neutral.totals.min_balance_month}: ${yen(neutral.totals.min_balance)}）` });
  }
  if (taxSum > 3_000_000) {
    alerts.push({ level: 'warn', msg: `今後30日の税金支払予定が ${yen(taxSum)} あります` });
  }

  const srcInfo = [];
  if (state.bankAccountsSource) srcInfo.push({src: state.bankAccountsSource, lbl: '銀行口座'});
  if (state.arSource) srcInfo.push({src: state.arSource, lbl: 'AR'});
  if (state.apSource) srcInfo.push({src: state.apSource, lbl: 'AP'});
  c.innerHTML = `
    ${alerts.map(a => `<div class="alert ${a.level}">${a.msg}</div>`).join('')}
    ${homePageSourceLine()}

    <div class="kpis">
      <div class="kpi-card">
        <div class="kpi-label">現預金合計</div>
        <div class="kpi-value">${yen(totalBank)}</div>
        <div class="kpi-sub">${banks.length}口座 + 現金</div>
      </div>
      <div class="kpi-card ${minBalance30d < 5_000_000 ? 'kpi-danger' : (minBalance30d < 15_000_000 ? 'kpi-warn' : '')}">
        <div class="kpi-label">30日以内の最低残高</div>
        <div class="kpi-value">${yen(minBalance30d)}</div>
        <div class="kpi-sub">${minDay ? dateJP(minDay.date) : '--'}</div>
      </div>
      <div class="kpi-card kpi-ok">
        <div class="kpi-label">30日の入金予定</div>
        <div class="kpi-value">${yen(arSum)}</div>
        <div class="kpi-sub">${arNext30.length}件の請求書</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">30日の支払予定</div>
        <div class="kpi-value">${yen(apSum + taxSum)}</div>
        <div class="kpi-sub">買掛 ${apNext30.length}件・税金 ${taxNext30.length}件</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">人件費対売上比率（年間）</div>
        <div class="kpi-value">${pct(labor.labor_to_revenue_ratio, 1)}</div>
        <div class="kpi-sub">従業員 ${labor.employee_count}名</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>残高推移（3シナリオ × 12ヶ月）</h2></div>
        <div class="chart-wrap"><canvas id="home-balance-chart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><h2>日次キャッシュフロー（向こう30日）</h2></div>
        <div class="chart-wrap"><canvas id="home-daily-chart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2>直近の重要イベント（次の30日）</h2>
        <span class="meta">入金・支払・税金・賞与</span>
      </div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>日付</th><th>区分</th><th style="text-align:left">内容</th><th>金額</th></tr></thead>
          <tbody>${renderUpcomingEvents(arNext30, apNext30, taxNext30)}</tbody>
        </table>
      </div>
    </div>
  `;

  // Charts
  const months = neutral.forecast_months;
  makeChart($('#home-balance-chart'), 'home-balance', {
    type: 'line',
    data: {
      labels: months,
      datasets: [
        { label: '楽観', data: fc.scenarios.optimistic.rows.map(r => r.ending_balance),
          borderColor: '#10b981', backgroundColor: '#10b98120', tension: 0.25, borderWidth: 2 },
        { label: '中立', data: neutral.rows.map(r => r.ending_balance),
          borderColor: '#001338', backgroundColor: '#00133820', tension: 0.25, borderWidth: 2.5 },
        { label: '悲観', data: fc.scenarios.pessimistic.rows.map(r => r.ending_balance),
          borderColor: '#b91c1c', backgroundColor: '#b91c1c20', tension: 0.25, borderWidth: 2 },
      ],
    },
    options: chartOpts(),
  });

  const days30 = daily.slice(0, 30);
  makeChart($('#home-daily-chart'), 'home-daily', {
    type: 'bar',
    data: {
      labels: days30.map(d => d.date.slice(5)),
      datasets: [
        { label: '入金', data: days30.map(d => d.inflow), backgroundColor: '#10b981', stack: 'flow' },
        { label: '支払', data: days30.map(d => -d.outflow), backgroundColor: '#b91c1c', stack: 'flow' },
        { label: '残高', data: days30.map(d => d.ending_balance),
          type: 'line', borderColor: '#E5C76E', backgroundColor: '#E5C76E20',
          borderWidth: 2, yAxisID: 'y1', pointRadius: 2 },
      ],
    },
    options: {
      ...chartOpts(),
      scales: {
        y: { ticks: { callback: v => yen(v) } },
        y1: { position: 'right', ticks: { callback: v => yen(v) }, grid: { drawOnChartArea: false } },
      },
    },
  });
}

function renderUpcomingEvents(ar, ap, tax) {
  const events = [];
  ar.forEach(x => events.push({ date: x.due_date, type: 'inflow',
    label: `入金: ${x.customer} (${x.invoice_no})`, amount: x.amount }));
  ap.forEach(x => events.push({ date: x.due_date, type: 'outflow',
    label: `支払: ${x.vendor} (${x.category})`, amount: -x.amount }));
  tax.forEach(x => events.push({ date: x.due_date, type: 'tax',
    label: `税金: ${x.name}`, amount: -x.amount }));
  events.sort((a, b) => a.date.localeCompare(b.date));
  if (events.length === 0)
    return '<tr><td colspan="4" class="empty-state">予定なし</td></tr>';
  return events.map(e => {
    const pillClass = e.type === 'inflow' ? 'ok' : (e.type === 'tax' ? 'warn' : 'info');
    const pillLabel = e.type === 'inflow' ? '入金' : (e.type === 'tax' ? '税金' : '支払');
    return `<tr>
      <td>${dateJP(e.date)}</td>
      <td><span class="pill ${pillClass}">${pillLabel}</span></td>
      <td style="text-align:left">${e.label}</td>
      <td class="${e.amount < 0 ? 'neg' : 'pos'}">${yen(e.amount)}</td>
    </tr>`;
  }).join('');
}

function homePageSourceLine() {
  const map = {
    '銀行口座': state.bankAccountsSource,
    '入出金予定': state.arSource,
    '日次予測': state.dailySource,
    '人件費': state.laborSource,
  };
  const items = Object.entries(map).filter(([_, v]) => v);
  if (items.length === 0) return '';
  return `<div style="margin-bottom:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:12px">
    <span style="color:#6b7280">データソース:</span>
    ${items.map(([lbl, src]) => {
      let cls, txt;
      if (src === 'freee') { cls = 'ok'; txt = 'freee実データ'; }
      else if (src === 'template') { cls = 'gold'; txt = 'テンプレート'; }
      else if (src === 'empty') { cls = 'info'; txt = '（手動登録）'; }
      else { cls = 'warn'; txt = 'Mockデータ'; }
      return `<span class="pill ${cls}">${lbl}: ${txt}</span>`;
    }).join('')}
  </div>`;
}

function sourceBadge(source, warning) {
  if (!source) return '';
  let label, pillCls;
  if (source === 'freee') { label = 'freeeから取得'; pillCls = 'ok'; }
  else if (source === 'template') { label = 'テンプレート'; pillCls = 'gold'; }
  else if (source === 'empty') { label = 'データなし'; pillCls = 'info'; }
  else { label = 'Mockデータ'; pillCls = 'warn'; }
  let html = `<div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <span class="pill ${pillCls}">${label}</span>`;
  if (warning) html += `<span style="font-size:12px;color:#6b7280">${warning}</span>`;
  html += '</div>';
  return html;
}

function chartOpts() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
      tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${yen(c.parsed.y)}` } },
    },
    scales: { y: { ticks: { callback: v => yen(v) } } },
  };
}

// ============================================================
// Page: Monthly (12-month CF)
// ============================================================

async function renderMonthly(c) {
  const fc = await getForecast();
  c.innerHTML = `
    <div class="card">
      <div class="card-header">
        <h2>月次CF予測表</h2>
        <div class="scenario-selector">
          <label>シナリオ:</label>
          <select id="mo-scenario-select">
            <option value="optimistic">楽観</option>
            <option value="neutral" selected>中立</option>
            <option value="pessimistic">悲観</option>
          </select>
        </div>
      </div>
      <div class="table-scroll" id="mo-table-wrap"></div>
    </div>
    <div class="card">
      <div class="card-header"><h2>3シナリオ サマリー</h2></div>
      <div class="table-scroll"><table class="data-table" id="mo-summary"></table></div>
    </div>
  `;
  $('#mo-scenario-select').value = state.selectedScenario;
  $('#mo-scenario-select').addEventListener('change', e => {
    state.selectedScenario = e.target.value;
    renderMonthlyTable();
  });
  renderMonthlyTable();
  renderMonthlySummary();
}

function renderMonthlyTable() {
  const fc = state.forecast;
  const scenario = fc.scenarios[state.selectedScenario];
  const months = scenario.forecast_months;
  const rows = scenario.rows;
  let thead = '<thead><tr><th>項目</th>';
  for (const m of months) thead += `<th>${m}</th>`;
  thead += '<th>合計</th></tr></thead>';

  const rowDefs = [
    { key: 'cash_in_sales', label: '売上入金' },
    { key: 'cash_out_purchase', label: '仕入・経費支払' },
    { key: 'cash_out_salary', label: '給与支払' },
    { key: 'loan_interest', label: '支払利息' },
    { key: 'adjustment_operating', label: '手動調整(営業)' },
    { key: 'operating_cf', label: '営業CF', cls: 'row-total' },
    { key: 'adjustment_investing', label: '手動調整(投資)' },
    { key: 'investing_cf', label: '投資CF', cls: 'row-total' },
    { key: 'loan_principal', label: '借入元金返済' },
    { key: 'adjustment_financing', label: '手動調整(財務)' },
    { key: 'financing_cf', label: '財務CF', cls: 'row-total' },
    { key: 'net_cf', label: '純CF', cls: 'row-net' },
    { key: 'ending_balance', label: '月末予想残高', cls: 'row-balance' },
  ];
  let body = '<tbody>';
  for (const def of rowDefs) {
    body += `<tr class="${def.cls || ''}"><td>${def.label}</td>`;
    let sum = 0;
    for (const r of rows) {
      const v = r[def.key];
      const cls = v < 0 ? 'neg' : '';
      body += `<td class="${cls}">${yen(v)}</td>`;
      if (def.key !== 'ending_balance') sum += (v || 0);
    }
    const last = def.key === 'ending_balance' ? rows[rows.length - 1].ending_balance : sum;
    body += `<td class="${last < 0 ? 'neg' : ''}"><strong>${yen(last)}</strong></td></tr>`;
  }
  body += '</tbody>';
  $('#mo-table-wrap').innerHTML = `<table class="data-table">${thead}${body}</table>`;
}

function renderMonthlySummary() {
  const fc = state.forecast;
  const labels = { optimistic: '楽観', neutral: '中立', pessimistic: '悲観' };
  let html = `<thead><tr><th>シナリオ</th><th>営業CF合計</th><th>投資CF合計</th><th>財務CF合計</th><th>純CF</th><th>12ヶ月後残高</th><th>最低残高月</th></tr></thead><tbody>`;
  for (const k of ['optimistic', 'neutral', 'pessimistic']) {
    const t = fc.scenarios[k].totals;
    html += `<tr>
      <td style="text-align:left;font-weight:600">${labels[k]}</td>
      <td class="${t.operating_cf < 0 ? 'neg' : ''}">${yen(t.operating_cf)}</td>
      <td class="${t.investing_cf < 0 ? 'neg' : ''}">${yen(t.investing_cf)}</td>
      <td class="${t.financing_cf < 0 ? 'neg' : ''}">${yen(t.financing_cf)}</td>
      <td class="${t.net_cf < 0 ? 'neg' : ''}"><strong>${yen(t.net_cf)}</strong></td>
      <td class="${t.ending_balance < 0 ? 'neg' : ''}"><strong>${yen(t.ending_balance)}</strong></td>
      <td class="${t.min_balance < 0 ? 'neg' : ''}">${t.min_balance_month} (${yen(t.min_balance)})</td>
    </tr>`;
  }
  html += '</tbody>';
  $('#mo-summary').innerHTML = html;
}

// ============================================================
// Page: Daily CF
// ============================================================

async function renderDaily(c) {
  const daily = await getDaily();
  c.innerHTML = `${sourceBadge(state.dailySource, state.dailyWarning)}
    
    <div class="kpis">
      <div class="kpi-card">
        <div class="kpi-label">期首残高</div>
        <div class="kpi-value">${yen(daily[0]?.ending_balance - (daily[0]?.net || 0))}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">30日後残高</div>
        <div class="kpi-value">${yen(daily[29]?.ending_balance)}</div>
      </div>
      <div class="kpi-card kpi-ok">
        <div class="kpi-label">30日合計 入金</div>
        <div class="kpi-value">${yen(daily.slice(0, 30).reduce((s, d) => s + d.inflow, 0))}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">30日合計 支払</div>
        <div class="kpi-value">${yen(daily.slice(0, 30).reduce((s, d) => s + d.outflow, 0))}</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h2>日次残高推移（60日）</h2></div>
      <div class="chart-wrap tall"><canvas id="daily-chart"></canvas></div>
    </div>

    <div class="card">
      <div class="card-header"><h2>日次明細</h2></div>
      <div class="table-scroll" style="max-height:700px">
        <table class="data-table">
          <thead><tr><th>日付</th><th>曜</th><th>入金</th><th>支払</th><th>純額</th><th>月末残高</th><th style="text-align:left">明細</th></tr></thead>
          <tbody>${daily.map(d => {
            const itemsTxt = [...d.inflow_items.map(i => `+${num(i.amount)} ${i.label}`),
                              ...d.outflow_items.map(i => `-${num(i.amount)} ${i.label}`)].join(' / ');
            const cls = d.is_weekend ? 'row-weekend' : '';
            return `<tr class="${cls}">
              <td>${d.date.slice(5)}</td>
              <td>${d.weekday}</td>
              <td class="pos">${d.inflow ? yen(d.inflow) : '--'}</td>
              <td class="neg">${d.outflow ? yen(d.outflow) : '--'}</td>
              <td class="${d.net < 0 ? 'neg' : 'pos'}">${yen(d.net)}</td>
              <td class="${d.ending_balance < 0 ? 'neg' : ''}"><strong>${yen(d.ending_balance)}</strong></td>
              <td style="text-align:left;font-size:11px;color:#6b7280">${itemsTxt}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
    </div>
  `;

  makeChart($('#daily-chart'), 'daily', {
    type: 'bar',
    data: {
      labels: daily.map(d => d.date.slice(5)),
      datasets: [
        { label: '入金', data: daily.map(d => d.inflow), backgroundColor: '#10b981', stack: 's' },
        { label: '支払', data: daily.map(d => -d.outflow), backgroundColor: '#b91c1c', stack: 's' },
        { label: '残高', data: daily.map(d => d.ending_balance), type: 'line',
          borderColor: '#001338', backgroundColor: '#00133820', borderWidth: 2.5, yAxisID: 'y1', pointRadius: 1 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top' },
                 tooltip: { callbacks: { label: c => `${c.dataset.label}: ${yen(c.parsed.y)}` } } },
      scales: {
        y: { stacked: true, ticks: { callback: v => yen(v) } },
        y1: { position: 'right', ticks: { callback: v => yen(v) }, grid: { drawOnChartArea: false } },
      },
    },
  });
}

// ============================================================
// Page: Receivables (AR)
// ============================================================

async function renderReceivables(c) {
  const ar = await getAR();
  const scheduled = ar.filter(x => x.status === 'scheduled');
  const totalSched = scheduled.reduce((s, x) => s + x.amount, 0);
  const byCust = {};
  scheduled.forEach(x => { byCust[x.customer] = (byCust[x.customer] || 0) + x.amount; });
  const topCusts = Object.entries(byCust).sort((a, b) => b[1] - a[1]).slice(0, 10);

  c.innerHTML = `${sourceBadge(state.arSource, state.arWarning)}
    
    <div class="kpis">
      <div class="kpi-card"><div class="kpi-label">未入金合計</div><div class="kpi-value">${yen(totalSched)}</div><div class="kpi-sub">${scheduled.length}件</div></div>
      <div class="kpi-card kpi-ok"><div class="kpi-label">今月入金予定</div><div class="kpi-value">${yen(monthFilter(scheduled, 0))}</div></div>
      <div class="kpi-card"><div class="kpi-label">来月入金予定</div><div class="kpi-value">${yen(monthFilter(scheduled, 1))}</div></div>
      <div class="kpi-card"><div class="kpi-label">2ヶ月先</div><div class="kpi-value">${yen(monthFilter(scheduled, 2))}</div></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>取引先別 未入金トップ10</h2></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th style="text-align:left">取引先</th><th>未入金額</th><th>比率</th></tr></thead>
            <tbody>${topCusts.map(([n, a]) => `<tr><td style="text-align:left">${n}</td><td>${yen(a)}</td><td>${pct(a / totalSched * 100, 1)}</td></tr>`).join('')}</tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>サイト別構成</h2></div>
        <div class="chart-wrap short"><canvas id="ar-term-chart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h2>請求書明細</h2><span class="meta">過去30日〜先90日</span></div>
      <div class="table-scroll" style="max-height:600px">
        <table class="data-table">
          <thead><tr><th>請求書No</th><th style="text-align:left">取引先</th><th>発行日</th><th>入金予定日</th><th>サイト</th><th>金額</th><th>ステータス</th></tr></thead>
          <tbody>${ar.map(x => `<tr class="${x.status==='paid'?'muted':''}">
            <td>${x.invoice_no}</td>
            <td style="text-align:left">${x.customer}</td>
            <td>${dateJP(x.issue_date)}</td>
            <td>${dateJP(x.due_date)}</td>
            <td>${x.payment_term_days}日</td>
            <td>${yen(x.amount)}</td>
            <td><span class="pill ${x.status==='paid'?'ok':'info'}">${x.status==='paid'?'入金済':'入金予定'}</span></td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    </div>
  `;

  const termBuckets = { '30日': 0, '45日': 0, '60日': 0, '90日': 0 };
  scheduled.forEach(x => { const k = x.payment_term_days + '日'; if (termBuckets[k] !== undefined) termBuckets[k] += x.amount; });
  makeChart($('#ar-term-chart'), 'ar-term', {
    type: 'doughnut',
    data: { labels: Object.keys(termBuckets), datasets: [{
      data: Object.values(termBuckets),
      backgroundColor: ['#001338', '#E5C76E', '#10b981', '#b91c1c'],
    }] },
    options: { responsive: true, maintainAspectRatio: false,
               plugins: { tooltip: { callbacks: { label: c => `${c.label}: ${yen(c.parsed)}` } } } },
  });
}

function monthFilter(items, monthOffset) {
  const today = new Date();
  const target = new Date(today.getFullYear(), today.getMonth() + monthOffset, 1);
  const next = new Date(today.getFullYear(), today.getMonth() + monthOffset + 1, 1);
  return items.filter(x => {
    const d = new Date(x.due_date || x.pay_date);
    return d >= target && d < next;
  }).reduce((s, x) => s + (x.amount || 0), 0);
}

// ============================================================
// Page: Payables (AP)
// ============================================================

async function renderPayables(c) {
  const ap = await getAP();
  const scheduled = ap.filter(x => x.status === 'scheduled');
  const totalSched = scheduled.reduce((s, x) => s + x.amount, 0);
  const byVendor = {};
  const byCategory = {};
  scheduled.forEach(x => {
    byVendor[x.vendor] = (byVendor[x.vendor] || 0) + x.amount;
    byCategory[x.category] = (byCategory[x.category] || 0) + x.amount;
  });
  const topV = Object.entries(byVendor).sort((a, b) => b[1] - a[1]).slice(0, 10);

  c.innerHTML = `${sourceBadge(state.apSource, state.apWarning)}
    
    <div class="kpis">
      <div class="kpi-card"><div class="kpi-label">未払合計</div><div class="kpi-value">${yen(totalSched)}</div><div class="kpi-sub">${scheduled.length}件</div></div>
      <div class="kpi-card"><div class="kpi-label">今月支払予定</div><div class="kpi-value">${yen(monthFilter(scheduled, 0))}</div></div>
      <div class="kpi-card"><div class="kpi-label">来月支払予定</div><div class="kpi-value">${yen(monthFilter(scheduled, 1))}</div></div>
      <div class="kpi-card"><div class="kpi-label">2ヶ月先</div><div class="kpi-value">${yen(monthFilter(scheduled, 2))}</div></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>取引先別 未払トップ10</h2></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th style="text-align:left">取引先</th><th>未払額</th><th>比率</th></tr></thead>
            <tbody>${topV.map(([n, a]) => `<tr><td style="text-align:left">${n}</td><td>${yen(a)}</td><td>${pct(a / totalSched * 100, 1)}</td></tr>`).join('')}</tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>科目別構成</h2></div>
        <div class="chart-wrap short"><canvas id="ap-cat-chart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h2>支払明細</h2><span class="meta">過去15日〜先90日</span></div>
      <div class="table-scroll" style="max-height:600px">
        <table class="data-table">
          <thead><tr><th>請求No</th><th style="text-align:left">取引先</th><th style="text-align:left">区分</th><th>請求日</th><th>支払予定日</th><th>金額</th><th>ステータス</th></tr></thead>
          <tbody>${ap.map(x => `<tr class="${x.status==='paid'?'muted':''}">
            <td>${x.bill_no}</td>
            <td style="text-align:left">${x.vendor}</td>
            <td style="text-align:left">${x.category}</td>
            <td>${dateJP(x.issue_date)}</td>
            <td>${dateJP(x.due_date)}</td>
            <td>${yen(x.amount)}</td>
            <td><span class="pill ${x.status==='paid'?'ok':'info'}">${x.status==='paid'?'支払済':'支払予定'}</span></td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    </div>
  `;
  makeChart($('#ap-cat-chart'), 'ap-cat', {
    type: 'doughnut',
    data: { labels: Object.keys(byCategory), datasets: [{
      data: Object.values(byCategory),
      backgroundColor: ['#001338', '#E5C76E', '#10b981', '#b91c1c', '#2563eb', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899'],
    }] },
    options: { responsive: true, maintainAspectRatio: false,
               plugins: { tooltip: { callbacks: { label: c => `${c.label}: ${yen(c.parsed)}` } } } },
  });
}

// ============================================================
// Page: Tax calendar
// ============================================================

async function renderTax(c) {
  c.innerHTML = '<div class="empty-state"><div class="icon">⌛</div><div>事業計画P/Lから税額を算出中...</div></div>';
  let resp;
  try {
    resp = await fetch('/api/tax-calendar').then(x => x.json());
  } catch (e) {
    c.innerHTML = `<div class="alert danger">取得失敗: ${e.message}</div>`;
    return;
  }
  const tax = resp.data || [];
  const warning = resp.warning;
  const source = resp.source || 'empty';

  const today = new Date();
  const in90 = new Date(today.getTime() + 90 * 86400000);
  const totalNext90 = tax.filter(x => {
    const d = new Date(x.due_date);
    return d >= today && d <= in90;
  }).reduce((s, x) => s + (x.amount || 0), 0);

  // 名称から種別を推定し色分け
  function kindOf(name) {
    if (name.includes('法人税')) return {label:'法人税等', color:'#001338'};
    if (name.includes('消費税')) return {label:'消費税', color:'#E5C76E'};
    if (name.includes('源泉')) return {label:'源泉所得税', color:'#10b981'};
    if (name.includes('住民')) return {label:'住民税', color:'#2563eb'};
    if (name.includes('社会保険') || name.includes('社保')) return {label:'社会保険料', color:'#8b5cf6'};
    return {label:'その他', color:'#6b7280'};
  }

  // 種別ごと年間合計
  const byKind = {};
  tax.forEach(x => {
    const k = kindOf(x.name || '').label;
    byKind[k] = (byKind[k] || 0) + (x.amount || 0);
  });

  c.innerHTML = `${sourceBadge(source, warning)}

    <div class="kpis">
      <div class="kpi-card kpi-warn">
        <div class="kpi-label">先90日の税金合計</div>
        <div class="kpi-value">${yen(totalNext90)}</div>
      </div>
      ${Object.entries(byKind).map(([k, v]) => `
        <div class="kpi-card">
          <div class="kpi-label">${k}（先12ヶ月）</div>
          <div class="kpi-value" style="font-size:18px">${yen(v)}</div>
        </div>
      `).join('')}
    </div>

    <div class="hint">事業計画P/L（入金/支払予測ベース・税抜会計）から自動計算。実効税率30%・消費税10%・源泉5%・住民税6%を仮定した概算です。</div>

    <div class="card">
      <div class="card-header"><h2>税金支払スケジュール</h2></div>
      <div class="table-scroll" style="max-height:700px">
        <table class="data-table">
          <thead><tr><th>支払日</th><th>区分</th><th style="text-align:left">項目</th><th>金額</th><th style="text-align:left">算出根拠</th></tr></thead>
          <tbody>${tax.length === 0 ? '<tr><td colspan="5" style="text-align:center;color:#6b7280">該当する税金支払予定はありません</td></tr>' :
            tax.map(x => {
              const k = kindOf(x.name || '');
              const isPast = new Date(x.due_date) < today;
              return `<tr class="${isPast ? 'muted' : ''}">
                <td>${dateJP(x.due_date)}</td>
                <td><span class="pill" style="background:${k.color}; color:#fff">${k.label}</span></td>
                <td style="text-align:left">${x.name}</td>
                <td><strong>${yen(x.amount)}</strong></td>
                <td style="text-align:left;font-size:11px;color:#6b7280">${x.note || ''}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ============================================================
// Page: Banks
// ============================================================

async function renderBanks(c) {
  const banks = await getBankAccounts();
  const excluded = state.bankAccountsExcluded || [];
  const total = banks.reduce((s, b) => s + (b.balance || 0), 0);
  const excludedTotal = excluded.reduce((s, b) => s + (b.balance || 0), 0);
  const typeLabels = { current: '当座', savings: '普通', cash: '現金', credit: 'クレジット', other: 'その他' };

  c.innerHTML = `${sourceBadge(state.bankAccountsSource, state.bankAccountsWarning)}
    
    <div class="kpis">
      <div class="kpi-card">
        <div class="kpi-label">現預金合計</div>
        <div class="kpi-value">${yen(total)}</div>
        <div class="kpi-sub">${banks.length}口座（負債系除外後）</div>
      </div>
      ${excluded.length > 0 ? `
      <div class="kpi-card">
        <div class="kpi-label">除外口座合計（参考）</div>
        <div class="kpi-value" style="color:#6b7280">${yen(excludedTotal)}</div>
        <div class="kpi-sub">${excluded.length}口座（借入金/預り金等）</div>
      </div>` : ''}
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>口座別残高</h2></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th style="text-align:left">口座名</th><th style="text-align:left">種別</th><th style="text-align:left">支店</th><th>残高</th><th>比率</th></tr></thead>
            <tbody>${banks.map(b => `<tr>
              <td style="text-align:left">${b.name}</td>
              <td style="text-align:left"><span class="pill gold">${typeLabels[b.type] || b.type}</span></td>
              <td style="text-align:left">${b.branch || '--'}</td>
              <td><strong>${yen(b.balance)}</strong></td>
              <td>${pct(b.balance / total * 100, 1)}</td>
            </tr>`).join('')}
            <tr class="row-balance"><td style="text-align:left"><strong>合計</strong></td><td></td><td></td><td><strong>${yen(total)}</strong></td><td>100.0%</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>残高構成</h2></div>
        <div class="chart-wrap"><canvas id="bank-chart"></canvas></div>
      </div>
    </div>
  `;
  makeChart($('#bank-chart'), 'bank', {
    type: 'doughnut',
    data: { labels: banks.map(b => b.name), datasets: [{
      data: banks.map(b => b.balance),
      backgroundColor: ['#001338', '#E5C76E', '#10b981', '#b91c1c', '#2563eb'],
    }] },
    options: { responsive: true, maintainAspectRatio: false,
               plugins: { tooltip: { callbacks: { label: c => `${c.label}: ${yen(c.parsed)}` } } } },
  });

  if (excluded.length > 0) {
    const wrap = document.createElement('div');
    wrap.className = 'card';
    wrap.innerHTML = `
      <div class="card-header">
        <h2>除外口座（現預金合計に含めない）</h2>
        <span class="meta">役員借入金・預り金・クレジット等</span>
      </div>
      <div class="hint">名前に「借入金」「預り金」「未払」「クレジット」「ローン」を含む口座は、freee上は walletable ですが資金繰りでは現預金として扱わないため除外しています。</div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th style="text-align:left">口座名</th><th>残高</th><th style="text-align:left">理由</th></tr></thead>
          <tbody>${excluded.map(b => `<tr>
            <td style="text-align:left">${b.name}</td>
            <td class="${b.balance < 0 ? 'neg' : ''}">${yen(b.balance)}</td>
            <td style="text-align:left;font-size:11px;color:#6b7280">${b.excluded_reason || ''}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    `;
    c.appendChild(wrap);
  }
}

// ============================================================
// Page: Loans
// ============================================================

async function renderLoans(c) {
  const loans = await getLoans();
  c.innerHTML = `
    <div class="kpis">
      <div class="kpi-card"><div class="kpi-label">借入残高合計</div><div class="kpi-value">${yen(loans.reduce((s, l) => s + l.outstanding, 0))}</div><div class="kpi-sub">${loans.length}本</div></div>
      <div class="kpi-card"><div class="kpi-label">月次元金返済合計</div><div class="kpi-value">${yen(loans.reduce((s, l) => s + (l.outstanding / Math.max(1, l.remaining_months)), 0))}</div></div>
      <div class="kpi-card"><div class="kpi-label">月次利息合計(概算)</div><div class="kpi-value">${yen(loans.reduce((s, l) => s + (l.outstanding * l.annual_rate / 12), 0))}</div></div>
    </div>
    <div class="card">
      <div class="card-header"><h2>借入金一覧</h2>
        <button class="btn btn-primary btn-small" id="btn-add-loan">＋ 借入を追加</button>
      </div>
      <div class="table-scroll">
        <table class="data-table" id="loans-table">
          <thead><tr><th style="text-align:left">借入名</th><th>残高</th><th>年利</th><th>残月数</th><th>据置月数</th><th>返済日</th><th>返済方式</th><th></th></tr></thead>
          <tbody>${loansTableBody(loans)}</tbody>
        </table>
      </div>
      <div class="card-footer"><button class="btn btn-primary" id="btn-save-loans">借入情報を保存</button></div>
    </div>
  `;
  $('#btn-add-loan').addEventListener('click', () => {
    state.loans.push({ name: '新規借入', outstanding: 10000000, annual_rate: 0.015,
                       remaining_months: 60, grace_months: 0, repayment_day: 31, method: 'equal_principal' });
    $('#loans-table tbody').innerHTML = loansTableBody(state.loans);
  });
  $('#btn-save-loans').addEventListener('click', async () => {
    const updated = [];
    $$('#loans-table tbody tr[data-loan-index]').forEach(tr => {
      updated.push({
        name: tr.querySelector('.loan-name').value,
        outstanding: parseInt(tr.querySelector('.loan-outstanding').value || 0),
        annual_rate: parseFloat(tr.querySelector('.loan-rate').value || 0),
        remaining_months: parseInt(tr.querySelector('.loan-remaining').value || 0),
        grace_months: parseInt(tr.querySelector('.loan-grace').value || 0),
        repayment_day: parseInt(tr.querySelector('.loan-repday').value || 31),
        method: tr.querySelector('.loan-method').value,
      });
    });
    await fetch('/api/loans', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updated) });
    state.loans = []; state.forecast = null;
    flash('借入情報を保存しました');
    renderLoans(c);
  });
}

function loansTableBody(loans) {
  if (!loans || loans.length === 0)
    return '<tr><td colspan="8" class="empty-state">借入金が登録されていません</td></tr>';
  return loans.map((l, i) => `<tr data-loan-index="${i}">
    <td style="text-align:left"><input type="text" class="loan-name" value="${l.name || ''}" style="width:240px"/></td>
    <td><input type="number" class="loan-outstanding" value="${l.outstanding || 0}"/></td>
    <td><input type="number" step="0.001" class="loan-rate" value="${l.annual_rate || 0}" style="width:90px"/></td>
    <td><input type="number" class="loan-remaining" value="${l.remaining_months || 0}" style="width:80px"/></td>
    <td><input type="number" class="loan-grace" value="${l.grace_months || 0}" style="width:80px" min="0"/></td>
    <td><select class="loan-repday" style="width:80px">
      ${[5,10,15,20,25,27,31].map(d => `<option value="${d}" ${(l.repayment_day||31)===d?'selected':''}>${d===31?'末日':d+'日'}</option>`).join('')}
    </select></td>
    <td><select class="loan-method">
      <option value="equal_principal" ${l.method==='equal_principal'?'selected':''}>元金均等</option>
      <option value="equal_payment" ${l.method==='equal_payment'?'selected':''}>元利均等</option>
    </select></td>
    <td><button class="btn btn-danger btn-small" onclick="window._rmLoan(${i})">削除</button></td>
  </tr>`).join('');
}
window._rmLoan = function(i) {
  if (!confirm('この借入を削除しますか？')) return;
  state.loans.splice(i, 1);
  $('#loans-table tbody').innerHTML = loansTableBody(state.loans);
};

// ============================================================
// Page: Organization Chart (freee人事労務マスタ連携)
// ============================================================

async function renderOrgChart(c) {
  const r = await fetch('/api/org-chart').then(x => x.json());
  window._orgChart = r;

  const formatYen = (n) => '¥' + (n || 0).toLocaleString('ja-JP');

  // 経営層カード
  const execCards = (r.executives || []).map((e, i) => `
    <div class="org-node org-exec" onclick="window._showOrgMember(${e.id})" data-id="${e.id}">
      <div class="org-exec-title">${e.position}</div>
      <div class="org-exec-name">${e.name}</div>
      <div class="org-exec-meta">従業員番号 ${e.employee_number}</div>
    </div>`).join('');

  // 部門カード
  const deptCards = (r.departments || []).map((d, i) => {
    const mgr = d.manager;
    return `
      <div class="org-node org-dept" onclick="window._showOrgDept(${i})" data-idx="${i}">
        <div class="org-dept-name">${d.name}</div>
        <div class="org-dept-stats">
          <div><span>所属人数</span><strong>${d.member_count}名</strong></div>
          <div><span>部門責任者</span><strong>${mgr ? mgr.name : '—'}</strong></div>
          <div><span>月給合計</span><strong>${formatYen(d.total_salary)}</strong></div>
        </div>
        <div class="org-dept-cta">クリックでメンバー一覧 ›</div>
      </div>`;
  }).join('');

  c.innerHTML = `
    ${sourceBadge('mock', null)}
    <div class="info-banner" style="background:#eff6ff;border:1px solid #bfdbfe;padding:12px 16px;border-radius:8px;margin-bottom:16px;color:#1e40af;">
      <strong>📊 freee人事労務 組織マスタ連携</strong> ・ ${r.company_name} ・ 全従業員 ${r.total_members}名
      <span style="margin-left:12px;color:#3b82f6;">部門カードをクリックすると所属メンバー・役職・月給が一覧できます</span>
    </div>

    <h3 style="margin:24px 0 12px 0;">経営層 (取締役会・執行役員)</h3>
    <div class="org-grid org-grid-exec">${execCards}</div>

    <h3 style="margin:32px 0 12px 0;">部門 (${(r.departments || []).length}部門)</h3>
    <div class="org-grid org-grid-dept">${deptCards}</div>

    <!-- detail modal -->
    <div id="org-modal" class="org-modal" hidden onclick="if(event.target.id==='org-modal') this.hidden=true;">
      <div class="org-modal-inner">
        <button class="org-modal-close" onclick="document.getElementById('org-modal').hidden=true;">×</button>
        <div id="org-modal-body"></div>
      </div>
    </div>
  `;
}

window._showOrgDept = function(idx) {
  const d = (window._orgChart.departments || [])[idx];
  if (!d) return;
  const formatYen = (n) => '¥' + (n || 0).toLocaleString('ja-JP');
  const rows = d.members.map(m => `
    <tr>
      <td>${m.employee_number}</td>
      <td><a href="#employees" onclick="setTimeout(()=>window._empShowDetail&&window._empShowDetail(${m.id-10000}),200)">${m.name}</a></td>
      <td>${m.position}</td>
      <td>${m.employment_type}</td>
      <td>${m.hire_date}</td>
      <td style="text-align:right;">${formatYen(m.monthly_salary)}</td>
    </tr>`).join('');
  document.getElementById('org-modal-body').innerHTML = `
    <h2 style="margin-top:0;">${d.name}</h2>
    <div style="color:#64748b;margin-bottom:12px;">
      所属 ${d.member_count}名 ・ 部門責任者 ${d.manager ? d.manager.name : '—'} ・
      月給合計 ${formatYen(d.total_salary)} ・ 平均月給 ${formatYen(d.avg_salary)}
    </div>
    <table class="data-table">
      <thead>
        <tr><th>従業員番号</th><th>氏名</th><th>役職</th><th>雇用形態</th><th>入社日</th><th style="text-align:right;">月給</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
  document.getElementById('org-modal').hidden = false;
};

window._showOrgMember = function(empId) {
  const e = ((window._orgChart.executives) || []).find(x => x.id === empId);
  if (!e) return;
  const formatYen = (n) => '¥' + (n || 0).toLocaleString('ja-JP');
  document.getElementById('org-modal-body').innerHTML = `
    <h2 style="margin-top:0;">${e.position} ・ ${e.name}</h2>
    <table class="data-table">
      <tr><th style="width:140px;">従業員番号</th><td>${e.employee_number}</td></tr>
      <tr><th>役職</th><td>${e.position}</td></tr>
      <tr><th>所属</th><td>${e.department || '—'}</td></tr>
      <tr><th>雇用形態</th><td>${e.employment_type}</td></tr>
      <tr><th>入社日</th><td>${e.hire_date}</td></tr>
      <tr><th>月給</th><td>${formatYen(e.monthly_salary)}</td></tr>
    </table>
    <div style="margin-top:16px;">
      <a href="#employees" onclick="setTimeout(()=>window._empShowDetail&&window._empShowDetail(${e.id-10000}),200);document.getElementById('org-modal').hidden=true;"
         class="btn btn-primary">従業員詳細を開く ›</a>
    </div>
  `;
  document.getElementById('org-modal').hidden = false;
};

// ============================================================
// Page: Employees
// ============================================================

async function renderEmployees(c) {
  const emps = await getEmployees();
  window._employees = emps;

  let sortKey = localStorage.getItem('empSortKey') || 'employee_number';
  let sortDir = localStorage.getItem('empSortDir') || 'asc';

  const COL_DEFS = [
    { key: 'employee_number', label: '従業員番号',
      val: e => { const n = parseInt(e.employee_number || e.id); return isNaN(n) ? (e.employee_number || '') : n; },
      type: 'num' },
    { key: 'name', label: '氏名', val: e => e.name || '', type: 'str' },
    { key: 'department', label: '部門', val: e => e.department || '', type: 'str' },
    { key: 'position', label: '役職', val: e => e.position || '', type: 'str' },
    { key: 'employment_type', label: '雇用形態', val: e => e.employment_type || '', type: 'str' },
    { key: 'monthly_salary', label: '月給', val: e => Number(e.monthly_salary || 0), type: 'num' },
    { key: 'commute_allowance', label: '交通費', val: e => Number(e.commute_allowance || 0), type: 'num' },
    { key: 'annual_salary', label: '年収', val: e => Number(e.annual_salary || 0), type: 'num' },
    { key: 'hire_date', label: '入社日', val: e => e.hire_date || '', type: 'str' },
  ];

  const sortEmps = (arr) => {
    const def = COL_DEFS.find(d => d.key === sortKey) || COL_DEFS[0];
    return arr.slice().sort((a, b) => {
      const va = def.val(a), vb = def.val(b);
      let cmp;
      if (def.type === 'num') {
        const na = typeof va === 'number' ? va : 0;
        const nb = typeof vb === 'number' ? vb : 0;
        cmp = na - nb;
      } else {
        cmp = String(va).localeCompare(String(vb), 'ja');
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  };

  const renderBody = () => {
    const totalMonthly = emps.reduce((s, e) => s + (e.monthly_salary || 0), 0);
    const totalCommute = emps.reduce((s, e) => s + (e.commute_allowance || 0), 0);
    const totalAnnual = emps.reduce((s, e) => s + (e.annual_salary || 0), 0);
    const avgMonthly = emps.length > 0 ? Math.round(totalMonthly / emps.length) : 0;
    const sorted = sortEmps(emps);

    const headerCell = (def) => {
      const isActive = sortKey === def.key;
      const arrow = isActive
        ? `<span style="color:#E5C76E;margin-left:4px">${sortDir === 'asc' ? '▲' : '▼'}</span>`
        : `<span style="color:#9ca3af;margin-left:4px;opacity:0.5">⇅</span>`;
      const style = `cursor:pointer;user-select:none;text-align:center;${isActive ? 'background:#001a5e' : ''}`;
      return `<th class="emp-sort-th" data-sort-key="${def.key}" style="${style}" title="クリックでソート">${def.label}${arrow}</th>`;
    };

    c.innerHTML = `${sourceBadge(state.employeesSource, state.employeesWarning)}

      <div class="kpis">
        <div class="kpi-card"><div class="kpi-label">従業員数</div><div class="kpi-value">${emps.length}名</div></div>
        <div class="kpi-card kpi-ok"><div class="kpi-label">月給合計</div><div class="kpi-value">${yen(totalMonthly)}</div></div>
        <div class="kpi-card"><div class="kpi-label">平均月給</div><div class="kpi-value">${yen(avgMonthly)}</div></div>
        <div class="kpi-card"><div class="kpi-label">年収合計</div><div class="kpi-value">${yen(totalAnnual)}</div></div>
        <div class="kpi-card"><div class="kpi-label">交通費合計(月)</div><div class="kpi-value">${yen(totalCommute)}</div></div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2>従業員一覧</h2>
        </div>
        <div class="hint">列ヘッダをクリックでソート。各行の「詳細」ボタンで入社手続き・面談履歴・評価等を表示。</div>
        <div class="table-scroll" style="max-height:700px">
          <table class="data-table emp-table">
            <thead><tr>${COL_DEFS.map(headerCell).join('')}<th>操作</th></tr></thead>
            <tbody>${sorted.map((e, sIdx) => `<tr>
              <td>${e.employee_number || e.id}</td>
              <td>${e.name}</td>
              <td>${e.department || '<span style="color:#9ca3af">—</span>'}</td>
              <td>${e.position || '<span style="color:#9ca3af">—</span>'}</td>
              <td><span class="pill ${e.employment_type==='パート'?'info':'gold'}">${e.employment_type}</span></td>
              <td>${yen(e.monthly_salary)}</td>
              <td>${yen(e.commute_allowance || 0)}</td>
              <td>${yen(e.annual_salary)}</td>
              <td>${dateJP(e.hire_date)}</td>
              <td><button class="btn btn-secondary btn-small" onclick="window._empShowDetail(${emps.indexOf(e)})">詳細</button></td>
            </tr>`).join('')}</tbody>
          </table>
        </div>
      </div>

      <div id="emp-detail-wrap"></div>
    `;
    document.querySelectorAll('.emp-sort-th').forEach(th => {
      th.addEventListener('click', () => {
        const k = th.dataset.sortKey;
        if (sortKey === k) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else { sortKey = k; sortDir = 'asc'; }
        localStorage.setItem('empSortKey', sortKey);
        localStorage.setItem('empSortDir', sortDir);
        renderBody();
      });
    });
  };
  renderBody();
}

// 従業員詳細パネル (編集対応)
window._empShowDetail = async function(idx) {
  const e = (window._employees || [])[idx];
  if (!e) { alert('従業員データが見つかりません'); return; }
  const wrap = document.getElementById('emp-detail-wrap');
  if (!wrap) return;
  // サーバから最新詳細を取得 (上書き反映)
  try {
    const r = await fetch(`/api/employee-detail/${e.id}`).then(x => x.json());
    if (r && r.data) {
      e.detail = r.data.detail || e.detail;
    }
  } catch (err) {}
  window._currentEmp = e;
  _empRenderDetail(e);
};

window._empSaveDetail = async function() {
  const e = window._currentEmp;
  if (!e) return;
  try {
    await fetch(`/api/employee-detail/${e.id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(e.detail || {}),
    });
    flash('詳細データを保存しました');
  } catch (err) { alert('保存失敗: ' + err.message); }
};

window._empToggleOnboard = function(i) {
  const e = window._currentEmp; if (!e) return;
  const ob = e.detail.onboarding_checklist || [];
  if (ob[i]) {
    ob[i].done = !ob[i].done;
    ob[i].completed_at = ob[i].done ? new Date().toISOString().slice(0,10) : null;
    e.detail.onboarding_checklist = ob;
    _empRenderDetail(e);
  }
};

window._empAddInterview = function() {
  const e = window._currentEmp; if (!e) return;
  if (!e.detail.interviews) e.detail.interviews = [];
  e.detail.interviews.unshift({
    date: new Date().toISOString().slice(0,10),
    type: "1on1",
    interviewer: "",
    summary: "",
    next_action: "",
  });
  _empRenderDetail(e);
};

window._empUpdInterview = function(i, field, val) {
  const e = window._currentEmp; if (!e) return;
  if (e.detail.interviews && e.detail.interviews[i]) {
    e.detail.interviews[i][field] = val;
  }
};

window._empDelInterview = function(i) {
  const e = window._currentEmp; if (!e) return;
  if (!confirm('この面談記録を削除しますか?')) return;
  e.detail.interviews.splice(i, 1);
  _empRenderDetail(e);
};

window._empAddEval = function() {
  const e = window._currentEmp; if (!e) return;
  if (!e.detail.evaluations) e.detail.evaluations = [];
  e.detail.evaluations.unshift({
    year: new Date().getFullYear(),
    overall: "A",
    achievement: 100,
    comment: "",
  });
  _empRenderDetail(e);
};

window._empUpdEval = function(i, field, val) {
  const e = window._currentEmp; if (!e) return;
  if (e.detail.evaluations && e.detail.evaluations[i]) {
    if (field === 'achievement' || field === 'year') val = parseInt(val) || 0;
    e.detail.evaluations[i][field] = val;
  }
};

window._empDelEval = function(i) {
  const e = window._currentEmp; if (!e) return;
  if (!confirm('この評価を削除しますか?')) return;
  e.detail.evaluations.splice(i, 1);
  _empRenderDetail(e);
};

window._empUpdBasic = function(field, val) {
  const e = window._currentEmp; if (!e) return;
  if (!e.detail) e.detail = {};
  if (field.includes('.')) {
    const [parent, child] = field.split('.');
    if (!e.detail[parent]) e.detail[parent] = {};
    e.detail[parent][child] = val;
  } else {
    e.detail[field] = val;
  }
};

function _empRenderDetail(e) {
  const wrap = document.getElementById('emp-detail-wrap');
  if (!wrap) return;
  const d = e.detail || {};
  const ob = d.onboarding_checklist || [];
  const ints = d.interviews || [];
  const evals = d.evaluations || [];
  const obDone = ob.filter(x => x.done).length;
  const ec = d.emergency_contact || {};
  wrap.innerHTML = `
    <div class="card" style="border-top:4px solid var(--accent)">
      <div class="card-header">
        <h2>👤 ${e.name} (${e.employee_number || e.id})</h2>
        <div style="display:flex;gap:8px">
          <button class="btn btn-primary btn-small" onclick="window._empSaveDetail()">💾 変更を保存</button>
          <button class="btn btn-secondary btn-small" onclick="document.getElementById('emp-detail-wrap').innerHTML=''">閉じる</button>
        </div>
      </div>
      <div class="hint">💡 各項目はクリックで直接編集できます。編集後は上の「変更を保存」を押してください。</div>

      <div class="kpis" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))">
        <div class="kpi-card"><div class="kpi-label">所属</div><div class="kpi-value" style="font-size:14px">${e.department || '—'}</div></div>
        <div class="kpi-card"><div class="kpi-label">役職</div><div class="kpi-value" style="font-size:14px">${e.position || '—'}</div></div>
        <div class="kpi-card"><div class="kpi-label">雇用形態</div><div class="kpi-value" style="font-size:14px">${e.employment_type}</div></div>
        <div class="kpi-card"><div class="kpi-label">入社日</div><div class="kpi-value" style="font-size:14px">${dateJP(e.hire_date)}</div></div>
        <div class="kpi-card"><div class="kpi-label">月給</div><div class="kpi-value" style="font-size:14px">${yen(e.monthly_salary)}</div></div>
        <div class="kpi-card"><div class="kpi-label">交通費</div><div class="kpi-value" style="font-size:14px">${yen(e.commute_allowance||0)}</div></div>
      </div>

      <h3 style="margin:20px 0 10px;color:var(--primary)">📋 基本情報 (編集可)</h3>
      <table class="data-table">
        <tbody>
          <tr><td style="text-align:left;width:25%">生年月日</td><td style="text-align:left"><input type="date" value="${d.birth_date || ''}" onchange="_empUpdBasic('birth_date', this.value)" style="width:160px"/> (${d.age || '?'}歳)</td></tr>
          <tr><td style="text-align:left">性別</td><td style="text-align:left"><select onchange="_empUpdBasic('gender', this.value)">${['男性','女性','その他'].map(g => `<option ${d.gender===g?'selected':''}>${g}</option>`).join('')}</select></td></tr>
          <tr><td style="text-align:left">住所</td><td style="text-align:left"><input type="text" value="${d.address || ''}" onchange="_empUpdBasic('address', this.value)" style="width:100%"/></td></tr>
          <tr><td style="text-align:left">携帯</td><td style="text-align:left"><input type="text" value="${d.phone_mobile || ''}" onchange="_empUpdBasic('phone_mobile', this.value)" style="width:200px"/></td></tr>
          <tr><td style="text-align:left">社用メール</td><td style="text-align:left"><input type="email" value="${d.email_work || ''}" onchange="_empUpdBasic('email_work', this.value)" style="width:300px"/></td></tr>
          <tr><td style="text-align:left">個人メール</td><td style="text-align:left"><input type="email" value="${d.email_personal || ''}" onchange="_empUpdBasic('email_personal', this.value)" style="width:300px"/></td></tr>
          <tr><td style="text-align:left">学歴</td><td style="text-align:left">${d.education ? `${d.education.university} ${d.education.faculty} (${d.education.graduation_year}年卒)` : '—'} <span class="muted">(基本情報のため編集不可)</span></td></tr>
          <tr><td style="text-align:left">スキル (カンマ区切り)</td><td style="text-align:left"><input type="text" value="${(d.skills||[]).join(', ')}" onchange="window._currentEmp.detail.skills = this.value.split(',').map(s=>s.trim()).filter(Boolean); _empRenderDetail(window._currentEmp)" style="width:100%"/></td></tr>
          <tr><td style="text-align:left">緊急連絡先 氏名</td><td style="text-align:left"><input type="text" value="${ec.name || ''}" onchange="_empUpdBasic('emergency_contact.name', this.value)" style="width:200px"/></td></tr>
          <tr><td style="text-align:left">緊急連絡先 続柄</td><td style="text-align:left"><input type="text" value="${ec.relationship || ''}" onchange="_empUpdBasic('emergency_contact.relationship', this.value)" style="width:120px"/></td></tr>
          <tr><td style="text-align:left">緊急連絡先 電話</td><td style="text-align:left"><input type="text" value="${ec.phone || ''}" onchange="_empUpdBasic('emergency_contact.phone', this.value)" style="width:200px"/></td></tr>
        </tbody>
      </table>

      <h3 style="margin:20px 0 10px;color:var(--primary)">✅ 入社手続き (${obDone}/${ob.length}完了)</h3>
      <div class="hint">チェックボックスをクリックで完了/未完了を切替</div>
      <table class="data-table">
        <thead><tr><th>状態</th><th>項目</th><th>完了日</th></tr></thead>
        <tbody>
          ${ob.map((item, i) => `<tr>
            <td><input type="checkbox" ${item.done?'checked':''} onchange="_empToggleOnboard(${i})" style="width:18px;height:18px;cursor:pointer"/></td>
            <td style="text-align:left">${item.item}</td>
            <td>${item.completed_at ? dateJP(item.completed_at) : '—'}</td>
          </tr>`).join('')}
        </tbody>
      </table>

      <h3 style="margin:20px 0 10px;color:var(--primary)">💬 面談履歴 (${ints.length}件) <button class="btn btn-primary btn-small" onclick="_empAddInterview()">＋ 新規追加</button></h3>
      <table class="data-table">
        <thead><tr><th style="width:130px">日付</th><th style="width:110px">種別</th><th style="text-align:left">面談者</th><th style="text-align:left">概要</th><th style="text-align:left">次のアクション</th><th>操作</th></tr></thead>
        <tbody>
          ${ints.length ? ints.map((it, i) => `<tr>
            <td><input type="date" value="${it.date||''}" onchange="_empUpdInterview(${i}, 'date', this.value)" style="width:130px"/></td>
            <td><select onchange="_empUpdInterview(${i}, 'type', this.value)">${['1on1','定期面談','目標設定','評価面談','キャリア面談'].map(t=>`<option ${it.type===t?'selected':''}>${t}</option>`).join('')}</select></td>
            <td style="text-align:left"><input type="text" value="${it.interviewer||''}" onchange="_empUpdInterview(${i}, 'interviewer', this.value)" style="width:100%"/></td>
            <td style="text-align:left"><input type="text" value="${it.summary||''}" onchange="_empUpdInterview(${i}, 'summary', this.value)" style="width:100%"/></td>
            <td style="text-align:left"><input type="text" value="${it.next_action||''}" onchange="_empUpdInterview(${i}, 'next_action', this.value)" style="width:100%"/></td>
            <td><button class="btn btn-danger btn-small" onclick="_empDelInterview(${i})">削除</button></td>
          </tr>`).join('') : '<tr><td colspan="6" style="color:#9ca3af">面談履歴なし - 「新規追加」で記録できます</td></tr>'}
        </tbody>
      </table>

      <h3 style="margin:20px 0 10px;color:var(--primary)">⭐ 評価履歴 <button class="btn btn-primary btn-small" onclick="_empAddEval()">＋ 新規追加</button></h3>
      <table class="data-table">
        <thead><tr><th>年度</th><th>総合評価</th><th>目標達成率(%)</th><th style="text-align:left">所感</th><th>操作</th></tr></thead>
        <tbody>
          ${evals.length ? evals.map((ev, i) => `<tr>
            <td><input type="number" value="${ev.year||''}" onchange="_empUpdEval(${i}, 'year', this.value)" style="width:80px"/></td>
            <td><select onchange="_empUpdEval(${i}, 'overall', this.value)">${['S','A','B','C','D'].map(g=>`<option ${ev.overall===g?'selected':''}>${g}</option>`).join('')}</select></td>
            <td><input type="number" value="${ev.achievement||0}" onchange="_empUpdEval(${i}, 'achievement', this.value)" style="width:80px"/></td>
            <td style="text-align:left"><input type="text" value="${ev.comment||''}" onchange="_empUpdEval(${i}, 'comment', this.value)" style="width:100%"/></td>
            <td><button class="btn btn-danger btn-small" onclick="_empDelEval(${i})">削除</button></td>
          </tr>`).join('') : '<tr><td colspan="5" style="color:#9ca3af">評価履歴なし - 「新規追加」で記録できます</td></tr>'}
        </tbody>
      </table>

      <div class="card-footer" style="text-align:center;margin-top:20px">
        <button class="btn btn-primary" onclick="window._empSaveDetail()" style="padding:10px 30px;font-size:15px">💾 すべての変更を保存</button>
      </div>
    </div>
  `;
  wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 編集モーダル（簡易: detail-wrap に展開）
window._empEdit = async function(idx) {
  const e = (window._employees || [])[idx];
  if (!e) { alert('従業員データが見つかりません'); return; }
  const wrap = document.getElementById('emp-edit-wrap');
  if (!wrap) return;
  // 現在の overrides を取得
  let ov = {};
  try { ov = await fetch('/api/employee-overrides').then(r => r.json()); } catch(err) {}
  const cur = ov[String(e.id)] || {};
  wrap.innerHTML = `
    <div class="card">
      <div class="card-header">
        <h2>${e.name} の手動上書き編集</h2>
        <button class="btn btn-secondary btn-small" onclick="document.getElementById('emp-edit-wrap').innerHTML=''">閉じる</button>
      </div>
      <div class="hint">入力した値は freee 由来の値より優先されます。空欄のままにすると freee 由来の値がそのまま使われます。</div>
      <div class="form-grid" style="grid-template-columns: 1fr 1fr">
        <label>月給（円・固定残業代込）<input type="number" id="emp-ed-monthly" step="10000" placeholder="freee値: ${e.monthly_salary || 0}" value="${cur.monthly_salary || ''}"/></label>
        <label>交通費（円/月）<input type="number" id="emp-ed-commute" step="1000" placeholder="freee値: ${e.commute_allowance || 0}" value="${cur.commute_allowance || ''}"/></label>
        <label>年収（円）<input type="number" id="emp-ed-annual" step="100000" placeholder="未入力なら月給×12で自動計算" value="${cur.annual_salary || ''}"/></label>
        <label>部門<input type="text" id="emp-ed-dept" placeholder="freee値: ${e.department || '(空)'}" value="${cur.department || ''}"/></label>
        <label>役職<input type="text" id="emp-ed-pos" placeholder="freee値: ${e.position || '(空)'}" value="${cur.position || ''}"/></label>
        <label>分類カテゴリ
          <select id="emp-ed-cat">
            <option value="" ${!cur.category?'selected':''}>自動推測（${e.category==='exec'?'役員':e.category==='engineer'?'エンジニア':'従業員'}）</option>
            <option value="exec" ${cur.category==='exec'?'selected':''}>役員（役員報酬）</option>
            <option value="employee" ${cur.category==='employee'?'selected':''}>従業員（給料手当）</option>
            <option value="engineer" ${cur.category==='engineer'?'selected':''}>エンジニア（給料手当原）</option>
          </select>
        </label>
        <label>雇用形態（上書き）<input type="text" id="emp-ed-etype" placeholder="freee値: ${e.employment_type || ''}" value="${cur.employment_type || ''}"/></label>
      </div>
      <div class="card-footer" style="display:flex;gap:8px">
        <button class="btn btn-primary" onclick="window._empSave(${idx})">保存</button>
        <button class="btn btn-danger btn-small" onclick="window._empClear(${idx})">上書きをクリア</button>
      </div>
    </div>
  `;
  wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

window._empSave = async function(idx) {
  const e = (window._employees || [])[idx];
  if (!e) return;
  let ov = {};
  try { ov = await fetch('/api/employee-overrides').then(r => r.json()); } catch(err) {}
  const rec = {};
  const v = (id) => document.getElementById(id).value.trim();
  const intV = (id) => { const x = v(id); return x === '' ? null : parseInt(x); };
  const m = intV('emp-ed-monthly'); if (m !== null) rec.monthly_salary = m;
  const cm = intV('emp-ed-commute'); if (cm !== null) rec.commute_allowance = cm;
  const an = intV('emp-ed-annual'); if (an !== null) rec.annual_salary = an;
  const d = v('emp-ed-dept'); if (d) rec.department = d;
  const p = v('emp-ed-pos'); if (p) rec.position = p;
  const c = v('emp-ed-cat'); if (c) rec.category = c;
  const et = v('emp-ed-etype'); if (et) rec.employment_type = et;

  ov[String(e.id)] = rec;
  await fetch('/api/employee-overrides', {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(ov),
  });
  flash('上書きを保存しました');
  // キャッシュではないので即時反映
  state.employees = null;  // 念のため
  renderPage('employees');
};

window._empClear = async function(idx) {
  const e = (window._employees || [])[idx];
  if (!e) return;
  if (!confirm(`${e.name} の手動上書きをすべてクリアして freee 由来の値に戻しますか？`)) return;
  let ov = {};
  try { ov = await fetch('/api/employee-overrides').then(r => r.json()); } catch(err) {}
  delete ov[String(e.id)];
  await fetch('/api/employee-overrides', {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(ov),
  });
  flash('上書きをクリアしました');
  state.employees = null;
  renderPage('employees');
};

// イベント委譲 (編集ボタン)
document.addEventListener('click', async (ev) => {
  const t = ev.target;
  if (t && t.dataset && t.dataset.empEdit !== undefined) {
    const idx = parseInt(t.dataset.empEdit);
    window._empEdit(idx);
  }
  // 全員上書きクリア
  if (t && t.id === 'emp-clear-all-overrides') {
    if (!confirm('全従業員の手動上書きをすべてクリアし、freee 自動読込に戻しますか？\n\nこの操作は取り消せません。')) return;
    try {
      await fetch('/api/employee-overrides', { method: 'DELETE' });
      flash('全員の上書きをクリアしました。再読込中...');
      state.employees = null;
      renderPage('employees');
    } catch (e) {
      alert('クリア失敗: ' + e.message);
    }
  }
});

// ============================================================
// Page: Payroll history
// ============================================================

async function renderPayroll(c) {
  const ph = await getPayrollHistory();
  const totalGross = ph.reduce((s, r) => s + r.gross_salary, 0);
  const totalEmployerCost = ph.reduce((s, r) => s + r.employer_total_cost, 0);
  const avgEmp = ph[0].employee_count;

  c.innerHTML = `${sourceBadge(state.payrollSource, state.payrollWarning)}
    
    <div class="kpis">
      <div class="kpi-card"><div class="kpi-label">過去12ヶ月 給与総支給</div><div class="kpi-value">${yen(totalGross)}</div></div>
      <div class="kpi-card"><div class="kpi-label">会社負担社保(年間)</div><div class="kpi-value">${yen(ph.reduce((s, r) => s + r.social_insurance_employer, 0))}</div></div>
      <div class="kpi-card"><div class="kpi-label">人件費総額(年間)</div><div class="kpi-value">${yen(totalEmployerCost)}</div></div>
      <div class="kpi-card"><div class="kpi-label">一人当たり月平均</div><div class="kpi-value">${yen(totalGross / 12 / avgEmp)}</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h2>給与支給推移（12ヶ月）</h2></div>
      <div class="chart-wrap tall"><canvas id="payroll-chart"></canvas></div>
    </div>

    <div class="card">
      <div class="card-header"><h2>月次給与明細</h2></div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>月</th><th>区分</th><th>総支給</th><th>従業員社保</th><th>会社社保</th><th>源泉所得税</th><th>住民税</th><th>差引手取</th><th>会社負担計</th></tr></thead>
          <tbody>${ph.map(r => `<tr class="${r.is_bonus_month?'row-warning':''}">
            <td>${monthJP(r.year_month)}</td>
            <td><span class="pill ${r.is_bonus_month?'warn':'info'}">${r.is_bonus_month?'賞与月':'通常月'}</span></td>
            <td>${yen(r.gross_salary)}</td>
            <td>${yen(r.social_insurance_employee)}</td>
            <td>${yen(r.social_insurance_employer)}</td>
            <td>${yen(r.withholding_tax)}</td>
            <td>${yen(r.resident_tax)}</td>
            <td><strong>${yen(r.net_payment)}</strong></td>
            <td><strong>${yen(r.employer_total_cost)}</strong></td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    </div>
  `;
  makeChart($('#payroll-chart'), 'payroll', {
    type: 'bar',
    data: {
      labels: ph.map(r => r.year_month),
      datasets: [
        { label: '総支給', data: ph.map(r => r.gross_salary), backgroundColor: '#001338', stack: 'cost' },
        { label: '会社負担社保', data: ph.map(r => r.social_insurance_employer), backgroundColor: '#E5C76E', stack: 'cost' },
        { label: '手取り', data: ph.map(r => r.net_payment), type: 'line',
          borderColor: '#10b981', backgroundColor: '#10b98120', borderWidth: 2.5, yAxisID: 'y1', pointRadius: 3 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: c => `${c.dataset.label}: ${yen(c.parsed.y)}` } } },
      scales: {
        y: { stacked: true, ticks: { callback: v => yen(v) } },
        y1: { position: 'right', ticks: { callback: v => yen(v) }, grid: { drawOnChartArea: false } },
      },
    },
  });
}

// ============================================================
// Page: Bonus calendar
// ============================================================

async function renderBonus(c) {
  const bonus = await getBonusCalendar();
  c.innerHTML = `${sourceBadge(state.bonusSource, state.bonusWarning)}
    
    <div class="kpis">
      <div class="kpi-card"><div class="kpi-label">今年度予定賞与合計</div><div class="kpi-value">${yen(bonus.reduce((s, b) => s + b.amount, 0))}</div></div>
    </div>
    <div class="card">
      <div class="card-header"><h2>賞与支給スケジュール</h2></div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>支給日</th><th style="text-align:left">区分</th><th>支給額</th><th style="text-align:left">備考</th></tr></thead>
          <tbody>${bonus.map(b => {
            const past = new Date(b.pay_date) < new Date();
            return `<tr class="${past?'muted':''}">
              <td>${dateJP(b.pay_date)}</td>
              <td style="text-align:left"><span class="pill ${b.name.includes('夏')?'warn':'info'}">${b.name}</span></td>
              <td><strong>${yen(b.amount)}</strong></td>
              <td style="text-align:left">${b.note}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
    </div>
  `;
}

// ============================================================
// Page: Labor cost analysis
// ============================================================

async function renderLaborCost(c) {
  const la = await getLaborAnalysis();
  // 切替モード（localStorage に保持）
  const modeKey = 'laborCostMode';
  let mode = localStorage.getItem(modeKey) || 'cogs';  // 'cogs' = 売上原価人件費、'all' = 全体
  const renderBody = () => {
    const isCogs = mode === 'cogs';
    // 月次行の選択
    const rowLabor = r => isCogs ? r.cogs_labor_total : r.labor_total;
    const rowRatio = r => isCogs ? r.cogs_labor_to_revenue_ratio : r.labor_to_revenue_ratio;
    const annualLabor = isCogs ? la.annual_cogs_labor_total : la.annual_total_labor_cost;
    const annualRatio = isCogs ? la.cogs_labor_to_revenue_ratio : la.labor_to_revenue_ratio;
    const empCount = Math.max(1, la.employee_count);
    const perEmpMonth = Math.round(annualLabor / 12 / empCount);

    document.getElementById('lc-body').innerHTML = `
      <div class="kpis">
        <div class="kpi-card"><div class="kpi-label">年間売上</div><div class="kpi-value">${yen(la.annual_revenue)}</div><div class="kpi-sub">P/L 売上高合計</div></div>
        <div class="kpi-card"><div class="kpi-label">${isCogs?'年間人件費(売上原価)':'年間人件費(全体)'}</div><div class="kpi-value">${yen(annualLabor)}</div>
          <div class="kpi-sub">${isCogs?'給料(原)+法定福利(原)+旅費交通(原)':'(原)+給料手当(販)+法定福利費(販)'}</div></div>
        <div class="kpi-card kpi-warn"><div class="kpi-label">${isCogs?'人件費(原)対売上比率':'人件費(全体)対売上比率'}</div><div class="kpi-value">${pct(annualRatio, 2)}</div></div>
        <div class="kpi-card kpi-ok"><div class="kpi-label">一人当たり年商</div><div class="kpi-value">${yen(la.revenue_per_employee_annual)}</div><div class="kpi-sub">${la.employee_count}名</div></div>
        <div class="kpi-card"><div class="kpi-label">一人当たり月次人件費</div><div class="kpi-value">${yen(perEmpMonth)}</div></div>
      </div>

      <div class="card">
        <div class="card-header"><h2>年間 人件費内訳</h2></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th style="text-align:left">区分</th><th>給料手当</th><th>法定福利費</th><th>旅費交通費</th><th>小計</th></tr></thead>
            <tbody>
              <tr><td style="text-align:left">売上原価</td>
                <td>${yen(la.annual_cogs_salary)}</td>
                <td>${yen(la.annual_cogs_social_insurance)}</td>
                <td>${yen(la.annual_cogs_travel)}</td>
                <td><strong>${yen(la.annual_cogs_labor_total)}</strong></td>
              </tr>
              <tr><td style="text-align:left">販管費</td>
                <td>${yen(la.annual_sga_salary)}</td>
                <td>${yen(la.annual_sga_social_insurance)}</td>
                <td>—</td>
                <td><strong>${yen(la.annual_sga_labor_total)}</strong></td>
              </tr>
              <tr class="row-total"><td style="text-align:left">合計</td>
                <td>${yen(la.annual_cogs_salary + la.annual_sga_salary)}</td>
                <td>${yen(la.annual_cogs_social_insurance + la.annual_sga_social_insurance)}</td>
                <td>${yen(la.annual_cogs_travel)}</td>
                <td><strong>${yen(la.annual_total_labor_cost)}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>月次推移：売上 vs ${isCogs?'人件費(売上原価)':'人件費(全体)'}</h2></div>
        <div class="chart-wrap tall"><canvas id="labor-chart"></canvas></div>
      </div>

      <div class="card">
        <div class="card-header"><h2>月次明細（${isCogs?'人件費=売上原価のみ':'人件費=売上原価+販管費'}）</h2></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th>月</th><th>売上</th>
              <th>給料(原)</th><th>法定福利(原)</th><th>旅費(原)</th>
              ${isCogs ? '' : '<th>給料(販)</th><th>法定福利(販)</th>'}
              <th>人件費${isCogs?'(原)':'計'}</th><th>対売上比率</th><th>一人当たり売上</th>
            </tr></thead>
            <tbody>${la.monthly_breakdown.map(r => `<tr>
              <td>${monthJP(r.year_month)}</td>
              <td>${yen(r.revenue)}</td>
              <td>${yen(r.cogs_salary)}</td>
              <td>${yen(r.cogs_social_insurance)}</td>
              <td>${yen(r.cogs_travel)}</td>
              ${isCogs ? '' : `<td>${yen(r.sga_salary)}</td><td>${yen(r.sga_social_insurance)}</td>`}
              <td><strong>${yen(rowLabor(r))}</strong></td>
              <td>${pct(rowRatio(r), 2)}</td>
              <td>${yen(r.revenue_per_employee)}</td>
            </tr>`).join('')}</tbody>
          </table>
        </div>
      </div>
    `;
    // チャート
    makeChart($('#labor-chart'), 'labor', {
      type: 'bar',
      data: {
        labels: la.monthly_breakdown.map(r => r.year_month),
        datasets: [
          { label: '売上', data: la.monthly_breakdown.map(r => r.revenue), backgroundColor: '#001338', order: 2 },
          { label: isCogs ? '人件費(売上原価)' : '人件費(全体)',
            data: la.monthly_breakdown.map(rowLabor), backgroundColor: '#E5C76E', order: 3 },
          { label: '対売上比率(%)', data: la.monthly_breakdown.map(rowRatio),
            type: 'line', borderColor: '#b91c1c', borderWidth: 2.5, yAxisID: 'y1', order: 1, pointRadius: 3 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { tooltip: { callbacks: { label: c => {
          if (c.dataset.label === '対売上比率(%)') return `${c.dataset.label}: ${c.parsed.y.toFixed(2)}%`;
          return `${c.dataset.label}: ${yen(c.parsed.y)}`;
        } } } },
        scales: {
          y: { ticks: { callback: v => yen(v) } },
          y1: { position: 'right', ticks: { callback: v => v + '%' }, grid: { drawOnChartArea: false } },
        },
      },
    });
  };

  c.innerHTML = `${sourceBadge(state.laborSource, state.laborWarning)}
    <div class="card">
      <div class="card-header">
        <h2>人件費の区分</h2>
        <div style="display:flex;gap:8px">
          <button class="btn btn-small ${mode==='cogs'?'btn-primary':'btn-secondary'}" id="lc-mode-cogs">人件費（売上原価のみ）</button>
          <button class="btn btn-small ${mode==='all'?'btn-primary':'btn-secondary'}" id="lc-mode-all">人件費（全体）</button>
        </div>
      </div>
      <div class="hint">
        <strong>人件費（売上原価）</strong>＝ 給料手当(原) ＋ 法定福利費(原) ＋ 旅費交通費(原)　&nbsp;|&nbsp;
        <strong>人件費（全体）</strong>＝ 上記 ＋ 給料手当(販管費) ＋ 法定福利費(販管費)
      </div>
    </div>
    <div id="lc-body"></div>
  `;
  renderBody();
  document.getElementById('lc-mode-cogs').addEventListener('click', () => {
    mode = 'cogs'; localStorage.setItem(modeKey, mode);
    document.getElementById('lc-mode-cogs').className = 'btn btn-small btn-primary';
    document.getElementById('lc-mode-all').className = 'btn btn-small btn-secondary';
    renderBody();
  });
  document.getElementById('lc-mode-all').addEventListener('click', () => {
    mode = 'all'; localStorage.setItem(modeKey, mode);
    document.getElementById('lc-mode-cogs').className = 'btn btn-small btn-secondary';
    document.getElementById('lc-mode-all').className = 'btn btn-small btn-primary';
    renderBody();
  });
}

// ============================================================
// Page: Scenarios
// ============================================================

async function renderScenarios(c) {
  const settings = await getSettings();
  const labels = { optimistic: '楽観', neutral: '中立', pessimistic: '悲観' };
  c.innerHTML = `
    <div class="hint">シナリオパラメータは、月次CF予測に乗算される倍率です。売上倍率1.10 = +10%、原価倍率0.95 = -5% を意味します。</div>
    <div class="card">
      <div class="card-header"><h2>シナリオパラメータ</h2></div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th style="text-align:left">シナリオ</th><th>売上倍率</th><th>原価倍率</th></tr></thead>
          <tbody id="sc-tbody">${['optimistic','neutral','pessimistic'].map(k => {
            const s = settings.scenarios[k];
            return `<tr data-scenario="${k}">
              <td style="text-align:left;font-weight:600">${labels[k]}</td>
              <td><input type="number" step="0.01" class="sc-rev" value="${s.revenue_multiplier}"/></td>
              <td><input type="number" step="0.01" class="sc-cost" value="${s.cost_multiplier}"/></td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
      <div class="card-footer"><button class="btn btn-primary" id="btn-save-sc">シナリオを保存</button></div>
    </div>
  `;
  $('#btn-save-sc').addEventListener('click', async () => {
    const scenarios = {};
    $$('#sc-tbody tr').forEach(tr => {
      scenarios[tr.dataset.scenario] = {
        revenue_multiplier: parseFloat(tr.querySelector('.sc-rev').value),
        cost_multiplier: parseFloat(tr.querySelector('.sc-cost').value),
      };
    });
    await fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenarios }) });
    state.settings = null; state.forecast = null;
    flash('シナリオを保存しました');
  });
}

// ============================================================
// Page: Adjustments
// ============================================================

async function renderAdjustments(c) {
  const adj = await getAdjustments();
  c.innerHTML = `
    <div class="hint">プラス=流入、マイナス=流出として入力してください。API外の予定（賞与、税金、設備投資など）を月別に登録できます。</div>
    <div class="card">
      <div class="card-header"><h2>手動調整</h2>
        <button class="btn btn-primary btn-small" id="btn-add-adj">＋ 調整を追加</button>
      </div>
      <div class="table-scroll">
        <table class="data-table" id="adj-table">
          <thead><tr><th>対象月</th><th>区分</th><th style="text-align:left">項目</th><th>金額</th><th></th></tr></thead>
          <tbody>${adjTableBody(adj)}</tbody>
        </table>
      </div>
      <div class="card-footer"><button class="btn btn-primary" id="btn-save-adj">調整を保存</button></div>
    </div>
  `;
  $('#btn-add-adj').addEventListener('click', () => {
    const ym = new Date().toISOString().slice(0, 7);
    if (!state.adjustments[ym]) state.adjustments[ym] = [];
    state.adjustments[ym].push({ category: '新規項目', amount: 0, type: 'operating' });
    $('#adj-table tbody').innerHTML = adjTableBody(state.adjustments);
  });
  $('#btn-save-adj').addEventListener('click', async () => {
    const grouped = {};
    $$('#adj-table tbody tr[data-adj]').forEach(tr => {
      const ym = tr.querySelector('.adj-ym').value;
      if (!ym) return;
      if (!grouped[ym]) grouped[ym] = [];
      grouped[ym].push({
        category: tr.querySelector('.adj-cat').value,
        amount: parseInt(tr.querySelector('.adj-amt').value || 0),
        type: tr.querySelector('.adj-type').value,
      });
    });
    await fetch('/api/adjustments', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(grouped) });
    state.adjustments = {}; state.forecast = null;
    flash('調整を保存しました');
  });
}

function adjTableBody(adj) {
  const flat = [];
  for (const ym of Object.keys(adj).sort()) {
    for (const item of adj[ym]) flat.push({ ym, ...item });
  }
  if (flat.length === 0) return '<tr><td colspan="5" class="empty-state">手動調整がありません</td></tr>';
  state._flatAdj = flat;
  return flat.map((a, i) => `<tr data-adj="${i}">
    <td><input type="month" class="adj-ym" value="${a.ym}"/></td>
    <td><select class="adj-type">
      <option value="operating" ${a.type==='operating'?'selected':''}>営業</option>
      <option value="investing" ${a.type==='investing'?'selected':''}>投資</option>
      <option value="financing" ${a.type==='financing'?'selected':''}>財務</option>
    </select></td>
    <td style="text-align:left"><input type="text" class="adj-cat" value="${a.category}" style="width:240px"/></td>
    <td><input type="number" step="10000" class="adj-amt" value="${a.amount}"/></td>
    <td><button class="btn btn-danger btn-small" onclick="window._rmAdj(${i})">削除</button></td>
  </tr>`).join('');
}
window._rmAdj = function(i) {
  const item = state._flatAdj[i];
  if (!item) return;
  if (!confirm('この調整を削除しますか？')) return;
  state.adjustments[item.ym] = (state.adjustments[item.ym] || []).filter(
    a => !(a.category === item.category && a.amount === item.amount && a.type === item.type)
  );
  $('#adj-table tbody').innerHTML = adjTableBody(state.adjustments);
};

// ============================================================
// Page: Preferences (sites + opening cash)
// ============================================================

async function renderPreferences(c) {
  const s = await getSettings();
  c.innerHTML = `
    <div class="card">
      <div class="card-header"><h2>サイト・期首残高 設定</h2></div>
      <div class="form-grid">
        <label>売上回収サイト（月）
          <input type="number" id="set-rcv" value="${s.receivable_months}" min="0" max="12"/>
          <small>1 = 翌月入金、2 = 翌々月入金</small>
        </label>
        <label>仕入・経費支払サイト（月）
          <input type="number" id="set-pay" value="${s.payable_months}" min="0" max="12"/>
          <small>2 = 翌々月支払</small>
        </label>
        <label>給与支払サイト（月）
          <input type="number" id="set-sal" value="${s.salary_payment_offset_months}" min="0" max="3"/>
          <small>0 = 当月支払、1 = 翌月支払</small>
        </label>
        <label>期首現預金（円・空欄ならAPI/Mockの残高合計を使用）
          <input type="number" id="set-open" value="${s.opening_cash_balance ?? ''}" step="100000"/>
        </label>
      </div>
      <div class="card-footer"><button class="btn btn-primary" id="btn-save-pref">設定を保存</button></div>
    </div>
  `;
  $('#btn-save-pref').addEventListener('click', async () => {
    const payload = {
      receivable_months: parseInt($('#set-rcv').value || 0),
      payable_months: parseInt($('#set-pay').value || 0),
      salary_payment_offset_months: parseInt($('#set-sal').value || 0),
      opening_cash_balance: $('#set-open').value === '' ? null : parseInt($('#set-open').value),
    };
    await fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    state.settings = null; state.forecast = null; state.dailyForecast = null;
    flash('設定を保存しました');
  });
}

// ============================================================
// Page: P/L (損益計算書)
// ============================================================

async function renderPL(c) {
  c.innerHTML = `${sourceBadge('freee')}
    <div class="card">
      <div class="card-header">
        <h2>月次P/L（直近12ヶ月実績）</h2>
        <span class="meta">freee会計の試算表を月別に集計</span>
      </div>
      <div id="pl-monthly-body"><div class="empty-state"><div class="icon">⌛</div><div>取得中... (月次取得は最大30秒)</div></div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2>P/L（事業計画 / CF逆算・税抜会計）</h2>
        <span class="meta">入金/支払予測 × 消費税率 から逆算</span>
      </div>
      <div id="pl-plan-body"><div class="empty-state"><div class="icon">⌛</div><div>計算中...</div></div></div>
    </div>
  `;
  // 並列取得
  Promise.all([
    fetch('/api/pl-monthly').then(x => x.json()).catch(() => ({source:'empty', data:null})),
    fetch('/api/pl-plan').then(x => x.json()).catch(() => ({source:'empty', data:null})),
  ]).then(([mo, pl]) => {
    const moBody = document.getElementById('pl-monthly-body');
    const plBody = document.getElementById('pl-plan-body');
    if (moBody) moBody.innerHTML = renderPLMonthly(mo);
    if (plBody) plBody.innerHTML = renderPLPlan(pl);
  });
}

function renderPLMonthly(r) {
  if (!r || !r.data || !r.data.length) {
    return `<div class="alert warn">${(r && r.warning) || '月次P/Lを取得できませんでした（freee連携が必要です）'}</div>`;
  }
  const rows = r.data; // 古→新
  // 表頭: 月、各KPI
  const ymHeaders = rows.map(r => `<th>${r.year_month}</th>`).join('');
  const cell = v => `<td>${yen(v)}</td>`;
  const rowFor = (label, key, opts={}) => {
    const cls = opts.bold ? 'row-total' : '';
    const total = rows.reduce((s, r) => s + (Number(r[key]) || 0), 0);
    return `<tr class="${cls}"><td style="text-align:left">${label}</td>${rows.map(r => cell(r[key])).join('')}<td><strong>${yen(total)}</strong></td></tr>`;
  };
  return `
    <div class="table-scroll">
      <table class="data-table">
        <thead><tr><th style="text-align:left">勘定科目</th>${ymHeaders}<th>合計</th></tr></thead>
        <tbody>
          ${rowFor('売上高', 'revenue', {bold:true})}
          ${rowFor('売上原価', 'cogs')}
          ${rowFor('売上総利益', 'gross_profit', {bold:true})}
          ${rowFor('販管費', 'sga')}
          ${rowFor('営業利益', 'operating_profit', {bold:true})}
          ${rowFor('営業外収益', 'non_operating_income')}
          ${rowFor('営業外費用', 'non_operating_expense')}
          ${rowFor('経常利益', 'ordinary_profit', {bold:true})}
          ${rowFor('特別利益', 'extraordinary_income')}
          ${rowFor('特別損失', 'extraordinary_loss')}
          ${rowFor('税引前利益', 'pretax_profit', {bold:true})}
          ${rowFor('法人税等', 'corporate_tax')}
          ${rowFor('当期純利益', 'net_profit', {bold:true})}
        </tbody>
      </table>
    </div>
  `;
}

function renderPLPlan(r) {
  if (!r || !r.data || !r.data.months || !r.data.months.length) {
    return `<div class="alert warn">${(r && r.warning) || '事業計画P/Lを生成できませんでした（入金/支払予測を登録してください）'}</div>`;
  }
  const months = r.data.months;
  const summary = r.data.summary || {};
  const ymHeaders = months.map(r => `<th>${r.year_month}</th>`).join('');
  const cell = v => `<td>${yen(v)}</td>`;
  const rowFor = (label, key, opts={}) => {
    const cls = opts.bold ? 'row-total' : '';
    const total = months.reduce((s, r) => s + (Number(r[key]) || 0), 0);
    return `<tr class="${cls}"><td style="text-align:left">${label}</td>${months.map(r => cell(r[key])).join('')}<td><strong>${yen(total)}</strong></td></tr>`;
  };
  return `
    <div class="hint">税抜会計。消費税は別枠管理。法人税は実効税率30%概算。</div>
    <div class="kpis">
      <div class="kpi-card kpi-ok"><div class="kpi-label">12ヶ月 売上高合計</div><div class="kpi-value">${yen(summary.total_revenue)}</div></div>
      <div class="kpi-card"><div class="kpi-label">営業利益合計</div><div class="kpi-value">${yen(summary.total_operating_profit)}</div></div>
      <div class="kpi-card"><div class="kpi-label">当期純利益合計</div><div class="kpi-value">${yen(summary.total_net_profit)}</div></div>
      <div class="kpi-card"><div class="kpi-label">消費税(納付見込)</div><div class="kpi-value">${yen(summary.net_consumption_tax)}</div></div>
    </div>
    <div class="table-scroll">
      <table class="data-table">
        <thead><tr><th style="text-align:left">勘定科目</th>${ymHeaders}<th>合計</th></tr></thead>
        <tbody>
          ${rowFor('売上高（税抜）', 'revenue', {bold:true})}
          ${rowFor('販管費・原価（税抜・給与除く）', 'sga')}
          ${rowFor('給与・賞与', 'salary')}
          ${rowFor('営業利益', 'operating_profit', {bold:true})}
          ${rowFor('支払利息（借入）', 'interest')}
          ${rowFor('経常利益', 'ordinary_profit', {bold:true})}
          ${rowFor('税引前利益', 'pretax_profit', {bold:true})}
          ${rowFor('法人税等（概算30%）', 'corporate_tax_estimate')}
          ${rowFor('当期純利益', 'net_profit', {bold:true})}
          <tr><td colspan="${months.length+2}" style="background:#f0f4f8;font-weight:bold;text-align:left">— 消費税内訳（参考） —</td></tr>
          ${rowFor('仮受消費税（売上）', 'consumption_tax_received')}
          ${rowFor('仮払消費税（経費）', 'consumption_tax_paid')}
        </tbody>
      </table>
    </div>
  `;
}

// ============================================================
// Page: B/S (貸借対照表)
// ============================================================

async function renderBS(c) {
  await renderReport(c, 'B/S', '/api/trial-bs', { withStartMonth: false });
}

async function renderReport(c, kind, apiPath, opts) {
  // Determine current fiscal year (3月決算想定)
  const today = new Date();
  const curFY = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1; // 0-indexed month: 3 = April
  const curEndMonth = today.getMonth() >= 3 ? today.getMonth() + 1 : 3; // 1-indexed
  // Get from URL hash or use defaults
  const stateKey = kind === 'B/S' ? 'bsParams' : 'plParams';
  const saved = state[stateKey] || {};
  const fy = saved.fy || curFY;
  const sm = saved.sm || 4;
  const em = saved.em || curEndMonth;

  c.innerHTML = `${sourceBadge('freee')}
    <div class="card">
      <div class="card-header">
        <h2>集計期間</h2>
        <span class="meta">3月決算（4月〜翌3月）</span>
      </div>
      <div class="form-grid" style="grid-template-columns: 1fr 1fr 1fr auto">
        <label>会計年度（開始年）
          <select id="rep-fy">
            ${[curFY+1, curFY, curFY-1, curFY-2, curFY-3].map(y => `<option value="${y}" ${y===fy?'selected':''}>${y}年度 (${y}年4月〜${y+1}年3月)</option>`).join('')}
          </select>
        </label>
        ${opts.withStartMonth ? `
        <label>開始月
          <select id="rep-sm">
            ${[4,5,6,7,8,9,10,11,12,1,2,3].map(mm => `<option value="${mm}" ${mm===sm?'selected':''}>${mm}月</option>`).join('')}
          </select>
        </label>` : '<div></div>'}
        <label>${opts.withStartMonth ? '終了月' : '対象月末'}
          <select id="rep-em">
            ${[4,5,6,7,8,9,10,11,12,1,2,3].map(mm => `<option value="${mm}" ${mm===em?'selected':''}>${mm}月</option>`).join('')}
          </select>
        </label>
        <button class="btn btn-primary" id="rep-apply" style="align-self:end">適用</button>
      </div>
    </div>
    <div id="rep-body"><div class="empty-state"><div class="icon">⌛</div><div>取得中...</div></div></div>
  `;

  const apply = async () => {
    const fyV = parseInt($('#rep-fy').value);
    const smV = opts.withStartMonth ? parseInt($('#rep-sm').value) : 4;
    const emV = parseInt($('#rep-em').value);
    state[stateKey] = { fy: fyV, sm: smV, em: emV };
    const body = $('#rep-body');
    body.innerHTML = '<div class="empty-state"><div class="icon">⌛</div><div>取得中...</div></div>';
    try {
      const url = `${apiPath}?fiscal_year=${fyV}&start_month=${smV}&end_month=${emV}`;
      const r = await fetch(url).then(x => x.json());
      if (!r.data || r.source === 'empty') {
        body.innerHTML = `<div class="alert warn">${r.warning || 'データなし'}</div>`;
        return;
      }
      const rep = r.data;
      const bals = rep.balances || [];
      body.innerHTML = renderReportTable(rep, bals, kind, 'closing_balance', r.source, r.fiscal_period);
    } catch (e) {
      body.innerHTML = `<div class="alert danger">エラー: ${e.message}</div>`;
    }
  };
  $('#rep-apply').addEventListener('click', apply);
  apply();
}

function renderReportTable(report, balances, kind, amountField, source, fiscalPeriod) {
  const periodLabel = fiscalPeriod || `${report.fiscal_year || ''}年度 ${report.start_month || 1}月〜${report.end_month || 12}月`;
  return `
    <div class="alert ok"><strong>取得した集計期間: ${periodLabel}</strong></div>
    <div class="card">
      <div class="card-header">
        <h2>${kind} 明細</h2>
        <span class="meta">${periodLabel}</span>
      </div>
      <div class="table-scroll" style="max-height:700px">
        <table class="data-table">
          <thead>
            <tr><th style="text-align:left">勘定科目</th><th>期首残高</th><th>借方</th><th>貸方</th><th>当期残高</th><th>構成比</th></tr>
          </thead>
          <tbody>${balances.map(b => {
            const isTotal = b.total_line || (b.hierarchy_level <= 1);
            const cls = isTotal ? 'row-total' : '';
            const lvl = b.hierarchy_level || 0;
            const indent = '　'.repeat(Math.max(0, lvl - 1));
            return `<tr class="${cls}">
              <td style="text-align:left">${indent}${b.account_item_name || b.account_category_name || ''}</td>
              <td>${yen(b.opening_balance)}</td>
              <td>${yen(b.debit_amount)}</td>
              <td>${yen(b.credit_amount)}</td>
              <td><strong>${yen(b.closing_balance)}</strong></td>
              <td>${b.composition_ratio != null ? b.composition_ratio.toFixed(1) + '%' : '--'}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
    </div>
  `;
}

// ============================================================
// Page: Receivables Forecast (入金予測)
// ============================================================

async function renderReceivablesForecast(c) {
  c.innerHTML = '<div class="empty-state"><div class="icon">⌛</div><div>過去1年の入金パターンを分析中...</div></div>';
  try {
    const r = await fetch('/api/payment-forecast').then(x => x.json());
    if (!r.data || r.source === 'empty') {
      c.innerHTML = `${sourceBadge(r.source, r.warning)}<div class="alert warn">freee連携時のみ取得可能です。</div>`;
      return;
    }
    c.innerHTML = renderForecastTable(r.data, 'income', r.source);
  } catch (e) {
    c.innerHTML = `<div class="alert danger">エラー: ${e.message}</div>`;
  }
}

// ============================================================
// Page: Payables Forecast (支払予測)
// ============================================================

async function renderPayablesForecast(c) {
  c.innerHTML = '<div class="empty-state"><div class="icon">⌛</div><div>過去1年の支払パターンを分析中...</div></div>';
  try {
    const r = await fetch('/api/expense-forecast').then(x => x.json());
    if (!r.data || r.source === 'empty') {
      c.innerHTML = `${sourceBadge(r.source, r.warning)}<div class="alert warn">freee連携時のみ取得可能です。</div>`;
      return;
    }
    c.innerHTML = renderForecastTable(r.data, 'expense', r.source);
  } catch (e) {
    c.innerHTML = `<div class="alert danger">エラー: ${e.message}</div>`;
  }
}

// payment_term_days → (month_offset, day)
function termMonthOffset(p) {
  // 構造化フィールドがあれば優先
  if (p && typeof p.payment_offset_months === 'number') return p.payment_offset_months;
  // 0-15日: 当月, 16-45日: 翌月, 46+: 翌々月
  const d = p.payment_term_days || 0;
  if (d <= 15) return 0;
  if (d <= 45) return 1;
  return 2;
}
function termPayDay(p) {
  // 構造化フィールドがあれば優先
  if (p && typeof p.payment_day === 'number') return p.payment_day;
  // close_day + payment_term_days を月日に変換
  const close = p.close_day || 25;
  const term = p.payment_term_days || 0;
  const offset = termMonthOffset(p);
  if (offset === 0) {
    const d = close + term;
    if (d >= 31) return 31;
    return d;
  }
  // 翌月以降: 末日付近なら末日扱い
  const dayInTargetMonth = (close + term) % 30;
  if (dayInTargetMonth <= 0 || dayInTargetMonth >= 28) return 31;
  // Snap to common days
  const snapValues = [1, 5, 10, 15, 20, 25, 28];
  let best = snapValues[0]; let minDiff = Math.abs(dayInTargetMonth - best);
  for (const sv of snapValues) {
    if (Math.abs(dayInTargetMonth - sv) < minDiff) { best = sv; minDiff = Math.abs(dayInTargetMonth - sv); }
  }
  return best;
}
// (month_offset, day) → payment_term_days (close_day基準)
function structToTermDays(monthOffset, payDay, closeDay) {
  // 締め日closeDay → monthOffset月後のpayDay までの日数
  let days = 0;
  if (monthOffset === 0) {
    days = payDay - closeDay;
    if (days < 0) days = 0;
  } else {
    // ざっくり: 締め日から翌月X日 = (30 - closeDay) + payDay + (monthOffset-1)*30
    days = (30 - closeDay) + payDay + (monthOffset - 1) * 30;
    if (payDay === 31) days += 1;  // 末日は1日多めに
  }
  return Math.max(0, days);
}

function renderForecastTable(data, kind, source) {
  const patterns = data.patterns || [];
  const isIncome = kind === 'income';
  const totalFuture = patterns.reduce((s, p) => s + p.future_total, 0);
  const totalCount = patterns.reduce((s, p) => s + p.future_count, 0);
  const titleFuture = isIncome ? '今後12ヶ月の予測入金' : '今後12ヶ月の予測支払';
  const inflowKind = isIncome ? 'income' : 'expense';

  // Store in window for editor access
  window._forecastPatterns = patterns;
  window._forecastKind = inflowKind;
  // ★ 保存後の詳細再オープン (_fcSaveMonthlyからのフラグ)
  if (window._fcReopenPartner) {
    const target = window._fcReopenPartner;
    window._fcReopenPartner = null;
    setTimeout(() => {
      const newIdx = patterns.findIndex(x => x.partner === target);
      if (newIdx >= 0) {
        window._fcDetail(newIdx);
      }
    }, 100);
  }

  return `${sourceBadge(source, '過去365日のパターン+編集内容を適用')}

    <div class="kpis">
      <div class="kpi-card">
        <div class="kpi-label">${isIncome ? '取引先数' : '支払先数'}</div>
        <div class="kpi-value">${patterns.length}</div>
      </div>
      <div class="kpi-card kpi-ok">
        <div class="kpi-label">${titleFuture} 合計</div>
        <div class="kpi-value">${yen(totalFuture)}</div>
        <div class="kpi-sub">${totalCount}件</div>
      </div>
    </div>

    <div class="hint">
      各行の<strong>頻度・締め日・サイト・1回金額</strong>は編集可能です。「詳細」で月別金額の手動編集ができます。締め日「末日」は31を選択。
    </div>

    <div class="card">
      <div class="card-header">
        <h2>取引先別 ${isIncome ? '入金' : '支払'}予測 <span id="fc-del-count" style="color:#b91c1c;font-weight:600;font-size:13px"></span></h2>
        <div style="display:flex;gap:8px">
          <button class="btn btn-secondary btn-small" id="fc-add-new">＋ 項目を追加</button>
          <button class="btn btn-primary btn-small" id="fc-save-all">編集を保存</button>
        </div>
      </div>
      <div class="table-scroll" style="max-height:700px">
        <table class="data-table">
          <thead><tr>
            <th style="text-align:left">取引先</th>
            <th>頻度</th>
            <th>締め日</th>
            <th>支払サイト</th>
            <th>1回金額(税込)</th>
            <th>消費税</th>
            <th>過去1年</th>
            <th>${titleFuture}</th>
            <th>操作</th>
          </tr></thead>
          <tbody>${patterns.map((p, idx) => renderForecastRow(p, idx, inflowKind)).join('')}</tbody>
        </table>
      </div>
    </div>

    <div id="fc-detail-wrap"></div>
  `;
}

function renderForecastRow(p, idx, kind) {
  const freqLabel = p.is_custom ? 'カスタム' :
                    p.frequency_months === 1 ? '毎月' :
                    p.frequency_months === 3 ? '四半期毎' :
                    p.frequency_months === 6 ? '半期毎' :
                    p.frequency_months === 12 ? '年1回' :
                    `${p.frequency_months}ヶ月毎`;
  const isExtra = p.is_extra;
  return `<tr data-fc-idx="${idx}">
    <td style="text-align:left">${p.partner}${p.is_custom ? ' <span class="pill warn">カスタム</span>' : ''}</td>
    <td><select class="fc-freq" data-idx="${idx}">
      ${[1,2,3,4,6,12].map(n => `<option value="${n}" ${n===p.frequency_months?'selected':''}>${n===1?'毎月':n===3?'四半期毎':n===6?'半期毎':n===12?'年1回':n+'ヶ月毎'}</option>`).join('')}
    </select></td>
    <td><select class="fc-close" data-idx="${idx}" style="width:80px">
      ${[5,10,15,20,25,28,31].map(d => `<option value="${d}" ${d===p.close_day?'selected':''}>${d===31?'末日':d+'日'}</option>`).join('')}
    </select></td>
    <td>
      <select class="fc-term-month" data-idx="${idx}" style="width:80px">
        <option value="0" ${termMonthOffset(p)===0?'selected':''}>当月</option>
        <option value="1" ${termMonthOffset(p)===1?'selected':''}>翌月</option>
        <option value="2" ${termMonthOffset(p)===2?'selected':''}>翌々月</option>
      </select>
      <select class="fc-term-day" data-idx="${idx}" style="width:75px">
        ${[1,5,10,15,20,25,28,31].map(d => `<option value="${d}" ${d===termPayDay(p)?'selected':''}>${d===31?'末日':d+'日'}</option>`).join('')}
      </select>
    </td>
    <td><input type="text" inputmode="numeric" class="fc-amount numeric-format" data-idx="${idx}" value="${Number(p.avg_amount||0).toLocaleString('ja-JP')}" style="width:130px;text-align:right"/></td>
    <td><select class="fc-tax" data-idx="${idx}" style="width:75px">
      ${[0,5,8,10].map(r => `<option value="${r}" ${r===Number(p.tax_rate ?? 10)?'selected':''}>${r}%</option>`).join('')}
    </select></td>
    <td>${yen(p.past_total)}</td>
    <td><strong>${yen(p.future_total)}</strong></td>
    <td>
      <button type="button" class="btn btn-secondary btn-small" data-fc-action="detail" data-idx="${idx}">詳細</button>
      <button type="button" class="btn btn-danger btn-small" data-fc-action="del" data-idx="${idx}">削除</button>
    </td>
  </tr>`;
}

window._fcAddNew = async function() {
  const kind = window._forecastKind;
  if (!kind) {
    alert('予測ページが正しく読み込まれていません');
    return;
  }
  const wrap = document.getElementById('fc-detail-wrap');
  if (!wrap) return;
  wrap.innerHTML = `
    <div class="card">
      <div class="card-header">
        <h2>新規${kind==='income'?'入金':'支払'}項目の追加</h2>
        <button class="btn btn-secondary btn-small" onclick="document.getElementById('fc-detail-wrap').innerHTML=''">閉じる</button>
      </div>
      <div class="form-grid">
        <label>名称<input type="text" id="fc-new-name" placeholder="例: 月極駐車場代"/></label>
        <label>頻度
          <select id="fc-new-freq">
            <option value="1">毎月</option>
            <option value="2">2ヶ月毎</option>
            <option value="3">四半期毎</option>
            <option value="6">半期毎</option>
            <option value="12">年1回</option>
          </select>
        </label>
        <label>締め日
          <select id="fc-new-close">
            ${[5,10,15,20,25,28,31].map(d => `<option value="${d}" ${d===31?'selected':''}>${d===31?'末日':d+'日'}</option>`).join('')}
          </select>
        </label>
        <label>支払サイト
          <div style="display:flex;gap:6px">
            <select id="fc-new-term-month" style="flex:1">
              <option value="0">当月</option>
              <option value="1" selected>翌月</option>
              <option value="2">翌々月</option>
            </select>
            <select id="fc-new-term-day" style="flex:1">
              ${[1,5,10,15,20,25,28,31].map(d => `<option value="${d}" ${d===31?'selected':''}>${d===31?'末日':d+'日'}</option>`).join('')}
            </select>
          </div>
        </label>
        <label>1回金額（税込・円）<input type="text" inputmode="numeric" id="fc-new-amount" class="numeric-format" value="0" style="text-align:right"/></label>
        <label>消費税率
          <select id="fc-new-tax">
            <option value="10" selected>10%</option>
            <option value="8">8%（軽減）</option>
            <option value="5">5%</option>
            <option value="0">0%（非課税）</option>
          </select>
        </label>
      </div>
      <div class="card-footer">
        <button class="btn btn-primary" onclick="window._fcSaveNew()">追加して保存</button>
      </div>
    </div>
  `;
  wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

window._fcSaveNew = async function() {
  const name = document.getElementById('fc-new-name').value.trim();
  const freq = parseInt(document.getElementById('fc-new-freq').value);
  const close = parseInt(document.getElementById('fc-new-close').value);
  const termMonth = parseInt(document.getElementById('fc-new-term-month').value);
  const termDay = parseInt(document.getElementById('fc-new-term-day').value);
  const amtRaw = (document.getElementById('fc-new-amount').value || '').replace(/[^0-9-]/g, '');
  const amount = parseInt(amtRaw || '0') || 0;
  const taxRateEl = document.getElementById('fc-new-tax');
  const taxRate = taxRateEl ? parseFloat(taxRateEl.value) : 10;
  const term = structToTermDays(termMonth, termDay, close);
  if (!name) { alert('名称を入力してください'); return; }
  if (!amount) { alert('金額を入力してください'); return; }

  const ov = await fetch('/api/forecast-overrides').then(r => r.json());
  if (!Array.isArray(ov.extra_items)) ov.extra_items = [];
  ov.extra_items.push({
    id: 'custom_' + Date.now(),
    name: name,
    type: window._forecastKind,
    frequency_months: freq,
    close_day: close,
    payment_term_days: term,
    payment_offset_months: termMonth,
    payment_day: termDay,
    avg_amount: amount,
    tax_rate: taxRate,
  });
  await fetch('/api/forecast-overrides', {
    method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(ov)
  });
  flash('項目を追加しました');
  document.getElementById('fc-detail-wrap').innerHTML = '';
  renderPage(state.currentRoute);
};

window._fcDetail = function(idx) {
  console.log('[_fcDetail] called with idx=', idx,
              'patterns count:', (window._forecastPatterns||[]).length);
  const p = window._forecastPatterns && window._forecastPatterns[idx];
  if (!p) {
    alert('詳細データが取得できませんでした (idx=' + idx + ', patterns=' + (window._forecastPatterns ? window._forecastPatterns.length : 'undefined') + ')');
    return;
  }
  console.log('[_fcDetail] partner:', p.partner, 'future count:', (p.future||[]).length);
  const wrap = document.getElementById('fc-detail-wrap');
  if (!wrap) {
    alert('表示先要素が見つかりません。サイドバーから予測ページをもう一度開いてください。');
    return;
  }
  const pastItemsHtml = (p.past_items || []).length > 0 ? `
    <div class="card">
      <div class="card-header">
        <h2>${p.partner} — 過去1年の明細（予測の元データ）</h2>
        <span class="meta">${p.past_items.length}件 / 合計 ${yen(p.past_total)}</span>
      </div>
      <div class="hint">予測ロジック: 締め日=最頻日(末日比率50%以上なら末日)、サイト・金額=中央値</div>
      <div class="table-scroll" style="max-height:300px">
        <table class="data-table">
          <thead><tr><th>発生日</th><th>期日</th><th>金額</th><th>日数差</th></tr></thead>
          <tbody>${(p.past_items||[]).map(it => {
            const i = new Date(it.issue_date), d = new Date(it.due_date);
            const days = Math.round((d - i)/86400000);
            return `<tr><td>${dateJP(it.issue_date)}</td><td>${dateJP(it.due_date)}</td><td>${yen(it.amount)}</td><td>${days}日</td></tr>`;
          }).join('')}</tbody>
        </table>
      </div>
    </div>` : '';

  if (!p.future || p.future.length === 0) {
    wrap.innerHTML = pastItemsHtml + `<div class="alert warn">${p.partner}: 今後12ヶ月以内の予測がありません。頻度・締め日・サイトを編集してから再度お試しください。</div>`;
    wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  wrap.innerHTML = pastItemsHtml + `
    <div class="card">
      <div class="card-header">
        <h2>${p.partner} — 月別予測明細</h2>
        <button class="btn btn-secondary btn-small" onclick="document.getElementById('fc-detail-wrap').innerHTML=''">閉じる</button>
      </div>
      <div class="hint">下記の金額を変更して「月別金額を保存」を押すと、その月の予測が固定されます。状態列に「編集済」が表示されれば保存完了です。</div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>請求日</th><th>${window._forecastKind==='income'?'入金':'支払'}予定日</th><th>予測金額（編集可）</th><th>状態</th></tr></thead>
          <tbody>${(p.future||[]).map(f => {
            const ymKey = f.issue_date.slice(0,7);
            const rowBg = f.is_override ? 'background:#fff8e1' : '';
            return `<tr style="${rowBg}">
              <td>${dateJP(f.issue_date)}</td>
              <td>${dateJP(f.due_date)}</td>
              <td><input type="text" inputmode="numeric" class="fc-month-amt numeric-format" data-ym="${ymKey}" value="${Number(f.amount||0).toLocaleString('ja-JP')}" style="width:150px;text-align:right"/></td>
              <td>${f.is_override ? '<span class="pill warn">編集済</span>' : '<span class="pill info">推定</span>'}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
      <div class="card-footer">
        <button class="btn btn-primary" onclick="window._fcSaveMonthly(${idx})">月別金額を保存</button>
      </div>
    </div>
  `;
  wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

window._fcSaveMonthly = async function(idx) {
  const p = window._forecastPatterns[idx];
  if (!p) return;
  const monthlyOverrides = {};
  document.querySelectorAll('.fc-month-amt').forEach(el => {
    const raw = (el.value || '').replace(/[^0-9-]/g, '');
    monthlyOverrides[el.dataset.ym] = parseInt(raw || '0') || 0;
  });
  console.log('[_fcSaveMonthly] partner=', p.partner, 'overrides=', monthlyOverrides);
  // Fetch current overrides, apply for this partner, save
  const ov = await fetch('/api/forecast-overrides').then(r => r.json());
  const kindKey = window._forecastKind;
  if (!ov[kindKey]) ov[kindKey] = {};
  const prev = ov[kindKey][p.partner] || {};
  ov[kindKey][p.partner] = {
    ...prev,
    frequency_months: p.frequency_months,
    close_day: p.close_day,
    payment_term_days: p.payment_term_days,
    payment_offset_months: prev.payment_offset_months ?? termMonthOffset(p),
    payment_day: prev.payment_day ?? termPayDay(p),
    avg_amount: p.avg_amount,
    monthly_overrides: monthlyOverrides,
  };
  const resp = await fetch('/api/forecast-overrides', {
    method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(ov)
  });
  console.log('[_fcSaveMonthly] saved, status=', resp.status);
  flash('月別金額を保存しました');
  // ★ 再レンダー後に同じ partner の詳細を自動再オープン
  window._fcReopenPartner = p.partner;
  state.forecast = null;
  renderPage(state.currentRoute);
};

// 削除候補をローカルで管理（partner名のSet）
window._fcDelMarks = window._fcDelMarks || new Set();

window._fcDel = function(idx) {
  const p = window._forecastPatterns[idx];
  if (!p) return;
  const tr = document.querySelector(`tr[data-fc-idx="${idx}"]`);
  if (!tr) return;
  if (window._fcDelMarks.has(p.partner)) {
    // 取消: マーク解除
    window._fcDelMarks.delete(p.partner);
    tr.classList.remove('row-deleted');
    const btn = tr.querySelector('button[data-fc-action="del"]');
    if (btn) { btn.textContent = '削除'; btn.className = 'btn btn-danger btn-small'; }
  } else {
    window._fcDelMarks.add(p.partner);
    tr.classList.add('row-deleted');
    const btn = tr.querySelector('button[data-fc-action="del"]');
    if (btn) { btn.textContent = '取消'; btn.className = 'btn btn-secondary btn-small'; }
  }
  // バッジ表示
  updateDeleteBadge();
};

function updateDeleteBadge() {
  const badge = document.getElementById('fc-del-count');
  if (badge) {
    const n = window._fcDelMarks.size;
    badge.textContent = n > 0 ? `(削除予定 ${n}件)` : '';
  }
}

// Save all row-level edits at once
document.addEventListener('click', async (e) => {
  const t = e.target;
  if (!t) return;
  // 予測編集ボタン (event delegation, closestで子要素クリックも捕捉)
  const fcBtn = t.closest && t.closest('button[data-fc-action]');
  if (fcBtn) {
    const action = fcBtn.dataset.fcAction;
    const idx = parseInt(fcBtn.dataset.idx);
    console.log('[fc-click]', action, 'idx=', idx, 'patterns=', (window._forecastPatterns||[]).length);
    if (action === 'detail') {
      try { window._fcDetail(idx); }
      catch (err) { console.error(err); alert('詳細表示エラー: ' + err.message); }
      return;
    }
    if (action === 'del') {
      try { window._fcDel(idx); }
      catch (err) { console.error(err); alert('削除エラー: ' + err.message); }
      return;
    }
  }
  if (t.id === 'fc-add-new') {
    window._fcAddNew();
    return;
  }
  if (t.id === 'fc-save-all') {
    const ov = await fetch('/api/forecast-overrides').then(r => r.json());
    const kindKey = window._forecastKind;
    if (!ov[kindKey]) ov[kindKey] = {};
    let changedCount = 0;
    // 通常編集 (削除マーク行は除外)
    document.querySelectorAll('tr[data-fc-idx]').forEach(tr => {
      const idx = parseInt(tr.dataset.fcIdx);
      const p = window._forecastPatterns[idx];
      if (!p) return;
      if (window._fcDelMarks.has(p.partner)) {
        ov[kindKey][p.partner] = {...(ov[kindKey][p.partner] || {}), deleted: true};
        changedCount++;
        return;
      }
      const freq = parseInt(tr.querySelector('.fc-freq').value);
      const close = parseInt(tr.querySelector('.fc-close').value);
      const termMonth = parseInt(tr.querySelector('.fc-term-month').value);
      const termDay = parseInt(tr.querySelector('.fc-term-day').value);
      const term = structToTermDays(termMonth, termDay, close);
      // カンマ除去して数値化
      const amtRaw = (tr.querySelector('.fc-amount').value || '').replace(/[^0-9-]/g, '');
      const amount = parseInt(amtRaw || '0') || 0;
      const taxSel = tr.querySelector('.fc-tax');
      const taxRate = taxSel ? parseFloat(taxSel.value) : (p.tax_rate ?? 10);
      // ★ 変更検出: 元の値と比較
      const prevOffset = typeof p.payment_offset_months === 'number' ? p.payment_offset_months : termMonthOffset(p);
      const prevDay = typeof p.payment_day === 'number' ? p.payment_day : termPayDay(p);
      const prevTax = Number(p.tax_rate ?? 10);
      const changed = (
        freq !== p.frequency_months
        || close !== p.close_day
        || termMonth !== prevOffset
        || termDay !== prevDay
        || amount !== Number(p.avg_amount)
        || taxRate !== prevTax
      );
      // ★ 変更のあった行だけ保存 (触ってない行はDB値を保持)
      if (changed) {
        ov[kindKey][p.partner] = {
          ...(ov[kindKey][p.partner] || {}),
          frequency_months: freq,
          close_day: close,
          payment_term_days: term,
          payment_offset_months: termMonth,
          payment_day: termDay,
          avg_amount: amount,
          tax_rate: taxRate,
        };
        changedCount++;
      }
    });
    await fetch('/api/forecast-overrides', {
      method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(ov)
    });
    const delCount = window._fcDelMarks.size;
    window._fcDelMarks.clear();
    flash(`編集を保存しました (変更 ${changedCount}行${delCount > 0 ? ` / 削除 ${delCount}件` : ''})`);
    renderPage(state.currentRoute);
  }
});

// 数値入力にカンマを自動挿入 (.numeric-format クラス)
document.addEventListener('input', (e) => {
  const t = e.target;
  if (!t || !t.classList || !t.classList.contains('numeric-format')) return;
  const raw = (t.value || '').replace(/[^0-9-]/g, '');
  const num = parseInt(raw || '0') || 0;
  const formatted = num.toLocaleString('ja-JP');
  if (t.value !== formatted) {
    const beforeLen = t.value.length;
    const pos = t.selectionStart;
    t.value = formatted;
    const afterLen = formatted.length;
    const diff = afterLen - beforeLen;
    try { t.selectionStart = t.selectionEnd = Math.max(0, pos + diff); } catch (_) {}
  }
});


// ============================================================
// Page: Diagnostics
// ============================================================

async function renderDiagnostics(c) {
  c.innerHTML = '<div class="empty-state"><div class="icon">⌛</div><div>診断中... (数秒〜30秒かかります)</div></div>';
  try {
    const r = await fetch('/api/diagnostics').then(x => x.json());
    const rows = r.results || [];
    const okCount = rows.filter(x => x.ok).length;
    const failCount = rows.filter(x => !x.ok).length;
    // Also fetch raw walletables for balance debugging
    let rawWalletables = null;
    try {
      rawWalletables = await fetch('/api/raw/api/1/walletables?with_balance=true').then(x => x.json());
    } catch(e) {}
    c.innerHTML = `
      <div class="kpis">
        <div class="kpi-card kpi-ok"><div class="kpi-label">成功</div><div class="kpi-value">${okCount}</div></div>
        <div class="kpi-card ${failCount > 0 ? 'kpi-danger' : ''}"><div class="kpi-label">失敗</div><div class="kpi-value">${failCount}</div></div>
      </div>

      ${failCount > 0 ? `
      <div class="alert warn">
        <strong>給与・従業員データが取れない場合の対処：</strong><br>
        1. freee Developers (<a href="https://app.secure.freee.co.jp/developers/applications" target="_blank">アプリ管理</a>) を開く<br>
        2. このアプリを選択 → 「権限設定」タブ<br>
        3. 「freee人事労務」セクションの「事業所」「従業員」「給与明細」に <strong>読み取り権限</strong> をチェック<br>
        4. 「下書き保存」 → 当アプリで「連携解除」 → 再度「freeeと連携」<br>
        その際、認可画面で <strong>freee人事労務</strong> 側の事業所も選択・許可してください
      </div>
      ` : ''}

      <div class="card">
        <div class="card-header"><h2>診断結果</h2></div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th>結果</th><th style="text-align:left">チェック項目</th><th style="text-align:left">詳細</th></tr></thead>
            <tbody>${rows.map(x => `<tr>
              <td><span class="pill ${x.ok ? 'ok' : 'danger'}">${x.ok ? 'OK' : 'NG'}</span></td>
              <td style="text-align:left">${x.label}</td>
              <td style="text-align:left;font-size:11px;color:#374151;word-break:break-all;white-space:normal">${(x.detail || '').replace(/</g, '&lt;')}</td>
            </tr>`).join('')}</tbody>
          </table>
        </div>
      </div>

      ${rawWalletables && rawWalletables.walletables ? `
      <div class="card">
        <div class="card-header">
          <h2>銀行口座 生データ（freee /api/1/walletables）</h2>
          <span class="meta">残金が合わない時はここを確認</span>
        </div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th>id</th><th style="text-align:left">名前</th><th style="text-align:left">type</th><th>walletable_balance</th><th>last_balance</th></tr></thead>
            <tbody>${rawWalletables.walletables.map(w => `<tr>
              <td>${w.id}</td>
              <td style="text-align:left">${w.name || ''}</td>
              <td style="text-align:left">${w.type || ''}</td>
              <td>${yen(w.walletable_balance)}</td>
              <td>${yen(w.last_balance)}</td>
            </tr>`).join('')}
            <tr class="row-balance">
              <td colspan="3" style="text-align:right"><strong>合計</strong></td>
              <td><strong>${yen(rawWalletables.walletables.reduce((s, w) => s + (w.walletable_balance || 0), 0))}</strong></td>
              <td><strong>${yen(rawWalletables.walletables.reduce((s, w) => s + (w.last_balance || 0), 0))}</strong></td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
      ` : ''}

      <div class="card">
        <div class="card-header"><h2>任意のfreee APIを直接叩く</h2></div>
        <div style="padding:16px">
          <div style="font-size:12px;color:#6b7280;margin-bottom:8px">パスを入力（例: api/1/walletables, api/1/deals?start_issue_date=2026-04-01）</div>
          <div style="display:flex;gap:8px">
            <input id="raw-path" type="text" placeholder="api/1/walletables" style="flex:1;padding:8px;border:1px solid #ddd;border-radius:4px"/>
            <label style="display:flex;align-items:center;gap:4px;font-size:12px"><input type="checkbox" id="raw-hr"/> 人事労務API</label>
            <button class="btn btn-primary" onclick="window._fetchRaw()">取得</button>
          </div>
          <pre id="raw-out" style="margin-top:12px;padding:12px;background:#0a0a1a;color:#a7f3d0;border-radius:6px;max-height:400px;overflow:auto;font-size:11px"></pre>
        </div>
      </div>
    `;
  } catch (e) {
    c.innerHTML = `<div class="alert danger">診断中にエラーが発生: ${e.message}</div>`;
  }
}
window._fetchRaw = async function() {
  const path = document.getElementById('raw-path').value.trim();
  const hr = document.getElementById('raw-hr').checked;
  if (!path) return;
  const out = document.getElementById('raw-out');
  out.textContent = '取得中...';
  try {
    const sep = path.includes('?') ? '&' : '?';
    const url = '/api/raw/' + path.replace(/^\//, '') + (hr ? sep + 'hr=1' : '');
    const r = await fetch(url).then(x => x.json());
    out.textContent = JSON.stringify(r, null, 2);
  } catch (e) {
    out.textContent = 'Error: ' + e.message;
  }
};

// ============================================================
// Boot
// ============================================================

bootstrap();
