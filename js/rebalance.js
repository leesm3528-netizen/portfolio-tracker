// 목표 비중과 리밸런싱 계산. 공식의 원본은 docs/03_계산규칙.md 11절, 함수 형식은 docs/02_설계문서.md 7.3 이다.
// DOM 과 브라우저 전역을 쓰지 않고 portfolio.js 만 import 한다.

import { ASSET_CLASSES, calcTotalValue } from "./portfolio.js";

const TARGET_TOTAL = 100;

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
