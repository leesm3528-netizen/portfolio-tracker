// 공통 상수와 순수 계산. 공식의 원본은 docs/03_계산규칙.md, 함수 형식은 docs/02_설계문서.md 7.1 이다.
// 다른 모듈을 import 하지 않고 브라우저 전역을 쓰지 않는다. 내부 계산은 반올림하지 않는다.

export const ASSET_CLASSES = ["stock", "bond", "cash", "other"];
export const ASSET_CLASS_LABELS = { stock: "주식", bond: "채권", cash: "현금", other: "기타" };
export const TRANSACTION_TYPES = ["buy", "sell"];
export const TRANSACTION_TYPE_LABELS = { buy: "매수", sell: "매도" };
export const CASH_NAME = "현금";
export const CASH_PRICE = 1;

// 실패 Result(02 4.1). 계산과 검증 모듈이 같이 쓴다(05 3.1 M-37).
export function fail(code, params = {}) {
  return { ok: false, error: { code, params } };
}

// 객체(배열과 null 아님) 판정(02 7.1). 거래 항목, 목표 비중, 저장 객체 검사가 같이 쓴다.
export function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

// 입력 숫자 해석(02 7.1). 범위 검사는 호출한 쪽이 한다.
export function parseNumber(raw) {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

// 처리 순서: date 오름차순, 같은 date 는 원래 배열 순서(안정 정렬). 03 3.1
export function sortTransactions(transactions) {
  return [...transactions].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}

// 03 3.2 절차로 종목별 상태를 재생한다. 초과 매도는 첫 위반 거래에서 멈추고 VE-25 로 실패한다(02 7.1).
export function calcPositions(transactions) {
  const indexOf = new Map(transactions.map((tx, i) => [tx, i]));
  const positions = new Map();
  for (const tx of sortTransactions(transactions)) {
    let pos = positions.get(tx.name);
    if (!pos) {
      pos = { name: tx.name, assetClass: tx.assetClass, quantity: 0, avgCost: 0, realizedPnl: 0 };
      positions.set(tx.name, pos);
    }
    if (tx.type === "buy") {
      pos.avgCost = (pos.quantity * pos.avgCost + tx.quantity * tx.price + tx.fee) / (pos.quantity + tx.quantity);
      pos.quantity += tx.quantity;
      continue;
    }
    if (tx.quantity > pos.quantity) {
      const detail = { date: tx.date, name: tx.name, quantity: tx.quantity, held: pos.quantity };
      return {
        ok: false,
        error: { code: "VE-25", params: { ...detail } },
        violation: { index: indexOf.get(tx), ...detail },
      };
    }
    pos.realizedPnl += (tx.price - pos.avgCost) * tx.quantity - tx.fee;
    pos.quantity -= tx.quantity;
    if (pos.quantity === 0) pos.avgCost = 0;
  }
  return { ok: true, value: [...positions.values()] };
}

// 보유 현황 행(02 6.2). 평가에 쓰는 현재가는 03 7.1 표 순서로 정한다.
export function buildHoldings(positions, prices) {
  const rows = positions.map((pos) => {
    const { name, assetClass, quantity, avgCost, realizedPnl } = pos;
    const costBasis = quantity * avgCost;
    if (quantity === 0) {
      return { name, assetClass, quantity, avgCost, price: null, priceMissing: false,
        marketValue: 0, costBasis, unrealizedPnl: 0, returnRate: null, realizedPnl };
    }
    const isCash = name === CASH_NAME;
    const hasPrice = !isCash && Object.prototype.hasOwnProperty.call(prices, name);
    const priceMissing = !isCash && !hasPrice;
    const price = isCash ? CASH_PRICE : hasPrice ? prices[name] : avgCost;
    const marketValue = quantity * price;
    const unrealizedPnl = marketValue - costBasis;
    return { name, assetClass, quantity, avgCost, price, priceMissing,
      marketValue, costBasis, unrealizedPnl, returnRate: (unrealizedPnl / costBasis) * 100, realizedPnl };
  });
  return rows.sort((a, b) => ASSET_CLASSES.indexOf(a.assetClass) - ASSET_CLASSES.indexOf(b.assetClass)
    || a.name.localeCompare(b.name, "ko"));
}

// 자산군별 평가금액(02 6.3). 4개 키를 항상 가진다.
export function sumValueByAssetClass(holdings) {
  const classValues = Object.fromEntries(ASSET_CLASSES.map((assetClass) => [assetClass, 0]));
  for (const row of holdings) classValues[row.assetClass] += row.marketValue;
  return classValues;
}

// 총평가금액 T(03 10절)
export function calcTotalValue(classValues) {
  return ASSET_CLASSES.reduce((sum, assetClass) => sum + classValues[assetClass], 0);
}

// 자산 비중(02 6.4). 총평가금액이 0 이면 비중은 null 이다.
export function buildAllocation(classValues) {
  const totalValue = calcTotalValue(classValues);
  const rows = ASSET_CLASSES.map((assetClass) => ({
    assetClass,
    value: classValues[assetClass],
    weight: totalValue === 0 ? null : (classValues[assetClass] / totalValue) * 100,
  }));
  return { totalValue, rows };
}

// 현재가 입력 규칙(02 7.1). 빈칸은 키를 지워 현재가 미입력으로 되돌리고, 0 보다 큰 수만 저장한다.
export function updatePrice(prices, name, raw) {
  if (name === CASH_NAME) return { ok: true, value: prices };
  if (raw.trim() === "") {
    return { ok: true, value: Object.fromEntries(Object.entries(prices).filter(([key]) => key !== name)) };
  }
  const price = parseNumber(raw);
  if (price === null || price <= 0) return fail("VE-12");
  return { ok: true, value: { ...prices, [name]: price } };
}

// 거래가 없는 종목과 현금 키를 뺀 현재가 객체(02 5.3)
export function prunePrices(prices, transactions) {
  const names = new Set(transactions.map((tx) => tx.name));
  return Object.fromEntries(Object.entries(prices).filter(([name]) => name !== CASH_NAME && names.has(name)));
}
