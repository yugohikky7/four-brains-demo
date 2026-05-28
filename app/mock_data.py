"""Demo mock data. 売上30億円規模の中堅企業を想定。
単一のマスター数値から全諸表を整合的に生成する。
"""
import random
from datetime import date, timedelta
from typing import Any, Dict, List


# ===================== マスター数値 (整合性の起点) =====================
DEMO_COMPANY_NAME = "株式会社スタアテクノロジー"
DEMO_COMPANY_ID = 99999
DEMO_FOUNDED_YEAR = date.today().year - 10                # 設立10年

ANNUAL_REVENUE = 3_000_000_000                            # 売上 30億
COGS_RATIO = 0.55                                          # 売上原価率
SGA_RATIO = 0.283                                          # 販管費率 (= 営業利益5億になる調整値)
# 売上総利益率 0.45, 営業利益率 0.167 → 営業利益 約5億

ANNUAL_COGS = int(ANNUAL_REVENUE * COGS_RATIO)            # 16.5億
ANNUAL_GROSS_PROFIT = ANNUAL_REVENUE - ANNUAL_COGS         # 13.5億
ANNUAL_SGA = int(ANNUAL_REVENUE * SGA_RATIO)              # 8.49億
ANNUAL_OPERATING_PROFIT = ANNUAL_GROSS_PROFIT - ANNUAL_SGA  # 約5.01億
ANNUAL_NET_PROFIT = int(ANNUAL_OPERATING_PROFIT * 0.7)    # 法人税30%控除後 ≒ 3.5億

CASH_BALANCE = 893_742_158                                 # 約8.94億 (端数付き)
LOAN_OUTSTANDING = 197_028_384                             # 約1.97億 (端数付き)
SHORT_TERM_LOAN = 38_549_127                               # 1年以内返済予定
LONG_TERM_LOAN = LOAN_OUTSTANDING - SHORT_TERM_LOAN        # 158,479,257

# AR/AP (期末残高想定)
ACCOUNTS_RECEIVABLE = int(ANNUAL_REVENUE / 12 * 1.5)      # 3.75億 (1.5月分)
ACCOUNTS_PAYABLE = int(ANNUAL_COGS / 12 * 1.5)            # 2.06億

DEMO_EMPLOYEE_COUNT = 100


def _seeded():
    return random.Random(20260518)


# ===================== 月次P/L (年間合計が必ず目標値になる) =====================
# 月別配分パターン (合計100、シーズナリティ反映)
_MONTHLY_PATTERN = [
    7.5,  # 4月
    7.0,  # 5月
    9.5,  # 6月 (Q1決算)
    8.5,  # 7月
    7.0,  # 8月 (お盆)
    8.5,  # 9月 (Q2決算)
    8.0,  # 10月
    8.5,  # 11月
    11.0, # 12月 (年末商戦)
    7.0,  # 1月 (正月)
    7.5,  # 2月
    10.0, # 3月 (FY決算)
]

def _calc_monthly_amount(annual: int, pattern_idx: int) -> int:
    """年間値を月別パターンに従って配分"""
    return int(annual * _MONTHLY_PATTERN[pattern_idx] / sum(_MONTHLY_PATTERN))


def generate_mock_pl_monthly() -> List[Dict[str, Any]]:
    """月次P/L (直近12ヶ月)。端数付きでリアル。年間合計は目標値と概ね一致。"""
    rng = _seeded()
    today = date.today()
    cursor = today.replace(day=1)
    for _ in range(12):
        cursor = (cursor - timedelta(days=1)).replace(day=1)

    rows = []
    revenues = []
    for i in range(12):
        month = cursor.month
        pattern_idx = (month - 4) % 12
        base = _calc_monthly_amount(ANNUAL_REVENUE, pattern_idx)
        # ±2.5% のリアルなブレを加える
        adj = int(base * rng.uniform(0.975, 1.025))
        revenues.append(adj)
        rows.append({"_cursor": cursor, "revenue": adj})
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    # 端数を最終月に吸収して年間合計を目標値に
    diff = ANNUAL_REVENUE - sum(revenues)
    rows[-1]["revenue"] += diff
    revenues[-1] += diff

    result = []
    for r in rows:
        rev = r["revenue"]
        # 売上原価: 53〜57%でブレ
        cogs = int(rev * rng.uniform(0.535, 0.565))
        gross_profit = rev - cogs
        # 販管費: 26〜30%でブレ
        sga = int(rev * rng.uniform(0.265, 0.295))
        op = gross_profit - sga
        # 営業外 (端数付きでリアル)
        non_op_rev = rng.randint(127_000, 832_000)     # 預金利息・雑収入
        non_op_exp = rng.randint(384_000, 891_000)     # 支払利息等
        ord_profit = op + non_op_rev - non_op_exp
        # 特別損益: 月によりたまに発生
        extra_rev = rng.randint(0, 1_800_000) if rng.random() < 0.15 else 0
        extra_exp = rng.randint(0, 1_200_000) if rng.random() < 0.10 else 0
        pretax = ord_profit + extra_rev - extra_exp
        # 実効税率約30%でブレ
        corp_tax = int(pretax * rng.uniform(0.290, 0.315)) if pretax > 0 else 0
        net = pretax - corp_tax
        result.append({
            "year_month": r["_cursor"].strftime("%Y-%m"),
            "revenue": rev,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "sga": sga,
            "operating_profit": op,
            "non_operating_income": non_op_rev,
            "non_operating_expense": non_op_exp,
            "ordinary_profit": ord_profit,
            "extraordinary_income": extra_rev,
            "extraordinary_loss": extra_exp,
            "pretax_profit": pretax,
            "corporate_tax": corp_tax,
            "net_profit": net,
        })
    return result


