// 모든 DOM 접근: 이벤트 등록, 폼 값 읽기, 표 렌더링, 메시지 문장, 숫자 표시 형식. 함수 형식은 docs/02_설계문서.md 7.5 다.
// 계산 공식과 입력 검증 규칙을 두지 않는다. portfolio.js 에서 상수만 import 한다(02 2절).

import { ASSET_CLASS_LABELS, CASH_NAME, TRANSACTION_TYPE_LABELS } from "./portfolio.js";

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

// 거래 내역 삭제 버튼(02 9.2)
const DELETE_BUTTON = 'button[data-action="delete-transaction"]';

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
const formatSignedPercent = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 }, true);

// 현재가 미입력 표시(01 FR-05 기준 3, 02 9.3)
const PRICE_MISSING = "현재가 미입력";

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

// 현재가 칸: 현금은 1, 그 밖에는 저장된 현재가. 미입력이면 "현재가 미입력" 을 표시한다(02 9.3).
function priceCell(row) {
  if (row.name === CASH_NAME || !row.priceMissing) return cell("td", formatPrice(row.price), "num");
  const td = cell("td", "", "num");
  td.append(cell("span", PRICE_MISSING, "price-missing"));
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

export function renderApp(view) {
  renderTransactions(view.transactions);
  renderHoldings(view.holdings);
}

// 날짜, 자산군, 구분은 유지하고 나머지를 비운 뒤 날짜 입력칸으로 포커스를 옮긴다(02 7.5).
export function resetTransactionForm() {
  for (const id of ["tx-name", "tx-quantity", "tx-price", "tx-fee"]) byId(id).value = "";
  byId("tx-date").focus();
}

export function showMessage(area, message, kind) {
  const el = byId(MESSAGE_AREAS[area]);
  el.textContent = PREFIXES[kind] + messageText(message);
  el.className = MESSAGE_CLASSES[kind];
}

// 머리말 없는 확인 문구(C-01, C-02)로 확인 창을 띄운다(02 4.3).
export function confirmAction(message) {
  return window.confirm(messageText(message));
}

export function clearMessage(area) {
  const el = byId(MESSAGE_AREAS[area]);
  el.textContent = "";
  el.removeAttribute("class");
}
