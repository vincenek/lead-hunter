# Lead Hunter

Lead Hunter is a Flask web app for finding local businesses that may need a website.

## What It Does

- Searches supported business types across multiple cities using OpenStreetMap Overpass data
- Prioritizes businesses with no detected website and visible contact details
- Can filter to email-only leads
- Tracks contacted businesses locally so you do not reach out twice
- Exports filtered leads to CSV

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

4. Open `http://127.0.0.1:5000/`

## Deployment Notes

This repo includes:

- `wsgi.py` for WSGI hosting
- `Procfile` for platforms that use a process file
- `gunicorn` in `requirements.txt`

The app reads the `PORT` environment variable automatically in production.

## Tests

Run:

```bash
python -m unittest -q
```
