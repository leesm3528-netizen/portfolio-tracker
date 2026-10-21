// 계산규칙 검증 스크립트. docs/03_계산규칙.md 14절 검증 사례를 계산 모듈 결과와 대조한다.
// 실행(프로젝트 루트, Node 22 이상): node skills/calc-rule-verify/scripts/verify.mjs [사례 ID | C | R ...] [--allow-missing]
// 세부 동작의 원본: docs/05_작업지시서.md 2.2, T2-04. 절차: skills/calc-rule-verify/SKILL.md
// 아래 포매터 설정은 docs/02_설계문서.md 10절을 옮긴 검증 기준이며 앱 코드가 아니다.

import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import process from "node:process";

const MODULE_URLS = {
  portfolio: new URL("../../../js/portfolio.js", import.meta.url),
  rebalance: new URL("../../../js/rebalance.js", import.meta.url),
  transactions: new URL("../../../js/transactions.js", import.meta.url),
};

const TOLERANCE = 0.000001;

// ---------------------------------------------------------------------------
// 사례 데이터 (03 14절). 거래 행은 [date, name, assetClass, type, quantity, price, fee].
// 종목 기대값 행은 [name, quantity, avgCost, realizedPnl, priceMissing, marketValue, unrealizedPnl, returnRate].
// 단계 행은 [거래 인덱스, quantity, avgCost, realizedPnl] 이고 처리 순서대로 적는다. 실패 단계는 [거래 인덱스, null].
// ---------------------------------------------------------------------------

const R01_TXS = [
  ["2026-01-02", "종목S", "stock", "buy", 100, 60000, 0],
  ["2026-01-02", "종목T", "bond", "buy", 20, 100000, 0],
  ["2026-01-02", "현금", "cash", "buy", 1000000, 1, 0],
];
const R01_PRICES = { "종목S": 70000, "종목T": 100000 };

