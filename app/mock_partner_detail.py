"""取引先詳細データ (mock)。
過去5年分の入出金履歴、契約条件、口座、担当者、商談履歴、契約書PDF。
"""
import random
from datetime import date, timedelta
from typing import Any, Dict, List
from . import mock_data as M


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


_INTERNAL_CONTACTS = [
    {"name": "山田 健太", "dept": "営業1部", "role": "営業部長", "email": "yamada@stahr-tech.co.jp", "phone": "03-1234-5678"},
    {"name": "鈴木 翔太", "dept": "営業2部", "role": "シニアマネージャー", "email": "suzuki@stahr-tech.co.jp", "phone": "03-1234-5679"},
    {"name": "佐藤 直樹", "dept": "営業3部", "role": "マネージャー", "email": "sato@stahr-tech.co.jp", "phone": "03-1234-5680"},
    {"name": "高橋 雄一", "dept": "営業企画部", "role": "執行役員", "email": "takahashi@stahr-tech.co.jp", "phone": "03-1234-5681"},
    {"name": "渡辺 美月", "dept": "営業1部", "role": "リーダー", "email": "watanabe@stahr-tech.co.jp", "phone": "03-1234-5682"},
]

_PARTNER_TITLES = ["代表取締役", "営業部長", "購買部長", "経理部長", "事業開発部長", "情報システム部長"]
_PARTNER_LAST = ["田中", "中村", "小林", "加藤", "吉田", "斎藤", "井上", "木村", "林", "清水"]
_PARTNER_FIRST = ["俊夫", "幸雄", "正樹", "孝", "順子", "智子", "由美", "明", "誠", "清"]


def _gen_partner_contact(rng: random.Random) -> Dict[str, Any]:
    last = rng.choice(_PARTNER_LAST)
    first = rng.choice(_PARTNER_FIRST)
    title = rng.choice(_PARTNER_TITLES)
    return {
        "name": f"{last} {first}",
        "title": title,
        "email": f"{last.lower()}@example.co.jp",
        "phone": f"03-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
        "mobile": f"090-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
    }


def _gen_bank_account(rng: random.Random) -> Dict[str, str]:
    banks = ["三菱UFJ銀行", "みずほ銀行", "三井住友銀行", "りそな銀行", "横浜銀行", "千葉銀行"]
    branches = ["新宿支店", "渋谷支店", "本店営業部", "丸の内支店", "横浜支店", "千葉支店"]
    return {
        "bank": rng.choice(banks),
        "branch": rng.choice(branches),
        "type": rng.choice(["普通", "当座"]),
        "number": f"{rng.randint(1000000, 9999999):07d}",
        "holder": "(取引先名義)",
    }


def _gen_5year_history(rng: random.Random, partner_name: str, deal_type: str = "income") -> List[Dict[str, Any]]:
    """過去5年分の取引履歴を生成 (月次)。"""
    today = date.today()
    rows = []

    # 取引先規模 (年間取引額)
    annual_base = rng.randint(15_000_000, 280_000_000)

    for year_offset in range(-5, 0):
        year_amt = int(annual_base * rng.uniform(0.7, 1.3))
        # 月別配分
        weights = [rng.uniform(0.6, 1.4) for _ in range(12)]
        wsum = sum(weights)
        for m_idx, w in enumerate(weights):
            ym = today.year + year_offset
            month = m_idx + 1
            amt = int(year_amt * w / wsum)
            if amt < 100_000:
                continue
            # 月末締・翌月末払いを想定
            close_date = date(ym, month, min(28, 25))
            if month < 12:
                due_date = date(ym, month + 1, min(28, 25))
            else:
                due_date = date(ym + 1, 1, 25)
            rows.append({
                "year_month": close_date.strftime("%Y-%m"),
                "issue_date": close_date.isoformat(),
                "due_date": due_date.isoformat(),
                "amount": amt,
                "tax_amount": int(amt * 0.1),
                "description": rng.choice([
                    "システム開発委託料", "保守運用費", "コンサルティング報酬",
                    "ライセンス利用料", "業務委託費", "プロジェクト推進費"
                ]),
                "deal_type": deal_type,
                "status": "paid",
            })
    return rows


