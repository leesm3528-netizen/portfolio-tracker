최종 갱신: 2026-10-21 / 갱신자: Claude Code (Opus)

## 현재 단계

4단계(MVP 구현) 진행 중. 사용자가 2026-10-21 4단계 진행을 승인했다. T4-01~T4-09 를 마쳤고 다음은 T4-10 이다. verify.mjs 는 옵션 없이 종료 코드 0 이어야 한다. 승인 대기 상태가 아니다(4단계 마지막 작업 T4-17 을 마치면 승인을 받는다).

## 완료한 작업

- T4-09 보유 현황 표: js/main.js `buildView` 에 `calcPositions`(실패면 throw) -> `buildHoldings` 를, js/ui.js 에 보유 현황 렌더(종목명 th scope=row, 보유수량 0 행의 평가 칸 "-", 현금 현재가 1, "현재가 미입력" `price-missing`, 표시값 부호로 `value-up`/`value-down`)와 내부 `formatWon`, `formatSignedWon`, `formatAvgCost`, `formatSignedPercent` 를, css/style.css 에 `value-up`, `value-down`, `price-missing` 을 추가했다. verify_ui.py 에 T4-09 시나리오 9개(C-02, C-11, C-04 #0~#1, C-10, C-14, C-15, C-03 #0/#2, R-06 순서, 빈 상태)를 추가했고 전체 통과 30 / 실패 0(T3-01 5, T3-02 4, T4-07 8, T4-08 4, T4-09 9). 표시값은 03 14절 표시값과 같다.
- T4-08 거래 삭제: js/ui.js 에 삭제 버튼(02 9.2 형식, aria-label "{날짜} {종목명} {구분} 거래 삭제"), `#transactions-body` click 위임과 삭제 뒤 포커스(같은 순번 행의 삭제 버튼, 없으면 `#transactions-heading`), `confirmAction` 을, js/main.js 에 `handlers.onDeleteTransaction`(C-01 확인 -> `deleteTransaction` -> 실패 VE-11/VE-24 는 `transactions` 영역 -> `prunePrices` -> `commit`)을, css/style.css 에 표 안 버튼과 호버를 추가했다. verify_ui.py 에 T4-08 시나리오 4개를 추가하고 T4-07 거래 행 기대값의 삭제 열을 "삭제" 로 고쳤다. 전체 통과 21 / 실패 0(T3-01 5, T3-02 4, T4-07 8, T4-08 4).
- T4-07 시작 흐름, 거래 입력, 거래 내역 표: js/main.js(`state`, `init`, `commit`, `buildView` 는 transactions 만, `render`, `handlers.onAddTransaction`)와 js/ui.js(`bindEvents`, `renderApp`, `resetTransactionForm`, `showMessage`, `clearMessage`, 내부 `MESSAGES` 35개, 치환 자리 표 `SLOTS`, `formatPrice`, `formatQuantity`)를 만들고, portfolio.js 에 `TRANSACTION_TYPE_LABELS`, index.html 에 main.js script 와 `#allocation-message` 의 `message-info` 클래스(04 10.9), css/style.css 에 `message-error`, `message-info`, tbody 행 호버를 추가했다. verify_ui.py 에 T4-07 시나리오 8개를 추가했고 전체 통과 17 / 실패 0(T3-01 5, T3-02 4, T4-07 8). `MESSAGES` 를 01 5.2~5.4 표와 기계 대조해 35개 일치. 숫자 입력칸의 badInput 이 빈칸으로 처리되는 문제를 M-32 로 추가하고 권장안("NaN" 을 넘김)으로 해소해 02 5.2, 7.3, 7.5 에 반영했다. 저장 성공 시 `#data-message` 를 지운다(04 10.8).
- T4-06 storage.js 저장 객체 검증과 읽기/쓰기: js/storage.js(`createEmptyData`, `parseData`, `loadData`, `saveData`. 내부 `STORAGE_KEY`, `DATA_VERSION`, `validateData`)를 만들고 js/rebalance.js 에 `createDefaultTargets`, `validateTargets`(범위와 자릿수 판정은 내부 함수 `targetValueError` 하나), js/portfolio.js 에 `prunePrices` 를 추가했다. `verify.mjs` 옵션 없이 통과 442 / 실패 0 / 건너뜀 0, 종료 코드 0. 임시 폴더 Node 확인에서 02 5.5 예시 통과와 `parseData` 확인 목록 1~9(VE-17, VD-01, VE-19 와 version 우선, VD-03 index 1 과 cause VE-04, VD-04, VE-25, VD-06, 합계 50 성공, prices 정리, VD-05)가 모두 기대대로. 05 에 정의된 화면 검증은 T4-07 이며, 확인용으로 localStorage 모의 객체를 써서 `loadData`(키 없음, 저장값, 손상 VE-21, 접근 예외 VE-21)와 `saveData`(성공, 예외 VE-20)도 확인했다. storage.js import 는 02 3절 표와 같고 DOM 접근 0 건.
- T4-05 transactions.js 거래 생성과 목록 검증: js/transactions.js(`createTransaction`, `validateTransactionFields`, `validateTransactionList`, `addTransaction`, `deleteTransaction`)를 만들고 js/portfolio.js 에 `parseNumber`, `TRANSACTION_TYPES`, `ASSET_CLASS_LABELS` 를 추가했다. `verify.mjs` 옵션 없이 통과 442 / 실패 0 / 건너뜀 0, 종료 코드 0. 임시 폴더 Node 확인 목록 1~9(VE-01 2026-02-30, 미래 날짜 허용, VE-02, VE-03, VE-22, VE-04, VE-05, 빈 수수료 0, VE-06, VE-08, 현금 수수료 1000 허용, VE-23 key, VE-26, error 가 { code, params })와 원래 배열 유지 모두 기대대로. 2.5 DOM 접근 검사 0 건, import 는 02 3절 표와 같다. VE-23 의 key 선택과 객체가 아닌 거래 항목 처리를 M-31 로 추가하고 권장안으로 해소했다(02 7.2 에 반영).
- T4-04 rebalance.js 리밸런싱 계산: js/rebalance.js 를 만들었다(내부 상수 `TARGET_TOTAL`, `sumTargets`, `calcRebalance`. portfolio.js 에서 `ASSET_CLASSES`, `calcTotalValue` 만 import). `verify.mjs R --allow-missing` 통과 167 / 실패 0 / 건너뜀 0, R-03 부동소수 합계 판정과 R-04 유지/매도 1 판정 PASS. 전체 `--allow-missing` 통과 395 / 실패 0 / 건너뜀 47(transactions.js 검사). 2.5 DOM 접근 검사 0 건, import 는 02 3절 표와 같다.
- T4-03 portfolio.js 자산군 합계와 비중: js/portfolio.js 에 `sumValueByAssetClass`, `calcTotalValue`, `buildAllocation` 을 추가했다. `verify.mjs R --allow-missing` 통과 85 / 실패 0 / 건너뜀 82(건너뜀은 모두 아직 없는 rebalance.calcRebalance 검사). R-04 비중 표시값 33.30, 33.30, 33.40, 0.00 과 R-05 총평가금액 0(빈 상태 포함) PASS. 2.5 DOM 접근 검사 0 건.
- T4-02 portfolio.js 보유 현황 행: js/portfolio.js 에 상수 `ASSET_CLASSES`, `CASH_NAME`, `CASH_PRICE` 와 `buildHoldings` 를 추가했다(03 7.1 현재가 순서, 보유수량 0 행 처리, 자산군 순서와 종목명 ko 정렬). `verify.mjs C --allow-missing` 통과 228 / 실패 0 / 건너뜀 47(건너뜀은 모두 transactions.js 검사), C-10, C-14 지정 실행 통과 20 / 실패 0 / 건너뜀 0. 2.5 DOM 접근 검사 0 건.
- T4-01 portfolio.js 거래 정렬과 종목 상태 재계산: js/portfolio.js 에 `sortTransactions`, `calcPositions` 를 만들었다(실패 Result 에 `violation`). `verify.mjs C --allow-missing` 통과 152 / 실패 0 / 건너뜀 123(건너뜀은 아직 없는 buildHoldings, transactions.js 검사), C-06, C-07 단계 실패(violation.index 1), C-12 의 calcPositions 검사 모두 PASS. 임시 폴더 Node 확인에서 C-07 전체 거래 결과 VE-25, violation.index 1, 원래 배열 유지. 2.5 DOM 접근 검사와 import 검사 0 건. README 상태 문구를 4단계 진행 중으로 고쳤다.

- T3-02 style.css 변수와 기본 스타일: css/style.css(04 의 변수 46개, 기본 요소, 폼, 버튼, 표, 빈 상태, 고지, 포커스 링, 640px/1024px 반응형), index.html 에 스타일시트 link 추가(M-28). verify_ui.py 에 T3-02 시나리오 4개(세 너비 가로 스크롤, 1024/1280px 두 열 top 일치, .num tabular-nums, Tab 이동 포커스 링 solid)를 추가했고 전체 통과 9 / 실패 0(T3-01 5, T3-02 4). px/hex grep 은 :root 와 미디어 쿼리 줄뿐, 금지 속성 grep 0 건, 정의 안 된 변수 사용 0 건. 360/768/1024/1280px 스크린샷을 눈으로 점검해 1024px 이상 자산군 선택칸 글자 잘림과 좁은 표 머리의 글자 단위 줄바꿈을 고쳤다. 아직 없는 요소의 스타일 범위를 M-30 으로 정하고 권장안으로 해소했다. README 상태 문구를 3단계 완료로 고쳤다.
- T3-01 index.html 영역 마크업: index.html(02 9.1~9.8 의 id 48개, 표 4개, 정적 문구, 고지). verify_ui.py 에 T3-01 시나리오 5개(id 개수, lang, label 연결, caption 과 scope, 정적 문구와 초기값)를 추가했고 통과 5 / 실패 0, 공통 확인(콘솔 오류 0, 외부 요청 0, 고지 문구) 통과. 스타일시트 link 를 T3-02 로 미루는 M-28, 정적 마크업의 초기 hidden 상태를 정한 M-29 를 추가하고 권장안으로 해소했다.
- T2-05 ui-verify 스킬 작성: skills/ui-verify/SKILL.md, scripts/verify_ui.py, scripts/fixtures.py. py_compile 통과, --list 시나리오 0 개 종료 코드 0, T9-99 와 모르는 옵션 종료 코드 1, 인자 없이 실행 시나리오 0 개 종료 코드 0, case_data("R-06") 키 4개와 거래 4건 필드 8개 확인. 저장소 밖 복사본에 임시 시나리오 4개와 임시 index.html 을 넣어 Playwright 실행 경로(서버 기동과 종료, fixture 주입과 새로고침 유지, 대화상자 기록, 콘솔 오류, 외부 요청, 너비, 문구 불일치, --base-url, playwright 없음 안내)를 시험해 정의대로 판정됨을 확인했다. 저장소에 __pycache__ 없음. R-02 목표 비중 선택을 M-27 로 추가했고 권장안(attempt 인자, 기본 "a")으로 해소.
- T2-04 verify.mjs 작성: skills/calc-rule-verify/scripts/verify.mjs. C-01~C-15, R-01~R-06 을 검사 442 개로 옮겼다. node --check 통과, js/ 없는 상태에서 옵션 없이 442 건 SKIP 종료 코드 1, --allow-missing 종료 코드 0, C-01 과 R 지정 동작 확인, 알 수 없는 인자(X-1, --foo, C-99) 종료 코드 1. 저장소 밖 임시 폴더에 03 공식대로 만든 모의 모듈과 스크립트 복사본으로 시험해 442 건 PASS, 일부러 틀린 구현 10 가지는 해당 사례에서 FAIL 또는 SKIP 으로 판정됨을 확인했다(모의 모듈은 커밋하지 않음). 거래 행 전사를 03 원문과 기계 대조해 일치.
- T2-03 calc-rule-verify 스킬 문서 작성: skills/calc-rule-verify/SKILL.md. 실행 명령과 옵션은 05 2.2 와 같다. 03 에 없는 사례 ID 도 알 수 없는 인자로 보고 종료 코드 1 로 정했다. 이모지 검사 0 건.
- T2-02 handoff-update 스킬 작성: skills/handoff-update/SKILL.md. 이 스킬 절차로 이 HANDOFF.md 를 갱신했다. 이모지 검사 0 건, "## " 제목 5개의 이름과 순서가 AGENTS.md 9절과 같다.
- T2-01 doc-writing-rules 스킬 작성: skills/doc-writing-rules/SKILL.md. 이 스킬로 기존 문서 9개를 점검해 05 E-05 의 "평가액" 을 "평가금액" 으로, CLAUDE.md 2절의 playwright 설치 상태를 실제와 맞게 고쳤다. 이모지 검사 10개 파일 0 건, docs 목차와 본문 제목 일치.
- T1-07 문서 간 불일치 해소: 2026-10-21 사용자 일괄 승인으로 M-01~M-26 과 01/02/03/04 의 모든 결정 항목을 권장안대로 확정하고 원본 문서에 반영했다. 결정 기록은 docs/05_작업지시서.md 3절. 03 에 C-15(현금 매수 수수료) 추가, 05 에 T2-05(ui-verify 스킬) 추가. 이모지 검사 0 건, 목차와 본문 제목 일치.
- T1-06 루트 지침 파일 작성: AGENTS.md, CLAUDE.md, HANDOFF.md, README.md(초안). 이모지 검사 4개 파일 0 건, CLAUDE.md 는 첫 줄 @AGENTS.md 이고 AGENTS.md 와 중복 규칙 없음.
- T1-05 작업지시서 작성: docs/05_작업지시서.md. 이모지 검사 0 건, 목차와 본문 제목 일치.
- T1-04 디자인가이드 작성: docs/04_디자인가이드.md. 이모지 검사 0 건, 목차와 본문 제목 일치.
- T1-03 계산규칙 작성: docs/03_계산규칙.md. 검증 사례 C-01~C-14, R-01~R-06. 이모지 검사 0 건, 목차와 본문 제목 일치.
- T1-02 설계문서 작성: docs/02_설계문서.md. 이모지 검사 0 건, 목차와 본문 제목 일치.
- T1-01 요구사항 정의서 작성: docs/01_요구사항.md. FR-01~FR-14, NFR-01~NFR-10. 이모지 검사 0 건, 목차와 본문 제목 일치.

## 다음 할 작업 (작업지시서 번호)

1. T4-10 현재가 입력

## 알려진 문제

1. 외부 스킬 doc-coauthoring, frontend-design, webapp-testing 이 설치되어 있지 않다. skill-creator 만 있다. 같은 원칙으로 진행한다(CLAUDE.md 2절). 화면 검증은 프로젝트 스킬 skills/ui-verify(T2-05)로 대신한다. 관련 작업: T3-01 이후 화면 작업.
2. 화면 검증 환경: 작성자 PC 에는 Python 3.14(`py`), playwright 1.64.0, Chromium 이 설치되어 있다(2026-10-21 확인). 다른 PC 에서는 `py -m pip install playwright`, `py -m playwright install chromium` 을 먼저 실행한다. Git Bash 에서 verify_ui.py 출력을 파이프로 받으면 한글이 깨지므로 `PYTHONUTF8=1` 을 붙인다(skills/ui-verify/SKILL.md 4.1). 관련 작업: T3-01 이후 화면 작업.
3. 객체 판정 식(`value !== null && typeof value === "object" && !Array.isArray(value)`)이 js/transactions.js(`validateTransactionFields`), js/rebalance.js(`validateTargets`), js/storage.js(내부 `isPlainObject`)에 한 번씩 있다. 02 7.1 에 공통 함수가 없어 각 모듈에 두었다. 공통 함수로 묶으려면 02 7.1 에 먼저 추가해야 하므로 T4-17 의 중복 코드 점검에서 판단한다. 재현: `grep -n "Array.isArray" js/*.js`. 관련 작업: T4-17.

## 다음 작업자에게 주의사항

1. 이전 작업의 대화 기록은 볼 수 없다. 이 파일, AGENTS.md, docs/, skills/ 만이 근거다. 사용자와 새로 정한 내용은 반드시 원본 문서에 적는다.
2. 1단계의 모든 결정은 확정되었다. 결정 내용은 docs/05_작업지시서.md 3절의 "원본" 열 위치에 있다. 구현할 때는 3절이 아니라 원본 문서를 읽는다. 새 불일치가 생기면 3.1 에 다음 번호(현재 M-33 부터) "미해결" 로 추가하고 사용자에게 묻는다. M-27~M-32 는 권장안대로 해소되었다.
3. 화면 메시지 문구의 원본은 docs/01_요구사항.md 5절 하나다. 계산과 검증 모듈은 문장을 만들지 않고 `{ code, params }` 만 반환한다(docs/02_설계문서.md 4.1, 11절).
4. index.html 은 데이터 0 건 상태의 정적 뼈대이고(05 3.1 M-29) ui.js 가 렌더 때 hidden 을 바꾼다. JS 가 붙이는 클래스 스타일은 그 클래스를 처음 쓰는 작업에서 css/style.css 에 추가한다(M-30). 화면 작업은 verify_ui.py 에 작업 ID 로 시나리오를 추가하고 이전 시나리오와 함께 실행한다. 메시지 문장은 ui.js 의 `MESSAGES` 와 치환 자리 표 `SLOTS` 로 만든다. VE-15 의 {합계} 자리는 `formatTargetSum` 을 만드는 T4-12 에서 `SLOTS` 에 추가한다. 숫자 입력칸 값은 ui.js 내부 `numberInputValue` 로 읽는다(M-32).
5. 결정 항목은 "03 D-01" 처럼 문서 번호를 붙여 부른다. 문서마다 D 번호가 따로 매겨져 있다.
6. 모든 문서에 이모지와 장식 기호를 쓰지 않는다. 화살표는 "->" 만 쓴다. 문체는 평서문 "~한다/~이다" 다. 화면 문구 인용만 "~합니다/~하세요" 다.
7. 02 7절 공개 이름 중 아직 앱 모듈 사용처가 없는 export 가 있다: `sumTargets`(T4-12), `parseData`(T4-15. 지금은 storage.js 안의 `loadData` 만 쓴다). 05 1.8 에 따라 허용되며 T4-17 시점에 사용처 없는 export 는 0 개여야 한다. `updatePrice` 는 T4-10, `parseTargetInput` 은 T4-12(rebalance.js 내부 `targetValueError` 를 같이 쓴다), `serializeData` 는 T4-14 에서 만든다.
8. 진행 상태는 `git log --oneline` 으로도 확인한다. 커밋 메시지는 작업 ID 로 시작한다.