const CASES = [
  {
    id: "C-01", sec: "14.2", prices: {},
    txs: [
      ["2026-01-02", "종목A", "stock", "buy", 10, 10000, 0],
      ["2026-01-03", "종목A", "stock", "buy", 10, 12000, 0],
      ["2026-01-04", "종목A", "stock", "sell", 5, 13000, 0],
    ],
    steps: { name: "종목A", rows: [[0, 10, 10000, 0], [1, 20, 11000, 0], [2, 15, 11000, 10000]] },
    final: [["종목A", 15, 11000, 10000, true, 165000, 0, 0]],
  },
  {
    id: "C-02", sec: "14.3", prices: { "종목B": 6000 },
    txs: [
      ["2026-02-02", "종목B", "stock", "buy", 10, 5000, 500],
      ["2026-02-03", "종목B", "stock", "buy", 20, 5600, 1000],
    ],
    steps: { name: "종목B", rows: [[0, 10, 5050, 0], [1, 30, 5450, 0]] },
    final: [["종목B", 30, 5450, 0, false, 180000, 16500, 1100 / 109]],
    display: [["종목B", "수익률", "10.09"]],
  },
  {
    id: "C-03", sec: "14.4", prices: { "종목C": 8800 },
    txs: [
      ["2026-03-02", "종목C", "stock", "buy", 20, 8000, 0],
      ["2026-03-10", "종목C", "stock", "sell", 8, 9500, 1200],
      ["2026-03-11", "종목C", "stock", "sell", 2, 7000, 300],
    ],
    steps: { name: "종목C", rows: [[0, 20, 8000, 0], [1, 12, 8000, 10800], [2, 10, 8000, 8500]] },
    final: [["종목C", 10, 8000, 8500, false, 88000, 8000, 10]],
  },
  {
    id: "C-04", sec: "14.5", prices: { "종목D": 4200 },
    txs: [
      ["2026-04-01", "종목D", "stock", "buy", 10, 3000, 0],
      ["2026-04-05", "종목D", "stock", "sell", 10, 3600, 0],
      ["2026-04-10", "종목D", "stock", "buy", 5, 4000, 100],
      ["2026-04-12", "종목D", "stock", "sell", 2, 4500, 0],
    ],
    steps: { name: "종목D", rows: [[0, 10, 3000, 0], [1, 0, 0, 6000], [2, 5, 4020, 6000], [3, 3, 4020, 6960]] },
    // #1 처리 직후(거래 #0, #1 만 있을 때)의 평가
    partial: { label: "#1 처리 직후", indices: [0, 1], holdings: [["종목D", 0, 0, 6000, false, 0, 0, null]] },
    final: [["종목D", 3, 4020, 6960, false, 12600, 540, 900 / 201]],
    display: [["종목D", "수익률", "4.48"]],
  },
  {
    id: "C-05", sec: "14.6", prices: {},
    txs: [["2026-05-02", "종목E", "stock", "buy", 10, 2000, 0]],
    existing: [["종목E", 10, 2000, 0]],
    adds: [
      { label: "a", row: ["2026-05-03", "종목E", "stock", "sell", 11, 2100, 0], code: "VE-09", params: { date: "2026-05-03", name: "종목E", held: 10 } },
      { label: "b", row: ["2026-05-03", "종목E", "stock", "sell", 10, 2100, 0], ok: true,
        final: [["종목E", 0, 0, 1000, false, 0, 0, null]] },
      { label: "c", row: ["2026-05-04", "종목Z", "stock", "sell", 1, 1000, 0], code: "VE-09", params: { date: "2026-05-04", name: "종목Z", held: 0 } },
    ],
  },
  {
    id: "C-06", sec: "14.7", prices: { "종목F": 2000 },
    txs: [
      ["2026-06-01", "종목F", "stock", "buy", 10, 1000, 0],
      ["2026-06-02", "종목F", "stock", "sell", 10, 1500, 0],
      ["2026-06-02", "종목F", "stock", "buy", 10, 2000, 0],
    ],
    steps: { name: "종목F", rows: [[0, 10, 1000, 0], [1, 0, 0, 5000], [2, 10, 2000, 5000]] },
    final: [["종목F", 10, 2000, 5000, false, 20000, 0, 0]],
  },
  {
    id: "C-07", sec: "14.8", prices: {},
    // #2 는 추가 시도 거래다. 기존 거래는 #0, #1 이다.
    txs: [
      ["2026-07-01", "종목G", "stock", "buy", 10, 1000, 0],
      ["2026-07-10", "종목G", "stock", "sell", 8, 1200, 0],
      ["2026-07-05", "종목G", "stock", "sell", 5, 1100, 0],
    ],
    existingCount: 2,
    steps: {
      name: "종목G", rows: [[0, 10, 1000, 0], [2, 5, 1000, 500], [1, null]],
      failure: { code: "VE-25", params: { date: "2026-07-10", name: "종목G", quantity: 8, held: 5 }, index: 1 },
    },
    adds: [{ label: "#2", index: 2, code: "VE-10", params: { date: "2026-07-10", name: "종목G" } }],
    final: [["종목G", 2, 1000, 1600, true, 2000, 0, 0]],
    finalIndices: [0, 1],
  },
  {
    id: "C-08", sec: "14.9", prices: {},
    txs: [
      ["2026-07-01", "종목H", "stock", "buy", 10, 1000, 0],
      ["2026-07-10", "종목H", "stock", "sell", 8, 1200, 0],
      ["2026-07-05", "종목H", "stock", "buy", 5, 1600, 0],
    ],
    existingCount: 2,
    existing: [["종목H", 2, 1000, 1600]],
    steps: { name: "종목H", rows: [[0, 10, 1000, 0], [2, 15, 1200, 0], [1, 7, 1200, 0]] },
    adds: [{ label: "#2", index: 2, ok: true }],
    final: [["종목H", 7, 1200, 0, true, 8400, 0, 0]],
  },
  {
    id: "C-09", sec: "14.10", prices: {},
    txs: [
      ["2026-08-01", "종목I", "stock", "buy", 10, 1000, 0],
      ["2026-08-02", "종목I", "stock", "buy", 5, 1300, 0],
      ["2026-08-03", "종목I", "stock", "sell", 12, 1500, 0],
    ],
    steps: { name: "종목I", rows: [[0, 10, 1000, 0], [1, 15, 1100, 0], [2, 3, 1100, 4800]] },
    deletes: [
      { label: "a", index: 1, code: "VE-11", params: { date: "2026-08-03", name: "종목I" } },
      { label: "b", index: 2, ok: true, final: [["종목I", 15, 1100, 0, true, 16500, 0, 0]] },
    ],
  },
  {
    id: "C-10", sec: "14.11", prices: {},
    txs: [["2026-09-01", "종목J", "stock", "buy", 10, 2500, 500]],
    final: [["종목J", 10, 2550, 0, true, 25500, 0, 0]],
  },
  {
    id: "C-11", sec: "14.12", prices: { "종목K": 11000 },
    txs: [
      ["2026-09-01", "종목K", "stock", "buy", 3, 10000, 500],
      ["2026-09-02", "종목K", "stock", "sell", 1, 12000, 0],
    ],
    steps: { name: "종목K", rows: [[0, 3, 30500 / 3, 0], [1, 2, 30500 / 3, 5500 / 3]] },
    final: [["종목K", 2, 30500 / 3, 5500 / 3, false, 22000, 5000 / 3, 500 / 61]],
    display: [
      ["종목K", "평균단가", "10166.67"],
      ["종목K", "실현손익", "1833"],
      ["종목K", "평가금액", "22000"],
      ["종목K", "평가손익", "1667"],
      ["종목K", "수익률", "8.20"],
    ],
  },
  {
    id: "C-12", sec: "14.13", prices: {},
    txs: [
      ["2026-09-01", "종목L", "stock", "buy", 300, 10000, 1000],
      ["2026-09-02", "종목L", "stock", "sell", 300, 10100, 0],
    ],
    steps: { name: "종목L", rows: [[0, 300, 30010 / 3, 0], [1, 0, 0, 29000]] },
    final: [["종목L", 0, 0, 29000, false, 0, 0, null]],
    display: [["종목L", "실현손익", "29000"]],
  },
  {
    id: "C-13", sec: "14.14", prices: {},
    txs: [["2026-09-01", "종목M", "stock", "buy", 1, 50000, 0]],
    creates: [
      { label: "a", input: { date: "2026-09-02", name: "종목M", assetClass: "bond", type: "buy", quantity: "1", price: "50000", fee: "0" } },
      { label: "b", input: { date: "2026-09-02", name: " 종목M ", assetClass: "bond", type: "buy", quantity: "1", price: "50000", fee: "0" } },
    ],
    createCode: "VE-07",
    createParams: { name: "종목M", assetClass: "stock" },
    final: [["종목M", 1, 50000, 0, true, 50000, 0, 0]],
  },
  {
    id: "C-14", sec: "14.15", prices: {},
    txs: [
      ["2026-09-01", "현금", "cash", "buy", 1000000, 1, 0],
      ["2026-09-15", "현금", "cash", "sell", 300000, 1, 0],
    ],
    steps: { name: "현금", rows: [[0, 1000000, 1, 0], [1, 700000, 1, 0]] },
    final: [["현금", 700000, 1, 0, false, 700000, 0, 0]],
  },
  {
    id: "C-15", sec: "14.22", prices: {},
    txs: [["2026-09-01", "현금", "cash", "buy", 1000000, 1, 1000]],
    steps: { name: "현금", rows: [[0, 1000000, 1001 / 1000, 0]] },
    final: [["현금", 1000000, 1001 / 1000, 0, false, 1000000, -1000, -100 / 1001]],
    display: [
      ["현금", "평균단가", "1.00"],
      ["현금", "평가금액", "1000000"],
      ["현금", "평가손익", "-1000"],
      ["현금", "수익률", "-0.10"],
    ],
  },
  {
    id: "R-01", sec: "14.16", prices: R01_PRICES, txs: R01_TXS,
    classValues: { stock: 7000000, bond: 2000000, cash: 1000000, other: 0 },
    total: 10000000,
    weights: { stock: 70, bond: 20, cash: 10, other: 0 },
    rebalances: [{
      label: "", targets: { stock: 60, bond: 30, cash: 10, other: 0 },
      rows: { stock: [-1000000, "sell", "1000000"], bond: [1000000, "buy", "1000000"], cash: [0, "hold", "0"], other: [0, "hold", "0"] },
    }],
  },
  {
    id: "R-02", sec: "14.17", prices: R01_PRICES, txs: R01_TXS,
    weights: { stock: 70, bond: 20, cash: 10, other: 0 },
    rebalances: [
      { label: "a", targets: { stock: 60, bond: 30, cash: 5, other: 0 }, code: "VE-15", params: { sum: 95 } },
      { label: "b", targets: { stock: 60, bond: 30, cash: 10, other: 0.1 }, code: "VE-15", params: { sum: 100.1 } },
    ],
  },
  {
    id: "R-03", sec: "14.18", prices: R01_PRICES, txs: R01_TXS,
    classValues: { stock: 7000000, bond: 2000000, cash: 1000000, other: 0 },
    total: 10000000,
    rebalances: [{
      label: "", targets: { stock: 0.1, bond: 0.2, cash: 84.1, other: 15.6 },
      rows: { stock: [-6990000, "sell", "6990000"], bond: [-1980000, "sell", "1980000"], cash: [7410000, "buy", "7410000"], other: [1560000, "buy", "1560000"] },
    }],
  },
  {
    id: "R-04", sec: "14.19", prices: {},
    txs: [
      ["2026-01-02", "종목U", "stock", "buy", 333, 10000, 0],
      ["2026-01-02", "종목V", "bond", "buy", 333, 10000, 0],
      ["2026-01-02", "현금", "cash", "buy", 3340001, 1, 0],
    ],
    classValues: { stock: 3330000, bond: 3330000, cash: 3340001, other: 0 },
    total: 10000001,
    weights: { stock: 333000000 / 10000001, bond: 333000000 / 10000001, cash: 334000100 / 10000001, other: 0 },
    weightDisplay: { stock: "33.30", bond: "33.30", cash: "33.40", other: "0.00" },
    rebalances: [{
      label: "", targets: { stock: 33.3, bond: 33.3, cash: 33.4, other: 0 },
      rows: { stock: [0.333, "hold", "0"], bond: [0.333, "hold", "0"], cash: [-0.666, "sell", "1"], other: [0, "hold", "0"] },
    }],
  },
  {
    id: "R-05", sec: "14.20", prices: {},
    txs: [
      ["2026-01-02", "종목W", "stock", "buy", 10, 1000, 0],
      ["2026-01-03", "종목W", "stock", "sell", 10, 1200, 0],
    ],
    // 03 R-05 표에 현재가 미입력 열이 없으므로 priceMissing 은 undefined 로 두고 비교하지 않는다.
    final: [["종목W", 0, 0, 2000, undefined, 0, 0, null]],
    total: 0,
    weights: { stock: null, bond: null, cash: null, other: null },
    rebalances: [{ label: "", targets: { stock: 60, bond: 30, cash: 10, other: 0 }, code: "VE-16", params: {} }],
    emptyState: true,
  },
  {
    id: "R-06", sec: "14.21", prices: { "종목N": 55000, "종목P": 10000 },
    txs: [
      ["2026-01-02", "종목N", "stock", "buy", 10, 50000, 5000],
      ["2026-01-02", "종목O", "bond", "buy", 30, 10000, 0],
      ["2026-01-02", "현금", "cash", "buy", 100000, 1, 0],
      ["2026-01-02", "종목P", "other", "buy", 5, 10000, 0],
    ],
    final: [
      ["종목N", 10, 50500, 0, false, 550000, 45000, 900 / 101],
      ["종목O", 30, 10000, 0, true, 300000, 0, 0],
      ["현금", 100000, 1, 0, false, 100000, 0, 0],
      ["종목P", 5, 10000, 0, false, 50000, 0, 0],
    ],
    display: [["종목N", "수익률", "8.91"]],
    classValues: { stock: 550000, bond: 300000, cash: 100000, other: 50000 },
    total: 1000000,
    weights: { stock: 55, bond: 30, cash: 10, other: 5 },
    rebalances: [{
      label: "", targets: { stock: 50, bond: 35.5, cash: 10, other: 4.5 },
      rows: { stock: [-50000, "sell", "50000"], bond: [55000, "buy", "55000"], cash: [0, "hold", "0"], other: [-5000, "sell", "5000"] },
    }],
  },
];

