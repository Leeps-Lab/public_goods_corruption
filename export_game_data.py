"""
Dump the experiment tables to a timestamped zip of CSVs.

Same tables as export_service/app.py, but as a one-off script so it works
where that service can't run (e.g. Heroku). Point DATABASE_URL at the
database and run it from any machine with psycopg2 installed:

    DATABASE_URL=$(heroku config:get DATABASE_URL -a <app-name>) python export_game_data.py

The 'game_data' tables are not part of oTree's own data export, so this is
the only way to get them.
"""
import io
import os
import sys
import zipfile
from datetime import datetime, timezone

import psycopg2

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
    ("COPY game_data.messages TO STDOUT WITH CSV HEADER", "messages.csv"),
    ("COPY game_data.sessions TO STDOUT WITH CSV HEADER", "sessions.csv"),
    ("COPY game_data.interaction_times TO STDOUT WITH CSV HEADER", "interaction_times.csv"),
]


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"pgc_export_{timestamp}.zip"

    conn = psycopg2.connect(database_url)
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf, conn.cursor() as cur:
            for copy_sql, filename in EXPORTS:
                csv_buffer = io.StringIO()
                try:
                    cur.copy_expert(copy_sql, csv_buffer)
                except psycopg2.Error as exc:
                    # Keep going if one table is missing (e.g. right after a
                    # reset) and leave a note in its place.
                    conn.rollback()
                    csv_buffer = io.StringIO()
                    csv_buffer.write(f"# export failed for {filename}: {exc}\n")
                    print(f"WARNING: {filename}: {exc}".strip())
                zf.writestr(filename, csv_buffer.getvalue())
    finally:
        conn.close()

    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
