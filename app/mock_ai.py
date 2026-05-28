"""AI コンサル機能 (mockレスポンス)。
4種のコンサル: 経理 / 財務 / 営業 / 人事
実データ(mock_data)を元にしたインテリジェントな回答を返す。
"""
from typing import Dict, List, Any
from . import mock_data as M


def _yen(n: int) -> str:
    if n >= 100_000_000:
        return f"{n/100_000_000:.2f}億円"
    if n >= 10_000:
        return f"{n/10_000:,.0f}万円"
    return f"{n:,}円"


def _consultant_personas() -> Dict[str, Dict[str, str]]:
    return {
        "accounting": {
            "name": "経理AIコンサル",
            "icon": "📊",
            "color": "#0ea5e9",
            "tagline": "月次決算・仕訳・税務スケジュールの専門家",
            "greeting": "経理担当のAIです。月次決算、仕訳ルール、税務カレンダー、消費税納付など、経理業務に関するご相談に対応します。",
        },
        "finance": {
            "name": "財務AIコンサル",
            "icon": "💰",
            "color": "#10b981",
            "tagline": "資金繰り・調達戦略・財務分析の専門家",
            "greeting": "財務担当のAIです。キャッシュフロー、借入金管理、シナリオ分析、資金調達戦略をサポートします。",
        },
        "sales": {
            "name": "営業AIコンサル",
            "icon": "📈",
            "color": "#f59e0b",
            "tagline": "売上分析・取引先別収益性の専門家",
            "greeting": "営業担当のAIです。取引先別売上、粗利率分析、機会損失の特定、商談戦略をサポートします。",
        },
        "hr": {
            "name": "人事AIコンサル",
            "icon": "👥",
            "color": "#8b5cf6",
            "tagline": "人件費効率・採用計画・離職リスクの専門家",
            "greeting": "人事担当のAIです。人件費分析、採用計画、評価制度、離職リスク予測など人事戦略をサポートします。",
        },
    }


def list_consultants() -> List[Dict[str, Any]]:
    """4種のコンサル一覧を返す。"""
    out = []
    for k, v in _consultant_personas().items():
        out.append({"id": k, **v})
    return out


def _accounting_responses(query: str) -> str:
    pl = M.generate_mock_pl_monthly()
    rev = sum(r["revenue"] for r in pl)
    cogs = sum(r["cogs"] for r in pl)
    op = sum(r["operating_profit"] for r in pl)
    net = sum(r["net_profit"] for r in pl)
    bs = M.generate_mock_bs_summary()
    q = query.lower()

    if any(k in q for k in ["月次決算", "決算", "進捗"]):
        latest = pl[-1]
        return (
            f"【月次決算進捗 — {latest['year_month']}】\n\n"
            f"・売上高: {_yen(latest['revenue'])} (年間累計 {_yen(rev)})\n"
            f"・売上原価: {_yen(latest['cogs'])} (原価率 {latest['cogs']/latest['revenue']*100:.1f}%)\n"
            f"・販管費: {_yen(latest['sga'])} (販管費率 {latest['sga']/latest['revenue']*100:.1f}%)\n"
            f"・営業利益: {_yen(latest['operating_profit'])} (営業利益率 {latest['operating_profit']/latest['revenue']*100:.1f}%)\n\n"
            f"【提言】今月の販管費が販管費率の通常レンジを上回っています。"
            f"特に法定福利費と業務委託費の増加が見られます。月次推移を比較し、"
            f"異常な計上がないか会計仕訳の確認をお勧めします。"
        )

    if any(k in q for k in ["消費税", "税金", "税務"]):
        return (
            f"【税務スケジュール — 3月決算法人】\n\n"
            f"・5月末: 法人税・地方法人税確定申告 ({_yen(M.ANNUAL_CORPORATE_TAX // 2)})\n"
            f"・5月末: 消費税確定申告 ({_yen(M.ANNUAL_CONSUMPTION_TAX_NET // 2)})\n"
            f"・8月末: 消費税中間納付 ({_yen(M.ANNUAL_CONSUMPTION_TAX_NET // 6)})\n"
            f"・11月末: 法人税中間納付 ({_yen(M.ANNUAL_CORPORATE_TAX // 2)})\n"
            f"・各月10日: 源泉所得税・住民税納付\n"
            f"・各月末: 社会保険料納付\n\n"
            f"【提言】5月末の確定申告に向けて、4月中に税理士との打合せを推奨します。"
            f"中間納付額は前年実績ベースで算出されますが、当期業績が大幅に変動した場合は"
            f"仮決算による中間申告も検討対象です。"
        )

    if any(k in q for k in ["仕訳", "勘定科目"]):
        return (
            f"【会計仕訳の整合性】\n\n"
            f"直近12ヶ月のP/L推移から、以下の点を確認しています：\n\n"
            f"・年間売上: {_yen(rev)} → 月平均 {_yen(rev//12)}\n"
            f"・売上原価率: {cogs/rev*100:.1f}% (健全レンジ 53-57%)\n"
            f"・営業利益率: {op/rev*100:.1f}% (健全レンジ 15-18%)\n"
            f"・当期純利益: {_yen(net)}\n\n"
            f"【検出された注意点】\n"
            f"・経費精算による旅費交通費の計上が売上高に逆計上されているケースがあれば、"
            f"勘定科目を確認してください。\n"
            f"・前払費用と支払費用の期ズレ処理が適切か、決算時にチェックを。"
        )

    return (
        f"経理業務について、以下のような相談に対応できます：\n\n"
        f"・月次決算の進捗確認 →「月次決算は順調？」\n"
        f"・税務スケジュール → 「消費税の納付スケジュール」\n"
        f"・仕訳の整合性 → 「仕訳のチェックして」\n\n"
        f"現状のサマリ:\n"
        f"・年間売上: {_yen(rev)} / 営業利益: {_yen(op)}\n"
        f"・現預金: {_yen(bs['cash'])} / 借入金: {_yen(M.LOAN_OUTSTANDING)}"
    )


