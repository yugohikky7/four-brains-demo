"""Demo mock data. 売上30億円規模の中堅企業を想定。
単一のマスター数値から全諸表を整合的に生成する。
v2: 統一CFモデル_monthly_cash_breakdown()でP/L・B/S・C/F・AR/AP・日次CF整合性確保。
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

DEMO_EMPLOYEE_COUNT = 138


# ===================== 統一CFモデル (全諸表の単一データソース) =====================
# 売上30億・営利5億・現預金9億・借入2億の会社想定。
# このモジュールの全 generate_mock_* は、ここで定義された数値整合性に従う。

# 販管費(¥849M/年)の内訳 ─────────────────────────────────
# 給料手当 (賞与抜き) : 40% → ¥339.6M/年 (月平均 ¥28.3M)
# 賞与               : 10% → ¥84.9M/年
# 法定福利           : 6.5% → ¥55.2M/年
# 旅費交通費等       : 3.5% → ¥29.7M/年
# 地代家賃・通信・水光 : 8% → ¥67.9M/年
# 業務委託・外注     : 12% → ¥101.9M/年
# 広告宣伝・販促     : 10% → ¥84.9M/年
# 減価償却(非現金)   : 6% → ¥50.9M/年
# その他経費         : 4% → ¥33.9M/年
ANNUAL_SALARY_GROSS    = int(ANNUAL_SGA * 0.40)   # ¥339,600,000
ANNUAL_BONUS_GROSS     = int(ANNUAL_SGA * 0.10)   # ¥84,900,000
ANNUAL_SI_EMPLOYER     = int(ANNUAL_SGA * 0.065)  # ¥55,185,000
ANNUAL_DEPRECIATION    = int(ANNUAL_SGA * 0.06)   # ¥50,940,000 (非現金、SGA内)
# SGAから「現金支出を伴う非給与経費」= SGA - 給与 - 賞与 - 社保 - 減価償却
ANNUAL_SGA_CASH_OTHER  = ANNUAL_SGA - ANNUAL_SALARY_GROSS - ANNUAL_BONUS_GROSS - ANNUAL_SI_EMPLOYER - ANNUAL_DEPRECIATION

# ベンダー支払 (税抜) = 売上原価 + 給与/賞与/社保/減価以外の販管費
ANNUAL_VENDOR_PAYABLE_EXCL = ANNUAL_COGS + ANNUAL_SGA_CASH_OTHER
# = 1,650,000,000 + 317,275,000 = 1,967,275,000

# 税金 (年間納付額) ─────────────────────────────────
ANNUAL_CONSUMPTION_TAX_NET = int(ANNUAL_REVENUE * 0.03)   # 預り消費税-払い消費税の差≒3% = ¥90M
ANNUAL_CORPORATE_TAX       = int(ANNUAL_OPERATING_PROFIT * 0.30)  # 法人税等 ≒ ¥150M
ANNUAL_PROPERTY_TAX        = 23_200_000                    # 固定資産税 (端数)
ANNUAL_TAX_PAYABLE_TOTAL   = ANNUAL_CONSUMPTION_TAX_NET + ANNUAL_CORPORATE_TAX + ANNUAL_PROPERTY_TAX
# ≒ ¥263.5M

# 借入 ─────────────────────────────────
ANNUAL_LOAN_PRINCIPAL_REPAY = SHORT_TERM_LOAN              # ¥38,549,127
ANNUAL_LOAN_INTEREST        = int(LOAN_OUTSTANDING * 0.012) # ≒ ¥2,364,340

# 投資 ─────────────────────────────────
ANNUAL_CAPEX = -55_300_000  # 投資CF (固定資産取得)

# CF合計の整合チェック ─────────────────────────────────
# 営業CF ≒ 営利5億 + 減価償却50.9M - 税金263.5M - 利息2.4M = ¥285.9M
# 投資CF = -¥55.3M
# 財務CF = -¥38.5M
# Free CF ≒ +¥192M / 年


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


def _month_share(month: int) -> float:
    """指定月の年間に対する比率"""
    idx = (month - 4) % 12
    return _MONTHLY_PATTERN[idx] / sum(_MONTHLY_PATTERN)


def _calc_monthly_amount(annual: int, pattern_idx: int) -> int:
    """年間値を月別パターンに従って配分"""
    return int(annual * _MONTHLY_PATTERN[pattern_idx] / sum(_MONTHLY_PATTERN))


# ===================== 統一月次CF分解 (キャッシュベース) =====================
_CASH_BREAKDOWN_CACHE = None


def _monthly_cash_breakdown() -> List[Dict[str, Any]]:
    """単一の月次キャッシュフロー分解 (直近12ヶ月)。
    全ての generate_mock_* がこの戻り値の数字に従う。
    キャッシュベースで年間合計はマスター数値と完全に一致。
    """
    global _CASH_BREAKDOWN_CACHE
    if _CASH_BREAKDOWN_CACHE is not None:
        return _CASH_BREAKDOWN_CACHE

    today = date.today()
    cursor = today.replace(day=1)
    for _ in range(12):
        cursor = (cursor - timedelta(days=1)).replace(day=1)

    rng = _seeded()
    rows = []
    rev_total = 0
    vendor_total = 0

    for i in range(12):
        share = _month_share(cursor.month)
        # ±2%のリアルなブレ
        rev_excl = int(ANNUAL_REVENUE * share * rng.uniform(0.98, 1.02))
        vendor_excl = int(ANNUAL_VENDOR_PAYABLE_EXCL * share * rng.uniform(0.97, 1.03))
        rev_total += rev_excl
        vendor_total += vendor_excl

        rows.append({
            "_cursor": cursor,
            "year_month": cursor.strftime("%Y-%m"),
            "month_num": cursor.month,
            "revenue_excl": rev_excl,
            "vendor_pay_excl": vendor_excl,
        })
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    # 端数を最終月に吸収して年間合計を目標値に一致
    rows[-1]["revenue_excl"] += (ANNUAL_REVENUE - rev_total)
    rows[-1]["vendor_pay_excl"] += (ANNUAL_VENDOR_PAYABLE_EXCL - vendor_total)

    # 月次の費目
    monthly_salary = ANNUAL_SALARY_GROSS // 12
    summer_bonus = int(ANNUAL_BONUS_GROSS * 1.5 / (1.5 + 2.2))
    winter_bonus = ANNUAL_BONUS_GROSS - summer_bonus
    monthly_si = ANNUAL_SI_EMPLOYER // 12
    monthly_withholding = int(monthly_salary * 0.08)        # 源泉所得税 (前月給与×8%)
    monthly_resident = int(monthly_salary * 0.06)            # 住民税納付
    monthly_principal = ANNUAL_LOAN_PRINCIPAL_REPAY // 12
    monthly_interest = ANNUAL_LOAN_INTEREST // 12
    monthly_capex = ANNUAL_CAPEX // 12                       # 投資CF (毎月均等)

    # 税金カレンダー (3月決算想定)
    def tax_for_month(m: int) -> int:
        amt = 0
        if m == 5:  # 確定申告
            amt += ANNUAL_CONSUMPTION_TAX_NET // 2
            amt += ANNUAL_CORPORATE_TAX // 2
        elif m == 11:  # 中間 (法人税+消費税)
            amt += ANNUAL_CORPORATE_TAX // 2
            amt += ANNUAL_CONSUMPTION_TAX_NET // 6
        elif m in (8, 2):  # 消費税中間
            amt += ANNUAL_CONSUMPTION_TAX_NET // 6
        if m in (4, 7, 12, 2):  # 固定資産税
            amt += ANNUAL_PROPERTY_TAX // 4
        return amt

    result = []
    for r in rows:
        m = r["month_num"]
        bonus = summer_bonus if m == 6 else (winter_bonus if m == 12 else 0)
        # 賞与月は社保多め
        si = int(monthly_si * (1.7 if bonus else 1.0))
        result.append({
            "year_month": r["year_month"],
            "month_num": m,
            "revenue_excl": r["revenue_excl"],
            "revenue_taxed": int(r["revenue_excl"] * 1.1),
            "vendor_pay_excl": r["vendor_pay_excl"],
            "vendor_pay_taxed": int(r["vendor_pay_excl"] * 1.1),
            "salary": monthly_salary,
            "bonus": bonus,
            "si_employer": si,
            "withholding_pay": monthly_withholding,
            "resident_tax_pay": monthly_resident,
            "tax_payment": tax_for_month(m),
            "loan_principal": monthly_principal,
            "loan_interest": monthly_interest,
            "capex": monthly_capex,
            "depreciation": ANNUAL_DEPRECIATION // 12,  # 非現金、P/L経費のみ
        })

    _CASH_BREAKDOWN_CACHE = result
    return result


def _monthly_total_outflow(row: Dict[str, Any]) -> int:
    """その月の現金支出合計 (forecast用)"""
    return (row["vendor_pay_taxed"]
            + row["salary"] + row["bonus"]
            + row["si_employer"]
            + row["withholding_pay"] + row["resident_tax_pay"]
            + row["tax_payment"]
            + row["loan_principal"] + row["loan_interest"]
            - row["capex"])  # capexは負数なので引く=足す


def generate_mock_pl_monthly() -> List[Dict[str, Any]]:
    """月次P/L (直近12ヶ月)。統一CFモデルから派生。
    年間合計: 売上¥3B, 営利¥501M, 当期純利益¥350M。
    """
    rng = _seeded()
    cash_rows = _monthly_cash_breakdown()

    result = []
    for cr in cash_rows:
        rev = cr["revenue_excl"]
        # 売上原価: 月別パターンに準じ(原価率±2%でブレ)
        cogs = int(rev * COGS_RATIO * rng.uniform(0.97, 1.03))
        gross_profit = rev - cogs
        # 販管費 = 給与+賞与+法定福利+減価償却+その他SGAキャッシュ経費
        # ※ 源泉所得税・住民税は給与に内包(従業員天引)のため別計上しない
        sga_cash_other = max(0, cr["vendor_pay_excl"] - cogs)
        sga = (cr["salary"] + cr["bonus"] + cr["si_employer"]
               + cr["depreciation"] + sga_cash_other)
        op = gross_profit - sga
        # 営業外 (リアルな端数)
        non_op_rev = rng.randint(127_000, 832_000)
        non_op_exp = cr["loan_interest"] + rng.randint(50_000, 240_000)
        ord_profit = op + non_op_rev - non_op_exp
        # 特別損益: たまに発生
        extra_rev = rng.randint(0, 1_800_000) if rng.random() < 0.15 else 0
        extra_exp = rng.randint(0, 1_200_000) if rng.random() < 0.10 else 0
        pretax = ord_profit + extra_rev - extra_exp
        # 法人税 (P/Lベース)
        corp_tax = int(pretax * rng.uniform(0.290, 0.315)) if pretax > 0 else 0
        net = pretax - corp_tax
        result.append({
            "year_month": cr["year_month"],
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


# ===================== B/S (AR/APはスケジュールから集計し整合) =====================
def generate_mock_bs_summary() -> Dict[str, Any]:
    """貸借対照表。
    - cash = CASH_BALANCE (= 口座合計)
    - AR  = AR scheduleの未収(scheduled)合計
    - AP  = AP scheduleの未払(scheduled)合計
    - 長短借入 = 借入残高
    - 利益剰余金 = 差額 (必ず貸借一致)
    """
    # AR/APをスケジュールから集計 (相互参照を避けるため遅延importは不要)
    ar_outstanding = sum(inv["amount"] for inv in generate_mock_ar_schedule()
                          if inv["status"] == "scheduled")
    ap_outstanding = sum(bill["amount"] for bill in generate_mock_ap_schedule()
                          if bill["status"] == "scheduled")

    # 流動資産 (端数付き)
    cash = CASH_BALANCE
    accounts_receivable = ar_outstanding
    inventory = 87_432_158                       # 約8,743万
    other_current = 73_521_684                   # 約7,352万 (前払費用等)
    current_assets = cash + accounts_receivable + inventory + other_current

    # 固定資産 (端数付き)
    tangible = 247_892_341                       # 有形固定資産
    intangible = 53_287_419                      # 無形固定資産
    investments = 98_541_762                     # 投資その他
    fixed_assets = tangible + intangible + investments

    total_assets = current_assets + fixed_assets

    # 流動負債 (端数付き)
    accounts_payable = ap_outstanding
    short_term_loan = SHORT_TERM_LOAN            # 1年内返済予定
    other_current_liab = 148_729_403             # 未払金・未払費用等
    current_liab = accounts_payable + short_term_loan + other_current_liab

    # 固定負債
    long_term_loan = LOAN_OUTSTANDING - SHORT_TERM_LOAN
    other_fixed_liab = 47_823_159                # 退職給付引当金等
    fixed_liab = long_term_loan + other_fixed_liab

    total_liab = current_liab + fixed_liab

    # 純資産: 資本金・資本剰余金は登記額(キリ良), 利益剰余金は差額
    capital = 100_000_000                        # 資本金 (登記)
    capital_surplus = 50_000_000                 # 資本剰余金 (登記)
    retained_earnings = total_assets - total_liab - capital - capital_surplus
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


# ===================== 月次履歴 (forecast用、統一CFモデルと一致) =====================
def generate_mock_history() -> dict:
    """forecast/labor分析用の月次集計 (統一CFモデル準拠)。
    forecast.py は「expense + salary + 借入 + 調整」をCF支出として扱うため、
    expense に [仕入支払(税込) + 賞与 + 法定福利(会社負担) + 税金納付 - 投資CF]
    を全て含める (給与を除く全現金支出)。
    ※ 源泉/住民税は給与に内包 (従業員天引→会社が代理納付) のため別計上しない。
    """
    cash_rows = _monthly_cash_breakdown()
    monthly = []
    for cr in cash_rows:
        non_salary_outflow = (
            cr["vendor_pay_taxed"]
            + cr["bonus"]
            + cr["si_employer"]
            + cr["tax_payment"]
            - cr["capex"]  # capex<0 → 引いて加算
        )
        monthly.append({
            "year_month": cr["year_month"],
            # 入金は税込売上 (顧客から受け取る金額)
            "revenue": cr["revenue_taxed"],
            "expense": non_salary_outflow,
            "salary": cr["salary"],
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


# ===================== 売掛金 (AR) - 統一CFモデルに整合 =====================
_AR_CACHE = None


def generate_mock_ar_schedule() -> List[Dict[str, Any]]:
    """月別の請求書をモデルの月次売上(税込)に厳密に一致させて生成。
    過去12ヶ月 + 来月分。発行月の合計が _monthly_cash_breakdown の revenue_taxed と一致。
    """
    global _AR_CACHE
    if _AR_CACHE is not None:
        return _AR_CACHE

    rng = random.Random(20260601)  # AR専用seed
    today = date.today()
    partners = generate_mock_partners()
    customers = [p for p in partners if not p["is_spot"]][:30]
    items = []
    inv_no = 26010001

    cash_rows = _monthly_cash_breakdown()
    cash_by_ym = {r["year_month"]: r for r in cash_rows}

    # 過去12ヶ月分は cash_rows と完全一致
    for cr in cash_rows:
        ay, am = int(cr["year_month"][:4]), int(cr["year_month"][5:7])
        month_revenue_taxed = cr["revenue_taxed"]
        n_cust = rng.randint(15, 22)
        billing = rng.sample(customers, k=n_cust)
        weights = [rng.uniform(0.4, 3.5) for _ in billing]
        wsum = sum(weights)
        # 月内合計が一致するように端数を最後の請求に吸収
        running = 0
        for idx, (cust, w) in enumerate(zip(billing, weights)):
            amount = int(month_revenue_taxed * w / wsum)
            if idx == len(billing) - 1:
                amount = month_revenue_taxed - running
            if amount < 100_000:
                continue
            running += amount
            # 発行日 (月末締めが多い)
            close_day = rng.choice([15, 20, 25, 31, 31])
            try:
                if close_day == 31:
                    nm = am + 1; ny = ay
                    if nm > 12: nm = 1; ny += 1
                    issue = date(ny, nm, 1) - timedelta(days=1)
                else:
                    issue = date(ay, am, close_day)
            except ValueError:
                issue = date(ay, am, 28)
            # 支払サイト (翌月末払いが最多)
            offset_months = rng.choice([1, 1, 1, 2])
            pay_day = rng.choice([20, 25, 31, 31, 31])
            due_y = issue.year; due_m = issue.month + offset_months
            while due_m > 12: due_m -= 12; due_y += 1
            try:
                if pay_day == 31:
                    nm = due_m + 1; ny = due_y
                    if nm > 12: nm = 1; ny += 1
                    due = date(ny, nm, 1) - timedelta(days=1)
                else:
                    due = date(due_y, due_m, pay_day)
            except ValueError:
                due = date(due_y, due_m, 28)
            payment_term = (due - issue).days
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

    # 未来予測ぶん (来月分) を1ヶ月追加
    next_anchor = today.replace(day=1)
    nm = next_anchor.month + 1; ny = next_anchor.year
    if nm > 12: nm = 1; ny += 1
    next_share = _month_share(nm)
    future_rev_taxed = int(ANNUAL_REVENUE * next_share * 1.1)
    n_cust = rng.randint(15, 22)
    billing = rng.sample(customers, k=n_cust)
    weights = [rng.uniform(0.4, 3.5) for _ in billing]
    wsum = sum(weights)
    running = 0
    for idx, (cust, w) in enumerate(zip(billing, weights)):
        amount = int(future_rev_taxed * w / wsum)
        if idx == len(billing) - 1:
            amount = future_rev_taxed - running
        if amount < 100_000:
            continue
        running += amount
        close_day = rng.choice([15, 20, 25, 31, 31])
        try:
            if close_day == 31:
                nnm = nm + 1; nny = ny
                if nnm > 12: nnm = 1; nny += 1
                issue = date(nny, nnm, 1) - timedelta(days=1)
            else:
                issue = date(ny, nm, close_day)
        except ValueError:
            issue = date(ny, nm, 28)
        offset_months = rng.choice([1, 1, 1, 2])
        pay_day = rng.choice([20, 25, 31, 31, 31])
        due_y = issue.year; due_m = issue.month + offset_months
        while due_m > 12: due_m -= 12; due_y += 1
        try:
            if pay_day == 31:
                nnm = due_m + 1; nny = due_y
                if nnm > 12: nnm = 1; nny += 1
                due = date(nny, nnm, 1) - timedelta(days=1)
            else:
                due = date(due_y, due_m, pay_day)
        except ValueError:
            due = date(due_y, due_m, 28)
        payment_term = (due - issue).days
        items.append({
            "invoice_no": f"INV-{inv_no:08d}",
            "customer": cust["name"],
            "issue_date": issue.isoformat(),
            "due_date": due.isoformat(),
            "amount": amount,
            "status": "scheduled",
            "payment_term_days": payment_term,
        })
        inv_no += 1

    _AR_CACHE = sorted(items, key=lambda x: x["due_date"])
    return _AR_CACHE


# ===================== 買掛金 (AP) - 統一CFモデルに整合 =====================
_AP_CACHE = None


def generate_mock_ap_schedule() -> List[Dict[str, Any]]:
    """月別の仕入請求書を vendor_pay_taxed と完全一致で生成。
    過去12ヶ月 + 来月分。
    """
    global _AP_CACHE
    if _AP_CACHE is not None:
        return _AP_CACHE

    rng = random.Random(20260602)
    today = date.today()
    partners = generate_mock_partners()
    vendors = [p for p in partners if not p["is_spot"]][30:65]
    categories = ["仕入", "外注費", "通信費", "水道光熱費", "地代家賃",
                  "業務委託費", "ソフトウェア利用料", "リース料", "広告宣伝費"]
    items = []
    bill_no = 50010001

    cash_rows = _monthly_cash_breakdown()

    for cr in cash_rows:
        ay, am = int(cr["year_month"][:4]), int(cr["year_month"][5:7])
        month_payable_taxed = cr["vendor_pay_taxed"]
        n_vend = rng.randint(18, 28)
        billing = rng.sample(vendors, k=n_vend)
        weights = [rng.uniform(0.3, 4.0) for _ in billing]
        wsum = sum(weights)
        running = 0
        for i, (vend, w) in enumerate(zip(billing, weights)):
            amount = int(month_payable_taxed * w / wsum)
            if i == len(billing) - 1:
                amount = month_payable_taxed - running
            if amount < 50_000:
                continue
            running += amount
            category = categories[i % len(categories)]
            close_day = rng.choice([20, 25, 31, 31])
            try:
                if close_day == 31:
                    nm = am + 1; ny = ay
                    if nm > 12: nm = 1; ny += 1
                    issue = date(ny, nm, 1) - timedelta(days=1)
                else:
                    issue = date(ay, am, close_day)
            except ValueError:
                issue = date(ay, am, 28)
            offset_months = rng.choice([1, 1, 2, 2])
            pay_day = rng.choice([25, 31, 31])
            due_y = issue.year; due_m = issue.month + offset_months
            while due_m > 12: due_m -= 12; due_y += 1
            try:
                if pay_day == 31:
                    nm = due_m + 1; ny = due_y
                    if nm > 12: nm = 1; ny += 1
                    due = date(ny, nm, 1) - timedelta(days=1)
                else:
                    due = date(due_y, due_m, pay_day)
            except ValueError:
                due = date(due_y, due_m, 28)
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

    # 来月分の予測
    next_anchor = today.replace(day=1)
    nm = next_anchor.month + 1; ny = next_anchor.year
    if nm > 12: nm = 1; ny += 1
    next_share = _month_share(nm)
    future_pay_taxed = int(ANNUAL_VENDOR_PAYABLE_EXCL * next_share * 1.1)
    n_vend = rng.randint(18, 28)
    billing = rng.sample(vendors, k=n_vend)
    weights = [rng.uniform(0.3, 4.0) for _ in billing]
    wsum = sum(weights)
    running = 0
    for i, (vend, w) in enumerate(zip(billing, weights)):
        amount = int(future_pay_taxed * w / wsum)
        if i == len(billing) - 1:
            amount = future_pay_taxed - running
        if amount < 50_000:
            continue
        running += amount
        category = categories[i % len(categories)]
        close_day = rng.choice([20, 25, 31, 31])
        try:
            if close_day == 31:
                nnm = nm + 1; nny = ny
                if nnm > 12: nnm = 1; nny += 1
                issue = date(nny, nnm, 1) - timedelta(days=1)
            else:
                issue = date(ny, nm, close_day)
        except ValueError:
            issue = date(ny, nm, 28)
        offset_months = rng.choice([1, 1, 2, 2])
        pay_day = rng.choice([25, 31, 31])
        due_y = issue.year; due_m = issue.month + offset_months
        while due_m > 12: due_m -= 12; due_y += 1
        try:
            if pay_day == 31:
                nnm = due_m + 1; nny = due_y
                if nnm > 12: nnm = 1; nny += 1
                due = date(nny, nnm, 1) - timedelta(days=1)
            else:
                due = date(due_y, due_m, pay_day)
        except ValueError:
            due = date(due_y, due_m, 28)
        items.append({
            "bill_no": f"AP-{bill_no:08d}",
            "vendor": vend["name"],
            "category": category,
            "issue_date": issue.isoformat(),
            "due_date": due.isoformat(),
            "amount": amount,
            "status": "scheduled",
        })
        bill_no += 1

    _AP_CACHE = sorted(items, key=lambda x: x["due_date"])
    return _AP_CACHE


# ===================== 税金カレンダー (統一CFモデルと完全整合) =====================
def generate_mock_tax_calendar() -> List[Dict[str, Any]]:
    """税金支払スケジュール。年間合計は統一モデルと一致。
    ※ 源泉/住民税は給与天引→翌月納付の流れで給与outflowに内包しているため、
      カレンダー上の重複を避けるため「会社が新たに負担する税」のみを掲載。
      ただし表示用に源泉/住民税の予定額は参考情報として残す。
    """
    today = date.today()
    items = []

    def _add(d: date, name: str, kind: str, amount: int, note: str = "", display_only: bool = False):
        items.append({"due_date": d.isoformat(), "name": name, "kind": kind,
                      "amount": amount, "note": note, "display_only": display_only})

    # 社会保険料納付 (月末)・会社負担+従業員負担を会社が代行納付
    # ※会社の本来負担分は si_employer。残りは給与から天引した分。
    monthly_si_employer = ANNUAL_SI_EMPLOYER // 12  # 会社負担分のみ

    cursor = today.replace(day=1)
    for _ in range(15):
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    for _ in range(20):
        last_day = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if last_day >= today - timedelta(days=60) and last_day <= today + timedelta(days=365):
            _add(last_day, "社会保険料 (会社負担)", "social_insurance", monthly_si_employer, "健保・厚年・子育拠出金 会社負担分")
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    consumption_intermediate = ANNUAL_CONSUMPTION_TAX_NET // 6
    consumption_final = ANNUAL_CONSUMPTION_TAX_NET // 2
    corporate_intermediate = ANNUAL_CORPORATE_TAX // 2
    corporate_final = ANNUAL_CORPORATE_TAX // 2
    property_quarterly = ANNUAL_PROPERTY_TAX // 4

    year = today.year
    for m in (8, 11, 2):
        y = year if m >= today.month else year + 1
        _add(date(y, m, 28), "消費税中間納付", "consumption", consumption_intermediate, "3月決算法人 中間納付")

    y_mid = year if 11 >= today.month else year + 1
    _add(date(y_mid, 11, 30), "法人税・地方法人税 中間納付", "corporate", corporate_intermediate, "前年度法人税額の1/2")

    y = year if 5 >= today.month else year + 1
    _add(date(y, 5, 31), "法人税・地方法人税 確定申告", "corporate", corporate_final, "3月決算 確定申告")
    _add(date(y, 5, 31), "消費税 確定申告", "consumption", consumption_final, "3月決算 確定申告")

    for idx, m in enumerate([4, 7, 12, 2]):
        y = year if m >= today.month else year + 1
        _add(date(y, m, 28), "固定資産税", "property", property_quarterly, f"第{idx+1}期")

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
    # 面談履歴 (過去6回)。役職に応じて面談相手・面談種別を変更
    pos = emp.get("position", "")
    if pos == "代表取締役":
        # 社長: 取締役会・監査役・社外取締役・株主・経営顧問
        interviewer_pool = [
            "取締役会 (定例)",
            "監査役会",
            "社外取締役 (経営アドバイス)",
            "経営顧問 (戦略レビュー)",
            "メインバンク (経営相談)",
        ]
        interview_types = ["取締役会", "経営戦略レビュー", "業績報告", "事業計画策定"]
        interview_topics = [
            "中期経営計画の進捗確認と次期方針策定",
            "新規事業領域の検討と投資判断",
            "業績見通しと配当政策の議論",
            "経営リスクと内部統制の確認",
            "資金調達戦略・M&A検討",
            "後継者育成・経営体制の議論",
            "コーポレートガバナンス強化施策",
        ]
        next_actions = [
            "次回取締役会で承認決議", "経営会議で詳細協議", "戦略案を月末までに提出",
            "中期計画を四半期内に更新", "監査役と継続協議", "特になし",
        ]
    elif pos == "取締役":
        # 取締役: 代表取締役・取締役会・監査役
        interviewer_pool = [
            "代表取締役社長",
            "取締役会 (定例)",
            "監査役",
            "他取締役 (担当領域協議)",
        ]
        interview_types = ["役員定例", "経営会議", "目標設定", "業績レビュー"]
        interview_topics = [
            "担当事業の業績進捗と次期戦略",
            "部門横断プロジェクトの調整事項",
            "重要意思決定事項の確認",
            "リスク管理状況の共有",
        ]
        interview_topics.extend(_INTERVIEW_TOPICS[:3])
        next_actions = [
            "次回経営会議で進捗報告", "施策案を再提示", "他部門と連携継続",
            "目標達成に向けた行動計画策定", "特になし",
        ]
    elif pos == "執行役員":
        interviewer_pool = [
            "代表取締役社長 (担当役員定例)",
            "管掌取締役",
            "人事部長 (キャリア面談)",
        ]
        interview_types = ["役員定例", "目標設定", "評価面談", "1on1"]
        interview_topics = list(_INTERVIEW_TOPICS)
        next_actions = [
            "次回までに事業計画見直し", "経営会議で報告", "施策実行フェーズへ",
            "メンバー育成計画策定", "特になし",
        ]
    else:
        # 一般従業員: 上長・人事
        interviewer_pool = [
            "佐藤 直樹 (人事部長)", "山田 健太 (上長)", "鈴木 由美 (HR)",
            "高橋 雄一 (執行役員)",
        ]
        interview_types = ["1on1", "定期面談", "目標設定", "評価面談"]
        interview_topics = list(_INTERVIEW_TOPICS)
        next_actions = [
            "次回までに研修受講予定", "新規プロジェクト参画検討", "目標進捗フォローアップ",
            "メンタリング継続", "業務改善提案を月末まで提出", "特になし",
        ]

    interviews = []
    for back_months in range(6, 0, -1):
        i_date = date.today() - timedelta(days=back_months * 30 + rng.randint(0, 7))
        if i_date < date.fromisoformat(emp["hire_date"]):
            continue
        interviews.append({
            "date": i_date.isoformat(),
            "interviewer": rng.choice(interviewer_pool),
            "type": rng.choice(interview_types),
            "summary": rng.choice(interview_topics),
            "next_action": rng.choice(next_actions),
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
    for _ in range(10):
        role_plan.append(("部長", 700_000, rng.choice(_DEPARTMENTS)))
    for _ in range(16):
        role_plan.append(("マネージャー", 520_000, rng.choice(_DEPARTMENTS)))
    for _ in range(14):
        role_plan.append(("チーフ", 450_000, rng.choice(_DEPARTMENTS)))
    for _ in range(16):
        role_plan.append(("リーダー", 400_000, rng.choice(_DEPARTMENTS)))
    for _ in range(72):
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


# ===================== 賞与カレンダー (統一モデル) =====================
def generate_mock_bonus_calendar() -> List[Dict[str, Any]]:
    """夏季・冬季賞与。合計は ANNUAL_BONUS_GROSS と一致。
    支払日: 6月10日 (夏) / 12月10日 (冬) ※モデルの月次配分と整合。
    """
    today = date.today()
    items = []
    year = today.year
    summer_amount = int(ANNUAL_BONUS_GROSS * 1.5 / (1.5 + 2.2))
    winter_amount = ANNUAL_BONUS_GROSS - summer_amount
    for offset in range(-1, 3):
        y = year + offset
        for m, label, amount in [(6, "夏季賞与", summer_amount), (12, "冬季賞与", winter_amount)]:
            pay_date = date(y, m, 10)
            if pay_date >= today - timedelta(days=180):
                items.append({
                    "pay_date": pay_date.isoformat(),
                    "name": label,
                    "amount": amount,
                    "note": f"年間¥{ANNUAL_BONUS_GROSS:,}÷2回",
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


# ===================== 日次CF予測 (統一モデルから完全派生) =====================
def generate_mock_daily_forecast(opening_balance: int = None, days: int = 30) -> List[Dict[str, Any]]:
    """日次CF予測。
    - AR/AP/税金/賞与カレンダーの実際の支払日をそのまま反映
    - 給与: 月末締翌月末払い (給与は AR/AP に含まれないため独立加算)
    - 月次CFと完全に一致するスケール (各月の合計が一致する設計)
    """
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

    # 給与: 月末締翌月末払い (今月末・来月末等)
    monthly_salary = ANNUAL_SALARY_GROSS // 12
    cursor = today.replace(day=1)
    for _ in range(3):  # 直近〜先 3ヶ月分の月末を候補に
        last_day = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        ds = last_day.isoformat()
        if ds in daily:
            daily[ds]["outflow"] += monthly_salary
            daily[ds]["outflow_items"].append({
                "label": f"給与支払 ({DEMO_EMPLOYEE_COUNT}名分)",
                "amount": monthly_salary,
            })
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    # 借入元利金: 月末払い
    monthly_principal = ANNUAL_LOAN_PRINCIPAL_REPAY // 12
    monthly_interest = ANNUAL_LOAN_INTEREST // 12
    cursor = today.replace(day=1)
    for _ in range(3):
        last_day = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        ds = last_day.isoformat()
        if ds in daily:
            daily[ds]["outflow"] += monthly_principal + monthly_interest
            daily[ds]["outflow_items"].append({
                "label": "借入金返済 (元利金)",
                "amount": monthly_principal + monthly_interest,
            })
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    rows = sorted(daily.values(), key=lambda x: x["date"])
    balance = opening_balance
    for row in rows:
        row["net"] = row["inflow"] - row["outflow"]
        balance += row["net"]
        row["ending_balance"] = balance
    return rows
