// 상태 보유와 흐름 조율: 검증 -> 상태 교체 -> 저장 -> 재계산 -> 렌더(docs/02_설계문서.md 7.6, 8절).
// DOM 과 localStorage 에 직접 접근하지 않고, 화면 문장을 만들지 않는다.

import { bindEvents, clearMessage, renderApp, resetTransactionForm, showMessage } from "./ui.js";
import { createEmptyData, loadData, saveData } from "./storage.js";
import { addTransaction, createTransaction } from "./transactions.js";
import { sortTransactions } from "./portfolio.js";

let state;

function buildView(data) {
  return { transactions: sortTransactions(data.transactions) };
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
};

function init() {
  const loaded = loadData();
  state = loaded.ok ? loaded.value : createEmptyData();
  if (!loaded.ok) showMessage("data", loaded.error, "error");
  bindEvents(handlers);
  render();
}

init();
