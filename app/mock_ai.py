"""AI コンサル (10種、mockレスポンス)"""
from typing import Dict, List, Any
from . import mock_data as M


def _yen(n):
    if n >= 100_000_000:
        return f"{n/100_000_000:.2f}億円"
    if n >= 10_000:
        return f"{n/10_000:,.0f}万円"
    return f"{n:,}円"


def _consultant_personas():
    return {
        "strategy": {"name": "経営AIコンサル", "icon": "🎯", "color": "#001338",
                     "tagline": "中期経営計画・M&A・新規事業の専門家",
                     "greeting": "経営戦略担当のAIです。中期計画、M&A判断、新規事業評価、競合分析、組織再編をサポートします。"},
        "accounting": {"name": "経理AIコンサル", "icon": "📊", "color": "#0ea5e9",
                       "tagline": "月次決算・仕訳・税務スケジュールの専門家",
                       "greeting": "経理担当のAIです。月次決算、仕訳ルール、税務カレンダー、消費税納付などをサポートします。"},
        "finance": {"name": "財務AIコンサル", "icon": "💰", "color": "#10b981",
                    "tagline": "資金繰り・調達戦略・財務分析の専門家",
                    "greeting": "財務AIです。キャッシュフロー、借入金管理、シナリオ分析、資金調達をサポートします。"},
        "sales": {"name": "営業AIコンサル", "icon": "📈", "color": "#f59e0b",
                  "tagline": "売上分析・取引先別収益性の専門家",
                  "greeting": "営業AIです。取引先別売上、粗利率分析、機会損失、商談戦略をサポートします。"},
        "marketing": {"name": "マーケAIコンサル", "icon": "📢", "color": "#ec4899",
                      "tagline": "ブランド戦略・広告ROI・顧客分析の専門家",
                      "greeting": "マーケAIです。ブランドポジショニング、広告ROI、顧客セグメント、デジタル施策をサポートします。"},
        "hr": {"name": "人事AIコンサル", "icon": "👥", "color": "#8b5cf6",
               "tagline": "人件費効率・採用計画・離職リスクの専門家",
               "greeting": "人事AIです。人件費分析、採用計画、評価制度、離職リスクをサポートします。"},
        "legal": {"name": "法務AIコンサル", "icon": "⚖️", "color": "#475569",
                  "tagline": "契約・コンプライアンス・知財の専門家",
                  "greeting": "法務AIです。契約書チェック、コンプライアンス、知財管理、規制対応をサポートします。"},
        "it": {"name": "IT/DX AIコンサル", "icon": "💻", "color": "#06b6d4",
               "tagline": "DX推進・セキュリティ・システム投資の専門家",
               "greeting": "IT/DX AIです。デジタル化、セキュリティ、システム投資、SaaS選定をサポートします。"},
        "manufacturing": {"name": "製造AIコンサル", "icon": "🏭", "color": "#dc2626",
                          "tagline": "生産性・在庫最適化・品質管理の専門家",
                          "greeting": "製造AIです。生産性向上、在庫最適化、QCD改善、サプライチェーンをサポートします。"},
        "sustainability": {"name": "ESG AIコンサル", "icon": "🌱", "color": "#22c55e",
                           "tagline": "ESG・脱炭素・SDGs対応の専門家",
                           "greeting": "ESG AIです。GHG排出量、サステナビリティ報告書、SDGs施策、脱炭素戦略をサポートします。"},
        "ma": {"name": "M&A・PE AIコンサル", "icon": "🤝", "color": "#f97316",
               "tagline": "買収戦略・バリュエーション・PMIの専門家",
               "greeting": "M&A AIです。買収候補、バリュエーション(DCF)、PMI、DDをサポートします。"},
    }


def list_consultants() -> List[Dict[str, Any]]:
    out = []
    for k, v in _consultant_personas().items():
        out.append({"id": k, **v})
    return out