# ===================== B/S (P/Lと整合・端数付き) =====================
def generate_mock_bs_summary() -> Dict[str, Any]:
    """貸借対照表。端数付きでリアルな数字。
    貸借差額で利益剰余金を算出するため、必ず貸借一致。
    """
    # 流動資産 (端数付き)
    cash = CASH_BALANCE                          # 900,000,000 (口座合計と一致)
    accounts_receivable = 387_294_851            # 約3.87億 (1.5月分の売上)
    inventory = 87_432_158                       # 約8,743万
    other_current = 73_521_684                   # 約7,352万 (前払費用等)
    current_assets = cash + accounts_receivable + inventory + other_current
    # = 1,448,248,693

    # 固定資産 (端数付き)
    tangible = 247_892_341                       # 有形固定資産
    intangible = 53_287_419                      # 無形固定資産
    investments = 98_541_762                     # 投資その他
    fixed_assets = tangible + intangible + investments
    # = 399,721,522

    total_assets = current_assets + fixed_assets
    # = 1,847,970,215

    # 流動負債 (端数付き)
    accounts_payable = 198_432_517               # 買掛金 (約1.5月分の仕入)
    short_term_loan = 38_549_127                 # 1年内返済予定借入金
    other_current_liab = 148_729_403             # 未払金・未払費用等
    current_liab = accounts_payable + short_term_loan + other_current_liab
    # = 385,711,047

    # 固定負債
    long_term_loan = LOAN_OUTSTANDING - short_term_loan  # = 161,450,873
    other_fixed_liab = 47_823_159                # 退職給付引当金等
    fixed_liab = long_term_loan + other_fixed_liab
    # = 209,274,032

    total_liab = current_liab + fixed_liab
    # = 594,985,079

    # 純資産: 資本金・資本剰余金は登記額(キリ良), 利益剰余金は差額
    capital = 100_000_000                        # 資本金 (登記)
    capital_surplus = 50_000_000                 # 資本剰余金 (登記)
    retained_earnings = total_assets - total_liab - capital - capital_surplus
    # = 1,102,985,136
    net_assets = capital + capital_surplus + retained_earnings

    return {
        "current_assets": current_assets,
        "cash": cash,
        "accounts_receivable": accounts_receivable,
        "inventory": inventory,
        "other_current_assets": other_current,
        "fixed_assets": fixed_assets,
        "tangible_assets": tangible,
        "intangible_assets": intangible,
        "investments": investments,
        "total_assets": total_assets,
        "current_liabilities": current_liab,
        "accounts_payable": accounts_payable,
        "short_term_loan": short_term_loan,
        "other_current_liabilities": other_current_liab,
        "fixed_liabilities": fixed_liab,
        "long_term_loan": long_term_loan,
        "other_fixed_liabilities": other_fixed_liab,
        "total_liabilities": total_liab,
        "capital": capital,
        "capital_surplus": capital_surplus,
        "retained_earnings": retained_earnings,
        "net_assets": net_assets,
    }


# ===================== 銀行口座 (BSのcashと完全一致) =====================
# 実残高は端数付きで、合計 = CASH_BALANCE (893,742,158) になるよう調整
_BANK_BALANCES = [
    ("三菱UFJ銀行 当座", "current", 381_524_876, "0005", "新宿支店"),
    ("みずほ銀行 普通",   "savings", 217_348_192, "0001", "渋谷支店"),
    ("三井住友銀行 普通", "savings", 146_731_584, "0009", "丸の内支店"),
    ("GMOあおぞらネット銀行", "savings", 78_245_613, "0310", "本店営業部"),
    ("西武信用金庫 普通", "savings", 57_398_472, "1341", "新宿支店"),
    ("現金",             "cash",    12_493_421, "", ""),
]
# 合計確認: 381524876 + 217348192 + 146731584 + 78245613 + 57398472 + 12493421 = 893,742,158 ✓


def generate_mock_bank_accounts() -> List[Dict[str, Any]]:
    """口座残高合計 = CASH_BALANCE。端数付きでリアル。"""
    accounts = []
    for i, (name, typ, bal, code, branch) in enumerate(_BANK_BALANCES, start=1):
        accounts.append({"id": i, "name": name, "type": typ,
                         "balance": bal, "bank_code": code, "branch": branch})
    # 負債系 (除外対象)
    accounts.append({
        "id": len(accounts) + 1, "name": "役員借入金", "type": "credit",
        "balance": -52_734_219, "bank_code": "", "branch": "",
    })
    return accounts


# ===================== 借入金 (BSと一致・端数付き) =====================
def generate_mock_loans() -> List[dict]:
    """借入金合計 = LOAN_OUTSTANDING (200,000,000)。各行は端数付き。"""
    return [
        {
            "name": "三菱UFJ銀行 運転資金",
            "principal": 100_000_000,
            "outstanding": 78_234_851,           # 返済が進んで端数発生
            "annual_rate": 0.0118,
            "term_months": 84,
            "remaining_months": 60,
            "grace_months": 0,
            "repayment_day": 25,
            "start_year_month": "2023-04",
            "method": "equal_principal",
        },
        {
            "name": "みずほ銀行 設備資金",
            "principal": 80_000_000,
            "outstanding": 74_921_374,
            "annual_rate": 0.0162,
            "term_months": 120,
            "remaining_months": 96,
            "grace_months": 12,
            "repayment_day": 31,
            "start_year_month": "2024-08",
            "method": "equal_principal",
        },
        {
            "name": "日本政策金融公庫",
            "principal": 50_000_000,
            "outstanding": 43_872_159,
            "annual_rate": 0.0088,
            "term_months": 60,
            "remaining_months": 56,
            "grace_months": 6,
            "repayment_day": 25,
            "start_year_month": "2025-12",
            "method": "equal_principal",
        },
    ]
# 合計確認: 78,234,851 + 74,921,374 + 43,872,159 = 197,028,384 ✓ (= LOAN_OUTSTANDING)


