"""Auditable OSRM distance and route client.

OSRM is the primary road-distance authority. Haversine estimates are permitted
only for pairs that OSRM identifies as unroutable or whose snapped coordinate
is farther from the road graph than the configured tolerance. Transport or
service failures are fatal and never trigger the fallback.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

Coordinate = tuple[float, float]
RequestGet = Callable[..., Any]
CACHE_SCHEMA_VERSION = 1


class OSRMError(RuntimeError):
    """Base class for auditable OSRM failures."""


class OSRMUnavailableError(OSRMError):
    """Raised when the OSRM service cannot be reached reliably."""


class OSRMResponseError(OSRMError):
    """Raised when OSRM returns an invalid or unsupported response."""


class OSRMNoRouteError(OSRMError):
    """Raised when OSRM cannot route a pair and fallback is disabled."""


@dataclass(frozen=True, slots=True)
class OSRMCacheRecord:
    """One provenance-bound route record stored in the persistent cache."""

    cache_key: str
    key_payload_json: str
    distance_m: float
    duration_s: float | None
    source: str
    fallback_reason: str | None
    data_version: str | None
    created_at_utc: str


class OSRMPairCache:
    """Persistent SQLite cache for ordered OSRM coordinate pairs."""

    def __init__(self, path: str | Path, *, busy_timeout_ms: int = 30_000) -> None:
        if busy_timeout_ms <= 0:
            raise ValueError("busy_timeout_ms must be positive.")

        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def read_many(self, cache_keys: list[str]) -> dict[str, OSRMCacheRecord]:
        """Read existing cache records without changing their timestamps."""

        if not cache_keys:
            return {}

        records: dict[str, OSRMCacheRecord] = {}
        with self._connect() as connection:
            for start in range(0, len(cache_keys), 900):
                chunk = cache_keys[start : start + 900]
                placeholders = ",".join("?" for _ in chunk)
                rows = connection.execute(
                    "SELECT cache_key, key_payload_json, distance_m, duration_s, "
                    "source, fallback_reason, data_version, created_at_utc "
                    f"FROM osrm_pair_cache WHERE cache_key IN ({placeholders})",
                    chunk,
                ).fetchall()
                for row in rows:
                    record = OSRMCacheRecord(*row)
                    records[record.cache_key] = record
        return records

    def write_many(self, records: list[OSRMCacheRecord]) -> int:
        """Atomically insert new records and preserve concurrent first writers."""

        if not records:
            return 0

        with self._connect() as connection:
            before = connection.total_changes
            connection.executemany(
                "INSERT OR IGNORE INTO osrm_pair_cache ("
                "cache_key, key_payload_json, distance_m, duration_s, source, "
                "fallback_reason, data_version, created_at_utc"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        record.cache_key,
                        record.key_payload_json,
                        record.distance_m,
                        record.duration_s,
                        record.source,
                        record.fallback_reason,
                        record.data_version,
                        record.created_at_utc,
                    )
                    for record in records
                ],
            )
            return connection.total_changes - before

    def _initialize(self) -> None:
        with self._connect() as connection:
            current_version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            if current_version not in {0, CACHE_SCHEMA_VERSION}:
                raise OSRMError(
                    "Unsupported OSRM cache schema version "
                    f"{current_version}; expected {CACHE_SCHEMA_VERSION}."
                )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS osrm_pair_cache ("
                "cache_key TEXT PRIMARY KEY, "
                "key_payload_json TEXT NOT NULL, "
                "distance_m REAL NOT NULL, "
                "duration_s REAL, "
                "source TEXT NOT NULL, "
                "fallback_reason TEXT, "
                "data_version TEXT, "
                "created_at_utc TEXT NOT NULL"
                ")"
            )
            connection.execute(f"PRAGMA user_version = {CACHE_SCHEMA_VERSION}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_ms / 1_000.0,
        )
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection


@dataclass(frozen=True, slots=True)
class OSRMMatrixResult:
    """Distance matrix and cell-level routing provenance."""

    distances_m: list[list[float]]
    durations_s: list[list[float | None]]
    sources: list[list[str]]
    fallback_reasons: list[list[str | None]]
    request_count: int
    data_versions: tuple[str, ...]
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    cache_write_count: int = 0

    @property
    def fallback_count(self) -> int:
        """Return the number of cells estimated outside the road graph."""

        return sum(
            source == "haversine_fallback"
            for row in self.sources
            for source in row
        )


class OSRMClient:
    """Query OSRM Table and Route services with explicit fallback semantics."""

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        max_table_size: int = 100,
        *,
        profile: str = "driving",
        timeout_seconds: float = 30.0,
        retries: int = 2,
        retry_backoff_seconds: float = 0.25,
        max_snap_distance_m: float = 50_000.0,
        haversine_fallback_factor: float = 1.3,
        fallback_on_no_route: bool = True,
        dataset_id: str | None = None,
        cache_path: str | Path | None = None,
        cache_busy_timeout_ms: int = 30_000,
        request_get: RequestGet | None = None,
    ) -> None:
        if max_table_size < 2:
            raise ValueError("max_table_size must be at least 2.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if retries < 0:
            raise ValueError("retries cannot be negative.")
        if max_snap_distance_m < 0:
            raise ValueError("max_snap_distance_m cannot be negative.")
        if haversine_fallback_factor < 1:
            raise ValueError("haversine_fallback_factor must be at least 1.")
        if cache_path is not None and not str(dataset_id or "").strip():
            raise ValueError(
                "dataset_id must be a non-empty immutable identifier when "
                "cache_path is configured."
            )

        self.base_url = base_url.rstrip("/")
        self.max_table_size = max_table_size
        self.profile = profile
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.max_snap_distance_m = max_snap_distance_m
        self.haversine_fallback_factor = haversine_fallback_factor
        self.fallback_on_no_route = fallback_on_no_route
        self.dataset_id = str(dataset_id).strip() if dataset_id else None
        self._cache = (
            OSRMPairCache(cache_path, busy_timeout_ms=cache_busy_timeout_ms)
            if cache_path is not None
            else None
        )
        self._request_get = request_get or requests.get

    def get_distance_matrix(
        self,
        origins: list[Coordinate],
        destinations: list[Coordinate],
    ) -> list[list[float]]:
        """Return distances in metres for compatibility with existing callers."""

        return self.get_distance_matrix_detailed(
            origins,
            destinations,
        ).distances_m

    def get_distance_matrix_detailed(
        self,
        origins: list[Coordinate],
        destinations: list[Coordinate],
    ) -> OSRMMatrixResult:
        """Return OSRM distances, durations, and cell-level provenance."""

        if not origins or not destinations:
            return OSRMMatrixResult([], [], [], [], 0, ())

        checked_origins = [self._validate_coordinate(item) for item in origins]
        checked_destinations = [
            self._validate_coordinate(item) for item in destinations
        ]
        row_count = len(checked_origins)
        column_count = len(checked_destinations)
        distances: list[list[float | None]] = [
            [None] * column_count for _ in range(row_count)
        ]
        durations: list[list[float | None]] = [
            [None] * column_count for _ in range(row_count)
        ]
        sources: list[list[str | None]] = [
            [None] * column_count for _ in range(row_count)
        ]
        reasons: list[list[str | None]] = [
            [None] * column_count for _ in range(row_count)
        ]
        cell_data_versions: list[list[str | None]] = [
            [None] * column_count for _ in range(row_count)
        ]

        request_count = 0
        data_versions: set[str] = set()
        cache_hit_count = 0
        cache_miss_count = 0
        cache_write_count = 0
        cache_keys: dict[tuple[int, int], tuple[str, str]] = {}
        missing_columns_by_row: dict[int, tuple[int, ...]] = {}

        if self._cache is None:
            missing_columns_by_row = {
                row: tuple(range(column_count)) for row in range(row_count)
            }
        else:
            for row, origin in enumerate(checked_origins):
                for column, destination in enumerate(checked_destinations):
                    cache_keys[row, column] = self._cache_identity(
                        origin,
                        destination,
                    )
            cached = self._cache.read_many(
                [cache_key for cache_key, _ in cache_keys.values()]
            )
            for row in range(row_count):
                missing: list[int] = []
                for column in range(column_count):
                    cache_key, _ = cache_keys[row, column]
                    record = cached.get(cache_key)
                    if record is None:
                        missing.append(column)
                        cache_miss_count += 1
                        continue
                    distances[row][column] = record.distance_m
                    durations[row][column] = record.duration_s
                    sources[row][column] = record.source
                    reasons[row][column] = record.fallback_reason
                    if record.data_version:
                        data_versions.add(record.data_version)
                    cache_hit_count += 1
                if missing:
                    missing_columns_by_row[row] = tuple(missing)

        grouped_rows: dict[tuple[int, ...], list[int]] = {}
        for row, columns in missing_columns_by_row.items():
            grouped_rows.setdefault(columns, []).append(row)

        for column_indices, row_indices in grouped_rows.items():
            if len(row_indices) + len(column_indices) <= self.max_table_size:
                row_chunk_size = len(row_indices)
                column_chunk_size = len(column_indices)
            else:
                row_chunk_size = max(1, self.max_table_size // 2)
                column_chunk_size = max(1, self.max_table_size - row_chunk_size)

            for row_start in range(0, len(row_indices), row_chunk_size):
                row_chunk = row_indices[row_start : row_start + row_chunk_size]
                origin_chunk = [checked_origins[row] for row in row_chunk]
                for column_start in range(
                    0,
                    len(column_indices),
                    column_chunk_size,
                ):
                    column_chunk = column_indices[
                        column_start : column_start + column_chunk_size
                    ]
                    destination_chunk = [
                        checked_destinations[column] for column in column_chunk
                    ]
                    payload = self._table_request(origin_chunk, destination_chunk)
                    request_count += 1
                    raw_data_version = payload.get("data_version")
                    data_version = (
                        str(raw_data_version) if raw_data_version else None
                    )
                    if data_version:
                        data_versions.add(data_version)
                    self._apply_table_chunk(
                        payload=payload,
                        origins=origin_chunk,
                        destinations=destination_chunk,
                        row_indices=row_chunk,
                        column_indices=list(column_chunk),
                        distances=distances,
                        durations=durations,
                        sources=sources,
                        reasons=reasons,
                    )
                    for row in row_chunk:
                        for column in column_chunk:
                            cell_data_versions[row][column] = data_version

        if self._cache is not None and cache_miss_count:
            created_at_utc = datetime.now(UTC).isoformat()
            records = []
            for (row, column), (cache_key, key_payload_json) in cache_keys.items():
                if row not in missing_columns_by_row:
                    continue
                if column not in missing_columns_by_row[row]:
                    continue
                records.append(
                    OSRMCacheRecord(
                        cache_key=cache_key,
                        key_payload_json=key_payload_json,
                        distance_m=float(distances[row][column]),
                        duration_s=durations[row][column],
                        source=str(sources[row][column]),
                        fallback_reason=reasons[row][column],
                        data_version=cell_data_versions[row][column],
                        created_at_utc=created_at_utc,
                    )
                )
            cache_write_count = self._cache.write_many(records)

        unresolved = [
            (row, column)
            for row in range(row_count)
            for column in range(column_count)
            if distances[row][column] is None or sources[row][column] is None
        ]
        if unresolved:
            raise OSRMResponseError(
                f"OSRM matrix left {len(unresolved)} cells without provenance."
            )

        return OSRMMatrixResult(
            distances_m=[
                [float(value) for value in row if value is not None]
                for row in distances
            ],
            durations_s=durations,
            sources=[
                [str(value) for value in row if value is not None]
                for row in sources
            ],
            fallback_reasons=reasons,
            request_count=request_count,
            data_versions=tuple(sorted(data_versions)),
            cache_hit_count=cache_hit_count,
            cache_miss_count=cache_miss_count,
            cache_write_count=cache_write_count,
        )

    def _cache_identity(
        self,
        origin: Coordinate,
        destination: Coordinate,
    ) -> tuple[str, str]:
        payload = {
            "annotations": ["distance", "duration"],
            "dataset_id": self.dataset_id,
            "destination": [destination[0], destination[1]],
            "fallback_on_no_route": self.fallback_on_no_route,
            "haversine_fallback_factor": self.haversine_fallback_factor,
            "max_snap_distance_m": self.max_snap_distance_m,
            "origin": [origin[0], origin[1]],
            "profile": self.profile,
            "schema_version": CACHE_SCHEMA_VERSION,
            "service": "table",
        }
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest(), serialized

    def get_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
    ) -> dict[str, Any]:
        """Return an OSRM route or an explicitly classified fallback."""

        origin = self._validate_coordinate(origin)
        destination = self._validate_coordinate(destination)
        coordinate_path = self._coordinate_path([origin, destination])
        url = (
            f"{self.base_url}/route/v1/{self.profile}/{coordinate_path}"
            "?overview=full&geometries=geojson"
        )
        payload = self._request_json(url)

        if payload.get("code") == "NoRoute":
            return self._fallback_route_or_raise(
                origin,
                destination,
                "osrm_no_route",
            )
        if payload.get("code") != "Ok":
            raise OSRMResponseError(
                "OSRM Route service returned code "
                f"{payload.get('code')!r}: {payload.get('message', '')}"
            )

        routes = payload.get("routes")
        waypoints = payload.get("waypoints")
        if not isinstance(routes, list) or not routes:
            raise OSRMResponseError("OSRM Route response has no routes.")
        if not isinstance(waypoints, list) or len(waypoints) != 2:
            raise OSRMResponseError("OSRM Route response has invalid waypoints.")

        if self._bad_snap_indices(waypoints):
            return self._fallback_route_or_raise(
                origin,
                destination,
                "osrm_snap_exceeds_limit",
            )

        route = routes[0]
        try:
            return {
                "geometry": route["geometry"],
                "distance": float(route["distance"]),
                "duration": float(route["duration"]),
                "type": "osrm",
                "fallback_reason": None,
                "data_version": payload.get("data_version"),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise OSRMResponseError(
                "OSRM Route response has invalid route fields."
            ) from exc

    def _table_request(
        self,
        origins: list[Coordinate],
        destinations: list[Coordinate],
    ) -> dict[str, Any]:
        coordinates = origins + destinations
        source_indices = range(len(origins))
        destination_indices = range(len(origins), len(coordinates))
        url = (
            f"{self.base_url}/table/v1/{self.profile}/"
            f"{self._coordinate_path(coordinates)}"
            f"?sources={';'.join(map(str, source_indices))}"
            f"&destinations={';'.join(map(str, destination_indices))}"
            "&annotations=distance,duration"
        )
        payload = self._request_json(url)
        code = payload.get("code")
        if code not in {"Ok", "NoTable"}:
            raise OSRMResponseError(
                f"OSRM Table service returned code {code!r}: "
                f"{payload.get('message', '')}"
            )
        return payload

    def _apply_table_chunk(
        self,
        *,
        payload: dict[str, Any],
        origins: list[Coordinate],
        destinations: list[Coordinate],
        row_indices: list[int],
        column_indices: list[int],
        distances: list[list[float | None]],
        durations: list[list[float | None]],
        sources: list[list[str | None]],
        reasons: list[list[str | None]],
    ) -> None:
        if payload.get("code") == "NoTable":
            for row, origin in enumerate(origins):
                for column, destination in enumerate(destinations):
                    self._assign_fallback(
                        origin,
                        destination,
                        "osrm_no_table",
                        row_indices[row],
                        column_indices[column],
                        distances,
                        durations,
                        sources,
                        reasons,
                    )
            return

        raw_distances = payload.get("distances")
        raw_durations = payload.get("durations")
        if not self._matrix_shape_matches(
            raw_distances,
            len(origins),
            len(destinations),
        ):
            raise OSRMResponseError("OSRM Table distance matrix has invalid shape.")
        if not self._matrix_shape_matches(
            raw_durations,
            len(origins),
            len(destinations),
        ):
            raise OSRMResponseError("OSRM Table duration matrix has invalid shape.")

        raw_sources = payload.get("sources")
        raw_destinations = payload.get("destinations")
        if not isinstance(raw_sources, list) or len(raw_sources) != len(origins):
            raise OSRMResponseError("OSRM Table response has invalid sources.")
        if (
            not isinstance(raw_destinations, list)
            or len(raw_destinations) != len(destinations)
        ):
            raise OSRMResponseError("OSRM Table response has invalid destinations.")

        bad_sources = self._bad_snap_indices(raw_sources)
        bad_destinations = self._bad_snap_indices(raw_destinations)

        for row, origin in enumerate(origins):
            for column, destination in enumerate(destinations):
                target_row = row_indices[row]
                target_column = column_indices[column]
                reason = None
                if row in bad_sources or column in bad_destinations:
                    reason = "osrm_snap_exceeds_limit"
                elif raw_distances[row][column] is None:
                    reason = "osrm_no_route"

                if reason is not None:
                    self._assign_fallback(
                        origin,
                        destination,
                        reason,
                        target_row,
                        target_column,
                        distances,
                        durations,
                        sources,
                        reasons,
                    )
                    continue

                try:
                    distances[target_row][target_column] = float(
                        raw_distances[row][column]
                    )
                    raw_duration = raw_durations[row][column]
                    durations[target_row][target_column] = (
                        None if raw_duration is None else float(raw_duration)
                    )
                except (TypeError, ValueError) as exc:
                    raise OSRMResponseError(
                        "OSRM Table response contains non-numeric values."
                    ) from exc
                sources[target_row][target_column] = "osrm"

    def _assign_fallback(
        self,
        origin: Coordinate,
        destination: Coordinate,
        reason: str,
        row: int,
        column: int,
        distances: list[list[float | None]],
        durations: list[list[float | None]],
        sources: list[list[str | None]],
        reasons: list[list[str | None]],
    ) -> None:
        route = self._fallback_route_or_raise(origin, destination, reason)
        distances[row][column] = float(route["distance"])
        durations[row][column] = None
        sources[row][column] = "haversine_fallback"
        reasons[row][column] = reason

    def _fallback_route_or_raise(
        self,
        origin: Coordinate,
        destination: Coordinate,
        reason: str,
    ) -> dict[str, Any]:
        if not self.fallback_on_no_route:
            raise OSRMNoRouteError(
                f"OSRM could not route {origin!r} -> {destination!r}: {reason}."
            )
        distance = (
            self._haversine_distance(origin, destination)
            * self.haversine_fallback_factor
        )
        return {
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [origin[1], origin[0]],
                    [destination[1], destination[0]],
                ],
            },
            "distance": distance,
            "duration": None,
            "type": "haversine_fallback",
            "fallback_reason": reason,
            "data_version": None,
        }

    def _request_json(self, url: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self._request_get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise OSRMResponseError(
                        "OSRM response body must be a JSON object."
                    )
                return payload
            except OSRMResponseError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))

        raise OSRMUnavailableError(
            f"OSRM request failed after {self.retries + 1} attempts: {last_error}"
        ) from last_error

    def _bad_snap_indices(self, waypoints: list[Any]) -> set[int]:
        bad: set[int] = set()
        for index, waypoint in enumerate(waypoints):
            if not isinstance(waypoint, dict):
                raise OSRMResponseError("OSRM waypoint must be a JSON object.")
            try:
                snap_distance = float(waypoint.get("distance", 0.0))
            except (TypeError, ValueError) as exc:
                raise OSRMResponseError(
                    "OSRM waypoint snap distance must be numeric."
                ) from exc
            if snap_distance > self.max_snap_distance_m:
                bad.add(index)
        return bad

    @staticmethod
    def _matrix_shape_matches(
        matrix: Any,
        row_count: int,
        column_count: int,
    ) -> bool:
        return (
            isinstance(matrix, list)
            and len(matrix) == row_count
            and all(isinstance(row, list) and len(row) == column_count for row in matrix)
        )

    @staticmethod
    def _coordinate_path(coordinates: list[Coordinate]) -> str:
        return ";".join(f"{longitude},{latitude}" for latitude, longitude in coordinates)

    @staticmethod
    def _validate_coordinate(coordinate: Coordinate) -> Coordinate:
        if len(coordinate) != 2:
            raise ValueError("Coordinates must be latitude-longitude pairs.")
        latitude = float(coordinate[0])
        longitude = float(coordinate[1])
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(f"Invalid coordinate {(latitude, longitude)!r}.")
        return latitude, longitude

    @staticmethod
    def _haversine_distance(
        coordinate_a: Coordinate,
        coordinate_b: Coordinate,
    ) -> float:
        latitude_a, longitude_a = coordinate_a
        latitude_b, longitude_b = coordinate_b
        earth_radius_m = 6_371_000.0

        latitude_a_rad = math.radians(latitude_a)
        latitude_b_rad = math.radians(latitude_b)
        delta_latitude = latitude_b_rad - latitude_a_rad
        delta_longitude = math.radians(longitude_b - longitude_a)
        haversine = (
            math.sin(delta_latitude / 2.0) ** 2
            + math.cos(latitude_a_rad)
            * math.cos(latitude_b_rad)
            * math.sin(delta_longitude / 2.0) ** 2
        )
        return 2.0 * earth_radius_m * math.asin(math.sqrt(haversine))

