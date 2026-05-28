// Partner detail (compact UI)
(function(){
var css = `
.fxsr{display:flex;gap:12px;align-items:center;margin-bottom:14px}
.fxsi{padding:10px 14px;border:1px solid #cbd5e1;border-radius:10px;font-size:13px;min-width:320px;outline:none;transition:border-color .15s}
.fxsi:focus{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.1)}
.fxpc{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;transition:all .15s}
.fxpc:hover{transform:translateX(3px);border-color:#cbd5e1;box-shadow:0 4px 12px rgba(0,0,0,.04)}
.fxpl{display:flex;align-items:center;gap:14px}
.fxpa{width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#fef3c7,#fde68a);display:flex;align-items:center;justify-content:center;font-size:18px;color:#92400e;font-weight:700}
.fxpn{font-weight:700;color:#1e293b;font-size:14px}
.fxpm{font-size:11px;color:#64748b;margin-top:2px}
.fxpb{padding:8px 16px;background:#001338;color:#fff;border:none;border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;transition:all .15s}
.fxpb:hover{background:#1a2350;transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,19,56,.18)}
.fxmd{position:fixed;inset:0;background:rgba(15,23,42,.6);z-index:9999;display:flex;align-items:flex-start;justify-content:center;padding:40px 20px;overflow-y:auto}
.fxmd[hidden]{display:none!important}
.fxmdi{background:#fff;border-radius:14px;max-width:920px;width:100%;position:relative;box-shadow:0 24px 80px rgba(0,0,0,.25);overflow:hidden}
.fxmdh{background:linear-gradient(135deg,#001338,#2a3b6e);color:#fff;padding:24px 32px}
.fxmdh h2{margin:0 0 4px;font-size:22px;font-weight:700}
.fxmds{font-size:12px;opacity:.78}
.fxmdc{position:absolute;top:18px;right:22px;background:rgba(255,255,255,.18);color:#fff;border:none;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:20px;line-height:1;transition:all .15s}
.fxmdc:hover{background:rgba(255,255,255,.3);transform:rotate(90deg)}
.fxmdb{padding:24px 32px 32px;max-height:75vh;overflow-y:auto}
.fxig{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:24px}
.fxib{background:linear-gradient(180deg,#fff,#fafbfc);border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px}
.fxib h3{margin:0 0 10px;font-size:12px;color:#64748b;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.fxibm{font-weight:700;font-size:14px;color:#1e293b}
.fxibs{font-size:12px;color:#64748b;margin-top:4px;line-height:1.6}
.fxst{font-size:14px;font-weight:700;color:#1e293b;margin:28px 0 12px;padding-bottom:8px;border-bottom:2px solid #fde68a}
.fxcc{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:14px}
.fxca{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#ddd6fe,#c4b5fd);color:#5b21b6;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}
.fxck{background:linear-gradient(180deg,#fffbeb,#fef3c7);border:1px solid #fcd34d;border-radius:12px;padding:14px 18px;margin-bottom:10px}
.fxckh{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.fxckt{font-weight:700;color:#78350f;font-size:14px}
.fxcks{padding:3px 10px;border-radius:999px;font-size:10.5px;font-weight:700}
.fxcksa{background:#d1fae5;color:#065f46}
.fxckse{background:#fee2e2;color:#991b1b}
.fxckm{font-size:12px;color:#78350f;line-height:1.7}
.fxckb{display:inline-flex;align-items:center;gap:6px;margin-top:10px;padding:8px 14px;background:#fff;color:#001338;border:1px solid #fcd34d;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none}
.fxckb:hover{background:#001338;color:#fff}
.fxdt{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.fxdt th{background:#f8fafc;color:#475569;padding:10px 14px;font-size:11px;font-weight:700;text-transform:uppercase;text-align:left;border-bottom:1px solid #e5e7eb}
.fxdt td{padding:10px 14px;font-size:13px;color:#1e293b;border-bottom:1px solid #f1f5f9}
.fxdt tr:hover td{background:#fafbfc}
.fxdt .num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
`;
var st = document.createElement('style');
st.id = 'fxstyle2'; st.textContent = css;
if (!document.getElementById('fxstyle2')) document.head.appendChild(st);

var FX = window.FX = window.FX || {};
if(!FX.esc) FX.esc = function(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); };
if(!FX.yen) FX.yen = function(n){ return n==null||isNaN(n) ? '--' : '¥' + Math.round(Number(n)).toLocaleString('ja-JP'); };
if(!FX.yenS) FX.yenS = function(n){ n = Number(n)||0; if(Math.abs(n)>=1e8) return (n/1e8).toFixed(2)+'億円'; if(Math.abs(n)>=1e4) return Math.round(n/1e4).toLocaleString()+'万円'; return n.toLocaleString()+'円'; };

async function renderPartners(container){
  try {
    var r = await fetch('/api/partners').then(function(x){return x.json();});
    var ps = r.data || [];
    var filter = '';
    function render(){
      var fp = ps.filter(function(p){ return !filter || p.name.toLowerCase().indexOf(filter.toLowerCase())>=0; });
      var cards = fp.map(function(p){
        var n1 = p.name.replace(/^株式会社|^合同会社|^有限会社|^一般社団法人/,'').slice(0,1);
        return '<div class="fxpc"><div class="fxpl"><div class="fxpa">'+n1+'</div><div><div class="fxpn">'+p.name+'</div><div class="fxpm">'+p.code+' ・ '+(p.is_spot?'スポット取引':'常時取引')+'</div></div></div><button class="fxpb" data-pid="'+p.id+'">詳細を見る ›</button></div>';
      }).join('');
      container.innerHTML =
        '<div class="fxh" style="background:linear-gradient(135deg,#0c4a6e,#0369a1)"><div class="fxh-bdg" style="background:rgba(56,189,248,.2);color:#7dd3fc">🏢 PARTNER MASTER</div><h2>取引先一覧</h2><p>'+ps.length+'社 ・ 詳細ボタンで過去5年の入出金、契約書PDF、商談履歴、担当者情報まで全て見られます</p></div>' +
        '<div class="fxsr"><input class="fxsi" id="fxpf" placeholder="🔍 取引先名で検索..." value="'+FX.esc(filter)+'"><div style="color:#64748b;font-size:13px">'+fp.length+'件表示</div></div>' +
        cards;
      var f = document.getElementById('fxpf'); if(f) f.addEventListener('input', function(e){ filter=e.target.value; render(); });
      container.querySelectorAll('button[data-pid]').forEach(function(b){ b.addEventListener('click', function(){ showDetail(parseInt(b.dataset.pid)); }); });
    }
    render();
  } catch(e) { container.innerHTML = '<div style="color:#b91c1c;padding:20px">エラー:'+e.message+'</div>'; }
}

async function showDetail(pid){
  var m = document.getElementById('fxmd');
  if(!m){
    m = document.createElement('div'); m.id='fxmd'; m.className='fxmd'; m.setAttribute('hidden','');
    m.addEventListener('click', function(e){ if(e.target.id==='fxmd') m.setAttribute('hidden',''); });
    document.body.appendChild(m);
  }
  m.innerHTML = '<div class="fxmdi"><button class="fxmdc" onclick="document.getElementById(\'fxmd\').setAttribute(\'hidden\',\'\')">×</button><div id="fxmdc"><div style="padding:40px;text-align:center;color:#94a3b8">読込中...</div></div></div>';
  m.removeAttribute('hidden');
  try {
    var d = await fetch('/api/partner-detail?id='+pid).then(function(x){return x.json();});
    var byY = {};
    (d.income_history||[]).forEach(function(h){ var y=h.year_month.slice(0,4); byY[y]=(byY[y]||0)+h.amount; });
    var yH = Object.entries(byY).sort().map(function(e){ return '<tr><td>'+e[0]+'年</td><td class="num">'+FX.yen(e[1])+'</td></tr>'; }).join('');
    var cH = (d.contracts||[]).map(function(c, idx){
      return '<div class="fxck"><div class="fxckh"><div class="fxckt">📄 '+c.title+'</div><span class="fxcks '+(c.status==='有効'?'fxcksa':'fxckse')+'">'+c.status+'</span></div><div class="fxckm">期間: '+c.start_date+' 〜 '+c.end_date+' '+(c.auto_renewal?'<span style="background:#fff;padding:1px 6px;border-radius:4px;font-size:10px">自動更新</span>':'')+'<br>月額: <strong>'+FX.yen(c.monthly_amount)+'</strong> ・ 契約ID: '+c.id+'<br>締結担当: '+c.signed_by_internal+'</div><a href="/api/contract-pdf/'+pid+'/'+idx+'" target="_blank" class="fxckb">📄 契約書PDFを開く</a></div>';
    }).join('');
    var mH = (d.meetings||[]).slice(0,10).map(function(t){
      return '<tr><td>'+t.date+'</td><td>'+t.type+'</td><td>'+t.attendees_internal+' ↔ '+t.attendees_partner+'</td><td style="font-size:12px">'+(t.topics||[]).join(' / ')+'</td><td>'+t.outcome+'</td></tr>';
    }).join('');
    var ctH = (d.partner_contacts||[]).map(function(c){
      return '<div class="fxcc"><div class="fxca">'+c.name.slice(0,1)+'</div><div><strong>'+c.name+'</strong> <span style="color:#64748b;font-size:12px">'+c.title+'</span><div style="font-size:11px;color:#64748b;margin-top:2px">✉️ '+c.email+' ・ ☎️ '+c.phone+' ・ 📱 '+c.mobile+'</div></div></div>';
    }).join('');
    document.getElementById('fxmdc').innerHTML =
      '<div class="fxmdh"><div class="fxmds">取引先コード: '+d.partner.code+' ・ '+(d.partner.is_spot?'スポット取引':'常時取引')+'</div><h2>'+d.partner.name+'</h2></div>' +
      '<div class="fxmdb">' +
        '<div class="fxig">' +
          '<div class="fxib"><h3>👤 当方担当</h3><div class="fxibm">'+d.internal_pic.name+'</div><div class="fxibs">'+d.internal_pic.role+' ('+d.internal_pic.dept+')<br>'+d.internal_pic.email+'<br>'+d.internal_pic.phone+'</div></div>' +
          '<div class="fxib"><h3>🏦 取引銀行口座</h3><div class="fxibm">'+d.bank_account.bank+'</div><div class="fxibs">'+d.bank_account.branch+' '+d.bank_account.type+'<br>口座番号: '+d.bank_account.number+'</div></div>' +
          '<div class="fxib"><h3>📋 取引条件</h3><div class="fxibs" style="margin-top:0"><strong>入金:</strong> '+d.payment_terms.income_close_day+'締 / '+d.payment_terms.income_payment_day+'<br><strong>支払:</strong> '+d.payment_terms.expense_close_day+'締 / '+d.payment_terms.expense_payment_day+'<br>消費税: '+d.payment_terms.tax_rate+'%</div></div>' +
          '<div class="fxib"><h3>📊 5年累計</h3><div class="fxibm">'+FX.yenS(d.summary_5y.total_income)+'</div><div class="fxibs">月平均: '+FX.yenS(d.summary_5y.avg_monthly_income)+'<br>初取引: '+(d.summary_5y.first_transaction||'-')+'</div></div>' +
        '</div>' +
        '<div class="fxst">👥 取引先担当者 ('+(d.partner_contacts||[]).length+'名)</div>'+ctH +
        '<div class="fxst">📄 締結中の契約 ('+(d.contracts||[]).length+'件)</div>'+cH +
        '<div class="fxst">📈 年次取引金額 (過去5年)</div>' +
        '<table class="fxdt" style="max-width:420px"><thead><tr><th>年</th><th style="text-align:right">入金合計</th></tr></thead><tbody>'+yH+'</tbody></table>' +
        '<div class="fxst">💬 商談履歴 (最新10件 / 全'+(d.meetings||[]).length+'件)</div>' +
        '<table class="fxdt"><thead><tr><th>日付</th><th>種別</th><th>参加者</th><th>議題</th><th>結果</th></tr></thead><tbody>'+mH+'</tbody></table>' +
      '</div>';
  } catch(e) { document.getElementById('fxmdc').innerHTML = '<div style="color:#b91c1c;padding:20px">エラー:'+e.message+'</div>'; }
}

FX.renderPartners = renderPartners;
FX.showDetail = showDetail;
})();