# ===================== 月次履歴 (forecast用、P/Lと一致) =====================
def generate_mock_history() -> dict:
    """forecast/labor分析用の月次集計。P/L月次と同じ数値を使用。"""
    pl_rows = generate_mock_pl_monthly()
    monthly = []
    for r in pl_rows:
        # 給与は販管費の約半分を仮定 (5,000万 月平均)
        sal = int(ANNUAL_SGA / 12 * 0.5)
        # 6月12月は賞与上乗せ
        ym = r["year_month"]
        m = int(ym.split("-")[1])
        if m in (6, 12):
            sal = int(sal * 2.2)
        monthly.append({
            "year_month": ym,
            "revenue": r["revenue"],
            "expense": r["cogs"] + r["sga"] - sal,  # 給与以外の経費
            "salary": sal,
        })
    return {
        "company_id": DEMO_COMPANY_ID,
        "company_name": DEMO_COMPANY_NAME,
        "opening_cash_balance": CASH_BALANCE,
        "monthly": monthly,
    }


# ===================== 取引先 (110社) =====================
_PARTNER_PREFIXES = ["株式会社", "合同会社", "有限会社", "一般社団法人"]
_PARTNER_NAMES = [
    "アクシス", "ベルテック", "クレスト", "デルタソリューションズ", "エクセリオ",
    "フォーチュン", "グランツ", "ヘリオス", "イノベート", "ジェネシス",
    "カインドネス", "ルミナス", "メリディアン", "ノヴァ", "オリオン",
    "プリズム", "クエスト", "リバティ", "サミット", "トライアド",
    "ユニフィエ", "ヴァンガード", "ウィングス", "ゼニス", "アトラス",
    "ブリッジ", "コンセプト", "ダイナミクス", "エンパイア", "フロンティア",
    "ガーディアン", "ホライゾン", "インテグラ", "ジュピター", "カタリスト",
    "ランドスケープ", "マトリックス", "ネクサス", "オアシス", "ピナクル",
    "クォンタム", "ラディアント", "サークル", "テラ", "ユートピア",
    "ヴェロシティ", "ウェイブ", "エクストラ", "イェルバ", "ザイオン",
    "エボリューション", "ハーモニー", "ライト", "ミラージュ", "ネビュラ",
    "オーロラ", "パルス", "リフレクト", "ソナタ", "テンペスト",
    "アライアンス", "ブリッジワークス", "コアシステム", "デジタルウェイ", "エッジテック",
    "フェニックス", "グラフィック", "ハイテック", "アイデアル", "ジェットスター",
    "キャピタル", "リーディング", "マイルストーン", "ナビゲーター", "オンセット",
    "パートナーシップ", "クオリティ", "リード", "シナジー", "トラスト",
    "ユナイテッド", "ベンチャー", "ワークス", "エキスパート", "イシュー",
    "ザインティ", "プロジェクト", "ベスト", "プラス", "プロフェッショナル",
    "メタル", "サンライズ", "クリスタル", "ブルーオーシャン", "グリーンフィールド",
    "ホワイトハウス", "ブラックボックス", "レッドオーシャン", "ゴールデン", "シルバー",
]
_PARTNER_SUFFIXES = ["商事", "システム", "工業", "コーポレーション", "産業",
                     "サービス", "コンサルティング", "ホールディングス", "テクノロジーズ", ""]


def generate_mock_partners() -> List[dict]:
    partners = []
    pid = 100001
    for i in range(100):
        prefix = _PARTNER_PREFIXES[i % len(_PARTNER_PREFIXES)]
        nm = _PARTNER_NAMES[i % len(_PARTNER_NAMES)]
        suf = _PARTNER_SUFFIXES[i % len(_PARTNER_SUFFIXES)]
        full = f"{prefix}{nm}{suf}" if suf else f"{prefix}{nm}"
        partners.append({"id": pid, "name": full, "code": f"P{i+1:04d}", "is_spot": False})
        pid += 1
    for i in range(10):
        prefix = _PARTNER_PREFIXES[(100 + i) % len(_PARTNER_PREFIXES)]
        nm = _PARTNER_NAMES[((100 + i) * 3) % len(_PARTNER_NAMES)]
        partners.append({"id": pid, "name": f"{prefix}{nm}スポット",
                         "code": f"S{i+1:03d}", "is_spot": True})
        pid += 1
    return partners


# ===================== 売掛金 (AR) - 年間売上30億に整合 =====================
def generate_mock_ar_schedule() -> List[Dict[str, Any]]:
    """月別売上配分(_MONTHLY_PATTERN)に従って各月に請求書を生成。
    年間合計 ≒ 30億(税抜)+消費税10% = 33億(税込)。
    端数まで残してリアルな金額に。"""
    rng = _seeded()
    today = date.today()
    partners = generate_mock_partners()
    customers = [p for p in partners if not p["is_spot"]][:30]  # 30社想定
    items = []
    inv_no = 26010001

    # 過去12ヶ月 + 来月の各月にinvoice生成
    for month_offset in range(-12, 1):
        # その月の1日を基準に
        anchor = today.replace(day=1)
        ay = anchor.year; am = anchor.month + month_offset
        while am < 1: am += 12; ay -= 1
        while am > 12: am -= 12; ay += 1
        target_month = date(ay, am, 1)

        # その月の売上目標(税抜) = 年間×月次パターン比率
        pattern_idx = (am - 4) % 12
        month_revenue = _calc_monthly_amount(ANNUAL_REVENUE, pattern_idx)

        # この月に請求する顧客 (15-22社サンプリング)
        n_cust = rng.randint(15, 22)
        billing = rng.sample(customers, k=n_cust)
        # ウェイト分配
        weights = [rng.uniform(0.4, 3.5) for _ in billing]
        wsum = sum(weights)

        for cust, w in zip(billing, weights):
            base = int(month_revenue * w / wsum)
            if base < 100_000:
                continue
            # 消費税10% → 端数発生
            tax = int(base * 0.1)
            amount = base + tax  # 税込

            # 発行日: 月末締めの企業多い設定
            close_day = rng.choice([15, 20, 25, 31])
            try:
                if close_day == 31:
                    nm = am + 1; ny = ay
                    if nm > 12: nm = 1; ny += 1
                    issue = date(ny, nm, 1) - timedelta(days=1)
                else:
                    issue = date(ay, am, close_day)
            except ValueError:
                issue = date(ay, am, 28)

            payment_term = rng.choice([30, 30, 45, 60])
            due = issue + timedelta(days=payment_term)

            items.append({
                "invoice_no": f"INV-{inv_no:08d}",
                "customer": cust["name"],
                "issue_date": issue.isoformat(),
                "due_date": due.isoformat(),
                "amount": amount,
                "status": "paid" if due < today else "scheduled",
                "payment_term_days": payment_term,
            })
            inv_no += 1
    return sorted(items, key=lambda x: x["due_date"])


