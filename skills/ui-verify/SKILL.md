---
name: ui-verify
description: index.html, css/style.css, js/ui.js, js/main.js 를 바꾸는 화면 작업(T3-01 이후)을 검증할 때, 4단계 끝 점검 때, 배포 주소를 확인할 때 Python Playwright 스크립트 verify_ui.py 로 작업 ID 별 화면 시나리오와 공통 확인(콘솔 오류, 외부 요청, 고지 문구)을 실행하는 절차다.
---

# ui-verify

## 1. 목적

- 화면 검증 시나리오를 저장소에 스크립트로 남겨, 세션이 바뀐 다음 작업자도 같은 검증을 같은 명령으로 다시 실행할 수 있게 한다(docs/05_작업지시서.md 3.1 M-23).
- 스크립트는 scripts/verify_ui.py, 미리 넣는 데이터는 scripts/fixtures.py 다. 세부 동작의 원본은 docs/05_작업지시서.md 2.3 과 T2-05 다.
- 확인용 정적 서버는 검증 용도로만 쓴다. 앱 기능은 서버에 의존하지 않는다(docs/01_요구사항.md 6.2).

## 2. 트리거 상황

- 화면 작업(T3-01 이후 index.html, css/style.css, js/ui.js, js/main.js 를 바꾸는 작업)의 검증. 작업마다 자기 시나리오를 추가하고 전체를 다시 실행한다.
- 4단계 끝 점검(T4-16, T4-17)과 단계 끝 보고 전.
- 배포 주소 확인(T5-03). `--base-url` 로 GitHub Pages 주소를 검사한다.

## 3. 절차

1. 준비(한 번만). playwright 가 없으면 스크립트가 아래 두 줄을 출력하고 종료 코드 1 로 끝난다.

   ```
   py -m pip install playwright
   py -m playwright install chromium
   ```

   `py` 는 Windows Python 런처다. 없는 환경은 `python3` 으로 바꿔 쓴다.
2. 작업 항목의 "검증 방법" 시나리오를 4.3 방법으로 verify_ui.py 의 `SCENARIOS` 에 그 작업 ID 로 추가한다. 요소는 docs/02_설계문서.md 9절의 id 로 찾고, 기대 문구는 docs/01_요구사항.md 5절 문구(머리말은 docs/04_디자인가이드.md 13.1)를 그대로 쓴다. 이전 작업의 시나리오는 지우지 않는다.
3. 프로젝트 루트에서 그 작업 ID 로 실행하고, 이어서 인자 없이 전체를 실행해 회귀를 확인한다(4.1).
4. 실패한 시나리오는 상세 열을 보고 화면 코드를 고친 뒤 다시 실행한다. 화면이 바뀌어 이전 시나리오의 기대값이 달라졌으면 문서 근거를 확인하고 그 작업에서 고친다.
5. 결과를 시나리오별 통과/실패로 HANDOFF.md 완료한 작업 줄에 요약한다(skills/handoff-update).
6. 스크린샷과 내려받은 파일은 스크립트가 `tempfile` 임시 폴더에만 저장하고 끝나면 지운다. 저장소에 생성물이 남지 않았는지 `git status --short` 로 확인한다.

## 4. 산출물

### 4.1 실행 명령

프로젝트 루트에서 실행한다(docs/05_작업지시서.md 2.3).

```
py skills/ui-verify/scripts/verify_ui.py T4-07
py skills/ui-verify/scripts/verify_ui.py
py skills/ui-verify/scripts/verify_ui.py --list
py skills/ui-verify/scripts/verify_ui.py --base-url https://{사용자 이름}.github.io/{저장소 이름}/
```

| 인자 | 의미 |
|---|---|
| 작업 ID(여러 개 가능) | 그 작업의 시나리오만 실행한다 |
| 없음 | 등록된 모든 시나리오를 실행한다. 등록된 시나리오가 0 개면 playwright 없이 `통과 0 / 실패 0` 을 출력하고 종료 코드 0 이다 |
| `--list` | 등록된 작업 ID 와 시나리오 이름만 출력한다. playwright 없이 동작한다 |
| `--base-url URL` | 서버를 띄우지 않고 그 주소를 검사한다. 외부 요청 판정의 허용 출처는 그 주소의 출처다 |
| `--port N` | 확인용 정적 서버 포트. 기본값 8000 |
| 그 밖의 인자, 등록되지 않은 작업 ID | 오류를 출력하고 종료 코드 1 |

