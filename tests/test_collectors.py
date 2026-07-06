from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.collectors import (
    CollectionResult,
    Collector,
    CollectorHttpPolicy,
    RawSample,
    RawSampleStore,
)


def test_http_policy_defaults_match_collector_baseline() -> None:
    policy = CollectorHttpPolicy()

    assert policy.timeout_seconds == 10.0
    assert policy.retry_attempts == 2
    assert policy.retry_backoff_seconds == 0.5
    assert policy.rate_limit_per_second == 1.0
    assert policy.user_agent == "kr-gov-job-mcp/0.1 (raw-data-observation)"


def test_raw_sample_store_writes_partitioned_json(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    sample = RawSample(
        source="job_alio",
        raw_type="detail",
        sample_id="../302423?debug=true",
        collected_at="2026-07-07T00:01:02Z",
        payload={"recrutPblntSn": 302423, "instNm": "창업진흥원"},
    )

    path = store.write_sample(sample)

    assert path == tmp_path / "job_alio" / "detail" / "2026-07-07" / "302423-debug-true.json"
    loaded = store.read_sample(path)
    assert loaded.source == "job_alio"
    assert loaded.payload == {"recrutPblntSn": 302423, "instNm": "창업진흥원"}


def test_collector_protocol_accepts_common_interface(tmp_path) -> None:
    class FakeCollector:
        name = "fake_source"
        http_policy = CollectorHttpPolicy()

        async def collect_raw(
            self,
            *,
            query: Mapping[str, Any],
            sample_store: RawSampleStore,
        ) -> CollectionResult:
            sample = RawSample(
                source=self.name,
                raw_type="metadata",
                sample_id=str(query["id"]),
                payload={"ok": True},
            )
            path = sample_store.write_sample(sample)
            return CollectionResult(source=self.name, run_id="test-run", raw_sample_paths=[path])

    collector = FakeCollector()

    assert isinstance(collector, Collector)
