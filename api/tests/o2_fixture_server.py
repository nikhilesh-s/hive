"""Test-only model injection for browser/DB integration; not a production backend."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "api")]
from app.config import settings  # noqa: E402

if not settings.db_ingest_url or "hiveblot_o2" not in settings.db_ingest_url or "/private/tmp/" not in settings.db_ingest_url:
    raise RuntimeError("This fixture may only run against the isolated O-2 Unix-socket database")

from app.experimental import ingest  # noqa: E402
from app.main import app  # noqa: E402, F401
from western_blot_miner.llm_client import MockLLMClient  # noqa: E402
from western_blot_miner.resolve import LocalMapResolver  # noqa: E402

real_records_stage = ingest.pipeline.run_records_stage


def fixture_records(summary, **kwargs):
    # The actual preprocessor and biological reconciliation run, but these
    # deliberately uncertain model responses are test fixtures, not inference.
    return real_records_stage(summary, use_cache=False,
        client=MockLLMClient({"rows": [{"raw_target": "STAT3", "sample": "O-2 MOCK FIXTURE",
            "bands": [{"lane_index": 1, "lane_condition": "Test fixture only", "band_state": "uncertain", "confidence": "low"}]}]}),
        resolver=LocalMapResolver())


ingest.backend_ready = lambda: (True, "MOCK FIXTURE - no AI inference")
ingest.pipeline.run_records_stage = fixture_records
