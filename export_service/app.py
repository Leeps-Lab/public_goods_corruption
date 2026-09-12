"""
Small on-demand export service.

Connects directly to the oTree Postgres database (same docker network,
no docker exec / SSH needed), dumps the tables the research team needs
as CSV, and zips them. Protected with HTTP Basic Auth so it can sit
behind nginx without a separate .htpasswd file — credentials come from
.env, same pattern as the rest of the project (see DATABASE_URL).

The landing page ("/") shows the list of past exports (with the button
to trigger a new one); it never downloads anything on its own. A new
export runs in a background thread — the page polls "/status" and
reloads itself once it's done — since gunicorn runs this app with a
single worker and a synchronous request would otherwise block the
service for the full duration of the DB dump.

Every generated export is also kept as a timestamped snapshot under
EXPORT_HISTORY_DIR (mounted on /data on the host, not the small root
disk) so past pulls stay available. Identical back-to-back exports are
not duplicated, and only the last EXPORTS_KEEP_LAST snapshots are kept.
Deleting a specific snapshot early is a manual/SSH operation on purpose
— it's not exposed here.
"""
import io
import os
import threading
import zipfile
from datetime import datetime, timezone
from functools import wraps

import psycopg2
from flask import Flask, Response, abort, redirect, request, send_from_directory

app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
EXPORTS_USER = os.environ.get("EXPORTS_USER")
EXPORTS_PASSWORD = os.environ.get("EXPORTS_PASSWORD")
HISTORY_DIR = os.environ.get("EXPORT_HISTORY_DIR", "/app/export-history")
KEEP_LAST = int(os.environ.get("EXPORTS_KEEP_LAST", "30"))

os.makedirs(HISTORY_DIR, exist_ok=True)

SNAPSHOT_PREFIX = "pgc_export_"
SNAPSHOT_SUFFIX = ".zip"
SNAPSHOT_TS_FORMAT = "%Y%m%dT%H%M%SZ"

# Background export job state, guarded by _job_lock (single job at a time).
_job_lock = threading.Lock()
_job_state = {"running": False, "error": None}

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


def _run_export_job():
    try:
        zip_bytes = _build_export_zip()
        _save_snapshot(zip_bytes)
        error = None
    except Exception as exc:
        error = str(exc)
    with _job_lock:
        _job_state["running"] = False
        _job_state["error"] = error


def _format_snapshot_label(name):
    """'pgc_export_20260912T040330Z.zip' -> '2026-09-12 04:03:30 UTC'."""
    ts = name[len(SNAPSHOT_PREFIX):-len(SNAPSHOT_SUFFIX)]
    try:
        dt = datetime.strptime(ts, SNAPSHOT_TS_FORMAT)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return name


def _render_index(running, error):
    files = list(reversed(_list_snapshots()))  # newest first
    if not files:
        list_html = "<p>No hay exports todavía — genera el primero con el botón de arriba.</p>"
    else:
        rows = []
        for name in files:
            size_kb = os.path.getsize(os.path.join(HISTORY_DIR, name)) // 1024
            rows.append(
                f"<li><span>{_format_snapshot_label(name)}</span> "
                f"<span class='size'>({size_kb} KB)</span> "
                f"<a href='history/{name}'>Descargar</a></li>"
            )
        list_html = "<ul class='exports'>" + "".join(rows) + "</ul>"

    error_html = f"<p class='error'>El último intento de generar un export falló: {error}</p>" if error else ""
    button_html = (
        "<button type='submit' disabled>Generando… <span class='spinner'></span></button>"
        if running
        else "<button type='submit'>Generar nuevo export</button>"
    )
    poll_script = (
        """
        <script>
        function poll() {
            fetch('status').then(r => r.json()).then(data => {
                if (!data.running) { location.reload(); }
                else { setTimeout(poll, 2000); }
            });
        }
        setTimeout(poll, 2000);
        </script>
        """
        if running
        else ""
    )

    return f"""
    <html>
    <head>
    <title>Exports del experimento</title>
    <style>
        body {{ font-family: sans-serif; max-width: 640px; margin: 2rem auto; }}
        ul.exports {{ list-style: none; padding: 0; }}
        ul.exports li {{ display: flex; gap: 0.75rem; align-items: center; padding: 0.4rem 0; border-bottom: 1px solid #eee; }}
        ul.exports .size {{ color: #666; font-size: 0.9em; }}
        .error {{ color: #b00020; }}
        .spinner {{
            display: inline-block; width: 0.8em; height: 0.8em;
            border: 2px solid #fff; border-top-color: transparent;
            border-radius: 50%; animation: spin 0.8s linear infinite;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
    </head>
    <body>
        <h1>Exports del experimento</h1>
        <form method="post" action="generate">{button_html}</form>
        {error_html}
        {list_html}
        {poll_script}
    </body>
    </html>
    """


@app.route("/")
@requires_auth
def index():
    with _job_lock:
        running = _job_state["running"]
        error = _job_state["error"]
    return Response(_render_index(running, error), mimetype="text/html")


@app.route("/generate", methods=["POST"])
@requires_auth
def generate():
    with _job_lock:
        already_running = _job_state["running"]
        if not already_running:
            _job_state["running"] = True
            _job_state["error"] = None
    if not already_running:
        threading.Thread(target=_run_export_job, daemon=True).start()
    # Relative redirect on purpose: nginx proxies "/exports/" -> "/" here
    # without telling Flask, so an absolute url_for("index") would resolve
    # to the site root (the oTree app) instead of back to "/exports/".
    return redirect(".", code=303)


@app.route("/status")
@requires_auth
def status():
    with _job_lock:
        return {"running": _job_state["running"], "error": _job_state["error"]}


@app.route("/history/")
@requires_auth
def history_redirect():
    return redirect("../", code=301)


@app.route("/history/<path:filename>")
@requires_auth
def download_history(filename):
    if not _is_snapshot_name(filename):
        abort(404)
    return send_from_directory(HISTORY_DIR, filename, as_attachment=True)


@app.route("/healthz")
def healthz():
    return {"status": "ok"}
