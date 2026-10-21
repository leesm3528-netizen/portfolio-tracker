// 모든 DOM 접근: 이벤트 등록, 폼 값 읽기, 표 렌더링, 메시지 문장, 숫자 표시 형식. 함수 형식은 docs/02_설계문서.md 7.5 다.
// 계산 공식과 입력 검증 규칙을 두지 않는다. portfolio.js 에서 상수만 import 한다(02 2절).

import { ASSET_CLASSES, ASSET_CLASS_LABELS, CASH_NAME, TRANSACTION_TYPE_LABELS } from "./portfolio.js";

// 01 5.2~5.4 의 메시지 문구(머리말 제외). 글자를 바꾸지 않는다(02 4.3).
const MESSAGES = {
  "VE-01": "날짜를 YYYY-MM-DD 형식의 실제 날짜로 입력하세요.",
  "VE-02": "종목명을 입력하세요.",
  "VE-03": "자산군을 선택하세요.",
  "VE-22": "매수 또는 매도를 선택하세요.",
  "VE-04": "수량은 1 이상의 정수로 입력하세요.",
  "VE-05": "가격은 0보다 큰 숫자로 입력하세요.",
  "VE-06": "수수료는 0 이상의 숫자로 입력하세요.",
  "VE-23": "거래 항목이 올바르지 않습니다({항목}).",
  "VE-26": "거래 id 가 올바르지 않습니다.",
  "VE-07": "'{종목명}'의 자산군은 {자산군}입니다. 같은 종목은 하나의 자산군만 가질 수 있습니다.",
  "VE-08": "현금 거래는 자산군을 현금으로, 가격을 1로 입력하세요.",
  "VE-09": "{날짜} 기준 '{종목명}'의 보유수량은 {보유수량}입니다. 그보다 많이 매도할 수 없습니다.",
  "VE-10": "이 거래를 추가하면 {날짜} '{종목명}' 매도가 보유수량을 초과합니다. 거래를 추가하지 않았습니다.",
  "VE-11": "이 거래를 삭제하면 {날짜} '{종목명}' 매도가 보유수량을 초과합니다. 거래를 삭제하지 않았습니다.",
  "VE-24": "삭제할 거래를 찾을 수 없습니다.",
  "VE-25": "{날짜} '{종목명}' 매도 수량({매도수량})이 그 시점 보유수량({보유수량})보다 많습니다.",
  "VE-12": "현재가는 0보다 큰 숫자로 입력하세요.",
  "VE-13": "목표 비중은 0 이상 100 이하의 숫자로 입력하세요.",
  "VE-14": "목표 비중은 소수 첫째 자리까지 입력할 수 있습니다.",
  "VE-15": "목표 비중 합계가 {합계}%입니다. 합계가 100%일 때 리밸런싱을 계산합니다.",
  "VE-16": "보유 중인 종목이 없어 리밸런싱을 계산할 수 없습니다.",
  "VE-17": "JSON 파일을 읽을 수 없습니다. 기존 데이터는 바뀌지 않았습니다.",
  "VE-18": "파일 형식이 올바르지 않습니다. {상세} 기존 데이터는 바뀌지 않았습니다.",
  "VE-19": "지원하지 않는 데이터 버전입니다(version: {값}). 기존 데이터는 바뀌지 않았습니다.",
  "VE-20": "브라우저 저장소에 저장하지 못했습니다. 새로고침하면 마지막 변경이 사라질 수 있으니 JSON 내보내기로 백업하세요.",
  "VE-21": "저장된 데이터를 읽을 수 없어 빈 상태로 시작합니다. 백업한 JSON 파일이 있으면 불러오기로 복구하세요.",
  "IN-04": "불러오기를 완료했습니다.",
  "C-01": "{날짜} {종목명} {구분} {수량} 거래를 삭제하시겠습니까?",
  "C-02": "현재 데이터(거래 {현재 건수}건)를 불러온 파일의 데이터(거래 {파일 건수}건)로 모두 교체합니다. 계속하시겠습니까?",
  "VD-01": "최상위 항목은 version, transactions, prices, targets 4개여야 합니다.",
  "VD-02": "transactions 는 배열이어야 합니다.",
  "VD-03": "transactions {순번}번째 항목: {원인}",
  "VD-04": "거래 id 가 중복됩니다({id}).",
  "VD-05": "prices 는 종목명마다 0보다 큰 숫자를 가진 객체여야 합니다.",
  "VD-06": "targets 는 stock, bond, cash, other 4개 항목이 0 이상 100 이하, 소수 첫째 자리까지인 숫자여야 합니다.",
};

