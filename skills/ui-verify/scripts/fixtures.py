"""화면 검증용 미리 넣는 데이터.

docs/03_계산규칙.md 14절 사례(C-01~C-15, R-01~R-06)를 docs/02_설계문서.md 5.5 저장 객체(AppData)로 바꾼다.
규칙의 원본: docs/05_작업지시서.md T2-05 작업 내용 3번.

- 거래는 사례 표의 거래다. 추가 시도가 있는 사례(C-05, C-07, C-08, C-13)는 기존 거래만 넣는다.
- 거래 id 는 "C01-0" 처럼 사례 ID 와 배열 인덱스다.
- prices 는 사례의 현재가, targets 는 R 사례는 사례의 목표 비중, C 사례는 모두 0 이다.
- R-02 는 목표 비중 시도가 a, b 두 개다. docs/05_작업지시서.md 3.1 M-27(해소) 에 따라
  attempt 인자로 고르게 하고 기본값은 "a" 다.
"""

import copy

STORAGE_KEY = "portfolio-tracker:v1"
FIELDS = ("date", "name", "assetClass", "type", "quantity", "price", "fee")

_ZERO_TARGETS = {"stock": 0, "bond": 0, "cash": 0, "other": 0}

_R01_TXS = [
    ("2026-01-02", "종목S", "stock", "buy", 100, 60000, 0),
    ("2026-01-02", "종목T", "bond", "buy", 20, 100000, 0),
    ("2026-01-02", "현금", "cash", "buy", 1000000, 1, 0),
]
_R01_PRICES = {"종목S": 70000, "종목T": 100000}

