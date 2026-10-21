// 상태 보유와 흐름 조율: 검증 -> 상태 교체 -> 저장 -> 재계산 -> 렌더(docs/02_설계문서.md 7.6, 8절).
// DOM 과 localStorage 에 직접 접근하지 않고, 화면 문장을 만들지 않는다.

import { bindEvents, clearMessage, confirmAction, renderApp, resetTransactionForm, showMessage } from "./ui.js";
import { createEmptyData, loadData, saveData } from "./storage.js";
import { addTransaction, createTransaction, deleteTransaction } from "./transactions.js";
import { buildHoldings, calcPositions, prunePrices, sortTransactions } from "./portfolio.js";

let state;

// 검증된 상태에서 calcPositions 가 실패하면 불변 조건 위반이므로 예외를 던진다(02 4.2).
function buildView(data) {
  const positions = calcPositions(data.transactions);
  if (!positions.ok) throw new Error(`calcPositions failed: ${positions.error.code}`);
  return {
    transactions: sortTransactions(data.transactions),
    holdings: buildHoldings(positions.value, data.prices),
  };
}

function render() {
  renderApp(buildView(state));
}

// 저장에 실패해도 화면 상태는 새 상태로 유지한다(01 FR-10 기준 3).
function commit(nextData) {
  state = nextData;
  const saved = saveData(state);
  if (saved.ok) clearMessage("data");
  else showMessage("data", saved.error, "error");
  render();
}

const handlers = {
  onAddTransaction(input) {
    const created = createTransaction(input);
    const result = created.ok ? addTransaction(state.transactions, created.value) : created;
    if (!result.ok) {
      showMessage("transaction", result.error, "error");
      return;
    }
    clearMessage("transaction");
    commit({ ...state, transactions: result.value });
    resetTransactionForm();
  },

  // 삭제해 상태를 바꿨으면 true, 취소나 거부면 false(02 7.5, 8절). 목록에 없는 id 는 확인 없이 VE-24 가 된다.
  onDeleteTransaction(id) {
    const tx = state.transactions.find((item) => item.id === id);
    if (tx) {
      const params = { date: tx.date, name: tx.name, type: tx.type, quantity: tx.quantity };
      if (!confirmAction({ code: "C-01", params })) return false;
    }
    const result = deleteTransaction(state.transactions, id);
    if (!result.ok) {
      showMessage("transactions", result.error, "error");
      return false;
    }
    clearMessage("transactions");
    commit({ ...state, transactions: result.value, prices: prunePrices(state.prices, result.value) });
    return true;
  },
};

function init() {
  const loaded = loadData();
  state = loaded.ok ? loaded.value : createEmptyData();
  if (!loaded.ok) showMessage("data", loaded.error, "error");
  bindEvents(handlers);
  render();
}

init();
