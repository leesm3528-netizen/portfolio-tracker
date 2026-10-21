"""화면 검증 스크립트 (Python Playwright).

실행(프로젝트 루트):
    py skills/ui-verify/scripts/verify_ui.py [작업 ID ...] [--list] [--base-url URL] [--port 8000]

세부 동작의 원본: docs/05_작업지시서.md 2.3, T2-05. 절차와 시나리오 추가 방법: skills/ui-verify/SKILL.md
Python 3 표준 라이브러리와 playwright.sync_api 만 쓴다. playwright 는 시나리오를 실행할 때만 불러온다.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.dont_write_bytecode = True  # fixtures 를 불러올 때 저장소 안에 __pycache__ 를 만들지 않는다

import fixtures  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]  # 스크립트 위치 기준 프로젝트 루트(../../..)
DISCLAIMER = "계산 결과는 참고용이며 투자 판단의 책임은 본인에게 있습니다."  # 01 8절
WIDTHS = (360, 768, 1280)  # 05 2.3 의 8번
INSTALL_HINT = (
    "py -m pip install playwright",
    "py -m playwright install chromium",
)
NON_NETWORK_SCHEMES = ("data", "blob", "about")


# ---------------------------------------------------------------------------
# 시나리오 등록 표. 키는 작업 ID, 값은 (시나리오 이름, 함수) 목록이다.
# 각 화면 작업(T3-01 이후)이 자기 작업 ID 로 추가한다. 이전 시나리오는 지우지 않는다.
# 함수는 Run 객체 하나를 받고, 실패하면 AssertionError 를 던진다.
# ---------------------------------------------------------------------------

SCENARIOS = {}


# T3-01 index.html 영역 마크업 (docs/05_작업지시서.md T3-01 검증 방법)

ELEMENT_IDS = (  # 02 9.1~9.8 의 id 전체
    # 9.1 거래 입력
    "transaction-section", "transaction-form", "tx-date", "tx-name", "tx-asset-class", "tx-type",
    "tx-quantity", "tx-price", "tx-fee", "tx-fee-help", "tx-submit", "tx-message",
    # 9.2 거래 내역
    "transactions-section", "transactions-heading", "transactions-message", "transactions-table",
    "transactions-body", "transactions-empty",
    # 9.3 보유 현황
    "holdings-section", "holdings-message", "holdings-table", "holdings-body", "holdings-empty",
    # 9.4 자산 비중
    "allocation-section", "allocation-table", "allocation-body", "allocation-total", "allocation-message",
    # 9.5 리밸런싱 묶음과 목표 비중 입력
    "rebalance-group", "targets-section", "targets-form", "target-stock", "target-bond", "target-cash",
    "target-other", "targets-help", "target-sum", "targets-message",
    # 9.6 리밸런싱 결과
    "rebalance-section", "rebalance-table", "rebalance-body", "rebalance-message",
    # 9.7 데이터 관리
    "data-section", "export-button", "import-button", "import-file", "data-message",
    # 9.8 하단 고지
    "disclaimer",
)

STATIC_TEXTS = {  # 01 5.5 정적 문구
    "#transactions-empty": "입력된 거래가 없습니다.",  # IN-01
    "#holdings-empty": "보유 종목이 없습니다.",  # IN-02
    "#tx-fee-help": "없으면 0",  # IN-05
    "#targets-help": "합계가 100%일 때 리밸런싱을 계산합니다.",  # IN-06
}
IN_03 = "안내: 보유 중인 종목이 없어 자산 비중을 계산할 수 없습니다."


def t3_01_ids(run):
    run.open()
    wrong = [f"{i}({n})" for i in ELEMENT_IDS if (n := run.page.locator("#" + i).count()) != 1]
    if wrong:
        raise AssertionError(f"id 개수가 1 이 아님: {', '.join(wrong)}")


def t3_01_lang(run):
    run.open()
    lang = run.page.evaluate("document.documentElement.lang")
    if lang != "ko":
        raise AssertionError(f"html lang: 기대 'ko', 실제 {lang!r}")


def t3_01_labels(run):
    run.open()
    missing = run.page.evaluate(
        """() => [...document.querySelectorAll('input:not([type=hidden]):not([hidden]), select')]
            .filter(el => el.labels.length === 0 && !el.getAttribute('aria-label'))
            .map(el => el.id || el.outerHTML)"""
    )
    if missing:
        raise AssertionError(f"label 없는 입력칸: {', '.join(missing)}")


def t3_01_static_texts(run):
    run.open()
    for selector, expected in STATIC_TEXTS.items():
        run.expect_text(selector, expected)
    # 표시 여부는 데이터에 따라 바뀌므로(02 9.4) T4-11 이 확인한다. 여기서는 문구만 본다.
    actual = run.page.locator("#allocation-message").text_content().strip()
    if actual != IN_03:
        raise AssertionError(f"#allocation-message 텍스트: 기대 {IN_03!r}, 실제 {actual!r}")
    asset_class = run.page.input_value("#tx-asset-class")
    if asset_class != "":
        raise AssertionError(f"#tx-asset-class 값: 기대 '', 실제 {asset_class!r}")
    fee = run.page.input_value("#tx-fee")
    if fee != "":
        raise AssertionError(f"#tx-fee 값: 기대 빈칸, 실제 {fee!r}")


def t3_01_tables(run):
    run.open()
    problems = run.page.evaluate(
        """() => [...document.querySelectorAll('table')].flatMap(t => {
            const out = [];
            if (!t.caption || !t.caption.textContent.trim()) out.push(t.id + ' caption 없음');
            const heads = t.querySelectorAll('thead th');
            if (heads.length === 0 || [...heads].some(th => th.getAttribute('scope') !== 'col'))
                out.push(t.id + ' 열 머리 scope=col 아님');
            return out;
        })"""
    )
    if problems:
        raise AssertionError("; ".join(problems))


SCENARIOS["T3-01"] = [
    ("02 9절 id 가 한 번씩 있다", t3_01_ids),
    ("html lang 이 ko", t3_01_lang),
    ("입력칸 label 연결", t3_01_labels),
    ("표 caption 과 scope=col", t3_01_tables),
    ("정적 문구와 입력칸 초기값", t3_01_static_texts),
]


# T3-02 style.css 변수와 기본 스타일 (docs/05_작업지시서.md T3-02 검증 방법)

def t3_02_widths(run):
    run.open()
    run.check_widths()


def t3_02_two_columns(run):
    run.open()
    for width in (1024, 1280):  # 04 7.5 넓음 기준점 이상
        run.page.set_viewport_size({"width": width, "height": 800})
        tops = run.page.evaluate(
            """() => ['allocation-section', 'rebalance-group']
                .map(id => document.getElementById(id).getBoundingClientRect().top)"""
        )
        if tops[0] != tops[1]:
            raise AssertionError(f"{width}px: #allocation-section top {tops[0]}, #rebalance-group top {tops[1]}")


def t3_02_numeric_font(run):
    run.open()
    wrong = run.page.evaluate(
        """() => [...document.querySelectorAll('.num')]
            .filter(el => getComputedStyle(el).fontVariantNumeric !== 'tabular-nums')
            .map(el => el.textContent.trim() || el.id || el.tagName)"""
    )
    if wrong:
        raise AssertionError(f"tabular-nums 아님: {', '.join(wrong)}")


def t3_02_focus_ring(run):
    run.open()
    expected = run.page.evaluate(
        """() => [...document.querySelectorAll('input, select, button')]
            .filter(el => !el.hidden && el.type !== 'hidden').map(el => el.id)"""
    )
    seen = {}
    for _ in range(len(expected) * 4):  # 날짜 입력칸은 칸 안의 연, 월, 일로 Tab 이 여러 번 머문다
        run.page.keyboard.press("Tab")
        state = run.page.evaluate(
            "() => [document.activeElement.id, getComputedStyle(document.activeElement).outlineStyle]"
        )
        if state[0] in expected and state[0] not in seen:
            seen[state[0]] = state[1]
        if len(seen) == len(expected):
            break
    missing = [i for i in expected if i not in seen]
    if missing:
        raise AssertionError(f"Tab 으로 가지 못한 요소: {', '.join(missing)}")
    wrong = [f"{i}({style})" for i, style in seen.items() if style != "solid"]
    if wrong:
        raise AssertionError(f"포커스 링 outlineStyle 이 solid 아님: {', '.join(wrong)}")


SCENARIOS["T3-02"] = [
    ("360, 768, 1280px 가로 스크롤 없음", t3_02_widths),
    ("1024px 이상 자산 비중과 리밸런싱 두 열", t3_02_two_columns),
    (".num 숫자 글꼴 tabular-nums", t3_02_numeric_font),
    ("Tab 이동 시 포커스 링", t3_02_focus_ring),
]


# T4-07 시작 흐름, 거래 입력, 거래 내역 표 (docs/05_작업지시서.md T4-07 검증 방법)
# 기대 문구는 01 5절 원문에 머리말(04 13.1)을 붙인 것이다.

ERROR = "오류: "
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
VE_01 = "날짜를 YYYY-MM-DD 형식의 실제 날짜로 입력하세요."
VE_02 = "종목명을 입력하세요."
VE_03 = "자산군을 선택하세요."
VE_04 = "수량은 1 이상의 정수로 입력하세요."
VE_05 = "가격은 0보다 큰 숫자로 입력하세요."
VE_06 = "수수료는 0 이상의 숫자로 입력하세요."
VE_08 = "현금 거래는 자산군을 현금으로, 가격을 1로 입력하세요."
VE_20 = "브라우저 저장소에 저장하지 못했습니다. 새로고침하면 마지막 변경이 사라질 수 있으니 JSON 내보내기로 백업하세요."
VE_21 = "저장된 데이터를 읽을 수 없어 빈 상태로 시작합니다. 백업한 JSON 파일이 있으면 불러오기로 복구하세요."
C01_FIRST = {"date": "2026-01-02", "name": "종목A", "asset_class": "stock", "type": "buy",
             "quantity": "10", "price": "10000", "fee": "0"}  # 03 14.2 C-01 의 #0


def fill_transaction(run, date, name, asset_class, type, quantity, price, fee=""):
    """거래 입력 폼을 채운다. 값은 폼에 넣는 문자열 그대로다."""
    page = run.page
    page.fill("#tx-date", date)
    page.fill("#tx-name", name)
    page.select_option("#tx-asset-class", asset_class)
    page.select_option("#tx-type", type)
    page.fill("#tx-quantity", quantity)
    page.fill("#tx-price", price)
    page.fill("#tx-fee", fee)


def add_transaction(run, **fields):
    fill_transaction(run, **fields)
    run.page.click("#tx-submit")


def row_count(run, tbody):
    return run.page.locator(f"#{tbody} tr").count()


def expect_rows(run, tbody, expected):
    actual = row_count(run, tbody)
    if actual != expected:
        raise AssertionError(f"#{tbody} 행 수: 기대 {expected}, 실제 {actual}")


def row_texts(run, tbody):
    """tbody 각 행의 칸 텍스트 목록(앞뒤 공백 제거)."""
    return run.page.evaluate(
        """(id) => [...document.getElementById(id).rows]
            .map(tr => [...tr.cells].map(c => c.innerText.trim()))""",
        tbody,
    )


def stored_data(run):
    """localStorage 의 저장 객체를 dict 로 읽는다. 키가 없으면 None."""
    text = run.page.evaluate(f"localStorage.getItem({json.dumps(fixtures.STORAGE_KEY)})")
    return None if text is None else json.loads(text)


def expect_hidden(run, selector, hidden):
    actual = run.page.locator(selector).is_hidden()
    if actual != hidden:
        raise AssertionError(f"{selector} hidden: 기대 {hidden}, 실제 {actual}")


def t4_07_empty(run):
    run.open()
    expect_hidden(run, "#transactions-empty", False)
    expect_hidden(run, "#transactions-table", True)
    expected = today(run)
    actual = run.page.input_value("#tx-date")
    if actual != expected:
        raise AssertionError(f"#tx-date 값: 기대 {expected}, 실제 {actual!r}")


def t4_07_add(run):
    run.open()
    add_transaction(run, **C01_FIRST)
    expect_rows(run, "transactions-body", 1)
    expected = ["2026-01-02", "종목A", "주식", "매수", "10", "10,000", "0", "삭제"]  # 삭제 버튼은 T4-08 부터(02 9.2)
    actual = row_texts(run, "transactions-body")[0]
    if actual != expected:
        raise AssertionError(f"거래 행: 기대 {expected}, 실제 {actual}")
    expect_hidden(run, "#transactions-empty", True)
    data = stored_data(run)
    if data is None or list(data) != ["version", "transactions", "prices", "targets"]:
        raise AssertionError(f"저장 객체 키: {None if data is None else list(data)}")
    tx = data["transactions"][0]
    if not re.match(UUID_PATTERN, tx["id"]):
        raise AssertionError(f"id 가 UUID 형식이 아님: {tx['id']!r}")
    expected_tx = {"date": "2026-01-02", "name": "종목A", "assetClass": "stock", "type": "buy",
                   "quantity": 10, "price": 10000, "fee": 0}
    if {k: v for k, v in tx.items() if k != "id"} != expected_tx or list(tx)[0] != "id":
        raise AssertionError(f"저장된 거래: {tx}")
    if data["version"] != 1 or data["prices"] != {} or data["targets"] != {"stock": 0, "bond": 0, "cash": 0, "other": 0}:
        raise AssertionError(f"저장 객체: {data}")
    # 추가 성공 후 폼 상태(02 7.5 resetTransactionForm)
    values = {i: run.page.input_value("#" + i) for i in
              ("tx-date", "tx-name", "tx-asset-class", "tx-type", "tx-quantity", "tx-price", "tx-fee")}
    expected_values = {"tx-date": "2026-01-02", "tx-name": "", "tx-asset-class": "stock", "tx-type": "buy",
                       "tx-quantity": "", "tx-price": "", "tx-fee": ""}
    if values != expected_values:
        raise AssertionError(f"추가 후 폼 값: {values}")
    focused = run.page.evaluate("document.activeElement.id")
    if focused != "tx-date":
        raise AssertionError(f"추가 후 포커스: 기대 tx-date, 실제 {focused!r}")


def t4_07_reload(run):
    run.open()
    add_transaction(run, **C01_FIRST)
    before = row_texts(run, "transactions-body")
    run.page.reload()
    after = row_texts(run, "transactions-body")
    if after != before:
        raise AssertionError(f"새로고침 후 행: 기대 {before}, 실제 {after}")


def t4_07_field_errors(run):
    run.open()
    cases = [
        ("종목명 공백", {"name": "   "}, VE_02),
        ("자산군 미선택", {"asset_class": ""}, VE_03),
        ("수량 1.5", {"quantity": "1.5"}, VE_04),
        ("가격 0", {"price": "0"}, VE_05),
        ("수수료 -1", {"fee": "-1"}, VE_06),
        ("날짜 비움", {"date": ""}, VE_01),
        ("현금과 자산군 주식", {"name": "현금", "price": "1"}, VE_08),
    ]
    for label, change, message in cases:
        fields = {**C01_FIRST, **change}
        add_transaction(run, **fields)
        run.expect_text("#tx-message", ERROR + message)
        expect_rows(run, "transactions-body", 0)
        # 입력값을 지우지 않는다(01 FR-01 기준 7)
        if run.page.input_value("#tx-name") != fields["name"] or run.page.input_value("#tx-date") != fields["date"]:
            raise AssertionError(f"{label}: 오류 후 입력값이 바뀌었다")
        if stored_data(run) is not None:
            raise AssertionError(f"{label}: 오류인데 저장되었다")
    # 숫자로 해석되지 않는 수수료(브라우저 badInput)는 0 이 아니라 오류다(05 3.1 M-32)
    fill_transaction(run, **C01_FIRST)
    run.page.fill("#tx-fee", "")
    run.page.focus("#tx-fee")
    run.page.keyboard.type("1e")
    run.page.click("#tx-submit")
    run.expect_text("#tx-message", ERROR + VE_06)
    expect_rows(run, "transactions-body", 0)
    # 다음 성공 때 오류가 사라진다
    add_transaction(run, **C01_FIRST)
    expect_rows(run, "transactions-body", 1)
    run.expect_text("#tx-message", "")


def t4_07_sell_and_class_errors(run):
    run.open()
    add_transaction(run, **C01_FIRST)
    add_transaction(run, **{**C01_FIRST, "date": "2026-01-03", "type": "sell", "quantity": "11"})
    run.expect_text("#tx-message", ERROR + "2026-01-03 기준 '종목A'의 보유수량은 10입니다. 그보다 많이 매도할 수 없습니다.")
    expect_rows(run, "transactions-body", 1)
    add_transaction(run, **{**C01_FIRST, "asset_class": "bond"})
    run.expect_text("#tx-message", ERROR + "'종목A'의 자산군은 주식입니다. 같은 종목은 하나의 자산군만 가질 수 있습니다.")
    expect_rows(run, "transactions-body", 1)


def t4_07_html_name(run):
    run.open()
    add_transaction(run, **{**C01_FIRST, "name": "<b>x</b>"})
    name_cell = run.page.locator("#transactions-body tr td").first
    if name_cell.inner_text() != "<b>x</b>":
        raise AssertionError(f"종목명 칸: {name_cell.inner_text()!r}")
    if run.page.locator("#transactions-body b").count() != 0:
        raise AssertionError("종목명이 HTML 로 해석되어 b 요소가 생겼다")


def t4_07_corrupt_storage(run):
    run.context.add_init_script(f"localStorage.setItem({json.dumps(fixtures.STORAGE_KEY)}, '{{')")
    run.open()
    run.expect_text("#data-message", ERROR + VE_21)
    expect_hidden(run, "#transactions-empty", False)
    expect_rows(run, "transactions-body", 0)


def t4_07_save_failure(run):
    run.context.add_init_script("Storage.prototype.setItem = function () { throw new Error('blocked'); };")
    run.open()
    add_transaction(run, **C01_FIRST)
    run.expect_text("#data-message", ERROR + VE_20)
    expect_rows(run, "transactions-body", 1)


SCENARIOS["T4-07"] = [
    ("빈 상태 문구와 날짜 초기값 오늘", t4_07_empty),
    ("C-01 #0 추가, 저장 객체와 UUID, 추가 후 폼", t4_07_add),
    ("새로고침 후 행 유지", t4_07_reload),
    ("항목 오류 VE-01~VE-08 과 입력값 유지", t4_07_field_errors),
    ("초과 매도 VE-09 와 자산군 불일치 VE-07", t4_07_sell_and_class_errors),
    ("종목명 HTML 문자열은 글자 그대로", t4_07_html_name),
    ("저장 데이터 손상 VE-21", t4_07_corrupt_storage),
    ("저장 실패 VE-20", t4_07_save_failure),
]


# T4-08 거래 삭제 (docs/05_작업지시서.md T4-08 검증 방법)

DELETE_BUTTON_SELECTOR = '#transactions-body button[data-action="delete-transaction"]'

def delete_row(run, index, action="accept"):
    """거래 내역 index 번째 행의 삭제 버튼을 누르고 확인 대화상자를 action 으로 처리한다."""
    run.dialog_action = action
    run.page.locator(DELETE_BUTTON_SELECTOR).nth(index).click()


def active_element(run):
    return run.page.evaluate(
        "() => ({ id: document.activeElement.id, action: document.activeElement.dataset.action || '',"
        " key: document.activeElement.dataset.id || document.activeElement.dataset.name || '' })"
    )


def t4_08_reject(run):
    run.open_with_data(fixtures.case_data("C-09"))
    delete_row(run, 1)
    run.expect_dialog("2026-08-02 종목I 매수 5 거래를 삭제하시겠습니까?")
    run.expect_text("#transactions-message",
                    ERROR + "이 거래를 삭제하면 2026-08-03 '종목I' 매도가 보유수량을 초과합니다. 거래를 삭제하지 않았습니다.")
    expect_rows(run, "transactions-body", 3)
    if len(stored_data(run)["transactions"]) != 3:
        raise AssertionError("거부했는데 저장 객체의 거래 수가 바뀌었다")


def t4_08_dismiss_accept(run):
    run.open_with_data(fixtures.case_data("C-09"))
    delete_row(run, 2, "dismiss")
    expect_rows(run, "transactions-body", 3)
    run.expect_dialog("2026-08-03 종목I 매도 12 거래를 삭제하시겠습니까?")
    delete_row(run, 2)
    expect_rows(run, "transactions-body", 2)
    run.expect_dialog("2026-08-03 종목I 매도 12 거래를 삭제하시겠습니까?")
    if len(run.dialogs) != 2:
        raise AssertionError(f"대화상자 수: 기대 2, 실제 {len(run.dialogs)}")
    run.page.reload()
    expect_rows(run, "transactions-body", 2)
    ids = [tx["id"] for tx in stored_data(run)["transactions"]]
    if ids != ["C09-0", "C09-1"]:
        raise AssertionError(f"삭제 후 저장된 거래 id: {ids}")


def t4_08_focus(run):
    run.open_with_data(fixtures.case_data("R-06"))
    label = run.page.locator(DELETE_BUTTON_SELECTOR).first.get_attribute("aria-label")
    if label != "2026-01-02 종목N 매수 거래 삭제":
        raise AssertionError(f"삭제 버튼 aria-label: {label!r}")
    delete_row(run, 0)
    focus = active_element(run)
    if focus != {"id": "", "action": "delete-transaction", "key": "R06-1"}:
        raise AssertionError(f"가운데 행 삭제 후 포커스: {focus}")
    delete_row(run, 2)
    focus = active_element(run)
    if focus["id"] != "transactions-heading":
        raise AssertionError(f"마지막 행 삭제 후 포커스: {focus}")


def t4_08_delete_all(run):
    run.open_with_data(fixtures.case_data("C-09"))
    delete_row(run, 2)
    delete_row(run, 1)
    delete_row(run, 0)
    expect_rows(run, "transactions-body", 0)
    expect_hidden(run, "#transactions-empty", False)
    expect_hidden(run, "#transactions-table", True)
    if run.page.evaluate("document.activeElement.id") != "transactions-heading":
        raise AssertionError("모두 삭제한 뒤 포커스가 거래 내역 제목이 아니다")


SCENARIOS["T4-08"] = [
    ("C-09 a 매수 삭제 거부 VE-11", t4_08_reject),
    ("취소하면 그대로, 확인하면 삭제와 저장", t4_08_dismiss_accept),
    ("aria-label 과 삭제 후 포커스", t4_08_focus),
    ("모두 삭제하면 빈 상태 문구", t4_08_delete_all),
]


# T4-09 보유 현황 표 (docs/05_작업지시서.md T4-09 검증 방법)
# 기대값은 03 14절 사례의 표시값(03 13.2 자릿수, 04 8절 형식)이다.
# 칸 순서: 종목명, 자산군, 보유수량, 평균단가, 현재가, 평가금액, 평가손익, 수익률, 실현손익(02 9.3)
# T4-10 부터 현재가 칸은 입력칸이므로 칸 텍스트는 입력칸 값 + 칸 글자("현재가 미입력")다.


def case_subset(case_id, indexes):
    """사례 데이터에서 indexes 위치의 거래만 남긴 저장 객체."""
    data = fixtures.case_data(case_id)
    data["transactions"] = [data["transactions"][i] for i in indexes]
    return data


def holding_cells(run, name):
    """보유 현황에서 종목명이 name 인 행의 칸별 (텍스트, 색 클래스) 목록. 입력칸이 있으면 그 값을 앞에 붙인다."""
    rows = run.page.evaluate(
        """() => [...document.getElementById('holdings-body').rows].map(tr => [...tr.cells].map(c => [
            ((c.querySelector('input') ? c.querySelector('input').value + ' ' : '') + c.innerText).trim(),
            ['value-up', 'value-down'].filter(k => c.classList.contains(k)).join(' ')]))"""
    )
    for row in rows:
        if row[0][0] == name:
            return row
    raise AssertionError(f"보유 현황에 {name} 행이 없다")


def expect_holding(run, name, texts, colors=None):
    """행 텍스트와 색 클래스(칸 번호 -> 클래스, 나머지 칸은 클래스 없음)를 확인한다."""
    cells = holding_cells(run, name)
    actual = [text for text, _ in cells]
    if actual != texts:
        raise AssertionError(f"{name} 행: 기대 {texts}, 실제 {actual}")
    colors = colors or {}
    actual_colors = {i: cls for i, (_, cls) in enumerate(cells) if cls}
    if actual_colors != colors:
        raise AssertionError(f"{name} 행 색 클래스: 기대 {colors}, 실제 {actual_colors}")


def t4_09_c02(run):
    run.open_with_data(fixtures.case_data("C-02"))
    expect_holding(run, "종목B", ["종목B", "주식", "30", "5,450.00", "6000", "180,000", "+16,500", "+10.09", "0"],
                   {6: "value-up", 7: "value-up"})
    expect_hidden(run, "#holdings-empty", True)
    first = run.page.locator("#holdings-body tr").first.locator("th")
    if first.get_attribute("scope") != "row":
        raise AssertionError("종목명 칸이 th scope=row 가 아니다")


def t4_09_c11(run):
    run.open_with_data(fixtures.case_data("C-11"))
    expect_holding(run, "종목K", ["종목K", "주식", "2", "10,166.67", "11000", "22,000", "+1,667", "+8.20", "+1,833"],
                   {6: "value-up", 7: "value-up", 8: "value-up"})


def t4_09_zero_quantity(run):
    run.open_with_data(case_subset("C-04", [0, 1]))
    expect_holding(run, "종목D", ["종목D", "주식", "0", "0.00", "-", "-", "-", "-", "+6,000"], {8: "value-up"})


def t4_09_price_missing_and_cash(run):
    run.open_with_data(fixtures.case_data("C-10"))
    expect_holding(run, "종목J", ["종목J", "주식", "10", "2,550.00", "현재가 미입력", "25,500", "0", "0.00", "0"])
    if run.page.locator("#holdings-body .price-missing").count() != 1:
        raise AssertionError("C-10: price-missing 표시가 1 개가 아니다")


def t4_09_cash(run):
    run.open_with_data(fixtures.case_data("C-14"))
    expect_holding(run, "현금", ["현금", "현금", "700,000", "1.00", "1", "700,000", "0", "0.00", "0"])
    if run.page.locator("#holdings-body .price-missing").count() != 0:
        raise AssertionError("C-14: 현금에 현재가 미입력 표시가 있다")


def t4_09_cash_fee(run):
    run.open_with_data(fixtures.case_data("C-15"))
    expect_holding(run, "현금", ["현금", "현금", "1,000,000", "1.00", "1", "1,000,000", "-1,000", "-0.10", "0"],
                   {6: "value-down", 7: "value-down"})


def t4_09_realized_loss(run):
    run.open_with_data(case_subset("C-03", [0, 2]))
    cells = holding_cells(run, "종목C")
    if cells[8] != ["-2,300", "value-down"]:
        raise AssertionError(f"실현손익 칸: 기대 ['-2,300', 'value-down'], 실제 {cells[8]}")


def t4_09_order(run):
    run.open_with_data(fixtures.case_data("R-06"))
    names = [row[0] for row in row_texts(run, "holdings-body")]
    if names != ["종목N", "종목O", "현금", "종목P"]:
        raise AssertionError(f"행 순서: {names}")
    expect_holding(run, "종목N", ["종목N", "주식", "10", "50,500.00", "55000", "550,000", "+45,000", "+8.91", "0"],
                   {6: "value-up", 7: "value-up"})


def t4_09_empty(run):
    run.open()
    expect_hidden(run, "#holdings-empty", False)
    expect_hidden(run, "#holdings-table", True)


SCENARIOS["T4-09"] = [
    ("C-02 수수료 포함 매수와 수익 색", t4_09_c02),
    ("C-11 평균단가 반올림 표시", t4_09_c11),
    ("C-04 보유수량 0 행은 평가 칸 -", t4_09_zero_quantity),
    ("C-10 현재가 미입력 표시", t4_09_price_missing_and_cash),
    ("C-14 현금 현재가 1", t4_09_cash),
    ("C-15 현금 수수료 손실 색", t4_09_cash_fee),
    ("C-03 실현손익 음수 손실 색", t4_09_realized_loss),
    ("R-06 행 순서와 종목N 표시값", t4_09_order),
    ("종목 0개 빈 상태 문구", t4_09_empty),
]


# T4-10 현재가 입력 (docs/05_작업지시서.md T4-10 검증 방법)

VE_12 = "현재가는 0보다 큰 숫자로 입력하세요."
C01_PRICED = ["종목A", "주식", "15", "11,000.00", "12000", "180,000", "+15,000", "+9.09", "+10,000"]  # 현재가 12000


def price_input(run, name):
    return run.page.locator(f'#holdings-body input[data-action="set-price"][data-name="{name}"]')


def enter_price(run, name, value):
    """현재가 입력칸에 값을 넣고 Tab 으로 벗어난다(change 이벤트). ui.js 는 처리를 다음 작업으로 미루므로(M-33) 그 처리가 끝나기를 기다린다."""
    field = price_input(run, name)
    field.fill(value)
    field.press("Tab")
    settle(run)


def settle(run):
    """페이지에 이미 예약된 setTimeout 작업이 실행될 때까지 기다린다."""
    run.page.evaluate("() => new Promise((resolve) => setTimeout(resolve))")


def stored_prices(run):
    return stored_data(run)["prices"]


def t4_10_set_price(run):
    run.open_with_data(fixtures.case_data("C-01"))
    enter_price(run, "종목A", "12000")
    expect_holding(run, "종목A", C01_PRICED, {6: "value-up", 7: "value-up", 8: "value-up"})
    if stored_prices(run) != {"종목A": 12000}:
        raise AssertionError(f"prices: {stored_prices(run)}")
    run.page.reload()
    expect_holding(run, "종목A", C01_PRICED, {6: "value-up", 7: "value-up", 8: "value-up"})
    label = price_input(run, "종목A").get_attribute("aria-label")
    mode = price_input(run, "종목A").get_attribute("inputmode")
    if label != "종목A 현재가" or mode != "decimal":
        raise AssertionError(f"현재가 입력칸 aria-label {label!r}, inputmode {mode!r}")


def t4_10_clear_price(run):
    run.open_with_data(fixtures.case_data("C-01"))
    enter_price(run, "종목A", "12000")
    enter_price(run, "종목A", "")
    expect_holding(run, "종목A", ["종목A", "주식", "15", "11,000.00", "현재가 미입력", "165,000", "0", "0.00", "+10,000"],
                   {8: "value-up"})
    if "종목A" in stored_prices(run):
        raise AssertionError(f"비웠는데 prices 에 종목A 키가 있다: {stored_prices(run)}")


def t4_10_invalid_price(run):
    run.open_with_data(fixtures.case_data("C-01"))
    enter_price(run, "종목A", "12000")
    for value in ("0", "-1"):
        enter_price(run, "종목A", value)
        run.expect_text("#holdings-message", ERROR + VE_12)
        if stored_prices(run) != {"종목A": 12000}:
            raise AssertionError(f"{value}: prices 가 바뀌었다 {stored_prices(run)}")
        actual = price_input(run, "종목A").input_value()
        if actual != value:
            raise AssertionError(f"{value}: 입력칸 값이 되돌려졌다 {actual!r}")
    # 숫자로 해석되지 않는 값(브라우저 badInput)은 미입력이 아니라 오류다(05 3.1 M-32)
    field = price_input(run, "종목A")
    field.fill("")
    field.focus()
    run.page.keyboard.type("1e")
    run.page.keyboard.press("Tab")
    settle(run)
    run.expect_text("#holdings-message", ERROR + VE_12)
    if stored_prices(run) != {"종목A": 12000}:
        raise AssertionError(f"badInput: prices 가 바뀌었다 {stored_prices(run)}")
    # 다음 성공 때 오류가 사라진다
    enter_price(run, "종목A", "13000")
    run.expect_text("#holdings-message", "")


def t4_10_tab_focus(run):
    run.open_with_data(fixtures.case_data("R-06"))
    enter_price(run, "종목N", "56000")
    focus = active_element(run)
    if focus != {"id": "", "action": "set-price", "key": "종목O"}:
        raise AssertionError(f"Tab 뒤 포커스: 기대 종목O 현재가 입력칸, 실제 {focus}")
    cells = holding_cells(run, "종목N")
    if cells[5][0] != "560,000":
        raise AssertionError(f"종목N 평가금액: {cells[5][0]}")


def t4_10_prune_on_delete(run):
    run.open_with_data(fixtures.case_data("C-01"))
    enter_price(run, "종목A", "12000")
    delete_row(run, 2)
    delete_row(run, 0)
    if stored_prices(run) != {"종목A": 12000}:
        raise AssertionError(f"거래가 남았는데 prices 가 바뀌었다: {stored_prices(run)}")
    delete_row(run, 0)
    if stored_prices(run) != {}:
        raise AssertionError(f"거래를 모두 삭제했는데 prices: {stored_prices(run)}")


SCENARIOS["T4-10"] = [
    ("C-01 종목A 현재가 12000 입력과 새로고침 유지", t4_10_set_price),
    ("현재가를 비우면 미입력과 키 삭제", t4_10_clear_price),
    ("0, -1, 숫자 아님은 VE-12 와 저장값 유지", t4_10_invalid_price),
    ("R-06 현재가 입력 뒤 Tab 포커스 유지", t4_10_tab_focus),
    ("거래를 모두 삭제하면 현재가 키 삭제", t4_10_prune_on_delete),
]


# T4-11 자산 비중 표 (docs/05_작업지시서.md T4-11 검증 방법)
# 기대값은 03 14.16(R-01), 14.19(R-04), 14.20(R-05)의 비중 표시값이다.

def expect_allocation(run, rows, total, message_shown):
    actual = row_texts(run, "allocation-body")
    if actual != rows:
        raise AssertionError(f"#allocation-body: 기대 {rows}, 실제 {actual}")
    run.expect_text("#allocation-total", total)
    expect_hidden(run, "#allocation-message", not message_shown)
    if message_shown:
        run.expect_text("#allocation-message", IN_03)
    colored = run.page.locator("#allocation-table .value-up, #allocation-table .value-down").count()
    if colored:
        raise AssertionError(f"자산 비중 표에 수익/손실 색 클래스 {colored} 개")
    scopes = run.page.evaluate(
        "() => [...document.getElementById('allocation-body').rows].map(tr => tr.cells[0].tagName + tr.cells[0].scope)"
    )
    if scopes != ["THrow"] * 4:
        raise AssertionError(f"자산군 칸이 th scope=row 가 아니다: {scopes}")


def t4_11_r01(run):
    run.open_with_data(fixtures.case_data("R-01"))
    expect_allocation(run, [["주식", "7,000,000", "70.00"], ["채권", "2,000,000", "20.00"],
                            ["현금", "1,000,000", "10.00"], ["기타", "0", "0.00"]], "10,000,000", False)


def t4_11_r04(run):
    run.open_with_data(fixtures.case_data("R-04"))
    expect_allocation(run, [["주식", "3,330,000", "33.30"], ["채권", "3,330,000", "33.30"],
                            ["현금", "3,340,001", "33.40"], ["기타", "0", "0.00"]], "10,000,001", False)


def t4_11_r05(run):
    run.open_with_data(fixtures.case_data("R-05"))
    expect_allocation(run, [["주식", "0", "-"], ["채권", "0", "-"], ["현금", "0", "-"], ["기타", "0", "-"]], "0", True)


def t4_11_empty(run):
    run.open()
    expect_allocation(run, [["주식", "0", "-"], ["채권", "0", "-"], ["현금", "0", "-"], ["기타", "0", "-"]], "0", True)
    # 거래를 추가하면 안내가 사라지고 비중이 보인다
    add_transaction(run, **C01_FIRST)
    expect_allocation(run, [["주식", "100,000", "100.00"], ["채권", "0", "0.00"],
                            ["현금", "0", "0.00"], ["기타", "0", "0.00"]], "100,000", False)


SCENARIOS["T4-11"] = [
    ("R-01 자산군 평가금액, 비중, 합계", t4_11_r01),
    ("R-04 비중 33.30, 33.30, 33.40, 0.00", t4_11_r04),
    ("R-05 총평가금액 0 이면 IN-03 과 비중 -", t4_11_r05),
    ("빈 상태 IN-03, 거래 추가 뒤 비중 표시", t4_11_empty),
]


# T4-12 목표 비중 입력 (docs/05_작업지시서.md T4-12 검증 방법)

TARGET_IDS = ("target-stock", "target-bond", "target-cash", "target-other")
VE_13 = "목표 비중은 0 이상 100 이하의 숫자로 입력하세요."
VE_14 = "목표 비중은 소수 첫째 자리까지 입력할 수 있습니다."


def target_values(run):
    return [run.page.input_value("#" + i) for i in TARGET_IDS]


def stored_targets(run):
    data = stored_data(run)
    return None if data is None else data["targets"]


def t4_12_initial(run):
    run.open()
    if target_values(run) != ["0", "0", "0", "0"]:
        raise AssertionError(f"목표 비중 입력칸 처음 값: {target_values(run)}")
    run.expect_text("#target-sum", "0.0%")


def t4_12_input_and_reload(run):
    run.open()
    run.page.fill("#target-stock", "60")
    run.expect_text("#target-sum", "60.0%")
    if stored_targets(run) != {"stock": 60, "bond": 0, "cash": 0, "other": 0}:
        raise AssertionError(f"저장된 targets: {stored_targets(run)}")
    run.page.reload()
    if target_values(run) != ["60", "0", "0", "0"]:
        raise AssertionError(f"새로고침 후 입력칸: {target_values(run)}")
    run.expect_text("#target-sum", "60.0%")


def t4_12_sum_100(run):
    run.open()
    for target_id, value in zip(TARGET_IDS, ("33.3", "33.3", "33.4", "0")):
        run.page.fill("#" + target_id, value)
    run.expect_text("#target-sum", "100.0%")
    if stored_targets(run) != {"stock": 33.3, "bond": 33.3, "cash": 33.4, "other": 0}:
        raise AssertionError(f"저장된 targets: {stored_targets(run)}")


def t4_12_errors(run):
    run.open()
    run.page.fill("#target-bond", "30")
    before = stored_targets(run)
    for value, message in (("33.33", VE_14), ("101", VE_13), ("-1", VE_13), ("", VE_13)):
        run.page.fill("#target-bond", value)
        run.expect_text("#targets-message", ERROR + message)
        if stored_targets(run) != before:
            raise AssertionError(f"{value!r}: 저장값이 바뀌었다 {stored_targets(run)}")
        if run.page.input_value("#target-bond") != value:
            raise AssertionError(f"{value!r}: 입력칸 값이 다시 써졌다 {run.page.input_value('#target-bond')!r}")
    run.expect_text("#target-sum", "30.0%")
    # 다음 성공 때 오류가 사라진다
    run.page.fill("#target-bond", "35.5")
    run.expect_text("#targets-message", "")
    run.expect_text("#target-sum", "35.5%")


def t4_12_typing(run):
    run.open()
    field = run.page.locator("#target-cash")
    field.fill("")
    field.focus()
    run.page.keyboard.type("12.5")
    actual = field.input_value()
    if actual != "12.5":
        raise AssertionError(f"한 글자씩 입력한 값: 기대 '12.5', 실제 {actual!r}")
    focused = run.page.evaluate("document.activeElement.id")
    if focused != "target-cash":
        raise AssertionError(f"입력 중 포커스: {focused!r}")
    run.expect_text("#target-sum", "12.5%")
    run.expect_text("#targets-message", "")
    if stored_targets(run)["cash"] != 12.5:
        raise AssertionError(f"저장된 targets: {stored_targets(run)}")


SCENARIOS["T4-12"] = [
    ("처음 4칸 0 과 합계 0.0%", t4_12_initial),
    ("주식 60 입력과 새로고침 유지", t4_12_input_and_reload),
    ("33.3, 33.3, 33.4, 0 합계 100.0%", t4_12_sum_100),
    ("33.33 VE-14, 101, -1, 빈칸 VE-13 과 저장값 유지", t4_12_errors),
    ("한 글자씩 입력해도 값과 포커스 유지", t4_12_typing),
]


# T4-13 리밸런싱 결과 표 (docs/05_작업지시서.md T4-13 검증 방법)
# 기대값은 03 14.16~14.21 의 판정과 표시 금액이다. 칸 순서는 02 9.6, 목표 비중은 소수 첫째 자리 고정(05 3.1 M-35).

INFO = "안내: "
VE_16 = "보유 중인 종목이 없어 리밸런싱을 계산할 수 없습니다."


def ve_15(total):
    return f"목표 비중 합계가 {total}%입니다. 합계가 100%일 때 리밸런싱을 계산합니다."


def expect_rebalance_rows(run, rows):
    actual = row_texts(run, "rebalance-body")
    if actual != rows:
        raise AssertionError(f"#rebalance-body: 기대 {rows}, 실제 {actual}")
    expect_hidden(run, "#rebalance-table", False)
    expect_hidden(run, "#rebalance-message", True)
    run.expect_text("#rebalance-message", "")
    colored = run.page.locator("#rebalance-table .value-up, #rebalance-table .value-down").count()
    if colored:
        raise AssertionError(f"리밸런싱 표에 수익/손실 색 클래스 {colored} 개")
    scopes = run.page.evaluate(
        "() => [...document.getElementById('rebalance-body').rows].map(tr => tr.cells[0].tagName + tr.cells[0].scope)"
    )
    if scopes != ["THrow"] * 4:
        raise AssertionError(f"자산군 칸이 th scope=row 가 아니다: {scopes}")


def expect_rebalance_info(run, message):
    expect_hidden(run, "#rebalance-table", True)
    expect_hidden(run, "#rebalance-message", False)
    run.expect_text("#rebalance-message", INFO + message)
    cls = run.page.locator("#rebalance-message").get_attribute("class")
    if cls != "message-info":
        raise AssertionError(f"#rebalance-message class: 기대 'message-info', 실제 {cls!r}")
    expect_rows(run, "rebalance-body", 0)


R01_REBALANCE = [
    ["주식", "7,000,000", "60.0", "6,000,000", "1,000,000", "매도"],
    ["채권", "2,000,000", "30.0", "3,000,000", "1,000,000", "매수"],
    ["현금", "1,000,000", "10.0", "1,000,000", "0", "유지"],
    ["기타", "0", "0.0", "0", "0", "유지"],
]


def t4_13_r01(run):
    run.open_with_data(fixtures.case_data("R-01"))
    expect_rebalance_rows(run, R01_REBALANCE)


def t4_13_r02(run):
    run.open_with_data(fixtures.case_data("R-02", "a"))
    expect_rebalance_info(run, ve_15("95.0"))


def t4_13_r02_b(run):
    run.open_with_data(fixtures.case_data("R-02", "b"))
    expect_rebalance_info(run, ve_15("100.1"))


def t4_13_r03(run):
    run.open_with_data(fixtures.case_data("R-03"))
    expect_rebalance_rows(run, [
        ["주식", "7,000,000", "0.1", "10,000", "6,990,000", "매도"],
        ["채권", "2,000,000", "0.2", "20,000", "1,980,000", "매도"],
        ["현금", "1,000,000", "84.1", "8,410,000", "7,410,000", "매수"],
        ["기타", "0", "15.6", "1,560,000", "1,560,000", "매수"],
    ])


def t4_13_r04(run):
    run.open_with_data(fixtures.case_data("R-04"))
    expect_rebalance_rows(run, [
        ["주식", "3,330,000", "33.3", "3,330,000", "0", "유지"],
        ["채권", "3,330,000", "33.3", "3,330,000", "0", "유지"],
        ["현금", "3,340,001", "33.4", "3,340,000", "1", "매도"],
        ["기타", "0", "0.0", "0", "0", "유지"],
    ])


def t4_13_r05(run):
    run.open_with_data(fixtures.case_data("R-05"))
    expect_rebalance_info(run, VE_16)


def t4_13_r06(run):
    run.open_with_data(fixtures.case_data("R-06"))
    expect_rebalance_rows(run, [
        ["주식", "550,000", "50.0", "500,000", "50,000", "매도"],
        ["채권", "300,000", "35.5", "355,000", "55,000", "매수"],
        ["현금", "100,000", "10.0", "100,000", "0", "유지"],
        ["기타", "50,000", "4.5", "45,000", "5,000", "매도"],
    ])


def t4_13_live(run):
    run.open_with_data(fixtures.case_data("R-01"))
    run.page.fill("#target-cash", "5")
    expect_rebalance_info(run, ve_15("95.0"))
    run.page.fill("#target-cash", "10")
    expect_rebalance_rows(run, R01_REBALANCE)
    # 빈 상태에서는 VE-16
    run.page.evaluate(f"localStorage.removeItem({json.dumps(fixtures.STORAGE_KEY)})")
    run.page.goto(run.url("?empty"))
    expect_rebalance_info(run, VE_16)


SCENARIOS["T4-13"] = [
    ("R-01 주식 매도, 채권 매수, 현금과 기타 유지", t4_13_r01),
    ("R-02 a 합계 95.0 이면 VE-15 안내", t4_13_r02),
    ("R-02 b 합계 100.1 이면 VE-15 안내", t4_13_r02_b),
    ("R-03 부동소수 합계 판정과 금액", t4_13_r03),
    ("R-04 표시 0 원 유지와 매도 1", t4_13_r04),
    ("R-05 총평가금액 0 이면 VE-16 안내", t4_13_r05),
    ("R-06 4개 자산군 금액과 판정", t4_13_r06),
    ("목표 비중 변경 즉시 반영과 빈 상태 VE-16", t4_13_live),
]


# T4-14 JSON 내보내기 (docs/05_작업지시서.md T4-14 검증 방법)

EMPTY_DATA = {"version": 1, "transactions": [], "prices": {}, "targets": {"stock": 0, "bond": 0, "cash": 0, "other": 0}}


def today(run):
    return run.page.evaluate(
        "(() => { const d = new Date(); const p = n => String(n).padStart(2, '0');"
        " return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })()"
    )


def export_file(run):
    """JSON 내보내기를 눌러 받은 파일의 (이름, 내용 텍스트)를 반환한다."""
    with run.page.expect_download() as info:
        run.page.click("#export-button")
    path = run.save_download(info.value)
    return info.value.suggested_filename, path.read_text(encoding="utf-8")


def expect_export(run, expected_data):
    name, text = export_file(run)
    expected_name = f"portfolio-tracker-{today(run)}.json"
    if name != expected_name:
        raise AssertionError(f"파일 이름: 기대 {expected_name}, 실제 {name}")
    content = json.loads(text)
    if content != expected_data:
        raise AssertionError(f"파일 내용: 기대 {expected_data}, 실제 {content}")
    if list(content) != ["version", "transactions", "prices", "targets"]:
        raise AssertionError(f"파일 키 순서: {list(content)}")
    if not text.startswith('{\n  "version": 1,'):
        raise AssertionError(f"들여쓰기 2칸이 아니다: {text[:30]!r}")


def t4_14_r06(run):
    run.open_with_data(fixtures.case_data("R-06"))
    expect_export(run, stored_data(run))
    # 변경 직후에도 같은 시점 localStorage 값과 같다
    enter_price(run, "종목O", "10500")
    expect_export(run, stored_data(run))


def t4_14_empty(run):
    run.open()
    # 처음 연 빈 상태는 저장 키가 없다(02 7.4 loadData). 내용은 02 5.5 빈 데이터다.
    if stored_data(run) is not None:
        raise AssertionError("처음 연 빈 상태에 저장 키가 있다")
    expect_export(run, EMPTY_DATA)
    # 거래를 넣었다가 모두 지운 빈 상태는 저장값과 같다
    add_transaction(run, **C01_FIRST)
    delete_row(run, 0)
    expect_export(run, stored_data(run))
    if stored_data(run) != EMPTY_DATA:
        raise AssertionError(f"모두 삭제한 뒤 저장 객체: {stored_data(run)}")


SCENARIOS["T4-14"] = [
    ("R-06 내보내기 파일 이름과 내용", t4_14_r06),
    ("거래 0건 내보내기", t4_14_empty),
]


# T4-15 JSON 불러오기 (docs/05_작업지시서.md T4-15 검증 방법)
# 불러올 파일은 저장소 밖 임시 폴더(run.temp_dir)에 만든다.

IN_04 = "불러오기를 완료했습니다."
VE_17 = "JSON 파일을 읽을 수 없습니다. 기존 데이터는 바뀌지 않았습니다."


def ve_18(detail):
    return f"파일 형식이 올바르지 않습니다. {detail} 기존 데이터는 바뀌지 않았습니다."


def c_02(current, file_count):
    return f"현재 데이터(거래 {current}건)를 불러온 파일의 데이터(거래 {file_count}건)로 모두 교체합니다. 계속하시겠습니까?"


def wait_until(run, condition, label):
    """파일 읽기(file.text())가 비동기라 화면 반영을 짧게 나눠 기다린다."""
    for _ in range(100):
        if condition():
            return
        run.page.wait_for_timeout(20)
    raise AssertionError(f"기다린 상태가 오지 않았다: {label}")


def write_file(run, name, data):
    """data 가 str 이면 그대로, 아니면 JSON 으로 임시 폴더에 쓴다."""
    path = run.temp_dir / name
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def import_file(run, path, action="accept"):
    """#import-file 로 파일을 고르고, 확인 대화상자가 뜨면 action 으로 처리한다. 결과 메시지나 대화상자를 기다린다."""
    run.dialog_action = action
    dialogs = len(run.dialogs)
    run.page.set_input_files("#import-file", str(path))
    wait_until(run, lambda: len(run.dialogs) > dialogs or run.text("#data-message") != "", "대화상자 또는 #data-message")
    if action == "accept" and len(run.dialogs) > dialogs:
        wait_until(run, lambda: run.text("#data-message") != "", "#data-message")
    if run.page.input_value("#import-file") != "":
        raise AssertionError("처리 뒤 #import-file 값이 비어 있지 않다")