# 사례 ID -> (거래 행 목록, 현재가, 목표 비중). 거래 행은 FIELDS 순서다.
_CASES = {
    "C-01": ([
        ("2026-01-02", "종목A", "stock", "buy", 10, 10000, 0),
        ("2026-01-03", "종목A", "stock", "buy", 10, 12000, 0),
        ("2026-01-04", "종목A", "stock", "sell", 5, 13000, 0),
    ], {}, None),
    "C-02": ([
        ("2026-02-02", "종목B", "stock", "buy", 10, 5000, 500),
        ("2026-02-03", "종목B", "stock", "buy", 20, 5600, 1000),
    ], {"종목B": 6000}, None),
    "C-03": ([
        ("2026-03-02", "종목C", "stock", "buy", 20, 8000, 0),
        ("2026-03-10", "종목C", "stock", "sell", 8, 9500, 1200),
        ("2026-03-11", "종목C", "stock", "sell", 2, 7000, 300),
    ], {"종목C": 8800}, None),
    "C-04": ([
        ("2026-04-01", "종목D", "stock", "buy", 10, 3000, 0),
        ("2026-04-05", "종목D", "stock", "sell", 10, 3600, 0),
        ("2026-04-10", "종목D", "stock", "buy", 5, 4000, 100),
        ("2026-04-12", "종목D", "stock", "sell", 2, 4500, 0),
    ], {"종목D": 4200}, None),
    "C-05": ([
        ("2026-05-02", "종목E", "stock", "buy", 10, 2000, 0),
    ], {}, None),
    "C-06": ([
        ("2026-06-01", "종목F", "stock", "buy", 10, 1000, 0),
        ("2026-06-02", "종목F", "stock", "sell", 10, 1500, 0),
        ("2026-06-02", "종목F", "stock", "buy", 10, 2000, 0),
    ], {"종목F": 2000}, None),
    "C-07": ([
        ("2026-07-01", "종목G", "stock", "buy", 10, 1000, 0),
        ("2026-07-10", "종목G", "stock", "sell", 8, 1200, 0),
    ], {}, None),
    "C-08": ([
        ("2026-07-01", "종목H", "stock", "buy", 10, 1000, 0),
        ("2026-07-10", "종목H", "stock", "sell", 8, 1200, 0),
    ], {}, None),
    "C-09": ([
        ("2026-08-01", "종목I", "stock", "buy", 10, 1000, 0),
        ("2026-08-02", "종목I", "stock", "buy", 5, 1300, 0),
        ("2026-08-03", "종목I", "stock", "sell", 12, 1500, 0),
    ], {}, None),
    "C-10": ([
        ("2026-09-01", "종목J", "stock", "buy", 10, 2500, 500),
    ], {}, None),
    "C-11": ([
        ("2026-09-01", "종목K", "stock", "buy", 3, 10000, 500),
        ("2026-09-02", "종목K", "stock", "sell", 1, 12000, 0),
    ], {"종목K": 11000}, None),
    "C-12": ([
        ("2026-09-01", "종목L", "stock", "buy", 300, 10000, 1000),
        ("2026-09-02", "종목L", "stock", "sell", 300, 10100, 0),
    ], {}, None),
    "C-13": ([
        ("2026-09-01", "종목M", "stock", "buy", 1, 50000, 0),
    ], {}, None),
    "C-14": ([
        ("2026-09-01", "현금", "cash", "buy", 1000000, 1, 0),
        ("2026-09-15", "현금", "cash", "sell", 300000, 1, 0),
    ], {}, None),
    "C-15": ([
        ("2026-09-01", "현금", "cash", "buy", 1000000, 1, 1000),
    ], {}, None),
    "R-01": (_R01_TXS, _R01_PRICES, {"stock": 60, "bond": 30, "cash": 10, "other": 0}),
    "R-02": (_R01_TXS, _R01_PRICES, {
        "a": {"stock": 60, "bond": 30, "cash": 5, "other": 0},
        "b": {"stock": 60, "bond": 30, "cash": 10, "other": 0.1},
    }),
    "R-03": (_R01_TXS, _R01_PRICES, {"stock": 0.1, "bond": 0.2, "cash": 84.1, "other": 15.6}),
    "R-04": ([
        ("2026-01-02", "종목U", "stock", "buy", 333, 10000, 0),
        ("2026-01-02", "종목V", "bond", "buy", 333, 10000, 0),
        ("2026-01-02", "현금", "cash", "buy", 3340001, 1, 0),
    ], {}, {"stock": 33.3, "bond": 33.3, "cash": 33.4, "other": 0}),
    "R-05": ([
        ("2026-01-02", "종목W", "stock", "buy", 10, 1000, 0),
        ("2026-01-03", "종목W", "stock", "sell", 10, 1200, 0),
    ], {}, {"stock": 60, "bond": 30, "cash": 10, "other": 0}),
    "R-06": ([
        ("2026-01-02", "종목N", "stock", "buy", 10, 50000, 5000),
        ("2026-01-02", "종목O", "bond", "buy", 30, 10000, 0),
        ("2026-01-02", "현금", "cash", "buy", 100000, 1, 0),
        ("2026-01-02", "종목P", "other", "buy", 5, 10000, 0),
    ], {"종목N": 55000, "종목P": 10000}, {"stock": 50, "bond": 35.5, "cash": 10, "other": 4.5}),
}

CASE_IDS = tuple(_CASES)


def case_data(case_id, attempt="a"):
    """사례 ID 의 저장 객체(dict)를 새로 만들어 반환한다. attempt 는 R-02 에서만 쓴다(M-27)."""
    if case_id not in _CASES:
        raise KeyError(f"알 수 없는 사례 ID: {case_id}")
    rows, prices, targets = _CASES[case_id]
    if case_id == "R-02":
        if attempt not in targets:
            raise KeyError(f"R-02 의 시도는 a 또는 b 다: {attempt}")
        targets = targets[attempt]
    prefix = case_id.replace("-", "")
    transactions = [
        {"id": f"{prefix}-{index}", **dict(zip(FIELDS, row))}
        for index, row in enumerate(rows)
    ]
    return {
        "version": 1,
        "transactions": transactions,
        "prices": copy.deepcopy(prices),
        "targets": copy.deepcopy(targets if targets is not None else _ZERO_TARGETS),
    }
