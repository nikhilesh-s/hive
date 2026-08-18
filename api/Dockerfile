# HiveBlot beta API. Any container host (Fly.io, Railway, Render, Cloud Run, EC2).
# Build context is the REPO ROOT, not api/ — the staged figure crops live outside api/app:
#   python scripts/stage_crops.py           # optional, ~6 MB, see below
#   docker build -f api/Dockerfile -t hiveblot-api .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app ./app
COPY api/db ./db

# --- figure crops (optional) -------------------------------------------------
# Records store an ABSOLUTE image_crop_ref and /records/{id}/crop requires the
# path to resolve inside CROP_BASE_DIR, so the image reproduces the authoring
# path verbatim. That serves crops in a container with zero code change and,
# more importantly, zero change to the reviewed corpus. Storing crop refs
# relative to CROP_BASE_DIR would be cleaner and is the tracked follow-up.
# `scripts/stage_crops.py` fills api/crops with only the crops the reviewed
# rows actually reference (21 files, ~6 MB). When it holds just .gitkeep the
# evidence panel degrades to text-only, which is documented, supported
# behaviour — not a failure.
COPY api/crops/ /Users/niks/hive/western_blot_miner/data/pdf_runs/
ENV CROP_BASE_DIR=/Users/niks/hive/western_blot_miner/data/pdf_runs

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
