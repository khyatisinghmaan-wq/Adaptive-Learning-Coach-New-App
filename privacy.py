import datetime
import sqlite3

RETENTION_DAYS = 90
AGG_MIN_N = 5

def purge_old_events(db_path: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=RETENTION_DAYS)).isoformat()
    # Events tables to purge by created_at
    for table in ["survey_responses", "lesson_events", "chat_logs"]:
        cur.execute(f"""DELETE FROM {table} WHERE created_at < ?""", (cutoff,))
    con.commit()
    con.close()

def can_show_aggregate(n: int) -> bool:
    return n >= AGG_MIN_N