- `--base-url` 이 없으면 스크립트가 프로젝트 루트에서 `{python} -m http.server {port} --bind 127.0.0.1` 을 띄우고 `http://localhost:{port}/` 를 검사한 뒤, 예외가 나도 서버를 종료한다. 서버를 따로 띄우지 않는다.
- 모든 시나리오 끝에 공통으로 확인한다: 콘솔 오류(console error, pageerror) 0 건, 검사 대상 출처 밖 요청 0 건(01 NFR-07, data:, blob:, about: 은 제외), `#disclaimer` 문구가 01 8절과 같음.
- 출력은 시나리오마다 `작업 | 시나리오 | 결과 | 상세` 한 줄이고 마지막 줄이 `통과 {n} / 실패 {n}` 이다. 종료 코드는 실패 0 이면 0, 아니면 1 이다.
- Git Bash 에서 파이프로 받은 출력의 한글이 깨지면 `PYTHONUTF8=1` 을 붙여 실행한다.

### 4.2 도우미 함수

시나리오 함수는 `Run` 객체 하나를 받는다.

| 이름 | 하는 일 |
|---|---|
| `run.page` | Playwright Page. 클릭, 입력 등은 이것으로 한다 |
| `run.open(path="")` | 검사 주소를 연다 |
| `run.open_with_data(data, path="")` | 저장 객체를 localStorage 키 `portfolio-tracker:v1` 에 `add_init_script` 로 넣고 연다. 새로고침 때는 다시 넣지 않는다 |
| `run.expect_text(selector, expected)` | 요소 텍스트(앞뒤 공백 제거)가 기대 문구와 같은지 확인한다 |
| `run.dialog_action` | 다음 확인 대화상자를 `"accept"`(기본) 또는 `"dismiss"` 로 처리한다 |
| `run.dialogs`, `run.expect_dialog(expected)` | 대화상자 문구 기록과 확인(마지막 대화상자 기준) |
| `run.check_widths()` | 360, 768, 1280px 에서 `document.documentElement.scrollWidth <= window.innerWidth` 를 확인한다 |
| `run.screenshot(name)`, `run.save_download(download)` | 임시 폴더에 저장하고 경로를 반환한다 |
| `fixtures.case_data(case_id)` | 03 14절 사례를 02 5.5 저장 객체로 반환한다. R-02 는 목표 비중 시도 a, b 를 `attempt` 인자로 고른다(기본 "a", 05 3.1 M-27) |

시나리오는 실패하면 `AssertionError` 를 던진다. 다른 예외도 실패로 기록하고 다음 시나리오를 계속한다. 시나리오마다 새 브라우저 컨텍스트를 쓰므로 localStorage 는 비어 있는 상태에서 시작한다.

### 4.3 시나리오 추가 예시

아래는 형식을 보이는 예시다. 실제 기대값은 각 작업 항목의 검증 방법과 01, 02 원문에서 가져온다. 함수는 `SCENARIOS = {}` 아래에 두고, 등록은 작업 ID 를 키로 (시나리오 이름, 함수) 목록을 넣는다. 같은 작업에 시나리오가 여러 개면 목록에 이어 붙인다.

```python
def t4_07_empty_state(run):
    run.open()
    run.expect_text("#transactions-empty", "입력된 거래가 없습니다.")


def t4_07_add_from_fixture(run):
    run.open_with_data(fixtures.case_data("C-01"))
    rows = run.page.locator("#transactions-body tr")
    if rows.count() != 3:
        raise AssertionError(f"거래 행 수: 기대 3, 실제 {rows.count()}")


SCENARIOS["T4-07"] = [
    ("빈 상태 문구", t4_07_empty_state),
    ("C-01 거래 3건 표시", t4_07_add_from_fixture),
]
```

### 4.4 문법 확인과 생성물

```
py -m py_compile skills/ui-verify/scripts/verify_ui.py skills/ui-verify/scripts/fixtures.py
```

- py_compile 과 `import fixtures` 를 쓰는 `py -c` 확인은 scripts/__pycache__/ 를 만든다. 확인 뒤 지우거나, 저장소 밖을 가리키는 `PYTHONPYCACHEPREFIX` 를 설정해 실행한다. __pycache__ 는 커밋하지 않는다.
- verify_ui.py 자체는 실행 중 `sys.dont_write_bytecode` 를 켜서 저장소 안에 파일을 쓰지 않는다.