def screen_texts(run):
    return {body: row_texts(run, body) for body in ("transactions-body", "holdings-body", "allocation-body", "rebalance-body")}


def expect_unchanged(run, before_texts, before_data):
    if screen_texts(run) != before_texts:
        raise AssertionError("화면이 바뀌었다")
    if stored_data(run) != before_data:
        raise AssertionError(f"저장 객체가 바뀌었다: {stored_data(run)}")


def t4_15_r06_file(run):
    run.open_with_data(fixtures.case_data("C-01"))
    before_texts, before_data = screen_texts(run), stored_data(run)
    path = write_file(run, "r06.json", fixtures.case_data("R-06"))
    import_file(run, path, "dismiss")
    run.expect_dialog(c_02(3, 4))
    expect_unchanged(run, before_texts, before_data)
    run.expect_text("#data-message", "")
    # 같은 파일을 연속으로 다시 고른다
    import_file(run, path, "accept")
    run.expect_dialog(c_02(3, 4))
    if len(run.dialogs) != 2:
        raise AssertionError(f"대화상자 수: 기대 2, 실제 {len(run.dialogs)}")
    run.expect_text("#data-message", INFO + IN_04)
    if stored_data(run) != fixtures.case_data("R-06"):
        raise AssertionError(f"불러온 뒤 저장 객체: {stored_data(run)}")
    if target_values(run) != ["50", "35.5", "10", "4.5"]:
        raise AssertionError(f"불러온 뒤 목표 비중 입력칸: {target_values(run)}")
    names = [row[0] for row in row_texts(run, "holdings-body")]
    if names != ["종목N", "종목O", "현금", "종목P"]:
        raise AssertionError(f"불러온 뒤 보유 현황: {names}")
    run.expect_text("#target-sum", "100.0%")
    expect_rows(run, "rebalance-body", 4)