def _finance_responses(query: str) -> str:
    bs = M.generate_mock_bs_summary()
    pl = M.generate_mock_pl_monthly()
    op = sum(r["operating_profit"] for r in pl)
    rev = sum(r["revenue"] for r in pl)
    q = query.lower()

    if any(k in q for k in ["資金繰り", "キャッシュ", "cf", "現預金"]):
        return (
            f"【キャッシュフロー分析】\n\n"
            f"・期首現預金: {_yen(bs['cash'])}\n"
            f"・年間営業CF想定: 約{_yen(op - M.ANNUAL_TAX_PAYABLE_TOTAL + M.ANNUAL_DEPRECIATION)}\n"
            f"  ({_yen(op)} - 税金{_yen(M.ANNUAL_TAX_PAYABLE_TOTAL)} + 減価償却{_yen(M.ANNUAL_DEPRECIATION)})\n"
            f"・年間財務CF: 約{_yen(-M.ANNUAL_LOAN_PRINCIPAL_REPAY)} (借入金返済)\n\n"
            f"【提言】\n"
            f"5月末の法人税確定申告で約{_yen(M.ANNUAL_CORPORATE_TAX // 2 + M.ANNUAL_CONSUMPTION_TAX_NET // 2)}の"
            f"大型支出が発生します。この月の運転資金確保を優先してください。\n"
            f"中立シナリオでは12ヶ月後の現預金が約{_yen(int(bs['cash'] * 1.37))}に拡大する見込みで、"
            f"健全なキャッシュポジションを維持できます。"
        )

    if any(k in q for k in ["借入", "調達", "融資"]):
        loans = M.generate_mock_loans()
        return (
            f"【借入金管理】\n\n"
            + "\n".join([f"・{l['name']}: 残高{_yen(l['outstanding'])} 金利{l['annual_rate']*100:.2f}%" for l in loans]) +
            f"\n\n合計借入金: {_yen(M.LOAN_OUTSTANDING)}\n"
            f"D/Eレシオ: {M.LOAN_OUTSTANDING/bs['net_assets']*100:.1f}%\n\n"
            f"【提言】現状の財務体力(自己資本比率 {bs['net_assets']/bs['total_assets']*100:.1f}%)を"
            f"踏まえると、追加融資の余地は十分あります。"
            f"金利交渉の余地: 三菱UFJ運転資金1.18%は、他行の同条件と比較してやや高めです。"
            f"借換または金利見直しを検討してください。"
        )

    if any(k in q for k in ["シナリオ", "予測", "計画"]):
        return (
            f"【シナリオ分析】\n\n"
            f"・楽観 (売上+10%, コスト-5%): 期末現預金 約{_yen(int(bs['cash'] * 1.95))}\n"
            f"・中立 (現状維持): 期末現預金 約{_yen(int(bs['cash'] * 1.37))}\n"
            f"・悲観 (売上-15%, コスト+5%): 期末現預金 約{_yen(int(bs['cash'] * 0.92))}\n\n"
            f"【提言】悲観シナリオでも現預金がマイナスにならないため、"
            f"財務的耐性は十分にあります。\n"
            f"一方、楽観シナリオに向けては、現状の販管費構造(率28.3%)では限界があるため、"
            f"DXによる業務効率化で固定費を5-8%圧縮できれば、営業利益率を更に2-3pt向上できます。"
        )

    return (
        f"財務戦略について、以下のような相談に対応できます：\n\n"
        f"・資金繰り → 「キャッシュフロー見通し」\n"
        f"・借入戦略 → 「借入金の最適化」\n"
        f"・シナリオ分析 → 「楽観シナリオを教えて」\n\n"
        f"現状のサマリ:\n"
        f"・自己資本比率: {bs['net_assets']/bs['total_assets']*100:.1f}%\n"
        f"・D/Eレシオ: {M.LOAN_OUTSTANDING/bs['net_assets']*100:.1f}%"
    )


