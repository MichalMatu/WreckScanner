from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from string import hexdigits
from typing import Any

ZIP_MAX_MEMBERS = 20_000
ZIP_MAX_TOTAL_UNCOMPRESSED_BYTES = 64 * 1024 * 1024 * 1024
ZIP_MAX_COMPRESSION_RATIO = 500.0
ZIP_MAX_MANIFEST_BYTES = 16 * 1024 * 1024
ZIP_READ_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class ZipRestoreLimits:
    max_members: int = ZIP_MAX_MEMBERS
    max_total_uncompressed_bytes: int = ZIP_MAX_TOTAL_UNCOMPRESSED_BYTES
    max_compression_ratio: float = ZIP_MAX_COMPRESSION_RATIO
    max_manifest_bytes: int = ZIP_MAX_MANIFEST_BYTES

    def __post_init__(self) -> None:
        if self.max_members <= 0:
            raise ValueError("Limit liczby wpisów ZIP musi być dodatni.")
        if self.max_total_uncompressed_bytes <= 0:
            raise ValueError("Limit rozmiaru ZIP musi być dodatni.")
        if self.max_compression_ratio <= 1:
            raise ValueError("Limit współczynnika kompresji ZIP musi być większy od 1.")
        if self.max_manifest_bytes <= 0:
            raise ValueError("Limit rozmiaru manifestu ZIP musi być dodatni.")


DEFAULT_ZIP_RESTORE_LIMITS = ZipRestoreLimits()
SUPPORTED_ZIP_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})


def _invalid_raw_archive_name(name: str) -> bool:
    return not name or name.startswith("/") or "\\" in name or "\x00" in name


def _invalid_archive_path_parts(path: PurePosixPath, parts: list[str]) -> bool:
    return path.is_absolute() or any(part in ("", ".", "..") for part in parts)


def _has_windows_drive_prefix(parts: list[str]) -> bool:
    return len(parts[0]) >= 2 and parts[0][1] == ":"


def _require_relative_archive_path(name: str) -> Path:
    if _invalid_raw_archive_name(name):
        raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {name}")
    normalized = name[:-1] if name.endswith("/") else name
    parts = normalized.split("/")
    path = PurePosixPath(normalized)
    if _invalid_archive_path_parts(path, parts):
        raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {name}")
    if _has_windows_drive_prefix(parts):
        raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {name}")
    return Path(*parts)


def _canonical_member_names(member: zipfile.ZipInfo) -> tuple[str, str]:
    relative_path = _require_relative_archive_path(member.filename)
    destination_name = relative_path.as_posix()
    canonical_name = destination_name
    if member.is_dir():
        canonical_name = f"{destination_name}/"
    if member.filename != canonical_name:
        raise ValueError(f"Nienormalna ścieżka w archiwum ZIP: {member.filename}")
    return destination_name, canonical_name


def _register_unique_member(
    member: zipfile.ZipInfo,
    *,
    destination_name: str,
    canonical_name: str,
    members: dict[str, zipfile.ZipInfo],
    destinations: set[str],
) -> None:
    if destination_name in destinations:
        raise ValueError(f"Powtórzona ścieżka w archiwum ZIP: {destination_name}")
    destinations.add(destination_name)
    members[canonical_name] = member