// 04 13.1 머리말
const PREFIXES = { error: "오류: ", info: "안내: " };
const MESSAGE_CLASSES = { error: "message-error", info: "message-info" };

// 02 7.5 MessageArea -> 메시지 줄 id
const MESSAGE_AREAS = {
  transaction: "tx-message",
  transactions: "transactions-message",
  holdings: "holdings-message",
  targets: "targets-message",
  data: "data-message",
};

// 거래 내역 삭제 버튼(02 9.2)과 보유 현황 현재가 입력칸(02 9.3)
const DELETE_BUTTON = 'button[data-action="delete-transaction"]';
const PRICE_INPUT = 'input[data-action="set-price"]';

// 다시 그린 뒤 포커스를 되돌리는 영역(02 7.5)
const FOCUS_BODIES = ["holdings-body", "transactions-body"];

// 숫자 입력칸에 브라우저가 숫자로 해석하지 못한 글자가 있으면 value 가 빈 문자열이 된다.
// 빈칸(수수료 0, 현재가 미입력)과 구분하도록 숫자가 아닌 문자열을 넘긴다(05 3.1 M-32).
const BAD_NUMBER_INPUT = "NaN";

// 02 10절 표시 함수. 포매터는 모듈 로드 때 한 번 만든다. 부호는 절댓값을 형식화한 뒤 붙인다.
function numberFormat(options, signed = false) {
  const formatter = new Intl.NumberFormat("ko-KR", options);
  return (n) => {
    if (n === null) return "-";
    const s = formatter.format(Math.abs(n));
    if (!/[1-9]/.test(s)) return s;
    if (n < 0) return "-" + s;
    return signed && n > 0 ? "+" + s : s;
  };
}

const formatWon = numberFormat({ maximumFractionDigits: 0 });
const formatSignedWon = numberFormat({ maximumFractionDigits: 0 }, true);
const formatAvgCost = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatPrice = numberFormat({ minimumFractionDigits: 0, maximumFractionDigits: 2 });
const formatQuantity = numberFormat({ maximumFractionDigits: 0 });
const formatPercent = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatSignedPercent = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 }, true);
const formatTargetSum = numberFormat({ minimumFractionDigits: 1, maximumFractionDigits: 1 });

// 현재가 미입력 표시(01 FR-05 기준 3, 02 9.3)
const PRICE_MISSING = "현재가 미입력";

// 리밸런싱 구분 칸(01 FR-09 기준 2, 3). 매수와 매도는 거래 구분 표시 이름과 같다.
const REBALANCE_ACTION_LABELS = { ...TRANSACTION_TYPE_LABELS, hold: "유지" };

// 치환 자리 -> params 값의 표시(02 11절)
const SLOTS = {
  "날짜": (p) => p.date,
  "종목명": (p) => p.name,
  "자산군": (p) => ASSET_CLASS_LABELS[p.assetClass],
  "구분": (p) => TRANSACTION_TYPE_LABELS[p.type],
  "수량": (p) => formatQuantity(p.quantity),
  "매도수량": (p) => formatQuantity(p.quantity),
  "보유수량": (p) => formatQuantity(p.held),
  "항목": (p) => p.key,
  "id": (p) => p.id,
  "순번": (p) => String(p.index),
  "원인": (p) => messageText(p.cause),
  "상세": (p) => messageText(p.detail),
  "값": (p) => (p.value === undefined ? "없음" : JSON.stringify(p.value)),
  "현재 건수": (p) => formatQuantity(p.currentCount),
  "파일 건수": (p) => formatQuantity(p.fileCount),
  "합계": (p) => formatTargetSum(p.sum),
};

