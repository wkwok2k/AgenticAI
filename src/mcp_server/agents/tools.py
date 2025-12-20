from typing import Any, Dict, List
from .schemas import HopBreak


def mock_top2_hop_breaks() -> List[HopBreak]:
    """Return two mocked hop-level breaks with full stats."""
    rows: List[Dict[str, Any]] = [
        {
            "recon_run_date": "2025-12-01",
            "hierarchy_path": "Global > FX > G10 > EURUSD",
            "hop_id": "HOP_FX_001",
            "total_rows": 120000,
            "eval_count": 120000,
            "eval_null_count": 500,
            "eval_valid_count": 119500,
            "eval_distinct_count": 3500,
            "p05": -2500000.0,
            "p50":  0.0,
            "p95":  3000000.0,
            "p99":  7500000.0,
            "exposure_amt": 95000000.0,
        },
        {
            "recon_run_date": "2025-12-01",
            "hierarchy_path": "Global > Rates > Swaps > USD",
            "hop_id": "HOP_RT_007",
            "total_rows": 85000,
            "eval_count": 85000,
            "eval_null_count": 0,
            "eval_valid_count": 85000,
            "eval_distinct_count": 1200,
            "p05": -1000000.0,
            "p50":  100000.0,
            "p95":  1800000.0,
            "p99":  4000000.0,
            "exposure_amt": 60000000.0,
        },
    ]

    return [HopBreak(**row) for row in rows]
