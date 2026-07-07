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

    assert path.parent == tmp_path / "job_alio" / "detail" / "2026-07-07"
    assert path.name.startswith("302423-debug-true-")
    assert path.name.endswith(".json")
    loaded = store.read_sample(path)
    assert loaded.source == "job_alio"
    assert loaded.payload == {"recrutPblntSn": 302423, "instNm": "창업진흥원"}


def test_raw_sample_store_keeps_non_ascii_sample_ids_distinct(tmp_path) -> None:
    store = RawSampleStore(tmp_path)

    kisa_path = store.path_for(
        RawSample(
            source="job_alio",
            raw_type="list",
            sample_id="list-page-1-limit-5-한국인터넷진흥원",
            collected_at="2026-07-07T00:01:02Z",
            payload={},
        )
    )
    metro_path = store.path_for(
        RawSample(
            source="job_alio",
            raw_type="list",
            sample_id="list-page-1-limit-5-서울교통공사",
            collected_at="2026-07-07T00:01:02Z",
            payload={},
        )
    )

    assert kisa_path.name != metro_path.name
    assert kisa_path.name.startswith("list-page-1-limit-5-")
    assert metro_path.name.startswith("list-page-1-limit-5-")
    assert kisa_path.name.isascii()
    assert metro_path.name.isascii()


def test_raw_sample_store_shortens_long_url_sample_ids(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    path = store.path_for(
        RawSample(
            source="press_release",
            raw_type="html",
            sample_id=(
                "https://www.kepco.co.kr/home/media/newsroom/pr/boardView.do"
                "?boardMngNo=15&boardNo=3106-detail-html"
            ),
            collected_at="2026-07-07T00:01:02Z",
            payload={},
        )
    )

    assert len(path.stem) <= 80
    assert path.name.endswith(".json")
    assert path.name.isascii()
    assert "detail-html" in path.stem


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