// ---------------------------------------------------------------------------
// 표시 형식 (02 10절). 포매터 옵션과 부호 처리 규칙을 그대로 옮긴다.
// ---------------------------------------------------------------------------

const FORMATTERS = {
  won: new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 }),
  avgCost: new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  percent: new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
};

function formatWith(formatter, n, signed) {
  const s = formatter.format(Math.abs(n));
  if (!/[1-9]/.test(s)) return s;
  if (n < 0) return "-" + s;
  if (signed && n > 0) return "+" + s;
  return s;
}

const DISPLAY = {
  평균단가: { field: "avgCost", format: (n) => formatWith(FORMATTERS.avgCost, n, false) }, // formatAvgCost
  실현손익: { field: "realizedPnl", format: (n) => formatWith(FORMATTERS.won, n, true) }, // formatSignedWon
  평가금액: { field: "marketValue", format: (n) => formatWith(FORMATTERS.won, n, false) }, // formatWon
  평가손익: { field: "unrealizedPnl", format: (n) => formatWith(FORMATTERS.won, n, true) }, // formatSignedWon
  수익률: { field: "returnRate", format: (n) => formatWith(FORMATTERS.percent, n, true) }, // formatSignedPercent
};
const formatWeight = (n) => formatWith(FORMATTERS.percent, n, false); // formatPercent
const formatWon = (n) => formatWith(FORMATTERS.won, n, false); // formatWon