def _validate_member_storage_type(member: zipfile.ZipInfo) -> None:
    if member.flag_bits & 0x1:
        raise ValueError(f"Zaszyfrowany wpis ZIP nie jest obsługiwany: {member.filename}")
    if member.compress_type not in SUPPORTED_ZIP_COMPRESSION:
        raise ValueError(f"Nieobsługiwana metoda kompresji ZIP: {member.filename}")
    unix_mode = (member.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(unix_mode)
    expected_type = stat.S_IFDIR if member.is_dir() else stat.S_IFREG
    if file_type not in (0, expected_type):
        raise ValueError(f"Wpis ZIP nie jest zwykłym plikiem ani katalogiem: {member.filename}")


def _validate_member_declared_sizes(member: zipfile.ZipInfo) -> None:
    if member.file_size < 0 or member.compress_size < 0:
        raise ValueError(f"Nieprawidłowy rozmiar wpisu ZIP: {member.filename}")
    if member.is_dir() and (member.file_size != 0 or member.compress_size != 0):
        raise ValueError(f"Katalog ZIP zawiera niedozwolone dane: {member.filename}")


def _updated_total_uncompressed(
    total_uncompressed: int,
    member: zipfile.ZipInfo,
    limits: ZipRestoreLimits,
) -> int:
    updated_total = total_uncompressed + member.file_size
    if updated_total > limits.max_total_uncompressed_bytes:
        raise ValueError(
            f"Łączny rozmiar rozpakowanych danych przekracza limit {limits.max_total_uncompressed_bytes} bajtów."
        )
    return updated_total


def _validate_member_compression_ratio(member: zipfile.ZipInfo, limits: ZipRestoreLimits) -> None:
    if not member.file_size:
        return
    if member.compress_size == 0:
        raise ValueError(f"Nieprawidłowy skompresowany rozmiar wpisu ZIP: {member.filename}")
    ratio = member.file_size / member.compress_size
    if ratio > limits.max_compression_ratio:
        raise ValueError(
            f"Współczynnik kompresji wpisu ZIP przekracza limit: {member.filename} "
            f"({ratio:.1f} > {limits.max_compression_ratio:.1f})."
        )


def _required_manifest_member(
    members: dict[str, zipfile.ZipInfo],
    limits: ZipRestoreLimits,
) -> zipfile.ZipInfo:
    manifest_info = members.get("manifest.json")
    if manifest_info is None or manifest_info.is_dir():
        raise ValueError("Archiwum nie ma pliku manifest.json.")
    if manifest_info.file_size > limits.max_manifest_bytes:
        raise ValueError(f"Manifest ZIP przekracza limit {limits.max_manifest_bytes} bajtów.")
    return manifest_info


def _validate_no_file_parent_collisions(
    members: dict[str, zipfile.ZipInfo],
    destinations: set[str],
) -> None:
    file_destinations = {name.rstrip("/") for name, member in members.items() if not member.is_dir()}
    for destination in destinations:
        for parent in PurePosixPath(destination).parents:
            parent_name = parent.as_posix()
            if parent_name == ".":
                break
            if parent_name in file_destinations:
                raise ValueError(f"Plik ZIP jest jednocześnie katalogiem nadrzędnym: {parent_name}")


def _validated_zip_members(
    zip_file: zipfile.ZipFile,
    limits: ZipRestoreLimits,
) -> dict[str, zipfile.ZipInfo]:
    infos = zip_file.infolist()
    if len(infos) > limits.max_members:
        raise ValueError(f"Archiwum ZIP ma za dużo wpisów: {len(infos)} > {limits.max_members}.")

    members: dict[str, zipfile.ZipInfo] = {}
    destinations: set[str] = set()
    total_uncompressed = 0
    for member in infos:
        destination_name, canonical_name = _canonical_member_names(member)
        _register_unique_member(
            member,
            destination_name=destination_name,
            canonical_name=canonical_name,
            members=members,
            destinations=destinations,
        )
        _validate_member_storage_type(member)
        _validate_member_declared_sizes(member)
        total_uncompressed = _updated_total_uncompressed(total_uncompressed, member, limits)
        _validate_member_compression_ratio(member, limits)

    _required_manifest_member(members, limits)
    _validate_no_file_parent_collisions(members, destinations)
    return members


def _read_zip_manifest(
    zip_file: zipfile.ZipFile,
    manifest_info: zipfile.ZipInfo,
    limits: ZipRestoreLimits,
    snapshot_format: str,
) -> tuple[dict[str, Any], int]:
    with zip_file.open(manifest_info, "r") as source:
        payload_bytes = source.read(limits.max_manifest_bytes + 1)
    if len(payload_bytes) > limits.max_manifest_bytes:
        raise ValueError(f"Manifest ZIP przekracza limit {limits.max_manifest_bytes} bajtów.")
    if len(payload_bytes) != manifest_info.file_size:
        raise ValueError("Rozmiar manifest.json nie zgadza się z metadanymi ZIP.")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Archiwum ma nieprawidłowy manifest.json.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Manifest ZIP musi być obiektem JSON.")
    if payload.get("format") != snapshot_format:
        raise ValueError(f"Archiwum nie jest snapshotem danych w formacie {snapshot_format}.")
    return payload, len(payload_bytes)


def _manifest_entry_identity(raw_entry: Any) -> tuple[dict[str, Any], str, str]:
    if not isinstance(raw_entry, dict):
        raise ValueError("Wpis manifestu ZIP musi być obiektem JSON.")
    raw_path = raw_entry.get("path")
    entry_type = raw_entry.get("type")
    if not isinstance(raw_path, str) or entry_type not in {"file", "directory"}:
        raise ValueError("Wpis manifestu ZIP ma nieprawidłową ścieżkę albo typ.")
    relative_path = _require_relative_archive_path(raw_path)
    canonical_path = relative_path.as_posix()
    if entry_type == "directory":
        canonical_path += "/"
    if raw_path != canonical_path or canonical_path == "manifest.json":
        raise ValueError(f"Nieprawidłowa ścieżka wpisu manifestu ZIP: {raw_path}")
    return raw_entry, entry_type, canonical_path


def _matched_manifest_member(
    *,
    canonical_path: str,
    entry_type: str,
    entries: dict[str, dict[str, Any]],
    members: dict[str, zipfile.ZipInfo],
) -> zipfile.ZipInfo:
    if canonical_path in entries:
        raise ValueError(f"Powtórzony wpis manifestu ZIP: {canonical_path}")
    member = members.get(canonical_path)
    if member is None or member.is_dir() != (entry_type == "directory"):
        raise ValueError(f"Manifest nie odpowiada zawartości ZIP: {canonical_path}")
    return member


def _is_lowercase_sha256(value: Any, lowercase_hex: set[str]) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 64 or value != value.lower():
        return False
    return all(character in lowercase_hex for character in value)


def _validate_manifest_file_metadata(
    raw_entry: dict[str, Any],
    member: zipfile.ZipInfo,
    canonical_path: str,
    lowercase_hex: set[str],
) -> None:
    size_bytes = raw_entry.get("size_bytes")
    if type(size_bytes) is not int or size_bytes < 0 or size_bytes != member.file_size:
        raise ValueError(f"Manifest ma nieprawidłowy rozmiar pliku: {canonical_path}")
    if not _is_lowercase_sha256(raw_entry.get("sha256"), lowercase_hex):
        raise ValueError(f"Manifest ma nieprawidłowy SHA-256: {canonical_path}")


def _validated_manifest_entry(
    raw_entry: Any,
    *,
    entries: dict[str, dict[str, Any]],
    members: dict[str, zipfile.ZipInfo],
    lowercase_hex: set[str],
) -> tuple[str, dict[str, Any]]:
    entry, entry_type, canonical_path = _manifest_entry_identity(raw_entry)
    member = _matched_manifest_member(
        canonical_path=canonical_path,
        entry_type=entry_type,
        entries=entries,
        members=members,
    )
    if entry_type == "file":
        _validate_manifest_file_metadata(entry, member, canonical_path, lowercase_hex)
    return canonical_path, entry


def _validate_manifest_coverage(
    entries: dict[str, dict[str, Any]],
    members: dict[str, zipfile.ZipInfo],
) -> None:
    archived_paths = set(members) - {"manifest.json"}
    if set(entries) == archived_paths:
        return
    missing = sorted(archived_paths - set(entries))
    extra = sorted(set(entries) - archived_paths)
    raise ValueError(
        f"Manifest nie opisuje dokładnie zawartości ZIP (brakujące: {missing or '-'}, nadmiarowe: {extra or '-'})."
    )


def _secret_entry_names(manifest: dict[str, Any]) -> list[str]:
    raw_secret_entries = manifest.get("secret_entries")
    if not isinstance(raw_secret_entries, list) or not all(isinstance(path, str) for path in raw_secret_entries):
        raise ValueError("Manifest ZIP ma nieprawidłową listę secret_entries.")
    if len(set(raw_secret_entries)) != len(raw_secret_entries):
        raise ValueError("Manifest ZIP ma powtórzone wpisy secret_entries.")
    return raw_secret_entries


def _is_nested_secret_path(path: str, allowed_secrets: set[str]) -> bool:
    return any(path.startswith(f"{secret_path}/") for secret_path in allowed_secrets)


def _validate_secret_archive_paths(
    entries: dict[str, dict[str, Any]],
    allowed_secrets: set[str],
) -> None:
    for archived_path, entry in entries.items():
        path_without_slash = archived_path.rstrip("/")
        if path_without_slash in allowed_secrets and entry["type"] != "file":
            raise ValueError(f"Sekret w ZIP musi być zwykłym plikiem: {archived_path}")
        if _is_nested_secret_path(path_without_slash, allowed_secrets):
            raise ValueError(f"Sekret w ZIP musi być pojedynczym plikiem: {archived_path}")


def _validate_secret_manifest_consistency(
    manifest: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    secret_paths: tuple[Path, ...],
) -> None:
    raw_secret_entries = _secret_entry_names(manifest)
    allowed_secrets = {path.as_posix() for path in secret_paths}
    _validate_secret_archive_paths(entries, allowed_secrets)
    actual_secret_entries = sorted(allowed_secrets & set(entries))
    if sorted(raw_secret_entries) != actual_secret_entries:
        raise ValueError("Manifest secret_entries nie odpowiada zawartości ZIP.")
    secrets_included = manifest.get("secrets_included")
    if type(secrets_included) is not bool or secrets_included != bool(actual_secret_entries):
        raise ValueError("Manifest ma niespójne pole secrets_included.")


def _validated_manifest_entries(
    manifest: dict[str, Any],
    members: dict[str, zipfile.ZipInfo],
    secret_paths: tuple[Path, ...],
) -> dict[str, dict[str, Any]]:
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("Manifest ZIP nie ma listy entries.")

    entries: dict[str, dict[str, Any]] = {}
    lowercase_hex = set(hexdigits.lower())
    for raw_entry in raw_entries:
        canonical_path, entry = _validated_manifest_entry(
            raw_entry,
            entries=entries,
            members=members,
            lowercase_hex=lowercase_hex,
        )
        entries[canonical_path] = entry

    _validate_manifest_coverage(entries, members)
    _validate_secret_manifest_consistency(manifest, entries, secret_paths)
    return entries


def _extract_validated_zip(
    zip_file: zipfile.ZipFile,
    *,
    target_dir: Path,
    members: dict[str, zipfile.ZipInfo],
    entries: dict[str, dict[str, Any]],
    limits: ZipRestoreLimits,
    manifest_size: int,
) -> None:
    target_root = target_dir.resolve()
    total_extracted = manifest_size
    for archive_name, entry in entries.items():
        member = members[archive_name]
        relative_path = _require_relative_archive_path(archive_name)
        destination = target_dir / relative_path
        try:
            destination.resolve().relative_to(target_root)
        except ValueError as exc:
            raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {archive_name}") from exc

        if member.is_dir():
            destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            destination.chmod(0o700)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        digest = hashlib.sha256()
        extracted_size = 0
        with zip_file.open(member, "r") as source, destination.open("xb") as target:
            while chunk := source.read(ZIP_READ_CHUNK_BYTES):
                extracted_size += len(chunk)
                total_extracted += len(chunk)
                if extracted_size > member.file_size or total_extracted > limits.max_total_uncompressed_bytes:
                    raise ValueError("Rozpakowane dane ZIP przekroczyły zadeklarowany rozmiar lub limit.")
                target.write(chunk)
                digest.update(chunk)
        if extracted_size != entry["size_bytes"]:
            raise ValueError(f"Rozmiar pliku nie zgadza się z manifestem: {archive_name}")
        if digest.hexdigest() != entry["sha256"]:
            raise ValueError(f"SHA-256 pliku nie zgadza się z manifestem: {archive_name}")
        destination.chmod(0o600)


def extract_verified_zip(
    archive_path: Path,
    target_dir: Path,
    *,
    limits: ZipRestoreLimits,
    snapshot_format: str,
    secret_paths: tuple[Path, ...],
) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(target_dir.iterdir()):
        raise ValueError("Katalog roboczy odtwarzania ZIP nie jest pusty.")
    with zipfile.ZipFile(archive_path) as zip_file:
        members = _validated_zip_members(zip_file, limits)
        manifest, manifest_size = _read_zip_manifest(
            zip_file,
            members["manifest.json"],
            limits,
            snapshot_format,
        )
        entries = _validated_manifest_entries(manifest, members, secret_paths)
        _extract_validated_zip(
            zip_file,
            target_dir=target_dir,
            members=members,
            entries=entries,
            limits=limits,
            manifest_size=manifest_size,
        )
    return manifest
