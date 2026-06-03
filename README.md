# Label Studio Data Sync

Scripts to export annotations from a Label Studio project.

**Japanese:** [README_ja.md](README_ja.md)

## Data layout

| Path | Description |
|---|---|
| `classes.txt` | Class names |
| `images/*.jpg` | Image files |
| `labels/*.txt` | YOLO-format labels (normalized bounding boxes) |
| `result.json` | COCO-format image and annotation metadata |
| `notes.json` | Category information |

## Sync from Label Studio

Install dependencies with [uv](https://docs.astral.sh/uv/) and fetch the latest annotations via the API.

```bash
cp .env.example .env
# Set LABEL_STUDIO_API_KEY and other values in .env

uv sync
uv run python sync_from_label_studio.py
```

### Environment variables

| Variable | Description | Example |
|---|---|---|
| `LABEL_STUDIO_URL` | Label Studio base URL | `http://localhost:8080` |
| `LABEL_STUDIO_API_KEY` | API token from account settings | (token string) |
| `LABEL_STUDIO_PROJECT_ID` | Project ID | `6` |
| `OUTPUT_DIR` | Output directory (defaults to repo root) | `./my_data` |

### CLI options

```bash
uv run python sync_from_label_studio.py --url http://localhost:8080 --project-id 6 -v
uv run python sync_from_label_studio.py --help
```

On each sync, existing files under `labels/` and `images/` are removed first, then replaced by Label Studio’s `YOLO_WITH_IMAGES` export. `result.json` and `classes.txt` are also updated to the latest versions.

To skip images and update labels only (saves ~30MB):

```bash
uv run python sync_from_label_studio.py --skip-images
```