# ===================== 買掛金 (AP) - 年間原価+販管費に整合 =====================
def generate_mock_ap_schedule() -> List[Dict[str, Any]]:
    """月別の原価+販管費(給与除く)に従って支払請求書を生成。
    年間合計 ≒ (16.5億 + 8.49億 - 給与年間6億) ≒ 19億(税抜) → 約21億(税込)"""
    rng = _seeded()
    today = date.today()
    partners = generate_mock_partners()
    vendors = [p for p in partners if not p["is_spot"]][30:65]  # 35社想定
    categories = ["仕入", "外注費", "通信費", "水道光熱費", "地代家賃",
                  "業務委託費", "ソフトウェア利用料", "リース料", "広告宣伝費"]

    salary_annual = int(ANNUAL_SGA * 0.5)  # 販管費の半分が給与
    annual_payable_base = ANNUAL_COGS + (ANNUAL_SGA - salary_annual)  # 給与以外
    items = []
    bill_no = 50010001

    for month_offset in range(-12, 1):
        anchor = today.replace(day=1)
        ay = anchor.year; am = anchor.month + month_offset
        while am < 1: am += 12; ay -= 1
        while am > 12: am -= 12; ay += 1
        target_month = date(ay, am, 1)

        pattern_idx = (am - 4) % 12
        month_payable = _calc_monthly_amount(annual_payable_base, pattern_idx)

        n_vend = rng.randint(18, 28)
        billing = rng.sample(vendors, k=n_vend)
        weights = [rng.uniform(0.3, 4.0) for _ in billing]
        wsum = sum(weights)

        for i, (vend, w) in enumerate(zip(billing, weights)):
            base = int(month_payable * w / wsum)
            if base < 50_000:
                continue
            tax = int(base * 0.1)
            amount = base + tax
            category = categories[i % len(categories)]

            close_day = rng.choice([20, 25, 31])
            try:
                if close_day == 31:
                    nm = am + 1; ny = ay
                    if nm > 12: nm = 1; ny += 1
                    issue = date(ny, nm, 1) - timedelta(days=1)
                else:
                    issue = date(ay, am, close_day)
            except ValueError:
                issue = date(ay, am, 28)

            payment_term = rng.choice([30, 30, 45, 60])
            due = issue + timedelta(days=payment_term)

            items.append({
                "bill_no": f"AP-{bill_no:08d}",
                "vendor": vend["name"],
                "category": category,
                "issue_date": issue.isoformat(),
                "due_date": due.isoformat(),
                "amount": amount,
                "status": "paid" if due < today else "scheduled",
            })
            bill_no += 1
    return sorted(items, key=lambda x: x["due_date"])


# ===================== 税金カレンダー =====================
def generate_mock_tax_calendar() -> List[Dict[str, Any]]:
    today = date.today()
    items = []
    year = today.year

    def _add(d: date, name: str, kind: str, amount: int, note: str = ""):
        items.append({"due_date": d.isoformat(), "name": name, "kind": kind,
                      "amount": amount, "note": note})

    cursor = today.replace(day=1)
    for _ in range(15):
        due = cursor.replace(day=10)
        if due >= today - timedelta(days=60):
            _add(due, "源泉所得税納付", "withholding", 3_500_000, "前月給与・報酬分")
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    cursor = today.replace(day=1)
    for _ in range(15):
        due = cursor.replace(day=10)
        if due >= today - timedelta(days=60):
            _add(due, "住民税特別徴収", "resident", 4_200_000, "従業員給与天引分")
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    cursor = today.replace(day=1)
    for _ in range(15):
        last_day = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if last_day >= today - timedelta(days=60):
            _add(last_day, "社会保険料納付", "social_insurance", 15_500_000, "健保・厚年・子育拠出金")
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    for m in (5, 8, 11, 2):
        y = year if m >= today.month else year + 1
        d = date(y, m, 28)
        _add(d, "消費税中間納付", "consumption", 30_000_000, "3月決算法人 中間納付")

    y_mid = year if 11 >= today.month else year + 1
    _add(date(y_mid, 11, 30), "法人税・地方法人税 中間納付", "corporate", 75_000_000, "前年度法人税額の1/2")

    y = year if 5 >= today.month else year + 1
    _add(date(y, 5, 31), "法人税・地方法人税 確定申告", "corporate", 95_000_000, "3月決算 確定申告")
    _add(date(y, 5, 31), "消費税 確定申告", "consumption", 55_000_000, "3月決算 確定申告")
    _add(date(y, 5, 31), "法人住民税・事業税 確定申告", "resident", 38_000_000, "3月決算 確定申告")

    for idx, m in enumerate([4, 7, 12, 2]):
        y = year if m >= today.month else year + 1
        _add(date(y, m, 28), "固定資産税", "property", 5_800_000, f"第{idx+1}期")

    items = [i for i in items
             if today - timedelta(days=60)
             <= date.fromisoformat(i["due_date"])
             <= today + timedelta(days=365)]
    return sorted(items, key=lambda x: x["due_date"])