// 비교 전 정규화: 천 단위 쉼표, 끝의 %, 앞의 + 만 지운다. - 는 남긴다.
function normalizeDisplay(s) {
  return s.replace(/,/g, "").replace(/%$/, "").replace(/^\+/, "");
}

// ---------------------------------------------------------------------------
// 공통 도우미
// ---------------------------------------------------------------------------

function makeTx(caseId, index, row) {
  const [date, name, assetClass, type, quantity, price, fee] = row;
  return { id: `${caseId.replace("-", "")}-${index}`, date, name, assetClass, type, quantity, price, fee };
}

function caseTxs(c, indices) {
  const all = c.txs.map((row, i) => makeTx(c.id, i, row));
  return indices ? indices.map((i) => all[i]) : all;
}

function positionsOf(m, txs) {
  const result = m.portfolio.calcPositions(txs);
  if (!result || result.ok !== true) throw new Error(`calcPositions 실패: ${JSON.stringify(result && result.error)}`);
  return result.value;
}

function findByName(list, name) {
  const found = list.find((item) => item.name === name);
  if (!found) throw new Error(`종목 없음: ${name}`);
  return found;
}

function holdingsOf(m, txs, prices) {
  return m.portfolio.buildHoldings(positionsOf(m, txs), prices);
}