// Message 를 머리말 없는 문장으로 만든다(02 4.3).
function messageText(message) {
  return MESSAGES[message.code].replace(/\{([^}]+)\}/g, (_, slot) => SLOTS[slot](message.params));
}

function byId(id) {
  return document.getElementById(id);
}

function cell(tag, text, className = "") {
  const el = document.createElement(tag);
  el.textContent = text;
  if (className) el.className = className;
  return el;
}

// 부호 있는 표시값 칸. 색 클래스는 표시값의 부호로 정한다(02 9.9, 표시값 0 은 부호와 클래스 없음).
function signedCell(text) {
  const color = text.startsWith("+") ? " value-up" : text.startsWith("-") ? " value-down" : "";
  return cell("td", text, "num" + color);
}

function rowHeader(text) {
  const th = cell("th", text);
  th.scope = "row";
  return th;
}

// 목표 비중 입력칸은 "target-" + 자산군 키 규칙으로 찾는다(02 9.5).
function targetInput(assetClass) {
  return byId("target-" + assetClass);
}

function numberInputValue(input) {
  return input.validity.badInput ? BAD_NUMBER_INPUT : input.value;
}

// 브라우저 로컬 날짜 "YYYY-MM-DD". 폼 기본값과 내보내기 파일 이름에 같이 쓴다(02 7.5).
function todayString() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function readTransactionForm() {
  return {
    date: byId("tx-date").value,
    name: byId("tx-name").value,
    assetClass: byId("tx-asset-class").value,
    type: byId("tx-type").value,
    quantity: numberInputValue(byId("tx-quantity")),
    price: numberInputValue(byId("tx-price")),
    fee: numberInputValue(byId("tx-fee")),
  };
}

// 이벤트를 한 번 등록한다. 날짜 입력칸의 처음 값(오늘)도 여기서 넣는다(02 9.1).
export function bindEvents(handlers) {
  byId("tx-date").value = todayString();
  byId("transaction-form").addEventListener("submit", (event) => {
    event.preventDefault();
    handlers.onAddTransaction(readTransactionForm());
  });
  // 삭제했으면 같은 순번 행(삭제한 행의 다음 행)의 삭제 버튼, 없으면 거래 내역 제목으로 포커스를 옮긴다(02 7.5).
  const body = byId("transactions-body");
  body.addEventListener("click", (event) => {
    const button = event.target.closest(DELETE_BUTTON);
    if (!button) return;
    const index = [...body.querySelectorAll(DELETE_BUTTON)].indexOf(button);
    if (!handlers.onDeleteTransaction(button.dataset.id)) return;
    (body.querySelectorAll(DELETE_BUTTON)[index] ?? byId("transactions-heading")).focus();
  });
  // 현재가는 입력칸을 벗어나거나 Enter 일 때(change) 반영한다(02 8절). change 는 Tab 의 포커스 이동이
  // 끝나기 전에 오므로, 처리를 다음 작업으로 미뤄 다음 입력칸에 포커스가 간 뒤 다시 그린다(05 3.1 M-33).
  byId("holdings-body").addEventListener("change", (event) => {
    const input = event.target.closest(PRICE_INPUT);
    if (!input) return;
    const { name } = input.dataset;
    const raw = numberInputValue(input);
    setTimeout(() => handlers.onPriceChange(name, raw));
  });
  byId("export-button").addEventListener("click", () => handlers.onExport());
  // 보이는 불러오기 버튼이 숨겨진 파일 선택칸을 연다. 같은 파일을 다시 고를 수 있도록 값을 비운다(02 8절).
  const fileInput = byId("import-file");
  byId("import-button").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    const [file] = fileInput.files;
    fileInput.value = "";
    if (file) handlers.onImportFile(file);
  });
  // 목표 비중은 입력할 때마다(input) 반영한다. 입력칸 값은 다시 쓰지 않는다(02 8절, 7.5).
  for (const assetClass of ASSET_CLASSES) {
    const input = targetInput(assetClass);
    input.addEventListener("input", () => handlers.onTargetInput(assetClass, numberInputValue(input)));
  }
}