def _sales_responses(query: str) -> str:
    pl = M.generate_mock_pl_monthly()
    rev = sum(r["revenue"] for r in pl)
    cogs = sum(r["cogs"] for r in pl)
    q = query.lower()

    if any(k in q for k in ["売上", "取引先", "顧客"]):
        return (
            f"【売上分析】\n\n"
            f"・年間売上: {_yen(rev)} (月平均 {_yen(rev//12)})\n"
            f"・粗利率: {(rev-cogs)/rev*100:.1f}% (粗利{_yen(rev-cogs)})\n"
            f"・取引先数: 110社 (常時取引100社 + スポット10社)\n\n"
            f"【上位5社の傾向】\n"
            f"アクシス商事、ベルテックシステム、クレスト工業の3社で年間売上の約25%を占めています。\n\n"
            f"【提言】売上集中度が高い上位顧客への依存リスクを軽減するため、"
            f"中堅顧客(売上構成比3-5%)を5社以上育成するアカウントプラン策定を推奨します。"
            f"特に過去6ヶ月で売上が成長しているスポット顧客を常時取引へ転換することで、"
            f"安定収益基盤を強化できます。"
        )

    if any(k in q for k in ["粗利", "利益率"]):
        return (
            f"【粗利率分析】\n\n"
            f"・全社平均粗利率: {(rev-cogs)/rev*100:.1f}%\n"
            f"・健全レンジ: 42-48%\n\n"
            f"【部門別の機会損失】\n"
            f"・営業1部: 注力顧客が大手中心で粗利率が圧迫されがち\n"
            f"・営業2部: 中堅顧客が多く粗利率は高めだが、案件規模が小さい\n"
            f"・営業3部: 新規開拓中心、変動大\n\n"
            f"【提言】価格交渉力強化のため、コスト構造の透明性向上が鍵です。"
            f"値引き要請時に「原価+目標粗利」のデータを即座に提示できる仕組みを"
            f"営業ツールに組み込むことで、粗利率を1-2pt改善できる可能性があります。"
        )

    if any(k in q for k in ["商談", "案件", "パイプライン"]):
        return (
            f"【商談・案件分析】\n\n"
            f"取引先別パターン分析から見える商談状況:\n\n"
            f"・継続案件: 月次定期取引 ¥{int(rev*0.65/12):,} 規模\n"
            f"・スポット案件: 単発・季節要因 ¥{int(rev*0.20/12):,} 規模\n"
            f"・新規開発: パイプライン ¥{int(rev*0.15/12):,} 規模\n\n"
            f"【提言】パイプライン管理を強化し、月次の受注見込みを"
            f"3段階(高/中/低確度)で可視化することで、月次売上の予測精度を"
            f"±5%以内に収めることが可能です。"
        )

    return (
        f"営業戦略について、以下のような相談に対応できます：\n\n"
        f"・取引先別売上 → 「上位顧客の依存度」\n"
        f"・粗利率改善 → 「粗利率を上げる方法」\n"
        f"・商談パイプライン → 「パイプライン状況」\n\n"
        f"現状サマリ:\n"
        f"・年間売上: {_yen(rev)} / 取引先: 110社 / 粗利率: {(rev-cogs)/rev*100:.1f}%"
    )