def expect_rejected(run, name, content, message):
    run.open_with_data(fixtures.case_data("C-01"))
    before_texts, before_data = screen_texts(run), stored_data(run)
    import_file(run, write_file(run, name, content))
    run.expect_text("#data-message", ERROR + message)
    if run.dialogs:
        raise AssertionError(f"검증 실패인데 대화상자가 떴다: {run.dialogs}")
    expect_unchanged(run, before_texts, before_data)


def t4_15_not_json(run):
    expect_rejected(run, "broken.json", "{", VE_17)


def t4_15_version(run):
    data = {**fixtures.case_data("R-06"), "version": 2}
    expect_rejected(run, "v2.json", data, "지원하지 않는 데이터 버전입니다(version: 2). 기존 데이터는 바뀌지 않았습니다.")


def t4_15_extra_key(run):
    data = fixtures.case_data("R-06")
    data["transactions"][0]["memo"] = "x"
    expect_rejected(run, "extra.json", data, ve_18("transactions 1번째 항목: 거래 항목이 올바르지 않습니다(memo)."))


def t4_15_over_sell(run):
    data = fixtures.case_data("C-07")
    data["transactions"].append({"id": "C07-2", "date": "2026-07-05", "name": "종목G", "assetClass": "stock",
                                 "type": "sell", "quantity": 5, "price": 1100, "fee": 0})  # 03 14.8 추가 시도
    expect_rejected(run, "oversell.json", data, ve_18("2026-07-10 '종목G' 매도 수량(8)이 그 시점 보유수량(5)보다 많습니다."))