function classValuesOf(m, c) {
  return m.portfolio.sumValueByAssetClass(holdingsOf(m, caseTxs(c), c.prices));
}

function sameNumber(expected, actual) {
  if (expected === null || actual === null) return expected === actual;
  return typeof actual === "number" && Number.isFinite(actual) && Math.abs(expected - actual) <= TOLERANCE;
}

function showValue(v) {
  if (v === undefined) return "undefined";
  if (typeof v === "number" && !Number.isInteger(v)) return String(Number(v.toFixed(6)));
  return JSON.stringify(v);
}

// 검사 하나: { caseId, sec, item, expected, needs, run, compare }
// compare: "num"(절대 오차), "exact"(=== 비교, 표시값 문자열 포함)
function check(c, item, expected, needs, run, compare = "num") {
  return { caseId: c.id, sec: c.sec, item, expected, needs, run, compare };
}

const P = (fn) => `portfolio.${fn}`;
const HOLDING_NEEDS = [P("calcPositions"), P("buildHoldings")];
const POSITION_FIELDS = ["quantity", "avgCost", "realizedPnl"];
const HOLDING_FIELDS = ["priceMissing", "marketValue", "unrealizedPnl", "returnRate"];

// 종목 기대값 행을 검사 목록으로 만든다. 단계와 기존 상태는 POSITION_FIELDS 만 쓴다.
function holdingChecks(c, label, getTxs, rows) {
  const out = [];
  for (const row of rows) {
    const [name, quantity, avgCost, realizedPnl, priceMissing, marketValue, unrealizedPnl, returnRate] = row;
    const pos = { quantity, avgCost, realizedPnl };
    for (const field of POSITION_FIELDS) {
      out.push(check(c, `${label} ${name} ${field}`, pos[field], [P("calcPositions")],
        (m) => findByName(positionsOf(m, getTxs()), name)[field]));
    }
    const hold = { priceMissing, marketValue, unrealizedPnl, returnRate };
    for (const field of HOLDING_FIELDS) {
      if (hold[field] === undefined) continue;
      out.push(check(c, `${label} ${name} ${field}`, hold[field], HOLDING_NEEDS,
        (m) => findByName(holdingsOf(m, getTxs(), c.prices), name)[field],
        field === "priceMissing" ? "exact" : "num"));
    }
  }
  return out;
}

function positionChecks(c, label, getTxs, rows) {
  const out = [];
  for (const [name, quantity, avgCost, realizedPnl] of rows) {
    const pos = { quantity, avgCost, realizedPnl };
    for (const field of POSITION_FIELDS) {
      out.push(check(c, `${label} ${name} ${field}`, pos[field], [P("calcPositions")],
        (m) => findByName(positionsOf(m, getTxs()), name)[field]));
    }
  }
  return out;
}