def _financial_snapshot():
    pl = M.generate_mock_pl_monthly()
    bs = M.generate_mock_bs_summary()
    return {
        "rev": sum(r["revenue"] for r in pl),
        "cogs": sum(r["cogs"] for r in pl),
        "op": sum(r["operating_profit"] for r in pl),
        "net": sum(r["net_profit"] for r in pl),
        "cash": bs["cash"],
        "loan": M.LOAN_OUTSTANDING,
        "assets": bs["total_assets"],
        "equity": bs["net_assets"],
        "emp": M.DEMO_EMPLOYEE_COUNT,
        "ar": bs["accounts_receivable"],
        "ap": bs["accounts_payable"],
    }


# 各コンサル別の回答テンプレ (キーワード→回答)
_RESPONSES = {
    "strategy": {
        "中期|経営計画|3年|5年": "【中期経営計画3カ年案】\n\n■現状: 売上{rev} / 営利{op} (利益率{op_r:.1f}%)\n\n■目標 (3年後)\n・売上: {rev_3y} (CAGR 15%)\n・営利率: 20% (現{op_r:.1f}%から+2.7pt)\n・自己資本比率: 70% (現{eq_r:.0f}%)\n\n■3つの柱\n①既存事業の収益性改善 (粗利率+3pt = 約{gain}/年)\n②新規事業領域 (SaaS/サブスク): 売上の15%を新規収益に\n③DX投資 ¥150M → 業務効率20%向上で固定費圧縮\n\n■投資キャッシュ確保\n現預金{cash}+営業CF年¥320M。M&A余力{ma_cap}。",
        "M&A|買収|統合|PMI": "【M&A戦略】\n\n貴社の財務体力ベースでの買収余力:\n・現預金{cash}のうち¥500Mを投資原資に\n・追加デットファイナンス{debt_cap}余地\n・総買収余力: 約¥1,500M (EV/EBITDA 5-6倍想定)\n\n候補セクター:\n①バリューチェーン上の補完 (川下: 顧客接点獲得 / 川上: コスト構造改善)\n②同業中小 (3-5社) のロールアップで規模優位確立\n③隣接業界の技術アセット獲得\n\nKey Risk: PMI失敗で価値毀損 (平均60%)。\n対策: 取得後100日プラン + 統合専任チーム設置。",
        "新規事業|新規|事業": "【新規事業検討フレーム】\n\n貴社のリソースアセット:\n・顧客基盤 110社 ・人材{emp}名 ・現預金{cash}\n\n推奨ドメイン:\n①既存顧客向けサブスクサービス (ARR ¥300M目標)\n②データ事業 (取引データを活用)\n③コンサル/トレーニング事業 (人材アセット活用)\n\n投資判断基準:\n・初期投資¥50-150M ・IRR 25%以上\n・損益分岐24ヶ月以内 ・既存事業とのシナジー有り",
    },
    "marketing": {
        "ブランド|認知|広告": "【ブランド戦略】\n\n現状の課題仮説:\n・取引先110社中BtoB主体 → 認知効率は高いが新規開拓限界\n・広告費は販管費の約3-5% (推定 ¥85-145M/年)\n\n施策提言:\n①ターゲットアカウントマーケティング(ABM): 上位50社の意思決定層に直接アプローチ\n②コンテンツマーケ: ホワイトペーパー/ウェビナーで月50リード獲得\n③インフルエンサー業界キーパーソン招聘イベント\n\nROI改善余地: 広告費¥100M→ROI 3.2倍 (現状想定2.0倍より +60%)",
        "顧客|セグメント|分析": "【顧客セグメント分析】\n\n取引先110社を以下4セグメントに分類提言:\n\n①コアロイヤル (上位20社): 売上の60% / 解約防止に最重点\n②成長ターゲット (中堅30社): 売上の25% / 拡販対象\n③メンテナンス (40社): 売上の12% / 効率運営\n④非効率 (20社): 売上の3% / 撤退or再交渉\n\n各セグメント別のリレーション設計:\n・コア: 月次の戦略会議 + 役員担当制\n・成長: 四半期レビュー + アップセル提案\n・メンテ: デジタル中心 / コスト最適化",
        "ROI|広告効果|デジタル": "【デジタル施策ROI】\n\n推奨施策ミックス:\n・SEO/SEM: 月¥500K → リード40件 (CPL ¥12,500)\n・LinkedIn Ads (BtoB): 月¥800K → リード30件 (CPL ¥26,667)\n・ウェビナー: 月¥300K → 商談10件 (CPA ¥30,000)\n・ABM tools: 月¥400K → アカウント別エンゲージ可視化\n\n合計月¥2M (年¥24M) で年間契約金額¥120M獲得目標 (5倍ROI)",
    },
    "legal": {
        "契約|チェック|レビュー": "【契約書レビュー観点】\n\n貴社で頻発する契約類型と要確認ポイント:\n\n①業務委託契約 (110社中約70社該当)\n・支払サイト ・知財帰属 ・損害賠償上限 ・契約解除条件\n\n②NDA: 開示情報の範囲 / 期間 (通常2-5年) / 残置事項\n\n③ライセンス契約: 利用範囲 / 二次利用 / 監査権 / 値上げ条項\n\nリスク高ポイント:\n・損害賠償無制限条項 (上限なし)\n・自動更新の縛り (解約予告6ヶ月超)\n・準拠法/裁判所 (海外指定)",
        "コンプライアンス|内部統制|不正": "【内部統制強化】\n\n上場検討時の必須整備項目:\n①J-SOX対応: 業務プロセス文書化 / 整備運用評価\n②内部監査機能: 独立した監査室 (現状 部長兼任→専任化)\n③コンプライアンス研修: 全従業員年1回必須\n④ハラスメント相談窓口: 社外設置を強く推奨\n⑤反社チェック: 全取引先について年1回実施\n\n直近の最優先: 個人情報保護法改正(2022)対応の進捗確認",
        "知財|特許|商標": "【知財ポートフォリオ】\n\n貴社の保有想定 (規模感):\n・商標: 主力サービス名 3-5件出願済\n・特許: 業務関連で2-3件\n・著作物: 自社開発のソフトウェア / コンテンツ\n\n強化方向:\n①未出願の社名/ロゴを商標出願 (年¥150K)\n②競合の特許マップ作成 (年¥500K) → 抜け穴探索\n③営業秘密管理規程の整備 (技術ノウハウ流出防止)\n④オープンソース利用管理 (GPL汚染リスク)",
    },
    "it": {
        "DX|デジタル|変革": "【DX推進ロードマップ】\n\nPhase1 (3ヶ月): 基盤整備\n・既存業務の見える化 (BPMN) ・データ整備 ・クラウド移行\n\nPhase2 (6-12ヶ月): 主要業務のデジタル化\n・営業: SFA/CRM導入 ¥30M\n・会計: 経理DX (本demo型) ¥20M\n・人事: タレントマネジメント ¥15M\n\nPhase3 (12-24ヶ月): データドリブン経営\n・全社ダッシュボード\n・AI予測 (需要/退職/受注)\n・自動化 (RPA, AIエージェント)\n\n投資総額: 約¥120M / 期待効果: 業務効率20%向上 + 売上+5%",
        "セキュリティ|サイバー|攻撃": "【セキュリティ態勢】\n\n中堅企業として必須レベル:\n①エンドポイント保護: EDR導入 (年¥3M)\n②メール: 添付ファイル無害化 + URL検査 (年¥2M)\n③クラウド: CSPM (Cloud Security Posture Mgmt) ¥4M/年\n④認証: 全社IDaaS + MFA必須 (年¥3M)\n⑤バックアップ: イミュータブル (改竄不可) 構成\n⑥SOC: 24/365 監視サービス (年¥10-15M)\n\n総額: 年¥25-30M (売上の1%以下)\nROI: ランサム1件の損害 ¥200M-1B回避",
        "SaaS|システム|投資": "【SaaS投資判断フレーム】\n\n選定基準:\n①シェア/事業継続性 ②API/連携 ③コスト/従量 ④日本語サポート ⑤データ主権\n\n貴社既導入推定:\n・freee会計+人事労務 (本demo) ・Salesforce/HubSpot ・Slack/Teams ・Google Workspace/M365\n\n追加検討:\n・Notion/Confluence (ナレッジ管理): 月¥5/人\n・Asana/Backlog (PJ管理): 月¥1.5K/人\n・Looker/Tableau (BI): 月¥100K\n・Datadog (監視): 月¥80K",
    },
    "manufacturing": {
        "生産性|向上|改善": "【生産性向上施策】\n\n現状の人時生産性 = 売上{rev_per_emp}/年/人\n業界平均: ¥18-22M/年/人 → 目標: ¥25M/年/人 (+20%)\n\n3つの柱:\n①プロセス自動化 (RPA/AIエージェント): 定型業務40%削減\n②ナレッジ共有: 暗黙知を形式知化 → 新人立上げ40%短縮\n③意思決定スピード: フラット組織 + データ可視化\n\n投資: ¥50M / 効果: 年¥120M (実質4名分の生産性増)",
        "在庫|最適化|SKU": "【在庫最適化】\n\n貴社のB/S上の棚卸資産¥87M = 月商の0.35月分 (健全)\n\n更なる効率化:\n①ABC分析: 売上80%を生む20%のSKUに在庫集中\n②安全在庫の見直し: リードタイム実績ベースで再計算 → 20%削減可能\n③需要予測: 過去3年データ + AIで予測精度向上\n④S&OP: 営業/生産/購買の月次調整会議で在庫膨張防止\n\n効果: 在庫¥17M削減 → 年間在庫保管コスト¥3M削減",
        "品質|QCD|歩留": "【QCD改善】\n\n品質(Q)/コスト(C)/納期(D) のバランス改善:\n\n①不良率低減: 統計的工程管理(SPC)導入で1.5%→0.5%\n  → 売上影響 +¥30M/年\n\n②原価低減: VA/VE活動で材料費5%削減\n  → 売上原価¥1.65Bの5% = ¥82M/年\n\n③リードタイム短縮: 段取り時間半減でロット小型化\n  → 受注機会損失減 + 在庫回転率1.2倍",
    },
    "sustainability": {
        "ESG|サステナ|報告": "【ESG情報開示】\n\n非上場でも取引先要求で必須化進行中:\n\n■E (環境)\n・Scope1+2排出量: 推定 200-400 tCO2/年\n・削減目標: 2030年までに50%削減\n\n■S (社会)\n・労働: 平均残業時間 / 有給取得率 / 女性管理職比率\n・人権: サプライチェーン人権DD\n\n■G (ガバナンス)\n・取締役会の独立性 / 多様性\n・内部通報制度の運用実績\n\n統合報告書 + サステナビリティWebサイトを推奨。",
        "脱炭素|カーボン|GHG": "【GHG削減ロードマップ】\n\nScope別の対応:\n\nScope1 (直接排出 = 社用車/設備燃料): ¥10M投資でEV化 + ガス→電化\nScope2 (購入電力): 再エネ電力契約 (年+¥3M) で実質ゼロ化\nScope3 (バリューチェーン全体): 主要15社にCDP回答依頼 + 排出量共有\n\nKPI:\n・2025: Scope1+2を30%削減\n・2030: 50%削減\n・2050: ネットゼロ達成",
        "SDGs|目標|貢献": "【SDGs貢献マッピング】\n\n貴社事業との関連度高目標:\n\n#8 働きがいも経済成長も: 多様な働き方 / 公正賃金\n#9 産業と技術革新の基盤: DX推進 / イノベーション\n#12 つくる責任つかう責任: 持続可能な調達\n#13 気候変動: GHG削減\n#17 パートナーシップ: 取引先協働\n\n施策パッケージ:\n・社員ボランティア有給化\n・地域貢献の事業活動\n・ダイバーシティ研修",
    },
    "ma": {
        "買収|M&A|ターゲット": "【M&A候補選定基準】\n\n貴社の戦略適合性スクリーニング:\n\n①規模: EV ¥1-3B (貴社の自己資本{equity}に対し30-50%)\n②シナジー: 顧客/技術/人材いずれかで合算>1+1=2.5\n③財務健全性: EBITDA率15%以上 / 純有利子負債/EBITDA<3倍\n④文化適合: 経営陣の継続意思 + バリュー類似\n\n候補リスト型:\n・PEファンドからの売却案件 (毎月10-20件)\n・ロングリスト → 5社程度に絞り IPアプローチ",
        "バリュエーション|DCF|算定": "【バリュエーション手法】\n\n3手法で算定し中央値を採用:\n\n①DCF: 将来CFを割引現在価値化 (WACC 8%想定)\n・5年予測 + ターミナルバリュー\n・成長率: 永久成長2%\n\n②類似会社比較: EV/EBITDA倍率\n・業界中央値 5-7倍 → EBITDA¥80Mなら EV ¥400-560M\n\n③DDM: 配当割引モデル (買い手目線)\n\nプレミアム交渉: 一般的に20-30% (シナジー期待値の50%還元)",
        "PMI|統合|シナジー": "【PMI 100日プラン】\n\nDay1-30: 統合方針発表 / キーパーソン引留め\nDay31-60: 業務統合 (会計/HR/IT)\nDay61-100: シナジー創出開始 (営業クロスセル/コスト統合)\n\n重要KPI:\n・キー人材の定着率: 90%以上\n・初年度シナジー実現率: 50%以上\n・統合費用: 取引額の10-15%以内\n\nNG事例:\n・文化統合の軽視で離職連鎖\n・100日後にも統合判断未確定 (士気低下)\n・既存事業への影響でROI低下",
    },
    "accounting": {
        "月次決算|決算|進捗": "【月次決算進捗】\n\n年間売上{rev} / 営利{op}\n\n月次平均: 売上 {rev_m} / 営利 {op_m}\n\n決算早期化のために:\n①受注/出荷/請求のタイムスタンプ統一\n②月末2営業日内のクローズを目指す\n③Excel依存を脱却 (本demoのような会計ダッシュボード活用)\n\n税理士連携: 四半期ごとの試算表確定 → 法人税予測精度向上",
        "消費税|税金|税務": "【税務スケジュール (3月決算法人)】\n\n・5月末: 法人税確定申告 ({corp_h})\n・5月末: 消費税確定申告 ({vat_h})\n・8月末: 消費税中間 ({vat_int})\n・11月末: 法人税中間 ({corp_h}) + 消費税中間 ({vat_int})\n・各月10日: 源泉/住民税納付\n・各月末: 社保納付\n\n対策: 5月の大型支払に向けて4月時点で¥{may_total} を確保。",
        "仕訳|科目|勘定": "【仕訳整合性チェック】\n\n年間集計:\n・売上高: {rev} (原価率{cogs_r:.1f}%)\n・販管費率: 28.3%\n・営業利益率: {op_r:.1f}%\n\n注意点:\n・経費精算による旅費交通費の売上計上に注意\n・前払/未払の期ズレ\n・税抜/税込の混在",
    },
    "finance": {
        "資金繰り|キャッシュ|CF": "【キャッシュフロー】\n\n期首現預金: {cash} / 年間営業CF約{ocf}\n5月の税金支払で一時減少→{may_after_cash}\n中立シナリオ12ヶ月後: {cash_1y_n}",
        "借入|調達|融資": "【借入金最適化】\n\n残高{loan} / D/E比{de_r:.1f}%\n金利交渉余地あり (1.18%→1.0%)\nコミットメントライン¥300M設定推奨",
        "シナリオ|予測|計画": "【シナリオ分析】\n楽観: {c_opt}\n中立: {c_n}\n悲観: {c_pess}\n悲観でも現預金プラス維持。財務的耐性十分",
    },
    "sales": {
        "売上|取引先|顧客": "【売上分析】\n年間{rev} (月平均{rev_m}) / 110社\n上位5社で約25%。中堅5社をアカウントプラン化推奨",
        "粗利|利益率|マージン": "【粗利率改善】\n全社平均45% (健全)\n原価+目標粗利の即時提示で1-2pt改善余地",
        "商談|パイプライン|案件": "【パイプライン】\n受注予測±5%以内: 高/中/低確度の加重平均 / 週次更新 / SFA導入",
    },
    "hr": {
        "人件費|給与|コスト": "【人件費】\n年間¥478M (売上比{labor_r:.1f}%) / 1人当たり売上¥{rev_per_emp:,}\n業界平均より健全",
        "採用|募集|増員": "【採用計画】\n現138名 / 売上120%目標で+15-28名\n優先: データ分析×2 / マネ候補×3",
        "離職|退職|リスク": "【離職リスク】\n2年未満メンバー層集中\n1on1月2 / メンター3年延長 / キャリアパス可視化",
    },
}