# ===================== 従業員 (100名) =====================
_NAMES_LAST = [
    "佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤",
    "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水",
    "山崎", "森", "池田", "橋本", "阿部", "石川", "山下", "中島", "石井", "小川",
    "前田", "岡田", "長谷川", "藤田", "近藤", "後藤", "村上", "遠藤", "青木", "坂本",
    "金子", "中野", "原田", "藤井", "西村",
]
_NAMES_FIRST = [
    "太郎", "次郎", "三郎", "健一", "雄一", "誠", "健太", "翔太", "拓海", "大輔",
    "亮", "和也", "雄大", "達也", "翔", "悠斗", "陽斗", "蓮", "颯太", "湊",
    "花子", "美咲", "由美", "彩", "麻衣", "理沙", "綾乃", "美穂", "明日香", "佳奈",
    "千尋", "葵", "結衣", "心春", "陽菜", "美月", "凛", "莉子", "結菜", "桜",
]
_DEPARTMENTS = ["経営企画部", "営業1部", "営業2部", "営業3部", "技術開発部",
                "プロダクト開発部", "マーケティング部", "コーポレート部", "経理財務部", "人事部"]


_PREFECTURES = ["東京都", "東京都", "東京都", "東京都", "神奈川県", "神奈川県",
                "埼玉県", "千葉県", "東京都", "神奈川県"]
_CITIES_TOKYO = ["渋谷区", "新宿区", "港区", "世田谷区", "杉並区", "目黒区",
                 "品川区", "中央区", "豊島区", "練馬区", "江東区", "大田区"]
_UNIVERSITIES = ["東京大学", "京都大学", "早稲田大学", "慶應義塾大学", "上智大学",
                 "東京理科大学", "明治大学", "立教大学", "中央大学", "法政大学",
                 "青山学院大学", "学習院大学", "津田塾大学", "国際基督教大学",
                 "東京工業大学", "一橋大学", "北海道大学", "東北大学", "名古屋大学",
                 "大阪大学", "九州大学", "筑波大学"]
_SKILLS_POOL = ["Excel", "PowerPoint", "Python", "JavaScript", "Java", "Go", "Rust",
                "AWS", "GCP", "Azure", "Docker", "Kubernetes", "React", "Vue.js",
                "Salesforce", "SAP", "Tableau", "Figma", "Adobe Illustrator",
                "簿記2級", "TOEIC900", "中小企業診断士", "宅地建物取引士",
                "プロジェクトマネジメント", "営業戦略", "マーケティング戦略",
                "データ分析", "プロダクトマネジメント"]
_BLOOD_TYPES = ["A", "B", "O", "AB"]
_INTERVIEW_TOPICS = [
    "現状の業務と課題感の共有",
    "キャリアパスの希望と中期的な目標",
    "チーム内コミュニケーションの状況",
    "業務改善提案・新規プロジェクトのアイデア",
    "ワークライフバランスと健康面の確認",
    "スキルアップ・研修希望のヒアリング",
    "目標進捗の振り返りと評価フィードバック",
    "他部署との連携状況確認",
]
_ONBOARDING_STEPS = [
    "雇用契約書の締結",
    "マイナンバー提出",
    "社会保険・雇用保険加入手続き",
    "源泉徴収票の提出",
    "PC・備品の貸与",
    "社内アカウント発行 (Slack, GitHub, Google Workspace)",
    "オリエンテーション参加",
    "メンター紹介",
    "セキュリティ研修受講",
    "コンプライアンス研修受講",
]


def _gen_employee_detail(rng, emp: dict) -> dict:
    """1名分の詳細データを生成"""
    # 生年月日 (年齢 22-58)
    age = rng.randint(22, 58)
    bday = date.today() - timedelta(days=age * 365 + rng.randint(0, 364))
    pref = rng.choice(_PREFECTURES)
    if pref == "東京都":
        city = rng.choice(_CITIES_TOKYO)
    else:
        city = rng.choice(["中央区", "西区", "北区", "南区", "緑区"])

    # 住所
    address = f"{pref}{city}{rng.randint(1,5)}-{rng.randint(1,30)}-{rng.randint(1,40)}"
    # 電話
    phone_mobile = f"090-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}"
    # 学歴
    grad_year = bday.year + 22
    university = rng.choice(_UNIVERSITIES)
    faculty = rng.choice(["経済学部", "商学部", "経営学部", "工学部", "理学部",
                          "文学部", "法学部", "情報学部", "国際関係学部"])
    # スキル
    skills = rng.sample(_SKILLS_POOL, k=rng.randint(3, 7))
    # 緊急連絡先
    emerg_name = f"{emp['name'].split()[0]} {rng.choice(['花子','一郎','明美','健治'])}"
    emerg_rel = rng.choice(["配偶者", "配偶者", "父", "母", "兄弟"])
    # 入社手続きチェックリスト
    onboarding = []
    completion_rate = rng.uniform(0.7, 1.0)
    for step in _ONBOARDING_STEPS:
        done = rng.random() < completion_rate
        onboarding.append({
            "item": step,
            "done": done,
            "completed_at": (date.fromisoformat(emp["hire_date"]) +
                             timedelta(days=rng.randint(0, 30))).isoformat() if done else None,
        })
    # 面談履歴 (過去6回)
    interviews = []
    for back_months in range(6, 0, -1):
        i_date = date.today() - timedelta(days=back_months * 30 + rng.randint(0, 7))
        if i_date < date.fromisoformat(emp["hire_date"]):
            continue
        interviews.append({
            "date": i_date.isoformat(),
            "interviewer": rng.choice(["佐藤 直樹 (人事部長)", "山田 健太 (上長)", "鈴木 由美 (HR)",
                                       "高橋 雄一 (執行役員)"]),
            "type": rng.choice(["1on1", "定期面談", "目標設定", "評価面談"]),
            "summary": rng.choice(_INTERVIEW_TOPICS),
            "next_action": rng.choice([
                "次回までに研修受講予定", "新規プロジェクト参画検討", "目標進捗フォローアップ",
                "メンタリング継続", "業務改善提案を月末まで提出", "特になし",
            ]),
        })
    # 評価
    evaluations = []
    for back_years in range(min(3, age - 21)):
        y = date.today().year - back_years - 1
        if y < int(emp["hire_date"][:4]):
            continue
        evaluations.append({
            "year": y,
            "overall": rng.choice(["S", "A", "A", "B", "B", "B", "C"]),
            "achievement": rng.randint(70, 130),  # 目標達成率%
            "comment": rng.choice([
                "目標を上回る成果を出している。来期は更なる挑戦に期待。",
                "業務遂行は安定しているが、リーダーシップ発揮が課題。",
                "チームへの貢献度高い。専門スキル向上を継続。",
                "新規案件で大きな成果を挙げた。マネジメント能力育成中。",
                "業務改善提案が多く、組織への貢献度が高い。",
            ]),
        })

    return {
        "birth_date": bday.isoformat(),
        "age": age,
        "gender": rng.choice(["男性", "男性", "女性", "女性", "その他"]),
        "blood_type": rng.choice(_BLOOD_TYPES),
        "address": address,
        "phone_mobile": phone_mobile,
        "email_personal": f"{emp['name'].replace(' ', '').lower()}@example.com",
        "email_work": f"emp{emp['employee_number']}@stahr-tech.co.jp",
        "education": {
            "university": university,
            "faculty": faculty,
            "graduation_year": grad_year,
        },
        "skills": skills,
        "languages": rng.sample(
            ["英語(ビジネス)", "英語(日常会話)", "中国語(ビジネス)", "韓国語(初級)", "なし"],
            k=rng.randint(1, 2),
        ),
        "emergency_contact": {
            "name": emerg_name,
            "relationship": emerg_rel,
            "phone": f"080-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
        },
        "bank_account": {
            "bank": rng.choice(["三菱UFJ銀行", "みずほ銀行", "三井住友銀行", "りそな銀行", "楽天銀行"]),
            "branch": rng.choice(["新宿支店", "渋谷支店", "本店営業部", "丸の内支店", "ネット支店"]),
            "type": "普通",
            "number_masked": f"****{rng.randint(1000,9999)}",
        },
        "onboarding_checklist": onboarding,
        "interviews": list(reversed(interviews)),  # 最新順
        "evaluations": list(reversed(evaluations)),
    }


