// localStorage 읽기/쓰기와 저장 객체 검증. 형식은 docs/02_설계문서.md 5.5, 5.7, 함수는 7.4 이다.
// DOM 에 접근하지 않는다. 실패는 { code, params } 만 담고 문장을 만들지 않는다.

import { validateTransactionFields, validateTransactionList } from "./transactions.js";
import { createDefaultTargets, validateTargets } from "./rebalance.js";
import { prunePrices } from "./portfolio.js";

const STORAGE_KEY = "portfolio-tracker:v1";
const DATA_VERSION = 1;
const DATA_KEYS = ["version", "transactions", "prices", "targets"];

function fail(code, params = {}) {
  return { ok: false, error: { code, params } };
}

// VE-18 의 {상세}에 하위 Message 를 넣는다(02 11절).
function invalidFormat(detail) {
  return fail("VE-18", { detail });
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function createEmptyData() {
  return { version: DATA_VERSION, transactions: [], prices: {}, targets: createDefaultTargets() };
}

// 02 5.7 의 2~10번 순서로 검사한다. version 검사가 키 집합 검사보다 먼저다.
function validateData(value) {
  if (!isPlainObject(value)) return invalidFormat({ code: "VD-01", params: {} });
  if (value.version !== DATA_VERSION) return fail("VE-19", { value: value.version });
  const keys = Object.keys(value);
  if (keys.length !== DATA_KEYS.length || !DATA_KEYS.every((key) => keys.includes(key))) {
    return invalidFormat({ code: "VD-01", params: {} });
  }
  const { transactions, prices, targets } = value;
  if (!Array.isArray(transactions)) return invalidFormat({ code: "VD-02", params: {} });
  for (let i = 0; i < transactions.length; i += 1) {
    const result = validateTransactionFields(transactions[i]);
    if (!result.ok) return invalidFormat({ code: "VD-03", params: { index: i + 1, cause: result.error } });
  }
  const ids = new Set();
  for (const tx of transactions) {
    if (ids.has(tx.id)) return invalidFormat({ code: "VD-04", params: { id: tx.id } });
    ids.add(tx.id);
  }
  const list = validateTransactionList(transactions);
  if (!list.ok) return invalidFormat(list.error);
  if (!isPlainObject(prices) || !Object.values(prices).every((price) => Number.isFinite(price) && price > 0)) {
    return invalidFormat({ code: "VD-05", params: {} });
  }
  const checkedTargets = validateTargets(targets);
  if (!checkedTargets.ok) return invalidFormat(checkedTargets.error);
  return { ok: true, value: { version: DATA_VERSION, transactions, prices: prunePrices(prices, transactions), targets } };
}

// 내보내기 파일 내용(02 5.6). 저장 객체와 같은 형식이고 들여쓰기 2칸이다.
export function serializeData(data) {
  return JSON.stringify(data, null, 2);
}

export function parseData(text) {
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    return fail("VE-17");
  }
  return validateData(value);
}

// 키가 없으면 빈 데이터. 검증 실패와 접근 예외는 원인과 관계없이 VE-21 이다(02 5.7).
export function loadData() {
  let text;
  try {
    text = localStorage.getItem(STORAGE_KEY);
  } catch {
    return fail("VE-21");
  }
  if (text === null) return { ok: true, value: createEmptyData() };
  const result = parseData(text);
  return result.ok ? result : fail("VE-21");
}

export function saveData(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    return fail("VE-20");
  }
  return { ok: true, value: null };
}
