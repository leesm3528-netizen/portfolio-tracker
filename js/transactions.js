// 거래 생성, 거래 목록 검증, 추가와 삭제. 함수 형식은 docs/02_설계문서.md 7.2, 메시지 ID 는 11절이다.
// 순수 함수이며 portfolio.js 만 import 한다. 실패는 { code, params } 만 담고 문장을 만들지 않는다.

import { ASSET_CLASSES, CASH_NAME, CASH_PRICE, TRANSACTION_TYPES, calcPositions, parseNumber } from "./portfolio.js";

const FIELDS = ["id", "date", "name", "assetClass", "type", "quantity", "price", "fee"];

function fail(code, params = {}) {
  return { ok: false, error: { code, params } };
}

// "YYYY-MM-DD" 형식이고 실제 존재하는 날짜인지 본다. 날짜 범위(미래 날짜)는 검사하지 않는다(01 5.2).
function isValidDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (month < 1 || month > 12) return false;
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const daysInMonth = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
  return day >= 1 && day <= daysInMonth;
}

export function createTransaction(input) {
  return validateTransactionFields({
    id: crypto.randomUUID(),
    date: input.date,
    name: input.name.trim(),
    assetClass: input.assetClass,
    type: input.type,
    quantity: parseNumber(input.quantity),
    price: parseNumber(input.price),
    fee: input.fee.trim() === "" ? 0 : parseNumber(input.fee),
  });
}

// 거래 한 건의 필드 검사. 순서는 01 5.1(VE-23, VE-26, VE-01, VE-02, VE-03, VE-22, VE-04, VE-05, VE-06, VE-08)이다.
// 객체가 아닌 값은 키가 없는 객체로 본다(05 3.1 M-31).
export function validateTransactionFields(value) {
  const isObject = value !== null && typeof value === "object" && !Array.isArray(value);
  const keys = isObject ? Object.keys(value) : [];
  const extraKey = keys.find((key) => !FIELDS.includes(key));
  if (extraKey !== undefined) return fail("VE-23", { key: extraKey });
  const missingKey = FIELDS.find((key) => !keys.includes(key));
  if (missingKey !== undefined) return fail("VE-23", { key: missingKey });

  const { id, date, name, assetClass, type, quantity, price, fee } = value;
  if (typeof id !== "string" || id === "") return fail("VE-26");
  if (!isValidDate(date)) return fail("VE-01");
  if (typeof name !== "string" || name.trim() === "") return fail("VE-02");
  if (!ASSET_CLASSES.includes(assetClass)) return fail("VE-03");
  if (!TRANSACTION_TYPES.includes(type)) return fail("VE-22");
  if (!Number.isSafeInteger(quantity) || quantity < 1) return fail("VE-04");
  if (!Number.isFinite(price) || price <= 0) return fail("VE-05");
  if (!Number.isFinite(fee) || fee < 0) return fail("VE-06");
  if (name === CASH_NAME && (assetClass !== "cash" || price !== CASH_PRICE)) return fail("VE-08");
  return { ok: true, value };
}

// 자산군 일관성(VE-07) 다음 초과 매도(calcPositions 의 VE-25 와 violation 그대로)를 검사한다(03 9절).
export function validateTransactionList(transactions) {
  const classByName = new Map();
  for (const tx of transactions) {
    const existing = classByName.get(tx.name);
    if (existing === undefined) classByName.set(tx.name, tx.assetClass);
    else if (existing !== tx.assetClass) return fail("VE-07", { name: tx.name, assetClass: existing });
  }
  const positions = calcPositions(transactions);
  return positions.ok ? { ok: true, value: transactions } : positions;
}

export function addTransaction(transactions, tx) {
  const result = validateTransactionList([...transactions, tx]);
  if (result.ok || !result.violation) return result;
  const { index, date, name, held } = result.violation;
  return index === transactions.length ? fail("VE-09", { date, name, held }) : fail("VE-10", { date, name });
}

export function deleteTransaction(transactions, id) {
  const next = transactions.filter((tx) => tx.id !== id);
  if (next.length === transactions.length) return fail("VE-24");
  const result = validateTransactionList(next);
  if (result.ok || !result.violation) return result;
  const { date, name } = result.violation;
  return fail("VE-11", { date, name });
}