def _gen_meeting_history(rng: random.Random, partner_name: str, contact_name: str) -> List[Dict[str, Any]]:
    """商談履歴 (過去2年, 約20件)。"""
    today = date.today()
    meetings = []
    for i in range(rng.randint(15, 25)):
        d = today - timedelta(days=rng.randint(7, 730))
        meeting_type = rng.choice([
            "定例ミーティング", "提案商談", "進捗確認", "新規案件相談",
            "条件交渉", "契約更新打合せ", "クレーム対応", "戦略会議",
        ])
        topics = rng.sample([
            "今期の取引方針について",
            "新規プロジェクト「DX推進」の提案",
            "保守契約の継続条件について",
            "支払サイトの見直し依頼",
            "値上げ交渉(原材料費高騰)",
            "別案件の引き合い",
            "繁忙期の納期調整",
            "ベンダーロックイン懸念への対応",
            "セキュリティ要件の確認",
            "決裁スピード向上の依頼",
        ], k=rng.randint(1, 3))
        outcome = rng.choice([
            "次回提案書を持参", "見積書を提出予定", "条件持ち帰り検討",
            "合意・契約書修正へ", "再提案を依頼", "クロージング成功",
            "保留 (社内検討)", "競合と比較中",
        ])
        meetings.append({
            "date": d.isoformat(),
            "type": meeting_type,
            "attendees_internal": f"{rng.choice(_INTERNAL_CONTACTS)['name']}",
            "attendees_partner": contact_name,
            "topics": topics,
            "outcome": outcome,
            "next_action_date": (d + timedelta(days=rng.randint(7, 30))).isoformat(),
        })
    return sorted(meetings, key=lambda x: x["date"], reverse=True)


def _gen_contracts(rng: random.Random, partner_name: str) -> List[Dict[str, Any]]:
    """契約書一覧 (締結中の契約)。"""
    contracts = []
    num_contracts = rng.randint(1, 4)
    today = date.today()
    types = [
        ("業務委託基本契約書", 36),
        ("システム開発委託契約書", 12),
        ("保守運用契約書", 24),
        ("秘密保持契約書(NDA)", 60),
        ("業務委託個別契約書", 6),
        ("ライセンス使用許諾契約書", 12),
    ]
    used = set()
    for i in range(num_contracts):
        ct, months = rng.choice([t for t in types if t[0] not in used])
        used.add(ct)
        start_date = today - timedelta(days=rng.randint(30, months * 30 - 30))
        end_date = start_date + timedelta(days=months * 30)
        contracts.append({
            "id": f"K{rng.randint(10000, 99999)}",
            "title": ct,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "auto_renewal": rng.choice([True, True, False]),
            "monthly_amount": rng.choice([300_000, 500_000, 800_000, 1_200_000, 2_500_000, 5_000_000]),
            "status": "有効" if end_date > today else "期限切れ",
            "pdf_url": f"/api/contract-pdf/{partner_name}/{i}",
            "signed_by_internal": rng.choice(_INTERNAL_CONTACTS)["name"],
            "signed_by_partner": "(取引先代表者)",
        })
    return contracts


