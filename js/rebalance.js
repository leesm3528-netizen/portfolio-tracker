// 목표 비중과 리밸런싱 계산. 공식의 원본은 docs/03_계산규칙.md 11절, 함수 형식은 docs/02_설계문서.md 7.3 이다.
// DOM 과 브라우저 전역을 쓰지 않고 portfolio.js 만 import 한다.

import { ASSET_CLASSES, calcTotalValue } from "./portfolio.js";

const TARGET_TOTAL = 100;

// 목표 비중 값 하나의 범위와 자릿수 판정(02 5.4). 통과하면 null, 아니면 범위 VE-13, 자릿수 VE-14.
function targetValueError(value) {
  if (!Number.isFinite(value) || value < 0 || value > 100) return "VE-13";
  if (Math.abs(value * 10 - Math.round(value * 10)) >= 1e-9) return "VE-14";
  return null;
}

export function createDefaultTargets() {
  return Object.fromEntries(ASSET_CLASSES.map((assetClass) => [assetClass, 0]));
}

// 키 4개 정확히, 각 값의 범위와 자릿수를 본다. 합계는 검사하지 않는다(02 5.4, 7.3).
export function validateTargets(value) {
  const keys = value !== null && typeof value === "object" && !Array.isArray(value) ? Object.keys(value) : [];
  const valid = keys.length === ASSET_CLASSES.length
    && ASSET_CLASSES.every((assetClass) => keys.includes(assetClass) && targetValueError(value[assetClass]) === null);
  return valid ? { ok: true, value } : { ok: false, error: { code: "VD-06", params: {} } };
}

// 각 값을 10배 해 정수로 반올림한 합을 10으로 나눈다(03 11.1, 02 7.3).
export function sumTargets(targets) {
  return ASSET_CLASSES.reduce((sum, assetClass) => sum + Math.round(targets[assetClass] * 10), 0) / 10;
}

// 리밸런싱 결과(02 6.5). 판정 기준은 |amount| 0.5 경계(03 11.3, 13.1)다.
export function calcRebalance(classValues, targets) {
  const totalValue = calcTotalValue(classValues);
  if (totalValue === 0) return { ok: false, error: { code: "VE-16", params: {} } };
  const sum = sumTargets(targets);
  if (sum !== TARGET_TOTAL) return { ok: false, error: { code: "VE-15", params: { sum } } };
  const rows = ASSET_CLASSES.map((assetClass) => {
    const currentValue = classValues[assetClass];
    const targetWeight = targets[assetClass];
    const targetValue = (totalValue * targetWeight) / 100;
    const amount = targetValue - currentValue;
    const action = amount >= 0.5 ? "buy" : amount <= -0.5 ? "sell" : "hold";
    return { assetClass, currentValue, targetWeight, targetValue, amount, tradeAmount: Math.abs(amount), action };
  });
  return { ok: true, value: { totalValue, rows } };
}
