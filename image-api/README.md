# Pillow Image Manipulation API

Declarative image transforms over HTTP — **Pillow as an API**.

Upload an image, describe a sequence of operations in JSON, and receive the
processed image back. Operations run in the exact order you specify.

```
resize → crop → grayscale → blur → WebP
```

---

## Features

- FastAPI + Uvicorn + Pillow + Pydantic v2
- Declarative transform pipeline with ordered operations
- EXIF orientation normalization
- JPEG / PNG / WebP output
- Configurable upload, pixel, and operation limits
- Optional API-key authentication
- Plugin-style operation registry for easy extension

---

## Installation

Requires **Python 3.12+**.

```bash
cd image-api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Running locally

```bash
uvicorn app.main:app --reload
```

Then open:

| URL | Purpose |
|-----|---------|
| http://localhost:8000/health | Health check |
| http://localhost:8000/docs | Interactive Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/openapi.json | OpenAPI schema |

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_UPLOAD_SIZE` | `20971520` (20 MB) | Max upload bytes |
| `MAX_IMAGE_PIXELS` | `50000000` (50 MP) | Max decoded pixels (decompression-bomb guard) |
| `MAX_OPERATIONS` | `20` | Max operations per request |
| `API_KEY_ENABLED` | `false` | Require `X-API-Key` header |
| `API_KEY` | _(empty)_ | Expected API key when auth is enabled |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Authentication

Disabled by default for local development.

```bash
API_KEY_ENABLED=true
API_KEY=your-secret-key
```

```bash
curl -H "X-API-Key: your-secret-key" ...
```

Missing or invalid keys return `401` with:

```json
{"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid API key"}}
```

`GET /health` remains public.

---

## API

### `GET /health`

```json
{"status": "ok"}
```

### `POST /v1/images/transform`

Multipart form fields:

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | Source image |
| `spec` | string | JSON transformation specification |

Returns the processed image bytes with the appropriate `Content-Type`.

#### curl example

```bash
curl -X POST http://localhost:8000/v1/images/transform \
  -F "file=@input.jpg" \
  -F 'spec={
    "operations":[
      {"type":"resize","width":800,"height":600},
      {"type":"grayscale"}
    ],
    "output":{"format":"jpeg","quality":85}
  }' \
  --output result.jpg
```

#### Complete example request

```json
{
  "operations": [
    {
      "type": "resize",
      "width": 1200
    },
    {
      "type": "crop",
      "x": 0,
      "y": 0,
      "width": 1200,
      "height": 630
    },
    {
      "type": "grayscale"
    }
  ],
  "output": {
    "format": "webp",
    "quality": 85
  }
}
```

---

## Transformation syntax

```json
{
  "operations": [ /* applied in order */ ],
  "output": {
    "format": "jpeg" | "png" | "webp",
    "quality": 1-100
  }
}
```

Order is significant: `resize → crop → grayscale` is not the same as
`grayscale → crop → resize`.

---

## Supported operations

### resize

```json
{"type": "resize", "width": 800, "height": 600}
{"type": "resize", "width": 800}
{"type": "resize", "height": 600}
{"type": "resize", "width": 800, "height": 600, "fit": "contain"}
```

| `fit` | Behaviour |
|-------|-----------|
| `stretch` | Force exact dimensions (default) |
| `contain` | Fit inside the box, keep aspect ratio |
| `cover` | Fill the box, keep aspect ratio (center crop) |

Single-dimension resize always preserves aspect ratio. Uses `LANCZOS` resampling.

### crop

```json
{"type": "crop", "x": 100, "y": 50, "width": 500, "height": 300}
```

Invalid regions that exceed image bounds return `INVALID_OPERATION` — never
silently clamped.

### grayscale

```json
{"type": "grayscale"}
```

Preserves alpha when present.

### rotate

```json
{"type": "rotate", "degrees": 90, "expand": true}
```

Arbitrary angles supported. `expand` defaults to `true`.

### flip

```json
{"type": "flip", "direction": "horizontal"}
{"type": "flip", "direction": "vertical"}
```

### blur

```json
{"type": "blur", "radius": 3}
```

Gaussian blur. Radius must be ≥ 0.

---

## Output formats

| Format | Notes |
|--------|-------|
| `jpeg` | Incompatible modes converted to RGB; transparency composited onto white |
| `png` | Alpha preserved when possible |
| `webp` | Quality supported; alpha preserved |

Before any operations, EXIF orientation is normalized via `ImageOps.exif_transpose()`.

---

## Limits & security

- Uploaded files are untrusted; filenames are never used for filesystem access
- Hard caps on upload size, pixel count, and operation count
- Pillow decompression-bomb protection (`Image.MAX_IMAGE_PIXELS`)
- No execution of image metadata
- Internal stack traces are never returned to clients

### Error format

```json
{
  "error": {
    "code": "INVALID_OPERATION",
    "message": "Crop region exceeds image bounds"
  }
}
```

| Code | Meaning |
|------|---------|
| `INVALID_IMAGE` | Unreadable / empty upload |
| `INVALID_OPERATION` | Operation failed (e.g. crop OOB) |
| `INVALID_SPEC` | Malformed or invalid JSON spec |
| `UNSUPPORTED_FORMAT` | Unknown output format |
| `IMAGE_TOO_LARGE` | Upload exceeds `MAX_UPLOAD_SIZE` |
| `IMAGE_TOO_MANY_PIXELS` | Exceeds `MAX_IMAGE_PIXELS` |
| `TOO_MANY_OPERATIONS` | Exceeds `MAX_OPERATIONS` |
| `INVALID_PARAMETER` | Bad request parameter |
| `UNAUTHORIZED` | Missing/invalid API key |
| `PROCESSING_FAILED` | Unexpected processing error |

---

## Testing

```bash
pip install -e ".[dev]"
pytest
```

Coverage includes health, transform API, validation/limits, auth, each
operation, output formats, EXIF orientation, and operation ordering.

---

## Architecture

```
app/
├── main.py                 # FastAPI app + error handlers
├── config.py               # Environment-backed settings
├── api/routes.py           # Thin HTTP layer
├── models/transforms.py    # Pydantic request models
├── services/image_service.py
├── processing/
│   ├── pipeline.py         # load → EXIF → ops → encode
│   └── operations/         # One module per operation + registry
└── security/api_key.py
```

Request flow:

```
route → validate upload/spec → ImageService → pipeline → Response(image)
```

The pipeline keeps a single Pillow `Image` in memory and encodes once at the
end. CPU work runs in a thread pool so the event loop stays responsive; the
same service boundary can later target a process pool or job queue without
changing the public API.

### Operation registry

```python
OPERATIONS = {
    "resize": resize.apply,
    "crop": crop.apply,
    "grayscale": grayscale.apply,
    # ...
}
```

Each operation exposes `apply(image, params) -> Image.Image`.

---

## Adding a new operation

1. Create `app/processing/operations/sharpen.py` with an `apply(image, params)` function.
2. Add a Pydantic model to `app/models/transforms.py` and include it in the `Operation` union.
3. Register it in `app/processing/operations/__init__.py` (`OPERATIONS["sharpen"] = sharpen.apply`).
4. Add unit tests in `tests/test_operations.py`.

No changes to the pipeline or routes are required.

---

## Future (not in v1)

Watermark, smart crop, color adjustments, text overlays, URL input, async
jobs, object storage, rate limiting, and usage tracking are intentionally
out of scope. The registry + pipeline design is meant to make those additions
straightforward.