def t4_15_prune(run):
    run.open()
    data = fixtures.case_data("R-01")
    data["prices"]["없는종목"] = 1000
    import_file(run, write_file(run, "prune.json", data))
    run.expect_dialog(c_02(0, 3))
    run.expect_text("#data-message", INFO + IN_04)
    if stored_prices(run) != {"종목S": 70000, "종목T": 100000}:
        raise AssertionError(f"불러온 뒤 prices: {stored_prices(run)}")


def t4_15_round_trip(run):
    run.open_with_data(fixtures.case_data("R-06"))
    before = screen_texts(run)
    name, text = export_file(run)
    path = write_file(run, name, text)
    # 화면을 바꾼 뒤 내보낸 파일을 다시 불러온다
    enter_price(run, "종목N", "60000")
    run.page.fill("#target-stock", "40")
    if screen_texts(run) == before:
        raise AssertionError("바꾼 뒤에도 화면이 같다")
    import_file(run, path)
    run.expect_dialog(c_02(4, 4))
    after = screen_texts(run)
    if after != before:
        raise AssertionError(f"왕복 뒤 화면: 기대 {before}, 실제 {after}")
    if target_values(run) != ["50", "35.5", "10", "4.5"]:
        raise AssertionError(f"왕복 뒤 목표 비중 입력칸: {target_values(run)}")