// 실패 Result 검사: ok, error 형식(문장이 아니라 code, params 객체), code, params 각 필드
function failureChecks(c, label, needs, call, code, params) {
  const out = [];
  out.push(check(c, `${label} ok`, false, needs, (m) => call(m).ok, "exact"));
  out.push(check(c, `${label} error 형식`, true, needs, (m) => {
    const e = call(m).error;
    return e !== null && typeof e === "object" && typeof e.code === "string"
      && e.params !== null && typeof e.params === "object" && !Array.isArray(e.params);
  }, "exact"));
  out.push(check(c, `${label} error.code`, code, needs, (m) => call(m).error.code, "exact"));
  for (const [key, value] of Object.entries(params)) {
    out.push(check(c, `${label} error.params.${key}`, value, needs, (m) => call(m).error.params[key],
      typeof value === "number" ? "num" : "exact"));
  }
  return out;
}

// ---------------------------------------------------------------------------
// 사례별 검사 목록 만들기 (05 T2-04 작업 내용 4번)
// ---------------------------------------------------------------------------

function buildChecks(c) {
  const out = [];

  // 4.2 단계별 상태: 처리 순서상 그 거래까지의 거래만으로 calcPositions 실행
  if (c.steps) {
    const order = [];
    for (const row of c.steps.rows) {
      const [index] = row;
      order.push(index);
      const indices = [...order].sort((a, b) => a - b);
      const getTxs = () => caseTxs(c, indices);
      if (row[1] === null) {
        const call = (m) => m.portfolio.calcPositions(getTxs());
        const f = c.steps.failure;
        out.push(...failureChecks(c, `단계 #${index}`, [P("calcPositions")], call, f.code, f.params));
        out.push(check(c, `단계 #${index} violation.index`, f.index, [P("calcPositions")],
          (m) => call(m).violation.index));
      } else {
        out.push(...positionChecks(c, `단계 #${index}`, getTxs, [[c.steps.name, row[1], row[2], row[3]]]));
      }
    }
  }

  // C-04 처럼 중간 시점의 평가가 적힌 사례
  if (c.partial) {
    out.push(...holdingChecks(c, c.partial.label, () => caseTxs(c, c.partial.indices), c.partial.holdings));
  }

  const existingIndices = c.existingCount ? [...Array(c.existingCount).keys()] : null;
  const existingTxs = () => caseTxs(c, existingIndices);

  // 기존 상태(추가나 삭제 시도 전, 거부 후 상태와 같다)
  if (c.existing) {
    out.push(...positionChecks(c, "기존 상태", existingTxs, c.existing));
  }

  // 4.3 거래 추가 시도
  for (const a of c.adds || []) {
    const needs = ["transactions.addTransaction"];
    const tx = a.row ? makeTx(c.id, existingTxs().length, a.row) : caseTxs(c)[a.index];
    const label = `추가 ${a.label}`;
    if (a.ok) {
      out.push(check(c, `${label} ok`, true, needs, (m) => m.transactions.addTransaction(existingTxs(), tx).ok, "exact"));
      if (a.final) {
        out.push(...holdingChecks(c, `${label} 후`, () => [...existingTxs(), tx], a.final));
      }
    } else {
      const call = (m) => m.transactions.addTransaction(existingTxs(), tx);
      out.push(...failureChecks(c, label, needs, call, a.code, a.params));
      out.push(check(c, `${label} violation 없음`, true, needs, (m) => call(m).violation === undefined, "exact"));
      out.push(check(c, `${label} 원래 배열 유지`, true, needs, (m) => {
        const before = existingTxs();
        const snapshot = JSON.stringify(before);
        m.transactions.addTransaction(before, tx);
        return JSON.stringify(before) === snapshot;
      }, "exact"));
    }
  }

  // 4.3 거래 삭제 시도
  for (const d of c.deletes || []) {
    const needs = ["transactions.deleteTransaction"];
    const id = caseTxs(c)[d.index].id;
    const label = `삭제 ${d.label}`;
    if (d.ok) {
      out.push(check(c, `${label} ok`, true, needs, (m) => m.transactions.deleteTransaction(caseTxs(c), id).ok, "exact"));
      const rest = caseTxs(c).map((_, i) => i).filter((i) => i !== d.index);
      out.push(...holdingChecks(c, `${label} 후`, () => caseTxs(c, rest), d.final));
    } else {
      const call = (m) => m.transactions.deleteTransaction(caseTxs(c), id);
      out.push(...failureChecks(c, label, needs, call, d.code, d.params));
      out.push(check(c, `${label} violation 없음`, true, needs, (m) => call(m).violation === undefined, "exact"));
      out.push(check(c, `${label} 원래 배열 유지`, true, needs, (m) => {
        const before = caseTxs(c);
        const snapshot = JSON.stringify(before);
        m.transactions.deleteTransaction(before, id);
        return JSON.stringify(before) === snapshot;
      }, "exact"));
    }
  }

  // 4.3 C-13: createTransaction 으로 만든 거래를 addTransaction
  for (const cr of c.creates || []) {
    const needs = ["transactions.createTransaction", "transactions.addTransaction"];
    const label = `추가 ${cr.label}`;
    out.push(check(c, `${label} createTransaction ok`, true, needs,
      (m) => m.transactions.createTransaction(cr.input).ok, "exact"));
    const call = (m) => {
      const created = m.transactions.createTransaction(cr.input);
      if (!created.ok) throw new Error(`createTransaction 실패: ${JSON.stringify(created.error)}`);
      return m.transactions.addTransaction(caseTxs(c), created.value);
    };
    out.push(...failureChecks(c, label, needs, call, c.createCode, c.createParams));
    out.push(check(c, `${label} 원래 배열 유지`, true, needs, (m) => {
      const before = caseTxs(c);
      const snapshot = JSON.stringify(before);
      const created = m.transactions.createTransaction(cr.input);
      if (created.ok) m.transactions.addTransaction(before, created.value);
      return JSON.stringify(before) === snapshot;
    }, "exact"));
  }

  // 4.1 최종 기대값
  if (c.final) {
    const getTxs = () => caseTxs(c, c.finalIndices || null);
    out.push(...holdingChecks(c, "최종", getTxs, c.final));
  }

  // 4.5 표시값 (종목)
  for (const [name, label, expected] of c.display || []) {
    const spec = DISPLAY[label];
    out.push(check(c, `표시 ${name} ${label}`, expected, HOLDING_NEEDS, (m) => {
      const row = findByName(holdingsOf(m, caseTxs(c, c.finalIndices || null), c.prices), name);
      return normalizeDisplay(spec.format(row[spec.field]));
    }, "exact"));
  }

  // 4.4 리밸런싱 사례
  const classNeeds = [...HOLDING_NEEDS, P("sumValueByAssetClass")];
  if (c.classValues) {
    for (const [key, value] of Object.entries(c.classValues)) {
      out.push(check(c, `자산군 평가금액 ${key}`, value, classNeeds, (m) => classValuesOf(m, c)[key]));
    }
  }
  if (c.total !== undefined) {
    out.push(check(c, "총평가금액", c.total, [...classNeeds, P("calcTotalValue")],
      (m) => m.portfolio.calcTotalValue(classValuesOf(m, c))));
  }
  if (c.weights) {
    const needs = [...classNeeds, P("buildAllocation")];
    const rowOf = (m, key) => {
      const row = m.portfolio.buildAllocation(classValuesOf(m, c)).rows.find((r) => r.assetClass === key);
      if (!row) throw new Error(`자산군 행 없음: ${key}`);
      return row;
    };
    for (const [key, value] of Object.entries(c.weights)) {
      out.push(check(c, `비중 ${key}`, value, needs, (m) => rowOf(m, key).weight));
    }
    for (const [key, value] of Object.entries(c.weightDisplay || {})) {
      out.push(check(c, `표시 비중 ${key}`, value, needs, (m) => normalizeDisplay(formatWeight(rowOf(m, key).weight)), "exact"));
    }
  }
  for (const r of c.rebalances || []) {
    const needs = [...classNeeds, "rebalance.calcRebalance"];
    const call = (m) => m.rebalance.calcRebalance(classValuesOf(m, c), r.targets);
    const label = r.label ? `리밸런싱 ${r.label}` : "리밸런싱";
    if (r.code) {
      out.push(...failureChecks(c, label, needs, call, r.code, r.params));
      continue;
    }
    out.push(check(c, `${label} ok`, true, needs, (m) => call(m).ok, "exact"));
    const rowOf = (m, key) => {
      const row = call(m).value.rows.find((x) => x.assetClass === key);
      if (!row) throw new Error(`자산군 행 없음: ${key}`);
      return row;
    };
    for (const [key, [amount, action, shown]] of Object.entries(r.rows)) {
      out.push(check(c, `${label} ${key} amount`, amount, needs, (m) => rowOf(m, key).amount));
      out.push(check(c, `${label} ${key} tradeAmount`, Math.abs(amount), needs, (m) => rowOf(m, key).tradeAmount));
      out.push(check(c, `${label} ${key} action`, action, needs, (m) => rowOf(m, key).action, "exact"));
      out.push(check(c, `표시 ${label} ${key} 금액`, shown, needs,
        (m) => normalizeDisplay(formatWon(rowOf(m, key).tradeAmount)), "exact"));
    }
  }

  // R-05: 거래가 하나도 없는 빈 상태도 같은 결과
  if (c.emptyState) {
    const empty = { ...c, txs: [], prices: {} };
    out.push(check(c, "빈 상태 총평가금액", 0, [...classNeeds, P("calcTotalValue")],
      (m) => m.portfolio.calcTotalValue(classValuesOf(m, empty))));
    for (const key of ["stock", "bond", "cash", "other"]) {
      out.push(check(c, `빈 상태 비중 ${key}`, null, [...classNeeds, P("buildAllocation")], (m) => {
        const row = m.portfolio.buildAllocation(classValuesOf(m, empty)).rows.find((x) => x.assetClass === key);
        if (!row) throw new Error(`자산군 행 없음: ${key}`);
        return row.weight;
      }));
    }
    const r = c.rebalances[0];
    out.push(...failureChecks(c, "빈 상태 리밸런싱", [...classNeeds, "rebalance.calcRebalance"],
      (m) => m.rebalance.calcRebalance(classValuesOf(m, empty), r.targets), r.code, r.params));
  }

  return out;
}

