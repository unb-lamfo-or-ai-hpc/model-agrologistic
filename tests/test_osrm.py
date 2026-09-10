from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from src.logic.osrm import (
    OSRMClient,
    OSRMNoRouteError,
    OSRMResponseError,
    OSRMUnavailableError,
)


def _response(payload: dict) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_distance_matrix_chunks_and_preserves_provenance():
    calls: list[tuple[str, float]] = []

    def request_get(url: str, *, timeout: float):
        calls.append((url, timeout))
        source_count = len(url.split("sources=")[1].split("&")[0].split(";"))
        destination_count = len(
            url.split("destinations=")[1].split("&")[0].split(";")
        )
        return _response(
            {
                "code": "Ok",
                "data_version": "brazil-2026-09",
                "distances": [
                    [1000.0] * destination_count for _ in range(source_count)
                ],
                "durations": [
                    [100.0] * destination_count for _ in range(source_count)
                ],
                "sources": [{"distance": 0.0}] * source_count,
                "destinations": [{"distance": 0.0}] * destination_count,
            }
        )

    client = OSRMClient(
        base_url="http://osrm.test",
        max_table_size=4,
        request_get=request_get,
    )
    result = client.get_distance_matrix_detailed(
        [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)],
        [(10.0, 10.0), (11.0, 11.0), (12.0, 12.0)],
    )

    assert result.request_count == 4
    assert len(calls) == 4
    assert result.distances_m == [[1000.0] * 3 for _ in range(3)]
    assert result.durations_s == [[100.0] * 3 for _ in range(3)]
    assert result.sources == [["osrm"] * 3 for _ in range(3)]
    assert result.fallback_count == 0
    assert result.data_versions == ("brazil-2026-09",)
    assert "annotations=distance,duration" in calls[0][0]


def test_service_failure_is_fatal_and_never_uses_haversine():
    def request_get(_url: str, *, timeout: float):
        del timeout
        raise requests.ConnectionError("service unavailable")

    client = OSRMClient(
        request_get=request_get,
        retries=1,
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(OSRMUnavailableError, match="2 attempts"):
        client.get_distance_matrix([(0.0, 0.0)], [(1.0, 1.0)])


def test_null_route_uses_audited_haversine_fallback():
    client = OSRMClient(
        request_get=lambda _url, timeout: _response(
            {
                "code": "Ok",
                "distances": [[None]],
                "durations": [[None]],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}],
            }
        )
    )

    result = client.get_distance_matrix_detailed(
        [(0.0, 0.0)],
        [(1.0, 1.0)],
    )

    assert result.distances_m[0][0] > 200_000
    assert result.durations_s == [[None]]
    assert result.sources == [["haversine_fallback"]]
    assert result.fallback_reasons == [["osrm_no_route"]]
    assert result.fallback_count == 1


def test_excessive_snap_uses_audited_haversine_fallback():
    client = OSRMClient(
        max_snap_distance_m=100.0,
        request_get=lambda _url, timeout: _response(
            {
                "code": "Ok",
                "distances": [[123.0]],
                "durations": [[12.0]],
                "sources": [{"distance": 101.0}],
                "destinations": [{"distance": 0.0}],
            }
        ),
    )

    result = client.get_distance_matrix_detailed(
        [(0.0, 0.0)],
        [(1.0, 1.0)],
    )

    assert result.sources == [["haversine_fallback"]]
    assert result.fallback_reasons == [["osrm_snap_exceeds_limit"]]


def test_no_route_can_fail_closed():
    client = OSRMClient(
        fallback_on_no_route=False,
        request_get=lambda _url, timeout: _response(
            {
                "code": "NoTable",
                "message": "No route found",
            }
        ),
    )

    with pytest.raises(OSRMNoRouteError, match="osrm_no_table"):
        client.get_distance_matrix([(0.0, 0.0)], [(1.0, 1.0)])


def test_malformed_table_response_is_fatal():
    client = OSRMClient(
        request_get=lambda _url, timeout: _response(
            {
                "code": "Ok",
                "distances": [[100.0]],
                "durations": [],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}],
            }
        )
    )

    with pytest.raises(OSRMResponseError, match="duration matrix"):
        client.get_distance_matrix([(0.0, 0.0)], [(1.0, 1.0)])


def test_cache_requires_immutable_dataset_identity(tmp_path):
    with pytest.raises(ValueError, match="dataset_id"):
        OSRMClient(cache_path=tmp_path / "routes.sqlite")


