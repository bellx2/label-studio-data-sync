#!/usr/bin/env python3
"""Export annotations from the Label Studio API and update the dataset."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Directory containing this script; default output location.
ROOT_DIR = Path(__file__).resolve().parent
# Top-level files from YOLO / YOLO_WITH_IMAGES exports.
YOLO_FILES = ("classes.txt", "notes.json")
# Subdirectories from YOLO_WITH_IMAGES exports.
YOLO_DIRS = ("labels", "images")
# Top-level file from COCO exports.
COCO_FILES = ("result.json",)
# Image extensions cleared and counted under images/.
IMAGE_GLOBS = ("*.jpg", "*.jpeg", "*.png", "*.webp")
DEFAULT_TIMEOUT = 600.0


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Token {api_key}"}


def download_export(
    base_url: str,
    api_key: str,
    project_id: int,
    export_type: str,
    *,
    timeout: float = 300.0,
) -> bytes:
    """Download a project export archive (ZIP bytes) from Label Studio."""
    url = f"{base_url.rstrip('/')}/api/projects/{project_id}/export"
    response = requests.get(
        url,
        params={"exportType": export_type},
        headers=_auth_headers(api_key),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.content


def _extract_members(
    zip_bytes: bytes,
    output_dir: Path,
    *,
    files: tuple[str, ...] = (),
    dirs: tuple[str, ...] = (),
) -> list[Path]:
    """Extract selected top-level files and directory trees from a ZIP archive."""
    written: list[Path] = []
    dir_prefixes = [f"{d}/" for d in dirs]

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            allowed = name in files or any(
                name.startswith(prefix) for prefix in dir_prefixes
            )
            if not allowed:
                continue
            target = output_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            written.append(target)
    return written


def _clear_dir_files(directory: Path, patterns: tuple[str, ...]) -> int:
    """Delete files matching glob patterns; return the number removed."""
    if not directory.exists():
        return 0
    removed = 0
    for pattern in patterns:
        for path in directory.glob(pattern):
            path.unlink()
            removed += 1
    return removed


def sync_dataset(
    base_url: str,
    api_key: str,
    project_id: int,
    output_dir: Path,
    *,
    download_images: bool = True,
    timeout: float = DEFAULT_TIMEOUT,
) -> None:
    """Refresh labels (and optionally images) plus COCO metadata under output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_dir = output_dir / "labels"
    images_dir = output_dir / "images"

    export_type = "YOLO_WITH_IMAGES" if download_images else "YOLO"
    logger.info(
        "Downloading %s export (project=%s)...",
        export_type,
        project_id,
    )
    yolo_zip = download_export(
        base_url, api_key, project_id, export_type, timeout=timeout
    )

    # Replace existing YOLO artifacts before extracting the new export.
    removed_labels = _clear_dir_files(labels_dir, ("*.txt",))
    if removed_labels:
        logger.info("Removed %d existing label file(s)", removed_labels)

    yolo_dirs: tuple[str, ...] = ("labels",)
    if download_images:
        removed_images = _clear_dir_files(images_dir, IMAGE_GLOBS)
        if removed_images:
            logger.info("Removed %d existing image file(s)", removed_images)
        yolo_dirs = YOLO_DIRS

    yolo_written = _extract_members(
        yolo_zip,
        output_dir,
        files=YOLO_FILES,
        dirs=yolo_dirs,
    )
    logger.info("YOLO: wrote %d file(s)", len(yolo_written))

    logger.info("Downloading COCO export...")
    coco_zip = download_export(
        base_url, api_key, project_id, "COCO", timeout=timeout
    )
    coco_written = _extract_members(coco_zip, output_dir, files=COCO_FILES)
    logger.info("COCO: wrote %d file(s)", len(coco_written))

    label_count = len(list(labels_dir.glob("*.txt"))) if labels_dir.exists() else 0
    image_count = 0
    if download_images and images_dir.exists():
        for pattern in IMAGE_GLOBS:
            image_count += len(list(images_dir.glob(pattern)))
    logger.info(
        "Done: labels=%d, images=%d, output=%s",
        label_count,
        image_count,
        output_dir,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    load_dotenv(ROOT_DIR / ".env")

    parser = argparse.ArgumentParser(
        description="Fetch annotations from Label Studio and update the dataset"
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Label Studio URL (env: LABEL_STUDIO_URL)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API token (env: LABEL_STUDIO_API_KEY)",
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=None,
        help="Project ID (env: LABEL_STUDIO_PROJECT_ID)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (env: OUTPUT_DIR, default: directory containing this script)",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image download (YOLO labels only)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"API timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args(argv)


def _env_or_arg(value: str | int | None, env_name: str) -> str | int | None:
    """Prefer CLI value; otherwise read from environment."""
    import os

    if value is not None:
        return value
    raw = os.environ.get(env_name)
    if raw is None or raw == "":
        return None
    if env_name == "LABEL_STUDIO_PROJECT_ID":
        return int(raw)
    return raw


def main(argv: list[str] | None = None) -> int:
    import os

    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    url = _env_or_arg(args.url, "LABEL_STUDIO_URL")
    api_key = _env_or_arg(args.api_key, "LABEL_STUDIO_API_KEY")
    project_id = _env_or_arg(args.project_id, "LABEL_STUDIO_PROJECT_ID")
    output_dir = args.output_dir or Path(
        os.environ.get("OUTPUT_DIR", str(ROOT_DIR))
    )

    missing = []
    if not url:
        missing.append("LABEL_STUDIO_URL")
    if not api_key:
        missing.append("LABEL_STUDIO_API_KEY")
    if project_id is None:
        missing.append("LABEL_STUDIO_PROJECT_ID")
    if missing:
        logger.error(
            "Missing required configuration: %s (set via .env or CLI flags)",
            ", ".join(missing),
        )
        return 1

    try:
        sync_dataset(
            str(url),
            str(api_key),
            int(project_id),
            output_dir,
            download_images=not args.skip_images,
            timeout=args.timeout,
        )
    except requests.HTTPError as exc:
        logger.error("Label Studio API error: %s", exc)
        if exc.response is not None:
            logger.error("Response: %s", exc.response.text[:500])
        return 1
    except requests.RequestException as exc:
        logger.error("Connection error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