// ---------------------------------------------------------------------------
// 모듈 불러오기, 실행, 출력
// ---------------------------------------------------------------------------

async function loadModules() {
  const modules = {};
  for (const [key, url] of Object.entries(MODULE_URLS)) {
    if (!existsSync(fileURLToPath(url))) {
      modules[key] = { missing: true };
      continue;
    }
    try {
      modules[key] = { exports: await import(url.href) };
    } catch (err) {
      modules[key] = { loadError: err };
    }
  }
  return modules;
}

function parseArgs(argv) {
  const ids = new Set(CASES.map((c) => c.id));
  const selectors = [];
  let allowMissing = false;
  const unknown = [];
  for (const arg of argv) {
    if (arg === "--allow-missing") allowMissing = true;
    else if (arg === "C" || arg === "R") selectors.push((c) => c.id.startsWith(`${arg}-`));
    else if (ids.has(arg)) selectors.push((c) => c.id === arg);
    else unknown.push(arg);
  }
  return { allowMissing, selectors, unknown };
}

function runCheck(chk, modules) {
  // 없는 모듈이나 export 되지 않은 함수를 쓰는 검사는 SKIP
  for (const need of chk.needs) {
    const [key, fn] = need.split(".");
    const mod = modules[key];
    if (mod.loadError) return { result: "FAIL", actual: `불러오기 실패: js/${key}.js: ${mod.loadError.message}` };
    if (mod.missing || typeof mod.exports[fn] !== "function") return { result: "SKIP", actual: `없음: ${need}` };
  }
  const m = Object.fromEntries(Object.entries(modules).map(([k, v]) => [k, v.exports]));
  try {
    const actual = chk.run(m);
    const pass = chk.compare === "exact" ? actual === chk.expected : sameNumber(chk.expected, actual);
    return { result: pass ? "PASS" : "FAIL", actual: showValue(actual) };
  } catch (err) {
    return { result: "FAIL", actual: `예외: ${err && err.message ? err.message : String(err)}` };
  }
}