// 초기화와 불러오기 직후에만 호출한다(02 7.5).
export function setTargetInputs(targets) {
  for (const assetClass of ASSET_CLASSES) targetInput(assetClass).value = String(targets[assetClass]);
}

function deleteButton(tx) {
  const button = cell("button", "삭제");
  button.type = "button";
  button.dataset.action = "delete-transaction";
  button.dataset.id = tx.id;
  button.setAttribute("aria-label", `${tx.date} ${tx.name} ${TRANSACTION_TYPE_LABELS[tx.type]} 거래 삭제`);
  const td = document.createElement("td");
  td.append(button);
  return td;
}

function renderTransactions(transactions) {
  const rows = transactions.map((tx) => {
    const tr = document.createElement("tr");
    tr.append(
      rowHeader(tx.date),
      cell("td", tx.name),
      cell("td", ASSET_CLASS_LABELS[tx.assetClass]),
      cell("td", TRANSACTION_TYPE_LABELS[tx.type]),
      cell("td", formatQuantity(tx.quantity), "num"),
      cell("td", formatPrice(tx.price), "num"),
      cell("td", formatPrice(tx.fee), "num"),
      deleteButton(tx),
    );
    return tr;
  });
  byId("transactions-body").replaceChildren(...rows);
  byId("transactions-table").hidden = transactions.length === 0;
  byId("transactions-empty").hidden = transactions.length > 0;
}

// 현재가 칸: 현금은 입력칸 없이 1, 그 밖에는 저장된 현재가(없으면 빈칸)의 입력칸과 "현재가 미입력" 표시(02 9.3).
function priceCell(row) {
  if (row.name === CASH_NAME) return cell("td", formatPrice(row.price), "num");
  const input = document.createElement("input");
  input.type = "number";
  input.step = "any";
  input.min = "0";
  input.inputMode = "decimal";
  input.dataset.action = "set-price";
  input.dataset.name = row.name;
  input.setAttribute("aria-label", `${row.name} 현재가`);
  input.value = row.priceMissing ? "" : String(row.price);
  const td = cell("td", "", "num");
  td.append(input);
  if (row.priceMissing) td.append(cell("span", PRICE_MISSING, "price-missing"));
  return td;
}

// 보유수량 0 행은 현재가, 평가금액, 평가손익, 수익률 칸을 "-" 로 둔다(02 6.2).
function renderHoldings(holdings) {
  const rows = holdings.map((row) => {
    const tr = document.createElement("tr");
    tr.append(rowHeader(row.name), cell("td", ASSET_CLASS_LABELS[row.assetClass]),
      cell("td", formatQuantity(row.quantity), "num"), cell("td", formatAvgCost(row.avgCost), "num"));
    if (row.quantity === 0) {
      tr.append(...["-", "-", "-", "-"].map((text) => cell("td", text, "num")));
    } else {
      tr.append(priceCell(row), cell("td", formatWon(row.marketValue), "num"),
        signedCell(formatSignedWon(row.unrealizedPnl)), signedCell(formatSignedPercent(row.returnRate)));
    }
    tr.append(signedCell(formatSignedWon(row.realizedPnl)));
    return tr;
  });
  byId("holdings-body").replaceChildren(...rows);
  byId("holdings-table").hidden = holdings.length === 0;
  byId("holdings-empty").hidden = holdings.length > 0;
}

// 자산 비중: 4개 자산군을 항상 표시한다. 총평가금액이 0 이면 비중은 "-" 이고 IN-03(정적 문구)을 보인다(02 9.4).
// 이 표에는 수익/손실 색을 쓰지 않는다(04 9.2).
function renderAllocation(allocation) {
  const rows = allocation.rows.map((row) => {
    const tr = document.createElement("tr");
    tr.append(rowHeader(ASSET_CLASS_LABELS[row.assetClass]), cell("td", formatWon(row.value), "num"),
      cell("td", formatPercent(row.weight), "num"));
    return tr;
  });
  byId("allocation-body").replaceChildren(...rows);
  byId("allocation-total").textContent = formatWon(allocation.totalValue);
  byId("allocation-message").hidden = allocation.totalValue !== 0;
}