SCENARIOS["T4-15"] = [
    ("R-06 파일 C-02 취소는 그대로, 같은 파일 다시 골라 확인하면 교체", t4_15_r06_file),
    ("JSON 아닌 파일 VE-17", t4_15_not_json),
    ("version 2 파일 VE-19", t4_15_version),
    ("거래 키가 하나 더 있는 파일 VE-18(VD-03, VE-23)", t4_15_extra_key),
    ("초과 매도 파일 VE-18(VE-25)", t4_15_over_sell),
    ("거래 없는 종목의 현재가 키는 제거", t4_15_prune),
    ("내보내기 -> 불러오기 왕복 화면 같음", t4_15_round_trip),
]


# T4-16 반응형, 접근성, 고지 점검 (docs/05_작업지시서.md T4-16 검증 방법)

FORBIDDEN = re.compile(  # 04 3절 금지 요소(그라데이션, 글래스모피즘, 알약 반경, 그림자, 애니메이션, 웹 글꼴)
    r"gradient|box-shadow|backdrop-filter|border-radius: *(999|50%)|transition|animation|@import|@font-face|fonts\.googleapis"
)
NON_TEXT = re.compile("[^\x00-\x7F가-힣ㄱ-ㆎ]")  # 이모지와 장식 기호(05 2.4)