async function main() {
  const { allowMissing, selectors, unknown } = parseArgs(process.argv.slice(2));
  if (unknown.length > 0) {
    console.error(`알 수 없는 인자: ${unknown.join(", ")}`);
    console.error("사용법: node skills/calc-rule-verify/scripts/verify.mjs [사례 ID(예: C-01) | C | R ...] [--allow-missing]");
    process.exitCode = 1;
    return;
  }
  const selected = selectors.length === 0 ? CASES : CASES.filter((c) => selectors.some((s) => s(c)));
  const modules = await loadModules();
  const counts = { PASS: 0, FAIL: 0, SKIP: 0 };
  console.log("사례 | 03절 | 항목 | 기대값 | 실제값 | 결과");
  for (const c of selected) {
    for (const chk of buildChecks(c)) {
      const { result, actual } = runCheck(chk, modules);
      counts[result] += 1;
      console.log(`${chk.caseId} | ${chk.sec} | ${chk.item} | ${showValue(chk.expected)} | ${actual} | ${result}`);
    }
  }
  console.log(`통과 ${counts.PASS} / 실패 ${counts.FAIL} / 건너뜀 ${counts.SKIP}`);
  process.exitCode = counts.FAIL > 0 || (counts.SKIP > 0 && !allowMissing) ? 1 : 0;
}

await main();