def generate_mock_employees() -> List[Dict[str, Any]]:
    rng = _seeded()
    role_plan = [
        ("代表取締役", 1_500_000, "経営企画部"),
        ("取締役", 1_000_000, "経営企画部"),
        ("取締役", 1_000_000, "経営企画部"),
    ]
    for _ in range(5):
        role_plan.append(("執行役員", 800_000, rng.choice(_DEPARTMENTS)))
    for _ in range(8):
        role_plan.append(("部長", 700_000, rng.choice(_DEPARTMENTS)))
    for _ in range(12):
        role_plan.append(("マネージャー", 520_000, rng.choice(_DEPARTMENTS)))
    for _ in range(10):
        role_plan.append(("チーフ", 450_000, rng.choice(_DEPARTMENTS)))
    for _ in range(10):
        role_plan.append(("リーダー", 400_000, rng.choice(_DEPARTMENTS)))
    for _ in range(50):
        base = rng.choice([280_000, 300_000, 320_000, 350_000, 380_000])
        role_plan.append(("メンバー", base, rng.choice(_DEPARTMENTS)))
    for _ in range(2):
        role_plan.append(("アソシエイト", 250_000, rng.choice(_DEPARTMENTS)))

    employees = []
    for i, (pos, base_pay, dept) in enumerate(role_plan):
        years_ago = rng.randint(0, 9)
        months_ago = rng.randint(0, 11)
        hire = date.today() - timedelta(days=years_ago * 365 + months_ago * 30)
        salary = int(base_pay * rng.uniform(0.95, 1.10) / 1000) * 1000
        commute = int(rng.uniform(5_000, 35_000) / 100) * 100
        etype = "役員" if pos in ("代表取締役", "取締役") else "正社員"
        full_name = f"{_NAMES_LAST[i % len(_NAMES_LAST)]} {_NAMES_FIRST[(i * 7) % len(_NAMES_FIRST)]}"
        emp = {
            "id": 10000 + i,
            "employee_number": f"{i+1:04d}",
            "name": full_name,
            "position": pos,
            "department": dept,
            "monthly_salary": salary,
            "commute_allowance": commute,
            "annual_salary": salary * 12 + (salary * 4 if etype != "役員" else 0),
            "hire_date": hire.isoformat(),
            "employment_type": etype,
            "remaining_paid_leave": int(rng.uniform(5, 20)),
            "overtime_hours_last_month": round(rng.uniform(0, 35), 1),
        }
        # 詳細データを付与
        emp["detail"] = _gen_employee_detail(rng, emp)
        employees.append(emp)
    return employees


# ===================== 給与履歴 =====================
def generate_mock_payroll_history() -> List[Dict[str, Any]]:
    """月次給与履歴。labor分析の母集団。"""
    today = date.today()
    cursor = today.replace(day=1)
    for _ in range(12):
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    rows = []
    for _ in range(12):
        ym = cursor.strftime("%Y-%m")
        is_bonus = cursor.month in (6, 12)
        base_gross = int(ANNUAL_SGA / 12 * 0.5)  # 販管費の半分を給与と仮定
        gross = int(base_gross * (2.2 if is_bonus else 1.0))
        social_ins_employee = int(gross * 0.155)
        social_ins_employer = int(gross * 0.165)
        withholding = int(gross * 0.08)
        resident_tax = int(gross * 0.06) if not is_bonus else 0
        net = gross - social_ins_employee - withholding - resident_tax
        rows.append({
            "year_month": ym,
            "is_bonus_month": is_bonus,
            "gross_salary": gross,
            "social_insurance_employee": social_ins_employee,
            "social_insurance_employer": social_ins_employer,
            "withholding_tax": withholding,
            "resident_tax": resident_tax,
            "net_payment": net,
            "employer_total_cost": gross + social_ins_employer,
            "employee_count": DEMO_EMPLOYEE_COUNT,
        })
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return rows