def test_complete_cache_hit_avoids_osrm_request(tmp_path):
    calls = 0

    def request_get(_url: str, *, timeout: float):
        nonlocal calls
        del timeout
        calls += 1
        return _response(
            {
                "code": "Ok",
                "data_version": "brazil-260901-osrm-v6",
                "distances": [[1234.0]],
                "durations": [[120.0]],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}],
            }
        )

    cache_path = tmp_path / "routes.sqlite"
    client = OSRMClient(
        dataset_id="pbf-sha256:abc;osrm:v6;profile:driving",
        cache_path=cache_path,
        request_get=request_get,
    )
    first = client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])
    second = client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])

    assert calls == 1
    assert first.cache_hit_count == 0
    assert first.cache_miss_count == 1
    assert first.cache_write_count == 1
    assert second.request_count == 0
    assert second.cache_hit_count == 1
    assert second.cache_miss_count == 0
    assert second.cache_write_count == 0
    assert second.distances_m == [[1234.0]]
    assert second.data_versions == ("brazil-260901-osrm-v6",)


def test_partial_cache_request_queries_only_missing_pairs(tmp_path):
    urls: list[str] = []

    def request_get(url: str, *, timeout: float):
        del timeout
        urls.append(url)
        destination_count = len(
            url.split("destinations=")[1].split("&")[0].split(";")
        )
        return _response(
            {
                "code": "Ok",
                "data_version": "brazil-260901-osrm-v6",
                "distances": [[1000.0] * destination_count],
                "durations": [[100.0] * destination_count],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}] * destination_count,
            }
        )

    cache_path = tmp_path / "routes.sqlite"
    client = OSRMClient(
        dataset_id="dataset-a",
        cache_path=cache_path,
        request_get=request_get,
    )
    client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])
    urls.clear()
    result = client.get_distance_matrix_detailed(
        [(0.0, 0.0)],
        [(1.0, 1.0), (2.0, 2.0)],
    )

    assert len(urls) == 1
    assert "2.0,2.0" in urls[0]
    assert "1.0,1.0" not in urls[0]
    assert result.cache_hit_count == 1
    assert result.cache_miss_count == 1
    assert result.cache_write_count == 1


def test_cache_identity_separates_osrm_datasets(tmp_path):
    calls = 0

    def request_get(_url: str, *, timeout: float):
        nonlocal calls
        del timeout
        calls += 1
        return _response(
            {
                "code": "Ok",
                "distances": [[float(calls)]],
                "durations": [[10.0]],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}],
            }
        )

    cache_path = tmp_path / "routes.sqlite"
    for dataset_id in ("dataset-a", "dataset-b"):
        client = OSRMClient(
            dataset_id=dataset_id,
            cache_path=cache_path,
            request_get=request_get,
        )
        result = client.get_distance_matrix_detailed(
            [(0.0, 0.0)],
            [(1.0, 1.0)],
        )
        assert result.cache_miss_count == 1

    assert calls == 2


def test_audited_fallback_is_persisted(tmp_path):
    calls = 0

    def request_get(_url: str, *, timeout: float):
        nonlocal calls
        del timeout
        calls += 1
        return _response(
            {
                "code": "Ok",
                "distances": [[None]],
                "durations": [[None]],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}],
            }
        )

    client = OSRMClient(
        dataset_id="dataset-a",
        cache_path=tmp_path / "routes.sqlite",
        request_get=request_get,
    )
    first = client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])
    second = client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])

    assert calls == 1
    assert first.sources == [["haversine_fallback"]]
    assert second.sources == [["haversine_fallback"]]
    assert second.fallback_reasons == [["osrm_no_route"]]
    assert second.cache_hit_count == 1


def test_operational_failure_is_not_persisted(tmp_path):
    calls = 0

    def request_get(_url: str, *, timeout: float):
        nonlocal calls
        del timeout
        calls += 1
        if calls == 1:
            raise requests.ConnectionError("temporary failure")
        return _response(
            {
                "code": "Ok",
                "distances": [[321.0]],
                "durations": [[32.0]],
                "sources": [{"distance": 0.0}],
                "destinations": [{"distance": 0.0}],
            }
        )

    client = OSRMClient(
        dataset_id="dataset-a",
        cache_path=tmp_path / "routes.sqlite",
        retries=0,
        request_get=request_get,
    )
    with pytest.raises(OSRMUnavailableError):
        client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])

    second = client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])
    third = client.get_distance_matrix_detailed([(0.0, 0.0)], [(1.0, 1.0)])

    assert calls == 2
    assert second.cache_miss_count == 1
    assert second.cache_write_count == 1
    assert third.cache_hit_count == 1

