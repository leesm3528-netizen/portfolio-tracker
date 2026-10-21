// 상태 보유와 흐름 조율: 검증 -> 상태 교체 -> 저장 -> 재계산 -> 렌더(docs/02_설계문서.md 7.6, 8절).
// DOM 과 localStorage 에 직접 접근하지 않고, 화면 문장을 만들지 않는다.

import { bindEvents, clearMessage, confirmAction, downloadJson, renderApp, resetTransactionForm, setTargetInputs, showMessage } from "./ui.js";
import { createEmptyData, loadData, saveData, serializeData } from "./storage.js";
import { addTransaction, createTransaction, deleteTransaction } from "./transactions.js";
import { buildAllocation, buildHoldings, calcPositions, prunePrices, sortTransactions, sumValueByAssetClass, updatePrice } from "./portfolio.js";
import { calcRebalance, parseTargetInput, sumTargets } from "./rebalance.js";

let state;

// 검증된 상태에서 calcPositions 가 실패하면 불변 조건 위반이므로 예외를 던진다(02 4.2).
function buildView(data) {
  const positions = calcPositions(data.transactions);
  if (!positions.ok) throw new Error(`calcPositions failed: ${positions.error.code}`);
  const holdings = buildHoldings(positions.value, data.prices);
  const classValues = sumValueByAssetClass(holdings);
  return {
    transactions: sortTransactions(data.transactions),
    holdings,
    allocation: buildAllocation(classValues),
    targetSum: sumTargets(data.targets),
    rebalance: calcRebalance(classValues, data.targets),
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

  // 실패하면 commit 과 렌더를 하지 않으므로 입력칸에는 사용자가 입력한 값이 남는다(02 8절).
  onPriceChange(name, raw) {
    const result = updatePrice(state.prices, name, raw);
    if (!result.ok) {
      showMessage("holdings", result.error, "error");
      return;
    }
    clearMessage("holdings");
    commit({ ...state, prices: result.value });
  },

  // 실패하면 저장하지 않으므로 이전 저장값이 유지된다(02 7.3). 입력칸 값은 ui.js 가 다시 쓰지 않는다.
  onTargetInput(assetClass, raw) {
    const result = parseTargetInput(raw);
    if (!result.ok) {
      showMessage("targets", result.error, "error");
      return;
    }
    clearMessage("targets");
    commit({ ...state, targets: { ...state.targets, [assetClass]: result.value } });
  },

  onExport() {
    downloadJson(serializeData(state));
  },
};

function init() {
  const loaded = loadData();
  state = loaded.ok ? loaded.value : createEmptyData();
  if (!loaded.ok) showMessage("data", loaded.error, "error");
  setTargetInputs(state.targets);
  bindEvents(handlers);
  render();
}

init();