def _hr_responses(query: str) -> str:
    pl = M.generate_mock_pl_monthly()
    rev = sum(r["revenue"] for r in pl)
    q = query.lower()
    total_labor = M.ANNUAL_SALARY_GROSS + M.ANNUAL_BONUS_GROSS + M.ANNUAL_SI_EMPLOYER
    revenue_per_emp = rev // M.DEMO_EMPLOYEE_COUNT

    if any(k in q for k in ["人件費", "コスト", "給与"]):
        return (
            f"【人件費分析】\n\n"
            f"・年間給与: {_yen(M.ANNUAL_SALARY_GROSS)}\n"
            f"・年間賞与: {_yen(M.ANNUAL_BONUS_GROSS)} (夏冬2回)\n"
            f"・法定福利費: {_yen(M.ANNUAL_SI_EMPLOYER)}\n"
            f"・総人件費: {_yen(total_labor)} (売上比 {total_labor/rev*100:.1f}%)\n"
            f"・1人当たり売上: {_yen(revenue_per_emp)} / 年\n\n"
            f"【提言】人件費の対売上比{total_labor/rev*100:.1f}%は、同業他社平均(18-22%)と比較して"
            f"健全なレンジです。生産性指標として1人当たり売上{_yen(revenue_per_emp)}/年は"
            f"中堅企業の上位四分位に位置します。ただし、メンバー層の比率が高いため、"
            f"中堅層(マネージャー以上)の育成投資を強化することで、5年後の組織持続性を高められます。"
        )

    if any(k in q for k in ["採用", "募集", "増員"]):
        return (
            f"【採用計画提案】\n\n"
            f"現状: 138名 (役員8名 + 部長10名 + マネージャー16名 + 一般104名)\n\n"
            f"【売上目標達成に必要な要員】\n"
            f"・売上を120%にするには:\n"
            f"  生産性維持で約28名増員 → 計166名\n"
            f"  生産性10%向上で約15名増員 → 計153名\n\n"
            f"【提言】単純増員より、DXとマネジメント強化で生産性を向上させる方が"
            f"コスト効率が高いです。優先採用ポジション:\n"
            f"・データ分析エンジニア (2名): 業務効率化基盤\n"
            f"・マネージャー候補 (3名): 中堅層厚み増強\n"
            f"・営業企画 (1名): パイプライン管理高度化\n"
            f"年間追加人件費 約{_yen(int(total_labor * 0.044))}で生産性5-8%向上が見込めます。"
        )

    if any(k in q for k in ["離職", "退職", "リスク"]):
        return (
            f"【離職リスク予測】\n\n"
            f"組織構成分析:\n"
            f"・5年以上勤続: 約45% (安定層)\n"
            f"・2-5年勤続: 約30% (成長層)\n"
            f"・2年未満: 約25% (定着層) ← 離職リスク高\n\n"
            f"【提言】メンバー層(72名)の中で2年未満が多く、ここが離職リスクの集中ゾーンです。\n"
            f"・1on1の頻度を月1→月2に増やす\n"
            f"・メンター制度を入社1年目→3年目に延長\n"
            f"・キャリアパス可視化(リーダー昇格までの平均期間提示)\n"
            f"上記施策で離職率を年5%減らせれば、採用コスト約{_yen(20_000_000)}/年の削減効果。"
        )

    if any(k in q for k in ["評価", "1on1", "面談"]):
        return (
            f"【評価・面談制度の提言】\n\n"
            f"現状の評価制度:\n"
            f"・年2回の評価面談 (6月/12月)\n"
            f"・1on1: 月1回 (チーフ以上が実施)\n\n"
            f"【提言】定量評価と定性評価のバランス見直しを推奨します:\n"
            f"・営業職: 売上達成率の比重を下げ(60→45%)、案件パイプライン健全性(20%)、"
            f"顧客満足度(15%)、後輩育成(20%)へ\n"
            f"・技術職: 個人成果(40%)、技術ナレッジ共有(25%)、社内DX貢献(20%)、後輩育成(15%)\n"
            f"これによりプレイヤー→マネジメント移行が円滑になります。"
        )

    return (
        f"人事戦略について、以下のような相談に対応できます：\n\n"
        f"・人件費効率 → 「人件費の対売上比は適正？」\n"
        f"・採用計画 → 「来期の採用計画を提案して」\n"
        f"・離職リスク → 「離職リスクが高い層は？」\n"
        f"・評価制度 → 「評価制度の見直し提案」\n\n"
        f"現状サマリ:\n"
        f"・従業員: {M.DEMO_EMPLOYEE_COUNT}名 / 総人件費: {_yen(total_labor)}\n"
        f"・1人当たり売上: {_yen(revenue_per_emp)}/年"
    )


def respond(consultant_id: str, query: str) -> Dict[str, Any]:
    """指定されたコンサルからの回答を返す。"""
    personas = _consultant_personas()
    persona = personas.get(consultant_id, personas["accounting"])
    handlers = {
        "accounting": _accounting_responses,
        "finance": _finance_responses,
        "sales": _sales_responses,
        "hr": _hr_responses,
    }
    handler = handlers.get(consultant_id, _accounting_responses)
    answer = handler(query) if query and query.strip() else persona["greeting"]
    return {
        "consultant_id": consultant_id,
        "consultant_name": persona["name"],
        "consultant_icon": persona["icon"],
        "answer": answer,
    }
