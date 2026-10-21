@AGENTS.md

# CLAUDE.md

이 파일은 Claude Code 전용 보충 내용만 둔다. 공통 규칙의 원본은 위에서 불러온 AGENTS.md 이며 여기서 반복하지 않는다.

## 1. 프로젝트 스킬 사용법

- 이 저장소의 프로젝트 전용 스킬은 skills/ 에 있다. .claude/skills/ 가 아니므로 Claude Code 가 자동으로 인식하지 않는다.
- 작업에 해당하는 skills/{스킬 이름}/SKILL.md 를 Read 도구로 직접 읽고 그 절차를 따른다. Skill 도구로 호출하지 않는다.
- 어떤 작업에 어떤 스킬을 읽는지는 AGENTS.md 2절을 따른다.

## 2. 외부 스킬과 설치 상태

2026-10-21 기준 상태다. 세션마다 사용 가능한 스킬 목록을 확인하고 달라졌으면 이 표와 HANDOFF.md 를 고친다. 화면 검증에 필요한 Python 패키지 playwright 는 아직 설치되어 있지 않다(설치 명령은 docs/05_작업지시서.md 2.3).

| 스킬 | 쓰는 곳 | 상태 | 설치되어 있지 않을 때 |
|---|---|---|---|
| doc-coauthoring | 문서 작성과 수정 | 설치 안 됨 | skills/doc-writing-rules 절차와 docs 머리말 형식으로 직접 작성한다 |
| frontend-design | index.html, css/style.css, ui.js 화면 작업 | 설치 안 됨 | docs/04_디자인가이드.md 의 변수, 컴포넌트, 금지 요소 규칙을 그대로 따른다 |
| webapp-testing | 화면 기능 확인 | 설치 안 됨 | 프로젝트 스킬 skills/ui-verify(T2-05)의 verify_ui.py 를 쓴다. 그 전에는 docs/05_작업지시서.md 2.3 을 따른다 |
| skill-creator | skills/ 의 SKILL.md 작성 | 설치됨 | - |

외부 스킬이 설치되어 있든 아니든 결과물의 기준은 같다. 외부 스킬의 일반 권장이 이 프로젝트 문서와 다르면 프로젝트 문서를 따른다.

## 3. 세션 한도 대비

- 세션이 언제 끊길지 모르므로 HANDOFF.md 를 작업 단위마다 갱신한다. 여러 작업을 끝낸 뒤 한꺼번에 갱신하지 않는다.
- 긴 작업 중간에 멈춰야 하면 커밋하지 않은 변경 파일과 남은 단계를 HANDOFF.md 에 먼저 적는다.
- 다음 세션의 Claude 는 이전 대화를 볼 수 없다. 대화 중에 사용자와 정한 내용은 해당 원본 문서나 HANDOFF.md 에 적어야만 남는다.

## 4. Claude Code 동작 주의

- git 커밋 시 Claude Code 가 기본으로 붙이는 Co-Authored-By 줄과 생성 표시 줄을 붙이지 않는다. 메시지는 `git commit -m "{작업 ID} {한 일}"` 처럼 한 줄로 지정한다.
- 서브에이전트에게 작업을 맡길 때도 AGENTS.md 와 HANDOFF.md 를 먼저 읽도록 지시한다.
- 화면 검증은 `py skills/ui-verify/scripts/verify_ui.py {작업 ID}` 로 실행한다. 스크립트가 정적 서버를 띄우고 끝나면 종료하므로 서버를 따로 띄우지 않는다. 손으로 화면을 보려고 `py -m http.server 8000` 을 띄웠다면 백그라운드로 실행하고 확인이 끝나면 종료한다.
- 화면 검증 스크립트는 skills/ui-verify/scripts/ 에 커밋한다. 스크린샷과 임시 파일만 저장소 밖 임시 폴더에 둔다.
