"""
Small on-demand export service.

Single endpoint that connects directly to the oTree Postgres database
(same docker network, no docker exec / SSH needed), dumps the tables the
research team needs as CSV, zips them in memory, and returns the zip as
a download. Protected with HTTP Basic Auth so it can sit behind nginx
without a separate .htpasswd file — credentials come from .env, same
pattern as the rest of the project (see DATABASE_URL).

Every generated export is also kept as a timestamped snapshot under
EXPORT_HISTORY_DIR (mounted on /data on the host, not the small root
disk) so past pulls stay available. Identical back-to-back exports are
not duplicated, and only the last EXPORTS_KEEP_LAST snapshots are kept.
Deleting a specific snapshot early is a manual/SSH operation on purpose
— it's not exposed here.
"""
import io
import os
import zipfile
from datetime import datetime, timezone
from functools import wraps

import psycopg2
from flask import Flask, Response, abort, request, send_from_directory

app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
EXPORTS_USER = os.environ.get("EXPORTS_USER")
EXPORTS_PASSWORD = os.environ.get("EXPORTS_PASSWORD")
HISTORY_DIR = os.environ.get("EXPORT_HISTORY_DIR", "/app/export-history")
KEEP_LAST = int(os.environ.get("EXPORTS_KEEP_LAST", "30"))

os.makedirs(HISTORY_DIR, exist_ok=True)

SNAPSHOT_PREFIX = "pgc_export_"
SNAPSHOT_SUFFIX = ".zip"

# (COPY statement, output filename inside the zip)
EXPORTS = [
    ("COPY public.public_goods_player TO STDOUT WITH CSV HEADER", "public_goods_player.csv"),
    ("COPY public.public_goods_group TO STDOUT WITH CSV HEADER", "public_goods_group.csv"),
    ("COPY public.public_goods_message TO STDOUT WITH CSV HEADER", "public_goods_message.csv"),
    (
        "COPY (SELECT id, code, label FROM otree_session) TO STDOUT WITH CSV HEADER",
        "otree_session.csv",
    ),
    (
        "COPY (SELECT id, code, session_id, id_in_session FROM otree_participant) "
        "TO STDOUT WITH CSV HEADER",
        "otree_participant.csv",
    ),
    ("COPY game_data.calculator_history TO STDOUT WITH CSV HEADER", "calculator_history.csv"),
    ("COPY game_data.history TO STDOUT WITH CSV HEADER", "history.csv"),
    ("COPY game_data.status TO STDOUT WITH CSV HEADER", "status.csv"),
    ("COPY game_data.transactions TO STDOUT WITH CSV HEADER", "transactions.csv"),
]


def requires_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not EXPORTS_USER or not EXPORTS_PASSWORD:
            return Response("Export credentials are not configured (EXPORTS_USER/EXPORTS_PASSWORD).", 500)

        auth = request.authorization
        if not auth or auth.username != EXPORTS_USER or auth.password != EXPORTS_PASSWORD:
            return Response(
                "Authentication required.",
                401,
                {"WWW-Authenticate": 'Basic realm="Datos del experimento"'},
            )
        return view(*args, **kwargs)

    return wrapped


def _is_snapshot_name(name):
    return name.startswith(SNAPSHOT_PREFIX) and name.endswith(SNAPSHOT_SUFFIX)


def _list_snapshots():
    """Snapshot filenames, oldest first (timestamp in the name sorts naturally)."""
    return sorted(f for f in os.listdir(HISTORY_DIR) if _is_snapshot_name(f))


def _build_export_zip():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            with conn.cursor() as cur:
                for copy_sql, filename in EXPORTS:
                    csv_buffer = io.StringIO()
                    try:
                        cur.copy_expert(copy_sql, csv_buffer)
                    except psycopg2.Error as exc:
                        # Don't let one missing/renamed table (e.g. right
                        # after a DB reset) kill the whole export — drop a
                        # note in its place and keep going.
                        conn.rollback()
                        csv_buffer = io.StringIO()
                        csv_buffer.write(f"# export failed for {filename}: {exc}\n")
                    zf.writestr(filename, csv_buffer.getvalue())
    finally:
        conn.close()
    return zip_buffer.getvalue()


def _save_snapshot(zip_bytes):
    """Persist zip_bytes as a new timestamped snapshot, unless it's byte-
    for-byte identical to the most recent one, then prune down to
    KEEP_LAST. Best-effort bookkeeping — never blocks the response."""
    existing = _list_snapshots()

    if existing:
        latest_path = os.path.join(HISTORY_DIR, existing[-1])
        with open(latest_path, "rb") as f:
            if f.read() == zip_bytes:
                return  # nothing changed since the last snapshot

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    new_name = f"{SNAPSHOT_PREFIX}{timestamp}{SNAPSHOT_SUFFIX}"
    with open(os.path.join(HISTORY_DIR, new_name), "wb") as f:
        f.write(zip_bytes)

    existing.append(new_name)
    overflow = len(existing) - KEEP_LAST
    for old_name in existing[:max(0, overflow)]:
        try:
            os.remove(os.path.join(HISTORY_DIR, old_name))
        except OSError:
            pass


@app.route("/")
@requires_auth
def generate():
    zip_bytes = _build_export_zip()
    _save_snapshot(zip_bytes)
    return Response(
        zip_bytes,
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=pgc_export.zip"},
    )


@app.route("/history/")
@requires_auth
def list_history():
    files = list(reversed(_list_snapshots()))  # newest first
    if not files:
        body = "<p>No hay snapshots todavía — pide un export primero.</p>"
    else:
        items = []
        for name in files:
            size_kb = os.path.getsize(os.path.join(HISTORY_DIR, name)) // 1024
            items.append(f'<li><a href="{name}">{name}</a> ({size_kb} KB)</li>')
        body = "<ul>" + "".join(items) + "</ul>"

    return Response(f"<html><body><h1>Export history</h1>{body}</body></html>", mimetype="text/html")


@app.route("/history/<path:filename>")
@requires_auth
def download_history(filename):
    if not _is_snapshot_name(filename):
        abort(404)
    return send_from_directory(HISTORY_DIR, filename, as_attachment=True)


@app.route("/healthz")
def healthz():
    return {"status": "ok"}
