// AIコンサル + ルーティング (高度版: typewriter / localStorage / freeeボタン)
(function(){
var css = `
.fxh{background:linear-gradient(135deg,#001338,#1a2350);color:#fff;border-radius:14px;padding:22px 26px;margin-bottom:18px;box-shadow:0 8px 32px rgba(0,19,56,.18)}
.fxh h2{margin:0 0 6px;font-size:20px;font-weight:700}
.fxh p{margin:0;opacity:.78;font-size:13px;line-height:1.55}
.fxh-bdg{display:inline-block;background:rgba(229,199,110,.18);color:#E5C76E;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:600;margin-bottom:8px}
.fxts{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-bottom:16px}
.fxt{display:flex;align-items:center;gap:10px;padding:12px 14px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.fxt:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(0,0,0,.06)}
.fxt.active{border-color:transparent;box-shadow:0 6px 18px var(--ts)}
.fxt.active::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--tc)}
.fxti{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0}
.fxtn{font-weight:700;font-size:12px;color:#1e293b}
.fxtg{font-size:10px;color:#64748b;margin-top:2px;line-height:1.3}
.fxc{background:#fff;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 4px 12px rgba(15,23,42,.04);overflow:hidden}
.fxch{padding:14px 18px;background:#fafbfc;border-bottom:1px solid #f1f5f9;display:flex;gap:10px;align-items:center;justify-content:space-between}
.fxchl{display:flex;gap:10px;align-items:center}
.fxchi{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;color:#fff}
.fxch-clr{font-size:11px;color:#94a3b8;cursor:pointer;padding:4px 10px;border:1px solid #e5e7eb;border-radius:6px;background:#fff}
.fxch-clr:hover{background:#f9fafb;color:#475569}
.fxcm{padding:18px;max-height:480px;min-height:300px;overflow-y:auto;background:linear-gradient(180deg,#f8fafc,#fff 60%)}
.fxg{display:flex;gap:14px;padding:18px 20px;background:#fff;border:1px solid #f1f5f9;border-radius:12px}
.fxgi{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;color:#fff;flex-shrink:0}
.fxgb p{margin:6px 0 0;color:#475569;font-size:13px;line-height:1.6}
.fxmr{display:flex;margin-bottom:14px;gap:10px;animation:fxf .3s ease}
.fxmr-u{justify-content:flex-end}
@keyframes fxf{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.fxma{width:32px;height:32px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:15px;color:#fff;flex-shrink:0}
.fxmb{padding:12px 16px;border-radius:14px;max-width:78%;line-height:1.7;font-size:13.5px;white-space:pre-wrap}
.fxmb-u{background:#001338;color:#fff;border-bottom-right-radius:4px;box-shadow:0 4px 12px rgba(0,19,56,.18)}
.fxmb-a{background:#fff;border:1px solid #e5e7eb;color:#1e293b;border-bottom-left-radius:4px;box-shadow:0 2px 6px rgba(0,0,0,.04)}
.fxmb-typing::after{content:'▊';animation:fxblink 1s infinite;color:#94a3b8}
@keyframes fxblink{50%{opacity:0}}
.fxex{display:flex;gap:8px;flex-wrap:wrap;padding:0 18px 14px}
.fxec{padding:8px 14px;font-size:12px;border:1px solid #e5e7eb;background:#fff;border-radius:999px;cursor:pointer;color:#475569;font-weight:500;transition:all .15s}
.fxec:hover{background:var(--ch);border-color:var(--cb);color:var(--cc);transform:translateY(-1px)}
.fxia{padding:14px 18px 18px;background:#fafbfc;border-top:1px solid #f1f5f9}
.fxir{display:flex;gap:10px;align-items:flex-end;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:8px}
.fxir:focus-within{border-color:var(--inf);box-shadow:0 0 0 3px var(--infs)}
.fxir textarea{flex:1;padding:8px 10px;border:none;outline:none;font-size:13.5px;resize:none;font-family:inherit;min-height:42px;max-height:160px;line-height:1.5}
.fxir button{padding:10px 22px;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;font-size:13px;min-width:78px}
.fxih{font-size:11px;color:#94a3b8;margin-top:6px;padding-left:8px}
.fxld{padding:40px;text-align:center;color:#94a3b8;font-size:13px}
.org-exec{background:linear-gradient(135deg,#F5E6B8 0%,#E5C76E 100%)!important;border-color:#C9A852!important}
.org-exec-title{color:#5a4209!important}
.org-exec-name{color:#3a2906!important}
.org-exec-meta{color:#6f5612!important}
.org-modal[hidden]{display:none!important}
.org-modal{position:fixed!important;inset:0;background:rgba(15,23,42,.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:40px 20px;overflow-y:auto}
.org-modal-inner{background:#fff;border-radius:14px;padding:28px 32px;max-width:920px;width:100%;position:relative;box-shadow:0 24px 80px rgba(0,0,0,.25);text-align:center}
.org-modal-inner h2,.org-modal-inner > div:first-of-type{text-align:center}
.org-modal-inner .data-table th,.org-modal-inner .data-table td{text-align:center!important}
.org-modal-close{position:absolute;top:14px;right:18px;background:rgba(0,0,0,.05);color:#475569;border:none;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:20px;line-height:1}
.org-modal-close:hover{background:#001338;color:#fff;transform:rotate(90deg)}
.fxfreee{padding:8px 16px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;font-size:12px;margin-right:8px}
.fxfreee:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(16,185,129,.3)}
.chart-wrap{padding:8px!important;height:240px!important}
`;
var st=document.createElement('style');st.id='fxstyle';st.textContent=css;
if(!document.getElementById('fxstyle'))document.head.appendChild(st);

window.FX=window.FX||{};
window.FX.esc=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')};
window.FX.yen=function(n){return n==null||isNaN(n)?'--':'¥'+Math.round(Number(n)).toLocaleString('ja-JP')};
window.FX.yenS=function(n){n=Number(n)||0;if(Math.abs(n)>=1e8)return(n/1e8).toFixed(2)+'億円';if(Math.abs(n)>=1e4)return Math.round(n/1e4).toLocaleString()+'万円';return n.toLocaleString()+'円'};

// LocalStorage 履歴
var LSK='fx_ai_history_v2';
function loadHistory(){try{return JSON.parse(localStorage.getItem(LSK)||'{}')}catch(e){return{}}}
function saveHistory(h){try{localStorage.setItem(LSK,JSON.stringify(h))}catch(e){}}

var aiState={c:'strategy',h:loadHistory()};
var lastRoute='';

async function renderAI(container){
try{
var r=await fetch('/api/ai-consultants').then(function(x){return x.json()});
var list=r.consultants||[];
list.forEach(function(c){if(!aiState.h[c.id])aiState.h[c.id]=[]});
var cid=aiState.c;
var cur=list.find(function(x){return x.id===cid})||list[0];
var E=window.FX.esc;
var tabs=list.map(function(c){
return '<div class="fxt '+(c.id===cid?'active':'')+'" data-cid="'+c.id+'" style="--tc:'+c.color+';--ts:'+c.color+'33"><div class="fxti" style="background:'+c.color+'22;color:'+c.color+'">'+c.icon+'</div><div><div class="fxtn">'+c.name+'</div><div class="fxtg">'+c.tagline+'</div></div></div>'
}).join('');
var msgs=aiState.h[cid]||[];
var msgH=msgs.length===0
?'<div class="fxg"><div class="fxgi" style="background:linear-gradient(135deg,'+cur.color+','+cur.color+'cc)">'+cur.icon+'</div><div class="fxgb"><strong>'+cur.name+'より</strong><p>'+cur.greeting+'</p></div></div>'
:msgs.map(function(m){
if(m.role==='user')return '<div class="fxmr fxmr-u"><div class="fxmb fxmb-u">'+E(m.text)+'</div><div class="fxma" style="background:#001338">U</div></div>';
return '<div class="fxmr"><div class="fxma" style="background:'+cur.color+'">'+cur.icon+'</div><div class="fxmb fxmb-a">'+E(m.text).replace(/\n/g,'<br>')+'</div></div>'
}).join('');
var examplesMap={
strategy:['中期経営計画を策定したい','M&A戦略を教えて','新規事業の検討'],
accounting:['月次決算は順調？','消費税納付スケジュール','仕訳のチェック'],
finance:['キャッシュフロー見通し','借入金の最適化','シナリオ分析'],
sales:['上位顧客の依存度','粗利率改善','商談パイプライン'],
marketing:['ブランド戦略','顧客セグメント分析','広告ROI'],
hr:['人件費の対売上比','採用計画','離職リスク'],
legal:['契約チェック観点','コンプライアンス強化','知財ポートフォリオ'],
it:['DX推進ロードマップ','セキュリティ態勢','SaaS投資判断'],
manufacturing:['生産性向上策','在庫最適化','QCD改善'],
sustainability:['ESG情報開示','脱炭素ロードマップ','SDGs貢献'],
ma:['買収候補選定','バリュエーション','PMI 100日']
};
var ex=examplesMap[cid]||[];
var exH=ex.map(function(e){return '<button class="fxec" style="--ch:'+cur.color+'11;--cb:'+cur.color+'66;--cc:'+cur.color+'" data-q="'+E(e)+'">'+e+'</button>'}).join('');
container.innerHTML=
'<div class="fxh"><div class="fxh-bdg">🤖 AI POWERED ・ '+list.length+'種のスペシャリスト</div><h2>AIコンサル機能</h2><p>各分野の専門AIが貴社の実データを分析し、課題発見・提言します。履歴はブラウザに保存され、後から見返せます。</p></div>'+
'<div class="fxts">'+tabs+'</div>'+
'<div class="fxc"><div class="fxch"><div class="fxchl"><div class="fxchi" style="background:'+cur.color+'">'+cur.icon+'</div><div><div class="fxtn">'+cur.name+'</div><div class="fxtg">'+cur.tagline+'</div></div></div><button class="fxch-clr" id="fxclr">🗑️ 履歴クリア</button></div>'+
'<div class="fxcm" id="fxmsgs">'+msgH+'</div>'+
'<div class="fxex">'+exH+'</div>'+
'<div class="fxia"><div class="fxir" style="--inf:'+cur.color+';--infs:'+cur.color+'1a"><textarea id="fxin" placeholder="'+cur.name+'に質問する..." rows="1"></textarea><button id="fxsd" style="background:linear-gradient(135deg,'+cur.color+','+cur.color+'cc)">送信</button></div><div class="fxih">💡 例文ボタンで即質問 / Cmd+Enterで送信 / 履歴はlocalStorage保存</div></div></div>';
container.querySelectorAll('.fxt').forEach(function(t){t.addEventListener('click',function(){aiState.c=t.dataset.cid;renderAI(container)})});
container.querySelectorAll('.fxec').forEach(function(b){b.addEventListener('click',function(){document.getElementById('fxin').value=b.dataset.q;document.getElementById('fxsd').click()})});
var clr=document.getElementById('fxclr');
if(clr)clr.addEventListener('click',function(){if(confirm(cur.name+'の履歴をクリアしますか?')){aiState.h[cid]=[];saveHistory(aiState.h);renderAI(container)}});
var sd=document.getElementById('fxsd');
if(sd)sd.addEventListener('click',async function(){
var i=document.getElementById('fxin');var q=(i.value||'').trim();if(!q)return;
var cid2=aiState.c;aiState.h[cid2].push({role:'user',text:q});saveHistory(aiState.h);i.value='';renderAI(container);
try{
var rs=await fetch('/api/ai-consult',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({consultant_id:cid2,query:q})}).then(function(x){return x.json()});
var full=rs.answer||'(回答なし)';
// typewriter chunked render
aiState.h[cid2].push({role:'ai',text:''});renderAI(container);
var msgsEl=document.getElementById('fxmsgs');
var bubbles=msgsEl?msgsEl.querySelectorAll('.fxmb-a'):[];
var target=bubbles[bubbles.length-1];
var idx=0;var chunk=6;
var iv=setInterval(function(){
if(idx>=full.length){clearInterval(iv);aiState.h[cid2][aiState.h[cid2].length-1].text=full;saveHistory(aiState.h);return}
idx=Math.min(idx+chunk,full.length);
if(target){target.innerHTML=window.FX.esc(full.substring(0,idx)).replace(/\n/g,'<br>')+'<span style="color:#94a3b8;animation:fxblink 1s infinite">▊</span>';if(msgsEl)msgsEl.scrollTop=msgsEl.scrollHeight}
},25);
}catch(e){aiState.h[cid2].push({role:'ai',text:'エラー:'+e.message});saveHistory(aiState.h);renderAI(container)}
});
var ie=document.getElementById('fxin');
if(ie)ie.addEventListener('keydown',function(e){if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();document.getElementById('fxsd').click()}});
var mm=document.getElementById('fxmsgs');if(mm)mm.scrollTop=mm.scrollHeight
}catch(e){container.innerHTML='<div class="fxld" style="color:#b91c1c">エラー:'+e.message+'</div>'}
}
window.FX.renderAI=renderAI;

