// 공통 상수와 순수 계산. 공식의 원본은 docs/03_계산규칙.md, 함수 형식은 docs/02_설계문서.md 7.1 이다.
// 다른 모듈을 import 하지 않고 브라우저 전역을 쓰지 않는다. 내부 계산은 반올림하지 않는다.

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