def get_partner_detail(partner_id: int = None, partner_name: str = None) -> Dict[str, Any]:
    """取引先詳細情報。partner_idまたはpartner_nameで指定。"""
    partners = M.generate_mock_partners()
    if partner_id is not None:
        partner = next((p for p in partners if p["id"] == partner_id), None)
    elif partner_name:
        partner = next((p for p in partners if p["name"] == partner_name), None)
    else:
        partner = partners[0]

    if not partner:
        return None

    rng = _rng(partner["id"] if partner.get("id") else 12345)

    # 担当者(取引先側)
    partner_contacts = [_gen_partner_contact(rng) for _ in range(rng.randint(2, 4))]
    # 銀行口座
    bank = _gen_bank_account(rng)
    # 5年分の入金履歴 (売上)
    income_history = _gen_5year_history(rng, partner["name"], "income")
    # 5年分の支払履歴 (もし vendor の場合)
    expense_history = _gen_5year_history(_rng(partner["id"] + 1000), partner["name"], "expense") if not partner.get("is_spot") else []

    # 契約書
    contracts = _gen_contracts(rng, partner["name"])

    # 商談履歴
    main_contact = partner_contacts[0]["name"] if partner_contacts else "(担当者)"
    meetings = _gen_meeting_history(rng, partner["name"], main_contact)

    # 内部担当
    internal_pic = rng.choice(_INTERNAL_CONTACTS)

    # 取引条件
    payment_terms = {
        "income_close_day": rng.choice(["20日", "25日", "末日"]),
        "income_payment_day": rng.choice(["翌月末", "翌々月末", "翌月25日"]),
        "expense_close_day": rng.choice(["20日", "25日", "末日"]),
        "expense_payment_day": rng.choice(["翌月末", "翌々月末"]),
        "tax_rate": 10,
    }

    # 集計
    annual_5y_income = sum(r["amount"] for r in income_history)
    annual_5y_expense = sum(r["amount"] for r in expense_history)

    return {
        "partner": partner,
        "internal_pic": internal_pic,
        "partner_contacts": partner_contacts,
        "bank_account": bank,
        "payment_terms": payment_terms,
        "income_history": income_history,
        "expense_history": expense_history,
        "summary_5y": {
            "total_income": annual_5y_income,
            "total_expense": annual_5y_expense,
            "avg_monthly_income": annual_5y_income // (5 * 12) if annual_5y_income else 0,
            "avg_monthly_expense": annual_5y_expense // (5 * 12) if annual_5y_expense else 0,
            "first_transaction": min((r["issue_date"] for r in (income_history + expense_history)), default=None),
            "last_transaction": max((r["issue_date"] for r in (income_history + expense_history)), default=None),
        },
        "contracts": contracts,
        "meetings": meetings,
    }


def generate_contract_pdf(partner_name: str, contract_idx: int = 0) -> bytes:
    """ダミー契約書PDFを生成。"""
    # 最小限のPDFバイト列 (1ページ・テキスト)
    text = (
        f"BT /F1 14 Tf 50 750 Td (Contract Document) Tj ET\n"
        f"BT /F1 11 Tf 50 720 Td (Partner: {partner_name}) Tj ET\n"
        f"BT /F1 11 Tf 50 700 Td (Document ID: K{abs(hash(partner_name + str(contract_idx))) % 100000:05d}) Tj ET\n"
        f"BT /F1 10 Tf 50 680 Td (This is a sample contract document for demo purposes.) Tj ET\n"
        f"BT /F1 10 Tf 50 650 Td (1. Scope of Work) Tj ET\n"
        f"BT /F1 9 Tf 60 630 Td (The supplier shall provide consulting services as agreed.) Tj ET\n"
        f"BT /F1 10 Tf 50 600 Td (2. Payment Terms) Tj ET\n"
        f"BT /F1 9 Tf 60 580 Td (Net 30 days from invoice date, monthly billing.) Tj ET\n"
        f"BT /F1 10 Tf 50 550 Td (3. Term) Tj ET\n"
        f"BT /F1 9 Tf 60 530 Td (24 months with auto-renewal.) Tj ET\n"
        f"BT /F1 10 Tf 50 500 Td (4. Confidentiality) Tj ET\n"
        f"BT /F1 9 Tf 60 480 Td (Both parties agree to keep all information confidential.) Tj ET\n"
        f"BT /F1 12 Tf 50 350 Td (Signed:) Tj ET\n"
        f"BT /F1 10 Tf 50 320 Td (Star Technology Inc. _____________ Date: ____) Tj ET\n"
        f"BT /F1 10 Tf 50 290 Td (Partner: {partner_name} _____________ Date: ____) Tj ET\n"
        f"BT /F1 8 Tf 50 60 Td (** SAMPLE - DEMO PURPOSES ONLY **) Tj ET\n"
    )
    body = text.encode("latin-1", errors="replace")
    # 最小PDF構造
    pdf = b"%PDF-1.4\n"
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    stream_content = b"q\n" + body + b"\nQ\n"
    objects.append(b"4 0 obj\n<< /Length " + str(len(stream_content)).encode() + b" >>\nstream\n" + stream_content + b"endstream\nendobj\n")
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    offsets = [0]
    cursor = len(pdf)
    for obj in objects:
        offsets.append(cursor)
        pdf += obj
        cursor += len(obj)
    xref_pos = cursor
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
    pdf += str(xref_pos).encode() + b"\n%%EOF\n"
    return pdf