def t4_16_widths(run):
    run.open_with_data(fixtures.case_data("R-06"))
    for width in WIDTHS:
        run.page.set_viewport_size({"width": width, "height": 800})
        if not run.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"):
            raise AssertionError(f"{width}px: 페이지 가로 스크롤")
        if not run.page.locator("#disclaimer").is_visible():
            raise AssertionError(f"{width}px: #disclaimer 가 보이지 않는다")
        # 넓은 표는 .table-wrap 안에서만 스크롤한다(04 10.1)
        bad = run.page.evaluate(
            """() => [...document.querySelectorAll('table')].filter(t => !t.hidden)
                .filter(t => !t.parentElement.classList.contains('table-wrap')
                    || getComputedStyle(t.parentElement).overflowX !== 'auto').map(t => t.id)"""
        )
        if bad:
            raise AssertionError(f"{width}px: .table-wrap(overflow-x auto) 밖의 표 {bad}")
    run.page.set_viewport_size({"width": 1024, "height": 800})
    tops = run.page.evaluate(
        "() => ['allocation-section', 'rebalance-group'].map(id => document.getElementById(id).getBoundingClientRect().top)"
    )
    if tops[0] != tops[1]:
        raise AssertionError(f"1024px: 자산 비중과 리밸런싱이 두 열이 아니다 {tops}")
    run.page.set_viewport_size({"width": 360, "height": 800})
    boxes = run.page.evaluate(
        """() => ['export-button', 'import-button'].map(id => {
            const r = document.getElementById(id).getBoundingClientRect(); return [r.top, r.width]; })"""
    )
    section = run.page.evaluate("document.getElementById('data-section').getBoundingClientRect().width")
    if not boxes[1][0] > boxes[0][0] or min(boxes[0][1], boxes[1][1]) < section / 2:
        raise AssertionError(f"360px: 데이터 관리 버튼이 세로로 쌓인 전체 너비가 아니다 {boxes}")
    # 640px 미만은 폼 항목 한 줄에 하나(04 7.5). 목표 비중 입력칸도 세로로 쌓인다
    tops = run.page.evaluate(
        "() => ['target-stock', 'target-bond'].map(id => document.getElementById(id).getBoundingClientRect().top)"
    )
    if not tops[1] > tops[0]:
        raise AssertionError(f"360px: 목표 비중 입력칸이 한 줄에 하나가 아니다 {tops}")


def focus_key(run):
    return run.page.evaluate(
        """() => { const el = document.activeElement;
            return el.id || (el.dataset.action ? el.dataset.action + ':' + (el.dataset.name || el.dataset.id) : el.tagName); }"""
    )


