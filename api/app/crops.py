from pathlib import Path

from .config import settings


REPO_ROOT = Path(__file__).resolve().parents[2]
STAGED_CROP_ARCHIVE = REPO_ROOT / "api" / "crops"


def resolve_reviewed_crop(ref: object) -> Path | None:
    """Return a servable reviewed-corpus crop path, or None.

    Historical reviewed rows store absolute authoring-machine paths under
    western_blot_miner/data/pdf_runs. Local/dev deployments stage those same
    files under api/crops, so map only that legacy corpus shape into the staged
    archive. Other outside paths remain unservable.
    """
    if not ref:
        return None

    base = Path(settings.crop_base_dir).resolve()
    crop = Path(str(ref)).resolve()
    if crop.suffix.lower() != ".png":
        return None

    try:
        crop.relative_to(base)
    except ValueError:
        pass
    else:
        return crop if crop.is_file() else None

    parts = Path(str(ref)).parts
    marker = ("western_blot_miner", "data", "pdf_runs")
    for i in range(0, len(parts) - len(marker) + 1):
        if parts[i:i + len(marker)] == marker:
            rel = Path(*parts[i + len(marker):])
            archive = STAGED_CROP_ARCHIVE.resolve()
            candidate = (archive / rel).resolve()
            try:
                candidate.relative_to(archive)
            except ValueError:
                return None
            return candidate if candidate.is_file() else None

    return None
