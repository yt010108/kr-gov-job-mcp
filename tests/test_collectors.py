import hashlib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import PureWindowsPath
from threading import Barrier
from typing import Any

import pytest

from kr_gov_job_mcp.collectors import (
    CollectionResult,
    Collector,
    CollectorHttpPolicy,
    RawSample,
    RawSampleStore,
)
from kr_gov_job_mcp.collectors import raw_store


def make_raw_sample(
    *,
    sample_id: str = "sample-id",
    collected_at: str = "2026-07-07T00:01:02Z",
) -> RawSample:
    return RawSample(
        source="job_alio",
        raw_type="detail",
        sample_id=sample_id,
        collected_at=collected_at,
        payload={"recrutPblntSn": 302423, "instNm": "창업진흥원"},
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
    sample = make_raw_sample(sample_id="../302423?debug=true")

    path = store.write_sample(sample)

    sample_digest = hashlib.sha256(sample.sample_id.encode("utf-8")).hexdigest()[:32]
    time_digest = hashlib.sha256(sample.collected_at.encode("utf-8")).hexdigest()[:32]
    assert path == (
        tmp_path
        / "job_alio"
        / "detail"
        / "2026-07-07"
        / f"302423-debug-true-{sample_digest}-2026-07-07T00-01-02Z-{time_digest}.json"
    )
    loaded = store.read_sample(path)
    assert loaded.source == "job_alio"
    assert loaded.payload == {"recrutPblntSn": 302423, "instNm": "창업진흥원"}


def test_raw_sample_store_distinguishes_korean_sample_ids(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    korean_only = make_raw_sample(sample_id="한국인터넷진흥원")
    another_korean_id = make_raw_sample(sample_id="창업진흥원")

    korean_path = store.write_sample(korean_only)
    another_path = store.write_sample(another_korean_id)

    assert korean_path != another_path
    assert korean_path.name.startswith("unknown-")
    assert store.read_sample(korean_path).sample_id == "한국인터넷진흥원"
    assert store.read_sample(another_path).sample_id == "창업진흥원"


def test_raw_sample_store_uses_safe_filename_for_special_characters(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    path = store.write_sample(make_raw_sample(sample_id='CON<>:"/\\|?* sample'))

    assert all(character not in path.name for character in '<>:"/\\|?*')
    assert path.suffix == ".json"


def test_raw_sample_store_uses_safe_windows_directory_segments(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    sample = RawSample(
        source="CON.",
        raw_type="detail",
        sample_id="sample-id",
        collected_at="2026-07-07T00:01:02Z",
        payload={},
    )

    path = store.write_sample(sample)

    assert path.parts[-4] == "_CON"
    assert all(not part.endswith((".", " ")) for part in path.parts)


def test_raw_sample_store_uses_safe_windows_reserved_names_with_extensions(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    sample = RawSample(
        source="CON.txt",
        raw_type="detail",
        sample_id="LPT1.log",
        collected_at="2026-07-07T00:01:02Z",
        payload={},
    )

    path = store.write_sample(sample)

    assert path.parts[-4] == "_CON.txt"
    assert path.name.startswith("_LPT1.log-")


def test_raw_sample_store_limits_long_sample_id_filename(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    path = store.write_sample(make_raw_sample(sample_id="long-id-" * 300))

    assert len(path.name) <= 160
    assert store.read_sample(path).sample_id == "long-id-" * 300


def test_raw_sample_store_leaves_room_for_legacy_windows_path_limit(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    path = store.path_for(make_raw_sample(sample_id="long-id-" * 300))
    relative_path = path.relative_to(tmp_path)
    representative_root = PureWindowsPath(
        "C:/Users/runner/work/kr-gov-job-mcp/kr-gov-job-mcp/data/raw_samples"
    )
    windows_path = representative_root.joinpath(*relative_path.parts)

    assert len(str(windows_path)) <= 260


def test_raw_sample_store_keeps_same_id_from_different_collection_times(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    first = make_raw_sample(collected_at="2026-07-07T00:01:02Z")
    second = make_raw_sample(collected_at="2026-07-07T00:01:03Z")

    first_path = store.write_sample(first)
    second_path = store.write_sample(second)

    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()


def test_raw_sample_store_rejects_existing_final_path_without_overwriting(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    sample = make_raw_sample()
    path = store.write_sample(sample)

    with pytest.raises(FileExistsError, match="Raw sample already exists"):
        store.write_sample(sample)

    assert store.read_sample(path) == sample


def test_raw_sample_store_allows_exactly_one_concurrent_writer(tmp_path, monkeypatch) -> None:
    store = RawSampleStore(tmp_path)
    sample = make_raw_sample()
    publish_barrier = Barrier(2)
    original_link = raw_store.os.link

    def synchronized_link(source, destination):
        publish_barrier.wait(timeout=5)
        return original_link(source, destination)

    monkeypatch.setattr(raw_store.os, "link", synchronized_link)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(store.write_sample, sample) for _ in range(2)]

    successful_paths = []
    failures = []
    for future in futures:
        try:
            successful_paths.append(future.result())
        except FileExistsError as error:
            failures.append(error)

    assert successful_paths == [store.path_for(sample)]
    assert len(failures) == 1
    assert store.read_sample(successful_paths[0]) == sample
    assert not list(successful_paths[0].parent.glob("*.tmp"))


def test_raw_sample_store_reads_existing_legacy_path(tmp_path) -> None:
    store = RawSampleStore(tmp_path)
    sample = make_raw_sample(sample_id="legacy-sample")
    legacy_path = tmp_path / "job_alio" / "detail" / "2026-07-07" / "legacy-sample.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(sample.model_dump_json(indent=2) + "\n", encoding="utf-8")

    assert store.read_sample(legacy_path) == sample


def test_raw_sample_store_cleans_up_temp_file_when_publish_fails(tmp_path, monkeypatch) -> None:
    store = RawSampleStore(tmp_path)
    sample = make_raw_sample()
    path = store.path_for(sample)

    def fail_publish(source, destination):
        raise OSError("publish failed")

    monkeypatch.setattr(raw_store.os, "link", fail_publish)

    with pytest.raises(OSError, match="publish failed"):
        store.write_sample(sample)

    assert not path.exists()
    assert not list(path.parent.glob("*.tmp"))


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