// 리밸런싱 결과(02 9.6). 실패(VE-15, VE-16)면 표를 숨기고 안내로 보인다. 금액은 부호 없는 tradeAmount 이고
// 이 표에는 색 클래스를 쓰지 않는다(04 8.5, 9.2). 목표 비중은 소수 첫째 자리 고정이다(05 3.1 M-35).
function renderRebalance(rebalance) {
  const rows = rebalance.ok ? rebalance.value.rows.map((row) => {
    const tr = document.createElement("tr");
    tr.append(rowHeader(ASSET_CLASS_LABELS[row.assetClass]), cell("td", formatWon(row.currentValue), "num"),
      cell("td", formatTargetSum(row.targetWeight), "num"), cell("td", formatWon(row.targetValue), "num"),
      cell("td", formatWon(row.tradeAmount), "num"), cell("td", REBALANCE_ACTION_LABELS[row.action]));
    return tr;
  }) : [];
  byId("rebalance-body").replaceChildren(...rows);
  byId("rebalance-table").hidden = !rebalance.ok;
  const message = byId("rebalance-message");
  if (rebalance.ok) clearMessageLine(message);
  else writeMessageLine(message, rebalance.error, "info");
  message.hidden = rebalance.ok;
}

// 포커스가 표 안 요소에 있으면 그 data-action 과 data-name(거래 행은 data-id)을 기억한다(02 7.5).
function focusedControl() {
  const el = document.activeElement;
  if (!el || !FOCUS_BODIES.some((id) => byId(id).contains(el))) return null;
  return { action: el.dataset.action, key: el.dataset.name ?? el.dataset.id };
}

function restoreFocus(saved) {
  if (!saved) return;
  const match = FOCUS_BODIES.flatMap((id) => [...byId(id).querySelectorAll("[data-action]")])
    .find((el) => el.dataset.action === saved.action && (el.dataset.name ?? el.dataset.id) === saved.key);
  if (match) match.focus();
}

export function renderApp(view) {
  const saved = focusedControl();
  renderTransactions(view.transactions);
  renderHoldings(view.holdings);
  renderAllocation(view.allocation);
  byId("target-sum").textContent = formatTargetSum(view.targetSum) + "%";
  renderRebalance(view.rebalance);
  restoreFocus(saved);
}

// 날짜, 자산군, 구분은 유지하고 나머지를 비운 뒤 날짜 입력칸으로 포커스를 옮긴다(02 7.5).
export function resetTransactionForm() {
  for (const id of ["tx-name", "tx-quantity", "tx-price", "tx-fee"]) byId(id).value = "";
  byId("tx-date").focus();
}

// 메시지 줄에 머리말을 붙인 문장과 상태 클래스를 넣는다(02 4.3, 04 10.8, 10.9).
function writeMessageLine(el, message, kind) {
  el.textContent = PREFIXES[kind] + messageText(message);
  el.className = MESSAGE_CLASSES[kind];
}

function clearMessageLine(el) {
  el.textContent = "";
  el.removeAttribute("class");
}

export function showMessage(area, message, kind) {
  writeMessageLine(byId(MESSAGE_AREAS[area]), message, kind);
}

// 내보내기 파일을 브라우저 안에서 만들어 내려받게 한다. 서버 요청이 없다(02 5.6, 01 FR-11).
export function downloadJson(text) {
  const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `portfolio-tracker-${todayString()}.json`;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url)); // 내려받기가 시작된 뒤 해제한다
}

// 머리말 없는 확인 문구(C-01, C-02)로 확인 창을 띄운다(02 4.3).
export function confirmAction(message) {
  return window.confirm(messageText(message));
}

export function clearMessage(area) {
  clearMessageLine(byId(MESSAGE_AREAS[area]));
}
