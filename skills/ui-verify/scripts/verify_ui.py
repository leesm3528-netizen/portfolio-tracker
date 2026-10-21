"""화면 검증 스크립트 (Python Playwright).

실행(프로젝트 루트):
    py skills/ui-verify/scripts/verify_ui.py [작업 ID ...] [--list] [--base-url URL] [--port 8000]

세부 동작의 원본: docs/05_작업지시서.md 2.3, T2-05. 절차와 시나리오 추가 방법: skills/ui-verify/SKILL.md
Python 3 표준 라이브러리와 playwright.sync_api 만 쓴다. playwright 는 시나리오를 실행할 때만 불러온다.
"""

import argparse
import json
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
    actual = run.page.locator("#allocation-message").text_content().strip()  # hidden 이므로 text_content
    if actual != IN_03:
        raise AssertionError(f"#allocation-message 텍스트: 기대 {IN_03!r}, 실제 {actual!r}")
    if not run.page.locator("#allocation-message").is_hidden():
        raise AssertionError("#allocation-message 가 hidden 이 아니다")
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