def t4_16_tab_order(run):
    run.page.set_viewport_size({"width": 1280, "height": 800})
    run.open_with_data(fixtures.case_data("R-06"))
    positive = run.page.evaluate("() => [...document.querySelectorAll('[tabindex]')].filter(el => el.tabIndex > 0).length")
    if positive:
        raise AssertionError(f"양수 tabindex {positive} 개")
    run.page.focus("#tx-date")
    order = ["tx-date"]
    for _ in range(80):  # 날짜 입력칸은 연, 월, 일 칸에서 Tab 이 여러 번 머문다
        run.page.keyboard.press("Tab")
        key = focus_key(run)
        if key != order[-1]:
            order.append(key)
        if key == "import-button":
            break
    expected = ["tx-date", "tx-name", "tx-asset-class", "tx-type", "tx-quantity", "tx-price", "tx-fee", "tx-submit",
                "set-price:종목N", "set-price:종목O", "set-price:종목P",
                "target-stock", "target-bond", "target-cash", "target-other",
                "delete-transaction:R06-0", "delete-transaction:R06-1", "delete-transaction:R06-2",
                "delete-transaction:R06-3", "export-button", "import-button"]
    if order != expected:
        raise AssertionError(f"Tab 순서: 기대 {expected}, 실제 {order}")


def t4_16_keyboard(run):
    # 파일 선택 창 가로채기는 듣는 함수를 등록할 때 비동기로 켜진다. expect_file_chooser 를 Enter 직전에 쓰면
    # Enter 가 먼저 처리되어 창을 놓치는 일이 있으므로 페이지를 열기 전에 등록해 둔다.
    choosers = []
    run.page.on("filechooser", lambda chooser: choosers.append(chooser))
    run.open_with_data(fixtures.case_data("R-06"))
    kb = run.page.keyboard
    # 거래 추가: Tab 으로 옮겨 가며 입력하고 수수료 칸에서 Enter 로 제출한다(날짜는 처음 값 오늘)
    run.page.focus("#tx-name")
    kb.type("종목Q")
    kb.press("Tab")
    kb.press("ArrowDown")  # 자산군: 선택하세요 -> 주식
    kb.press("Tab")
    kb.press("Tab")
    kb.type("3")
    kb.press("Tab")
    kb.type("2000")
    kb.press("Tab")
    kb.press("Enter")
    expect_rows(run, "transactions-body", 5)
    if run.page.evaluate("document.activeElement.id") != "tx-date":
        raise AssertionError("거래 추가 뒤 포커스가 날짜 입력칸이 아니다")
    # 현재가 입력: Enter 로 반영
    price_input(run, "종목Q").focus()
    kb.type("2100")
    kb.press("Enter")
    settle(run)
    if stored_prices(run).get("종목Q") != 2100:
        raise AssertionError(f"키보드 현재가 입력: {stored_prices(run)}")
    # 목표 비중 입력
    run.page.focus("#target-other")
    kb.press("Control+A")
    kb.type("5")
    if stored_targets(run)["other"] != 5:
        raise AssertionError(f"키보드 목표 비중 입력: {stored_targets(run)}")
    # 내보내기와 불러오기 버튼
    run.page.focus("#export-button")
    with run.page.expect_download() as info:
        kb.press("Enter")
    if not info.value.suggested_filename.startswith("portfolio-tracker-"):
        raise AssertionError(f"키보드 내보내기 파일 이름: {info.value.suggested_filename}")
    run.page.focus("#import-button")
    kb.press("Enter")
    wait_until(run, lambda: choosers, "파일 선택 창")
    choosers[0].set_files(str(write_file(run, "r06.json", fixtures.case_data("R-06"))))
    wait_until(run, lambda: run.text("#data-message") != "", "#data-message")
    run.expect_text("#data-message", INFO + IN_04)
    run.expect_dialog(c_02(5, 4))
    expect_rows(run, "transactions-body", 4)
    # 삭제: 거래를 하나 더 넣고 마지막 거래(종목Q)의 삭제 버튼에서 Enter, 확인 accept
    add_transaction(run, date="2026-01-03", name="종목Q", asset_class="stock", type="buy", quantity="3", price="2000")
    run.page.locator(DELETE_BUTTON_SELECTOR).nth(4).focus()
    kb.press("Enter")
    run.expect_dialog("2026-01-03 종목Q 매수 3 거래를 삭제하시겠습니까?")
    expect_rows(run, "transactions-body", 4)
    if run.page.evaluate("document.activeElement.id") != "transactions-heading":
        raise AssertionError("마지막 행 삭제 뒤 포커스가 거래 내역 제목이 아니다")


def t4_16_aria(run):
    run.open_with_data(fixtures.case_data("R-06"))
    problems = run.page.evaluate(
        """() => {
            const out = [];
            for (const id of ['tx-message', 'transactions-message', 'holdings-message', 'targets-message', 'data-message', 'rebalance-message'])
                if (document.getElementById(id).getAttribute('aria-live') !== 'polite') out.push(id + ' aria-live');
            for (const id of ['tx-fee', 'target-stock', 'target-bond', 'target-cash', 'target-other']) {
                const help = id === 'tx-fee' ? 'tx-fee-help' : 'targets-help';
                if (document.getElementById(id).getAttribute('aria-describedby') !== help) out.push(id + ' aria-describedby');
            }
            for (const t of document.querySelectorAll('table')) {
                if (!t.caption || !t.caption.textContent.trim()) out.push(t.id + ' caption');
                for (const tr of t.querySelectorAll('tbody tr, tfoot tr'))
                    if (tr.cells[0].tagName !== 'TH' || tr.cells[0].scope !== 'row') out.push(t.id + ' 행 머리');
            }
            return out;
        }"""
    )
    if problems:
        raise AssertionError("; ".join(problems))


