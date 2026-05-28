// ============================================================
// 追加機能: AIコンサル + 取引先詳細
// app.js とは独立して動作。ハッシュ変化を監視して該当ページを描画。
// ============================================================

(function() {
  const yen = (n) => {
    if (n == null || isNaN(n)) return '--';
    return '¥' + Math.round(Number(n)).toLocaleString('ja-JP');
  };
  const yenShort = (n) => {
    n = Number(n) || 0;
    if (Math.abs(n) >= 100_000_000) return (n/100_000_000).toFixed(2) + '億円';
    if (Math.abs(n) >= 10_000) return Math.round(n/10_000).toLocaleString() + '万円';
    return n.toLocaleString() + '円';
  };

  // ============================================================
  // AI Consult
  // ============================================================
  let aiState = { currentConsultant: 'accounting', history: {} };

  async function renderAiConsult(container) {
    container.innerHTML = '<div style="padding:20px;color:#64748b;">AIコンサル読込中...</div>';
    try {
      const r = await fetch('/api/ai-consultants').then(x => x.json());
      const consultants = r.consultants || [];
      // 初期化
      consultants.forEach(c => {
        if (!aiState.history[c.id]) aiState.history[c.id] = [];
      });
      const c = aiState.currentConsultant;
      const tabs = consultants.map(con => `
        <div class="ai-tab ${con.id === c ? 'active' : ''}" data-cid="${con.id}"
             style="border-bottom-color: ${con.id === c ? con.color : 'transparent'};">
          <div class="ai-tab-icon" style="background:${con.color}22;color:${con.color};">${con.icon}</div>
          <div class="ai-tab-text">
            <div class="ai-tab-name">${con.name}</div>
            <div class="ai-tab-tagline">${con.tagline}</div>
          </div>
        </div>
      `).join('');

      const current = consultants.find(x => x.id === c);
      const messages = aiState.history[c] || [];
      const msgHtml = messages.length === 0
        ? `<div class="ai-greeting" style="border-color:${current.color}44;">
             <div class="ai-greeting-icon" style="background:${current.color};">${current.icon}</div>
             <div>
               <strong>${current.name}</strong>
               <p style="margin:6px 0 0;color:#475569;">${current.greeting}</p>
               <p style="margin:10px 0 0;font-size:12px;color:#94a3b8;">下の入力欄から質問してください。例: 「月次決算は順調？」「キャッシュフロー見通し」</p>
             </div>
           </div>`
        : messages.map(m => `
            <div class="ai-msg ai-msg-${m.role}">
              ${m.role === 'user' ? '<div class="ai-msg-bubble ai-msg-user-bubble">' + escapeHtml(m.text) + '</div>'
                                  : '<div class="ai-msg-bubble ai-msg-ai-bubble" style="border-color:' + current.color + '33;">' + escapeHtml(m.text).replace(/\n/g, '<br>') + '</div>'}
            </div>
          `).join('');

      const examples = {
        accounting: ['月次決算は順調？', '消費税の納付スケジュール', '仕訳のチェック'],
        finance: ['キャッシュフロー見通し', '借入金の最適化', '楽観シナリオを教えて'],
        sales: ['上位顧客の依存度', '粗利率を上げる方法', 'パイプライン状況'],
        hr: ['人件費の対売上比', '来期の採用計画', '離職リスクが高い層', '評価制度の見直し'],
      };
      const exampleBtns = (examples[c] || []).map(e =>
        `<button class="ai-example-btn" data-q="${escapeHtml(e)}">${e}</button>`
      ).join('');

      container.innerHTML = `
        <div class="info-banner" style="background:#fef3c7;border:1px solid #fcd34d;padding:10px 14px;border-radius:8px;margin-bottom:14px;color:#92400e;font-size:13px;">
          <strong>🤖 AIコンサル機能</strong> ・ 4種の専門コンサル(経理/財務/営業/人事)が貴社データを分析して回答します
        </div>
        <div class="ai-tabs">${tabs}</div>
        <div class="ai-main" style="border-color:${current.color}44;">
          <div class="ai-messages" id="ai-messages">${msgHtml}</div>
          <div class="ai-examples">${exampleBtns}</div>
          <div class="ai-input-row">
            <textarea id="ai-input" placeholder="${current.name}に質問する..." rows="2"></textarea>
            <button id="ai-send" style="background:${current.color};">送信</button>
          </div>
        </div>
      `;

      // tab click
      container.querySelectorAll('.ai-tab').forEach(t => {
        t.addEventListener('click', () => {
          aiState.currentConsultant = t.dataset.cid;
          renderAiConsult(container);
        });
      });
      // examples
      container.querySelectorAll('.ai-example-btn').forEach(b => {
        b.addEventListener('click', () => {
          document.getElementById('ai-input').value = b.dataset.q;
          document.getElementById('ai-send').click();
        });
      });
      // send
      document.getElementById('ai-send').addEventListener('click', async () => {
        const input = document.getElementById('ai-input');
        const q = (input.value || '').trim();
        if (!q) return;
        const cid = aiState.currentConsultant;
        aiState.history[cid].push({ role: 'user', text: q });
        input.value = '';
        renderAiConsult(container);
        try {
          const resp = await fetch('/api/ai-consult', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ consultant_id: cid, query: q })
          }).then(x => x.json());
          aiState.history[cid].push({ role: 'ai', text: resp.answer || '(回答なし)' });
        } catch (e) {
          aiState.history[cid].push({ role: 'ai', text: 'エラー: ' + e.message });
        }
        renderAiConsult(container);
      });
      // enter key
      document.getElementById('ai-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
          document.getElementById('ai-send').click();
        }
      });
    } catch (e) {
      container.innerHTML = '<div style="color:#b91c1c;padding:20px;">エラー: ' + e.message + '</div>';
    }
  }

  // ============================================================
  // Partners list
  // ============================================================
  async function renderPartners(container) {
    container.innerHTML = '<div style="padding:20px;color:#64748b;">取引先一覧読込中...</div>';
    try {
      const r = await fetch('/api/partners').then(x => x.json());
      const partners = r.data || [];
      let filter = '';
      const renderList = () => {
        const filtered = partners.filter(p =>
          !filter || p.name.toLowerCase().includes(filter.toLowerCase()));
        container.innerHTML = `
          <div class="info-banner" style="background:#eff6ff;border:1px solid #bfdbfe;padding:10px 14px;border-radius:8px;margin-bottom:14px;color:#1e40af;font-size:13px;">
            <strong>🏢 取引先マスタ</strong> ・ ${partners.length}社 ・ クリックすると過去5年の取引履歴、契約書、商談履歴が見られます
          </div>
          <div style="margin-bottom:12px;">
            <input id="partner-filter" placeholder="取引先名で検索..." value="${escapeHtml(filter)}"
                   style="width:300px;padding:8px 12px;border:1px solid #cbd5e1;border-radius:6px;">
          </div>
          <table class="data-table">
            <thead><tr><th style="text-align:left;">コード</th><th style="text-align:left;">取引先名</th><th style="text-align:left;">区分</th><th></th></tr></thead>
            <tbody>${filtered.map(p => `
              <tr>
                <td style="text-align:left;">${p.code}</td>
                <td style="text-align:left;">${p.name}</td>
                <td style="text-align:left;">${p.is_spot ? 'スポット' : '常時取引'}</td>
                <td><button class="btn btn-small btn-primary" data-pid="${p.id}">詳細 ›</button></td>
              </tr>
            `).join('')}</tbody>
          </table>
        `;
        document.getElementById('partner-filter').addEventListener('input', (e) => {
          filter = e.target.value;
          renderList();
        });
        container.querySelectorAll('button[data-pid]').forEach(b => {
          b.addEventListener('click', () => showPartnerDetail(parseInt(b.dataset.pid)));
        });
      };
      renderList();
    } catch (e) {
      container.innerHTML = '<div style="color:#b91c1c;padding:20px;">エラー: ' + e.message + '</div>';
    }
  }

  async function showPartnerDetail(pid) {
    const modal = document.getElementById('partner-detail-modal');
    const body = document.getElementById('partner-detail-body');
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#64748b;">読込中...</div>';
    modal.removeAttribute('hidden');
    try {
      const d = await fetch('/api/partner-detail?id=' + pid).then(x => x.json());
      // Group income by year
      const byYear = {};
      (d.income_history || []).forEach(h => {
        const y = h.year_month.slice(0,4);
        if (!byYear[y]) byYear[y] = 0;
        byYear[y] += h.amount;
      });
      const yearlyHtml = Object.entries(byYear).sort().map(([y,a]) =>
        `<tr><td style="text-align:left;">${y}年</td><td style="text-align:right;">${yen(a)}</td></tr>`
      ).join('');

      const contractsHtml = (d.contracts || []).map((c, idx) => `
        <div class="contract-card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <strong>${c.title}</strong>
            <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${c.status === '有効' ? '#d1fae5' : '#fee2e2'};color:${c.status === '有効' ? '#065f46' : '#991b1b'};">${c.status}</span>
          </div>
          <div style="font-size:12px;color:#64748b;line-height:1.6;">
            期間: ${c.start_date} 〜 ${c.end_date} ${c.auto_renewal ? '(自動更新)' : ''}<br>
            月額: ${yen(c.monthly_amount)} / 契約ID: ${c.id}<br>
            締結担当: ${c.signed_by_internal}
          </div>
          <a href="/api/contract-pdf/${pid}/${idx}" target="_blank" class="btn btn-small btn-primary" style="margin-top:8px;display:inline-block;">📄 契約書PDFを開く</a>
        </div>
      `).join('');

      const meetingsHtml = (d.meetings || []).slice(0, 10).map(m => `
        <tr>
          <td style="text-align:left;">${m.date}</td>
          <td style="text-align:left;">${m.type}</td>
          <td style="text-align:left;">${m.attendees_internal} ↔ ${m.attendees_partner}</td>
          <td style="text-align:left;">${(m.topics || []).join(' / ')}</td>
          <td style="text-align:left;">${m.outcome}</td>
        </tr>
      `).join('');

      const contactsHtml = (d.partner_contacts || []).map(c => `
        <div class="contact-card">
          <div><strong>${c.name}</strong> <span style="color:#64748b;">${c.title}</span></div>
          <div style="font-size:12px;color:#64748b;">${c.email} / TEL: ${c.phone} / 携帯: ${c.mobile}</div>
        </div>
      `).join('');

      body.innerHTML = `
        <h2 style="margin:0 0 8px 0;">${d.partner.name}</h2>
        <div style="color:#64748b;margin-bottom:16px;font-size:13px;">
          取引先コード: ${d.partner.code} ・ 区分: ${d.partner.is_spot ? 'スポット' : '常時取引'}
        </div>

        <div class="partner-grid">
          <div class="partner-block">
            <h3>👤 当方担当</h3>
            <div><strong>${d.internal_pic.name}</strong> ${d.internal_pic.role}</div>
            <div style="font-size:12px;color:#64748b;">${d.internal_pic.dept}<br>${d.internal_pic.email} / ${d.internal_pic.phone}</div>
          </div>
          <div class="partner-block">
            <h3>🏦 入金/支払口座</h3>
            <div>${d.bank_account.bank} ${d.bank_account.branch}</div>
            <div style="font-size:12px;color:#64748b;">${d.bank_account.type} ${d.bank_account.number}</div>
          </div>
          <div class="partner-block">
            <h3>📋 取引条件</h3>
            <div style="font-size:13px;line-height:1.7;">
              入金: ${d.payment_terms.income_close_day}締 / ${d.payment_terms.income_payment_day}<br>
              支払: ${d.payment_terms.expense_close_day}締 / ${d.payment_terms.expense_payment_day}<br>
              消費税: ${d.payment_terms.tax_rate}%
            </div>
          </div>
          <div class="partner-block">
            <h3>📊 5年累計</h3>
            <div style="font-size:13px;line-height:1.7;">
              入金累計: ${yenShort(d.summary_5y.total_income)}<br>
              月平均入金: ${yenShort(d.summary_5y.avg_monthly_income)}<br>
              初回取引: ${d.summary_5y.first_transaction || '-'}
            </div>
          </div>
        </div>

        <h3 style="margin-top:24px;">👥 取引先担当者 (${(d.partner_contacts || []).length}名)</h3>
        ${contactsHtml}

        <h3 style="margin-top:24px;">📄 締結中の契約 (${(d.contracts || []).length}件)</h3>
        ${contractsHtml}

        <h3 style="margin-top:24px;">📈 年次取引金額 (過去5年)</h3>
        <table class="data-table" style="max-width:400px;">
          <thead><tr><th style="text-align:left;">年</th><th style="text-align:right;">入金合計</th></tr></thead>
          <tbody>${yearlyHtml}</tbody>
        </table>

        <h3 style="margin-top:24px;">💬 商談履歴 (最新10件 / 全${(d.meetings || []).length}件)</h3>
        <table class="data-table">
          <thead><tr><th style="text-align:left;">日付</th><th style="text-align:left;">種別</th><th style="text-align:left;">参加者</th><th style="text-align:left;">議題</th><th style="text-align:left;">結果</th></tr></thead>
          <tbody>${meetingsHtml}</tbody>
        </table>
      `;
    } catch (e) {
      body.innerHTML = '<div style="color:#b91c1c;padding:20px;">エラー: ' + e.message + '</div>';
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ============================================================
  // Hash router hook
  // ============================================================
  function checkAndRender() {
    const hash = (location.hash || '#home').replace('#', '');
    if (hash === 'ai-consult') {
      const c = document.querySelector('section.page[data-page="ai-consult"]');
      if (c) {
        document.querySelectorAll('section.page').forEach(p => p.classList.remove('active'));
        c.classList.add('active');
        const titleEl = document.getElementById('page-title');
        const subEl = document.getElementById('page-subtitle');
        if (titleEl) titleEl.textContent = 'AIコンサル';
        if (subEl) subEl.textContent = '4種の専門AIが貴社データを分析・助言';
        document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.route === hash));
        renderAiConsult(c);
      }
    } else if (hash === 'partners') {
      const c = document.querySelector('section.page[data-page="partners"]');
      if (c) {
        document.querySelectorAll('section.page').forEach(p => p.classList.remove('active'));
        c.classList.add('active');
        const titleEl = document.getElementById('page-title');
        const subEl = document.getElementById('page-subtitle');
        if (titleEl) titleEl.textContent = '取引先一覧';
        if (subEl) subEl.textContent = '110社の詳細データ（過去5年） / 契約書 / 商談履歴';
        document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.route === hash));
        renderPartners(c);
      }
    }
  }

  window.addEventListener('hashchange', checkAndRender);
  window.addEventListener('DOMContentLoaded', () => {
    // Inject extra page sections if missing
    const pageWrap = document.querySelector('.page-wrap');
    if (pageWrap) {
      ['ai-consult', 'partners'].forEach(p => {
        if (!document.querySelector(`section.page[data-page="${p}"]`)) {
          const sec = document.createElement('section');
          sec.className = 'page';
          sec.dataset.page = p;
          pageWrap.appendChild(sec);
        }
      });
    }
    // Inject modal
    if (!document.getElementById('partner-detail-modal')) {
      const m = document.createElement('div');
      m.id = 'partner-detail-modal';
      m.className = 'org-modal';
      m.setAttribute('hidden', '');
      m.addEventListener('click', (e) => { if (e.target.id === 'partner-detail-modal') m.setAttribute('hidden', ''); });
      m.innerHTML = `
        <div class="org-modal-inner">
          <button class="org-modal-close" onclick="document.getElementById('partner-detail-modal').setAttribute('hidden','');">×</button>
          <div id="partner-detail-body"></div>
        </div>
      `;
      document.body.appendChild(m);
    }
    // Inject sidebar links + active state
    const sidenav = document.getElementById('sidenav');
    if (sidenav && !document.querySelector('a[data-route="ai-consult"]')) {
      // 「労務・人事」セクション直後にAIコンサルを追加 (実は新セクションに)
      const section = document.createElement('div');
      section.className = 'nav-section';
      section.textContent = 'AI / 取引先';
      const aiLink = document.createElement('a');
      aiLink.href = '#ai-consult';
      aiLink.className = 'nav-item';
      aiLink.dataset.route = 'ai-consult';
      aiLink.innerHTML = '<span class="nav-icon">🤖</span> AIコンサル';
      const partnerLink = document.createElement('a');
      partnerLink.href = '#partners';
      partnerLink.className = 'nav-item';
      partnerLink.dataset.route = 'partners';
      partnerLink.innerHTML = '<span class="nav-icon">🏢</span> 取引先一覧';
      sidenav.insertBefore(section, sidenav.firstChild);
      section.after(aiLink);
      aiLink.after(partnerLink);
    }
    checkAndRender();
  });
})();