# ===================== 賞与カレンダー =====================
def generate_mock_bonus_calendar() -> List[Dict[str, Any]]:
    today = date.today()
    items = []
    year = today.year
    for offset in range(-1, 3):
        y = year + offset
        for m, label, factor in [(7, "夏季賞与", 1.5), (12, "冬季賞与", 2.2)]:
            pay_date = date(y, m, 10)
            base = int(ANNUAL_SGA / 12 * 0.5)
            amount = int(base * factor)
            if pay_date >= today - timedelta(days=180):
                items.append({
                    "pay_date": pay_date.isoformat(),
                    "name": label,
                    "amount": amount,
                    "note": f"基準額×{factor}ヶ月",
                })
    return sorted(items, key=lambda x: x["pay_date"])


# ===================== 人件費分析 =====================
def generate_mock_labor_analysis() -> Dict[str, Any]:
    """人件費分析。P/L月次と整合。"""
    pl_rows = generate_mock_pl_monthly()
    total_rev = sum(r["revenue"] for r in pl_rows)
    # 人件費構成: SGAの50%が給料手当 + 法定福利16.5% + 旅費1.5%
    monthly_sal_base = int(ANNUAL_SGA / 12 * 0.5)
    total_sal = monthly_sal_base * 12

    cogs_salary_ratio = 0.55  # 売上原価人件費の比率
    cogs_salary = int(total_sal * cogs_salary_ratio)
    sga_salary = total_sal - cogs_salary
    cogs_si = int(cogs_salary * 0.165)
    sga_si = int(sga_salary * 0.165)
    cogs_travel = int(total_rev * 0.005)
    cogs_labor_total = cogs_salary + cogs_si + cogs_travel
    sga_labor_total = sga_salary + sga_si
    total_labor = cogs_labor_total + sga_labor_total

    monthly_breakdown = []
    for r in pl_rows:
        rev = r["revenue"]
        sal_factor = rev / (total_rev / 12)  # 売上に比例
        sal_m = int(monthly_sal_base * sal_factor)
        c_sal = int(sal_m * cogs_salary_ratio)
        s_sal = sal_m - c_sal
        c_si = int(c_sal * 0.165)
        s_si = int(s_sal * 0.165)
        c_tr = int(rev * 0.005)
        c_total = c_sal + c_si + c_tr
        s_total = s_sal + s_si
        m_total = c_total + s_total
        monthly_breakdown.append({
            "year_month": r["year_month"],
            "revenue": rev,
            "cogs_salary": c_sal,
            "cogs_social_insurance": c_si,
            "cogs_travel": c_tr,
            "cogs_labor_total": c_total,
            "sga_salary": s_sal,
            "sga_social_insurance": s_si,
            "sga_labor_total": s_total,
            "labor_total": m_total,
            "cogs_labor_to_revenue_ratio": round(c_total / rev * 100, 2) if rev else 0,
            "labor_to_revenue_ratio": round(m_total / rev * 100, 2) if rev else 0,
            "revenue_per_employee": int(rev / DEMO_EMPLOYEE_COUNT),
            "employee_count": DEMO_EMPLOYEE_COUNT,
        })

    return {
        "annual_revenue": total_rev,
        "annual_cogs_salary": cogs_salary,
        "annual_cogs_social_insurance": cogs_si,
        "annual_cogs_travel": cogs_travel,
        "annual_cogs_labor_total": cogs_labor_total,
        "annual_sga_salary": sga_salary,
        "annual_sga_social_insurance": sga_si,
        "annual_sga_labor_total": sga_labor_total,
        "annual_total_labor_cost": total_labor,
        "cogs_labor_to_revenue_ratio": round(cogs_labor_total / total_rev * 100, 2),
        "labor_to_revenue_ratio": round(total_labor / total_rev * 100, 2),
        "revenue_per_employee_annual": int(total_rev / DEMO_EMPLOYEE_COUNT),
        "labor_cost_per_employee_monthly": int(total_labor / 12 / DEMO_EMPLOYEE_COUNT),
        "employee_count": DEMO_EMPLOYEE_COUNT,
        "monthly_breakdown": monthly_breakdown,
    }