def t4_16_forbidden(run):
    run.open()
    found = []
    for rel in ("css/style.css", "index.html", "js/ui.js"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN.search(line) or NON_TEXT.search(line):
                found.append(f"{rel}:{number}")
    if found:
        raise AssertionError(f"04 3절 금지 요소: {', '.join(found)}")
    if run.page.locator("script[src^='http'], link[href^='http']").count():
        raise AssertionError("외부 스크립트나 글꼴 link 가 있다")


SCENARIOS["T4-16"] = [
    ("세 너비 가로 스크롤 없음, 고지 보임, 두 열과 세로 버튼", t4_16_widths),
    ("R-06 Tab 순서와 양수 tabindex 없음", t4_16_tab_order),
    ("키보드만으로 추가, 현재가, 목표 비중, 삭제, 내보내기, 불러오기", t4_16_keyboard),
    ("aria-live, aria-describedby, caption 과 scope", t4_16_aria),
    ("04 3절 금지 요소 0 건", t4_16_forbidden),
]


# T4-17 MVP 완료 점검: 거래 5,000건 성능 (docs/05_작업지시서.md T4-17 검증 방법, 01 NFR-03, NFR-06)

PERF_COUNT = 5000
PERF_LIMIT_MS = 200  # 01 NFR-06 화면 갱신
FIRST_PAINT_LIMIT_MS = 1000  # 01 NFR-06 첫 화면


def perf_data():
    """종목 50개에 매수 100건씩, 거래 5,000건의 저장 객체(02 5.5)."""
    transactions = []
    for i in range(PERF_COUNT):
        stock = i % 50
        transactions.append({
            "id": f"P-{i}", "date": f"2025-{(i // 500) % 12 + 1:02d}-{(i % 28) + 1:02d}",
            "name": f"종목{stock:02d}", "assetClass": ("stock", "bond", "cash", "other")[stock % 4],
            "type": "buy", "quantity": 1 + i % 7, "price": 1000 + i % 300, "fee": i % 3,
        })
    prices = {f"종목{s:02d}": 1200 for s in range(0, 50, 2)}
    return {"version": 1, "transactions": transactions, "prices": prices,
            "targets": {"stock": 50, "bond": 30, "cash": 0, "other": 20}}


def t4_17_performance(run):
    run.page.set_viewport_size({"width": 1280, "height": 800})
    run.open()
    import_file(run, write_file(run, "perf-5000.json", perf_data()))
    run.expect_dialog(c_02(0, f"{PERF_COUNT:,}"))  # 건수는 formatQuantity(쉼표)
    run.expect_text("#data-message", INFO + IN_04)
    expect_rows(run, "transactions-body", PERF_COUNT)
    expect_rows(run, "holdings-body", 50)
    expect_rows(run, "rebalance-body", 4)

    # 거래 추가: submit 직전부터 #transactions-body 행 수가 바뀐 직후까지(submit 처리는 동기)
    fill_transaction(run, date="2026-01-02", name="종목00", asset_class="stock", type="buy", quantity="1", price="1000")
    add_ms = run.page.evaluate(
        """() => { const body = document.getElementById('transactions-body'); const before = body.rows.length;
            const t0 = performance.now(); document.getElementById('transaction-form').requestSubmit();
            const t1 = performance.now(); return body.rows.length === before + 1 ? t1 - t0 : -1; }"""
    )
    # 거래 삭제: 확인 창은 사람이 누르는 시간이 들어가므로 이 측정에서만 바로 확인으로 바꾼다
    delete_ms = run.page.evaluate(
        """() => { window.confirm = () => true; const body = document.getElementById('transactions-body');
            const before = body.rows.length; const button = body.querySelector('button[data-action="delete-transaction"]');
            const t0 = performance.now(); button.click(); const t1 = performance.now();
            return body.rows.length === before - 1 ? t1 - t0 : -1; }"""
    )
    # 현재가 변경: change 처리는 다음 작업으로 미뤄지므로(05 3.1 M-33) 그 작업이 끝난 뒤를 잰다
    price_ms = run.page.evaluate(
        """async () => { const input = document.querySelector('#holdings-body input[data-name="종목01"]');
            input.value = '1500'; const t0 = performance.now();
            input.dispatchEvent(new Event('change', { bubbles: true }));
            await new Promise((resolve) => setTimeout(resolve)); const t1 = performance.now();
            const stored = JSON.parse(localStorage.getItem('portfolio-tracker:v1')).prices['종목01'];
            return stored === 1500 ? t1 - t0 : -1; }"""
    )
    # 첫 화면: 5,000건이 저장된 상태로 새로고침(01 NFR-03 저장 유지 확인을 겸함)
    run.page.reload()
    expect_rows(run, "transactions-body", PERF_COUNT)
    load_ms = run.page.evaluate("performance.getEntriesByType('navigation')[0].loadEventEnd")
    print(f"T4-17 측정(ms): 추가 {add_ms:.1f}, 삭제 {delete_ms:.1f}, 현재가 변경 {price_ms:.1f}, 첫 화면 load {load_ms:.1f}")
    problems = [f"{label} {ms:.1f}ms" for label, ms in (("추가", add_ms), ("삭제", delete_ms), ("현재가 변경", price_ms))
                if ms < 0 or ms > PERF_LIMIT_MS]
    if load_ms > FIRST_PAINT_LIMIT_MS:
        problems.append(f"첫 화면 {load_ms:.1f}ms")
    if problems:
        raise AssertionError(f"성능 기준 초과 또는 반영 안 됨(-1): {', '.join(problems)}")


SCENARIOS["T4-17"] = [
    ("거래 5,000건 불러오기, 추가, 삭제, 현재가 변경 200ms 와 첫 화면 1초", t4_17_performance),
]


# ---------------------------------------------------------------------------
# 시나리오 도우미
# ---------------------------------------------------------------------------

class Run:
    """시나리오 하나의 실행 상태와 도우미 함수."""

    def __init__(self, context, page, base_url, temp_dir):
        self.context = context
        self.page = page
        self.base_url = base_url
        self.temp_dir = Path(temp_dir)
        self.dialogs = []  # 대화상자 문구 기록(type, message)
        self.dialog_action = "accept"  # 다음 대화상자 처리: "accept" 또는 "dismiss"
        page.on("dialog", self._on_dialog)

    def _on_dialog(self, dialog):
        self.dialogs.append((dialog.type, dialog.message))
        if self.dialog_action == "dismiss":
            dialog.dismiss()
        else:
            dialog.accept()

    def url(self, path=""):
        return urljoin(self.base_url, path)

    def open(self, path=""):
        """페이지를 연다."""
        self.page.goto(self.url(path))

    def open_with_data(self, data, path=""):
        """저장 객체를 localStorage 키 portfolio-tracker:v1 에 넣고 페이지를 연다.

        data 는 fixtures.case_data(...) 결과 같은 dict 다. 새로고침 때 다시 덮어쓰지 않도록
        탭마다 한 번만 넣는다(sessionStorage 표시 사용).
        """
        text = json.dumps(data, ensure_ascii=False)
        script = (
            "if (!sessionStorage.getItem('ui-verify:fixture')) {"
            f" localStorage.setItem({json.dumps(fixtures.STORAGE_KEY)}, {json.dumps(text)});"
            " sessionStorage.setItem('ui-verify:fixture', '1'); }"
        )
        self.context.add_init_script(script)
        self.open(path)

    def text(self, selector):
        return self.page.locator(selector).inner_text().strip()

    def expect_text(self, selector, expected):
        """요소 텍스트(앞뒤 공백 제거)가 기대 문구와 같은지 확인한다."""
        actual = self.text(selector)
        if actual != expected:
            raise AssertionError(f"{selector} 텍스트: 기대 {expected!r}, 실제 {actual!r}")

    def expect_dialog(self, expected, index=-1):
        """기록된 대화상자 문구를 확인한다. 기본은 마지막 대화상자다."""
        if not self.dialogs:
            raise AssertionError(f"대화상자 없음: 기대 {expected!r}")
        actual = self.dialogs[index][1]
        if actual != expected:
            raise AssertionError(f"대화상자 문구: 기대 {expected!r}, 실제 {actual!r}")

    def check_widths(self, widths=WIDTHS):
        """각 너비에서 페이지 전체 가로 스크롤이 없는지 확인한다."""
        failed = []
        for width in widths:
            self.page.set_viewport_size({"width": width, "height": 800})
            ok = self.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            if not ok:
                failed.append(width)
        if failed:
            raise AssertionError(f"가로 스크롤 발생 너비: {failed}")

    def screenshot(self, name):
        """스크린샷을 저장소 밖 임시 폴더에 저장하고 경로를 반환한다."""
        path = self.temp_dir / f"{name}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def save_download(self, download):
        """내려받은 파일을 저장소 밖 임시 폴더에 저장하고 경로를 반환한다."""
        path = self.temp_dir / download.suggested_filename
        download.save_as(str(path))
        return path


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------

class ArgError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgError(message)


def parse_args(argv):
    parser = Parser(description="화면 검증 시나리오를 실행한다(docs/05_작업지시서.md 2.3).")
    parser.add_argument("tasks", nargs="*", help="작업 ID(예: T4-07). 없으면 전체")
    parser.add_argument("--list", action="store_true", help="등록된 작업 ID 와 시나리오 이름만 출력")
    parser.add_argument("--base-url", help="서버를 띄우지 않고 검사할 주소")
    parser.add_argument("--port", type=int, default=8000, help="확인용 정적 서버 포트(기본 8000)")
    args = parser.parse_args(argv)
    unknown = [t for t in args.tasks if t not in SCENARIOS]
    if unknown:
        raise ArgError(f"알 수 없는 작업 ID: {', '.join(unknown)} (등록된 작업 ID: {', '.join(SCENARIOS) or '없음'})")
    if args.base_url:
        parts = urlsplit(args.base_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ArgError(f"--base-url 은 http 또는 https 주소여야 한다: {args.base_url}")
        if not args.base_url.endswith("/"):
            args.base_url += "/"
    return args


def print_list():
    count = 0
    print("작업 | 시나리오")
    for task_id, items in SCENARIOS.items():
        for name, _ in items:
            print(f"{task_id} | {name}")
            count += 1
    print(f"등록된 시나리오 {count} 개")


def start_server(port):
    """프로젝트 루트에서 확인용 정적 서버를 띄우고 응답할 때까지 기다린다."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"정적 서버가 시작되지 않았다(포트 {port} 사용 중일 수 있다)")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1):
                return proc
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    stop_server(proc)
    raise RuntimeError("정적 서버 응답 대기 시간 초과")


def stop_server(proc):
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def allowed_origins(base_url, local_port):
    if local_port is not None:
        return {f"http://localhost:{local_port}", f"http://127.0.0.1:{local_port}"}
    parts = urlsplit(base_url)
    return {f"{parts.scheme}://{parts.netloc}"}


def origin_of(url):
    parts = urlsplit(url)
    return parts.scheme, f"{parts.scheme}://{parts.netloc}"


def run_one(browser, base_url, origins, temp_dir, func):
    """시나리오 하나를 새 컨텍스트에서 실행하고 공통 확인(05 2.3 의 7번)을 한다. 실패 상세 목록을 반환한다."""
    problems = []
    console_errors = []
    outside_requests = []
    context = browser.new_context(accept_downloads=True)
    try:
        page = context.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        def on_request(request):
            scheme, origin = origin_of(request.url)
            if scheme not in NON_NETWORK_SCHEMES and origin not in origins:
                outside_requests.append(request.url)

        context.on("request", on_request)
        run = Run(context, page, base_url, temp_dir)
        try:
            func(run)
        except AssertionError as err:
            problems.append(str(err) or "AssertionError")
        except Exception as err:  # 시나리오 안의 예외도 실패로 기록하고 다음 시나리오를 계속한다
            problems.append(f"예외: {type(err).__name__}: {err}")

        # 공통 확인
        try:
            actual = page.locator("#disclaimer").inner_text(timeout=3000).strip()
            if actual != DISCLAIMER:
                problems.append(f"#disclaimer 문구 불일치: {actual!r}")
        except Exception as err:
            problems.append(f"#disclaimer 확인 실패: {type(err).__name__}")
        if console_errors:
            problems.append(f"콘솔 오류 {len(console_errors)} 건: {console_errors[0]}")
        if outside_requests:
            problems.append(f"검사 주소 밖 요청 {len(outside_requests)} 건: {outside_requests[0]}")
    finally:
        context.close()
    return problems


def run_scenarios(selected, base_url, port):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 가 설치되어 있지 않다. 아래 두 명령을 실행한 뒤 다시 실행한다.")
        for line in INSTALL_HINT:
            print(line)
        return 1

    server = None
    local_port = None
    results = []
    try:
        if base_url is None:
            server = start_server(port)
            local_port = port
            base_url = f"http://localhost:{port}/"
        origins = allowed_origins(base_url, local_port)
        with tempfile.TemporaryDirectory(prefix="ui-verify-") as temp_dir:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    for task_id, name, func in selected:
                        problems = run_one(browser, base_url, origins, temp_dir, func)
                        results.append((task_id, name, not problems, "; ".join(problems)))
                finally:
                    browser.close()
    finally:
        stop_server(server)

    print("작업 | 시나리오 | 결과 | 상세")
    for task_id, name, ok, detail in results:
        print(f"{task_id} | {name} | {'통과' if ok else '실패'} | {detail or '-'}")
    passed = sum(1 for r in results if r[2])
    failed = len(results) - passed
    print(f"통과 {passed} / 실패 {failed}")
    return 0 if failed == 0 else 1


def main(argv):
    try:
        args = parse_args(argv)
    except ArgError as err:
        print(f"오류: {err}", file=sys.stderr)
        return 1
    if args.list:
        print_list()
        return 0
    task_ids = args.tasks or list(SCENARIOS)
    selected = [(t, name, func) for t in task_ids for name, func in SCENARIOS[t]]
    if not selected:
        print("작업 | 시나리오 | 결과 | 상세")
        print("통과 0 / 실패 0")
        return 0
    try:
        return run_scenarios(selected, args.base_url, args.port)
    except RuntimeError as err:
        print(f"오류: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