def _fill_template(template, snap):
    rev=snap["rev"];op=snap["op"];cash=snap["cash"];loan=snap["loan"]
    equity=snap["equity"];emp=snap["emp"]
    op_r=op/rev*100 if rev else 0
    cogs_r=snap["cogs"]/rev*100 if rev else 0
    eq_r=equity/snap["assets"]*100 if snap["assets"] else 0
    de_r=loan/equity*100 if equity else 0
    labor_r=478_000_000/rev*100 if rev else 0
    may_tax=M.ANNUAL_CONSUMPTION_TAX_NET//2+M.ANNUAL_CORPORATE_TAX//2
    vals={
        "rev":_yen(rev),"op":_yen(op),"cash":_yen(cash),"loan":_yen(loan),
        "equity":_yen(equity),"emp":emp,
        "rev_m":_yen(rev//12),"op_m":_yen(op//12),
        "op_r":op_r,"cogs_r":cogs_r,"eq_r":eq_r,"de_r":de_r,"labor_r":labor_r,
        "rev_3y":_yen(int(rev*1.52)),
        "gain":_yen(int(rev*0.03)),
        "ma_cap":_yen(int(cash*0.5+800_000_000)),
        "debt_cap":_yen(int(equity*0.5)),
        "may_tax":_yen(may_tax),"may_total":_yen(may_tax+100_000_000),
        "corp_h":_yen(M.ANNUAL_CORPORATE_TAX//2),
        "vat_h":_yen(M.ANNUAL_CONSUMPTION_TAX_NET//2),
        "vat_int":_yen(M.ANNUAL_CONSUMPTION_TAX_NET//6),
        "ocf":_yen(op-M.ANNUAL_TAX_PAYABLE_TOTAL+M.ANNUAL_DEPRECIATION),
        "may_after_cash":_yen(int(cash*0.65)),
        "cash_1y_n":_yen(int(cash*1.37)),
        "c_opt":_yen(int(cash*1.95)),"c_n":_yen(int(cash*1.37)),"c_pess":_yen(int(cash*0.92)),
        "rev_per_emp":rev//emp if emp else 0,
    }
    try: return template.format(**vals)
    except Exception: return template


def respond(consultant_id, query):
    personas=_consultant_personas()
    persona=personas.get(consultant_id, personas["accounting"])
    if not query or not query.strip():
        return {"consultant_id":consultant_id,"consultant_name":persona["name"],
                "consultant_icon":persona["icon"],"answer":persona["greeting"]}
    snap=_financial_snapshot()
    responses=_RESPONSES.get(consultant_id, _RESPONSES.get("accounting", {}))
    for kw_pattern, template in responses.items():
        for kw in kw_pattern.split("|"):
            if kw and kw in query:
                return {"consultant_id":consultant_id,"consultant_name":persona["name"],
                        "consultant_icon":persona["icon"],"answer":_fill_template(template, snap)}
    return {"consultant_id":consultant_id,"consultant_name":persona["name"],"consultant_icon":persona["icon"],
            "answer":(persona['name']+'\nより\n\n'+persona['greeting']+'\n\n以下のキーワードで詳細提言:\n'+
                      '\n'.join('・'+k.split('|')[0] for k in list(responses.keys())[:5])+
                      '\n\n現状:\n・売上: '+_yen(snap['rev'])+'\n・営利: '+_yen(snap['op'])+'\n・現預金: '+_yen(snap['cash'])+'\n・従業員: '+str(snap['emp'])+'名')}