# ===================== 入金/支払予測 (12ヶ月) =====================
def generate_mock_payment_forecast(deal_type: str = "income", months_ahead: int = 12) -> Dict[str, Any]:
    """取引先別の入金・支払予測。年間30億売上ベース。"""
    rng = _seeded()
    today = date.today()
    partners = generate_mock_partners()

    if deal_type == "income":
        target_partners = [p for p in partners if not p["is_spot"]][:30]
        annual_total = ANNUAL_REVENUE
    else:
        target_partners = [p for p in partners if not p["is_spot"]][30:65]
        annual_total = ANNUAL_COGS + (ANNUAL_SGA - int(ANNUAL_SGA * 0.5))  # 仕入+販管費(給与除く)

    patterns = []
    per_partner_annual = annual_total // len(target_partners)

    for i, partner in enumerate(target_partners):
        # 各取引先の規模・頻度をランダム決定
        size_factor = rng.uniform(0.4, 3.0)
        partner_annual_excl = int(per_partner_annual * size_factor)  # 税抜年間
        freq = rng.choice([1, 1, 1, 1, 2, 3, 6, 12])  # 毎月が一番多い
        per_invoice_excl = int(partner_annual_excl / (12 / freq))
        per_invoice_taxed = int(per_invoice_excl * 1.1)  # 税込

        close_day = rng.choice([15, 20, 25, 31, 31, 31])  # 末日が多い
        # 支払サイト
        offset_months = rng.choice([0, 1, 1, 1, 2])
        pay_day = rng.choice([10, 15, 20, 25, 31, 31])

        # 過去履歴 (12ヶ月分)
        past_items = []
        for back in range(12, 0, -1):
            issue_y = today.year; issue_m = today.month - back
            while issue_m < 1: issue_m += 12; issue_y -= 1
            # 頻度に合わせて
            if back % freq != 0:
                continue
            try:
                if close_day >= 31:
                    nm = issue_m + 1; ny = issue_y
                    if nm > 12: nm = 1; ny += 1
                    issue_d = date(ny, nm, 1) - timedelta(days=1)
                else:
                    issue_d = date(issue_y, issue_m, min(close_day, 28))
            except ValueError:
                issue_d = date(issue_y, issue_m, 28)
            due_y = issue_d.year; due_m = issue_d.month + offset_months
            while due_m > 12: due_m -= 12; due_y += 1
            if pay_day >= 31:
                nm = due_m + 1; ny = due_y
                if nm > 12: nm = 1; ny += 1
                due_d = date(ny, nm, 1) - timedelta(days=1)
            else:
                try:
                    due_d = date(due_y, due_m, pay_day)
                except ValueError:
                    due_d = date(due_y, due_m, 28)
            amt = int(per_invoice_taxed * rng.uniform(0.92, 1.08))
            past_items.append({
                "issue_date": issue_d.isoformat(),
                "due_date": due_d.isoformat(),
                "amount": amt,
            })

        # 将来予測 (months_ahead月分)
        future = []
        for fwd in range(1, months_ahead + 1):
            if fwd % freq != 0:
                continue
            issue_y = today.year; issue_m = today.month + fwd
            while issue_m > 12: issue_m -= 12; issue_y += 1
            try:
                if close_day >= 31:
                    nm = issue_m + 1; ny = issue_y
                    if nm > 12: nm = 1; ny += 1
                    issue_d = date(ny, nm, 1) - timedelta(days=1)
                else:
                    issue_d = date(issue_y, issue_m, min(close_day, 28))
            except ValueError:
                issue_d = date(issue_y, issue_m, 28)
            due_y = issue_d.year; due_m = issue_d.month + offset_months
            while due_m > 12: due_m -= 12; due_y += 1
            if pay_day >= 31:
                nm = due_m + 1; ny = due_y
                if nm > 12: nm = 1; ny += 1
                due_d = date(ny, nm, 1) - timedelta(days=1)
            else:
                try:
                    due_d = date(due_y, due_m, pay_day)
                except ValueError:
                    due_d = date(due_y, due_m, 28)
            future.append({
                "issue_date": issue_d.isoformat(),
                "due_date": due_d.isoformat(),
                "amount": per_invoice_taxed,
                "is_override": False,
            })

        if not past_items and not future:
            continue
        last_issue = past_items[-1]["issue_date"] if past_items else today.isoformat()
        last_due = past_items[-1]["due_date"] if past_items else today.isoformat()
        patterns.append({
            "partner": partner["name"],
            "past_count": len(past_items),
            "past_total": sum(i["amount"] for i in past_items),
            "avg_amount": per_invoice_taxed,
            "frequency_months": freq,
            "close_day": close_day,
            "payment_term_days": (offset_months * 30) + pay_day,
            "payment_offset_months": offset_months,
            "payment_day": pay_day,
            "tax_rate": 10,
            "last_issue_date": last_issue,
            "last_due_date": last_due,
            "past_items": past_items,
            "future": future,
            "future_count": len(future),
            "future_total": sum(f["amount"] for f in future),
        })

    return {
        "deal_type": deal_type,
        "based_on_days": 365,
        "months_ahead": months_ahead,
        "patterns": sorted(patterns, key=lambda x: x["future_total"], reverse=True),
    }


# ===================== 日次CF予測 =====================
def generate_mock_daily_forecast(opening_balance: int = None, days: int = 30) -> List[Dict[str, Any]]:
    """日次CF予測。期首残高=CASH_BALANCE。"""
    if opening_balance is None:
        opening_balance = CASH_BALANCE
    today = date.today()
    ar = generate_mock_ar_schedule()
    ap = generate_mock_ap_schedule()
    tax = generate_mock_tax_calendar()
    bonus = generate_mock_bonus_calendar()

    daily: Dict[str, Dict[str, Any]] = {}
    for offset in range(days):
        d = today + timedelta(days=offset)
        ds = d.isoformat()
        daily[ds] = {
            "date": ds,
            "weekday": ["月", "火", "水", "木", "金", "土", "日"][d.weekday()],
            "is_weekend": d.weekday() >= 5,
            "inflow": 0, "outflow": 0,
            "inflow_items": [], "outflow_items": [],
        }

    for inv in ar:
        ds = inv["due_date"]
        if ds in daily and inv["status"] == "scheduled":
            daily[ds]["inflow"] += inv["amount"]
            daily[ds]["inflow_items"].append({"label": inv["customer"], "amount": inv["amount"]})
    for bill in ap:
        ds = bill["due_date"]
        if ds in daily and bill["status"] == "scheduled":
            daily[ds]["outflow"] += bill["amount"]
            daily[ds]["outflow_items"].append({"label": f"{bill['vendor']} ({bill['category']})", "amount": bill["amount"]})
    for t in tax:
        ds = t["due_date"]
        if ds in daily:
            daily[ds]["outflow"] += t["amount"]
            daily[ds]["outflow_items"].append({"label": f"税金: {t['name']}", "amount": t["amount"]})
    for b in bonus:
        ds = b["pay_date"]
        if ds in daily:
            daily[ds]["outflow"] += b["amount"]
            daily[ds]["outflow_items"].append({"label": f"賞与: {b['name']}", "amount": b["amount"]})
    # 給与
    salary_monthly = int(ANNUAL_SGA / 12 * 0.5)
    for offset in range(days):
        d = today + timedelta(days=offset)
        if d.day == 25:
            ds = d.isoformat()
            daily[ds]["outflow"] += salary_monthly
            daily[ds]["outflow_items"].append({"label": f"給与支払 ({DEMO_EMPLOYEE_COUNT}名分)", "amount": salary_monthly})

    rows = sorted(daily.values(), key=lambda x: x["date"])
    balance = opening_balance
    for row in rows:
        row["net"] = row["inflow"] - row["outflow"]
        balance += row["net"]
        row["ending_balance"] = balance
    return rows