function applyRoute(){
var hash=(location.hash||'#home').replace('#','');
if(hash!=='ai-consult'&&hash!=='partners')return;
document.querySelectorAll('section.page').forEach(function(p){p.classList.remove('active')});
var sec=document.querySelector('section.page[data-page="'+hash+'"]');
if(!sec){var pw=document.querySelector('.page-wrap');if(pw){sec=document.createElement('section');sec.className='page';sec.dataset.page=hash;pw.appendChild(sec)}}
if(!sec)return;
sec.classList.add('active');
var t=document.getElementById('page-title');var s=document.getElementById('page-subtitle');
if(hash==='ai-consult'){if(t)t.textContent='AIコンサル';if(s)s.textContent='11種の専門AIが貴社データを分析・助言'}
else if(hash==='partners'){if(t)t.textContent='取引先一覧';if(s)s.textContent='110社 / 過去5年データ / 契約書PDF / 商談履歴'}
document.querySelectorAll('.nav-item').forEach(function(el){el.classList.toggle('active',el.dataset.route===hash)});
if(lastRoute!==hash||!sec.innerHTML||sec.innerHTML.indexOf('読込中')>=0){
lastRoute=hash;
if(hash==='ai-consult')renderAI(sec);
else if(hash==='partners'&&window.FX.renderPartners)window.FX.renderPartners(sec)
}
}
function scheduleApply(){setTimeout(applyRoute,20);setTimeout(applyRoute,100);setTimeout(applyRoute,300)}
function injectFreeeBtn(){
var actions=document.querySelector('.topbar-actions');
if(!actions||document.getElementById('fxfreee-btn'))return;
var btn=document.createElement('button');btn.id='fxfreee-btn';btn.className='fxfreee';btn.innerHTML='🔗 freeeAPI連携';
btn.addEventListener('click',function(){alert('これはデモサイトです。\n\nfreeeAPIへの実際の連携は本番環境のみで使用できます。\nお問い合わせ: y.hikita@four-brains.co.jp')});
actions.insertBefore(btn,actions.firstChild);
}
function init(){scheduleApply();injectFreeeBtn();setTimeout(injectFreeeBtn,500);setTimeout(injectFreeeBtn,1500)}
window.FX.applyRoute=applyRoute;
window.addEventListener('hashchange',scheduleApply);
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',init);else init();
setInterval(applyRoute,500);
})();
