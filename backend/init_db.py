import os
import pymysql
from dotenv import load_dotenv

# Load environment
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Lamo@2008")
DB_NAME = os.getenv("DB_NAME", "flywise_db")

def init_database():
    print(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4',
        autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.execute(f"USE {DB_NAME};")
    print(f"Database '{DB_NAME}' selected.")

    schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Split script into blocks handling DELIMITER //
    sections = content.split("DELIMITER //")
    standard_prefix = sections[0]
    
    # Execute normal statements
    statements = [stmt.strip() for stmt in standard_prefix.split(";") if stmt.strip()]
    for stmt in statements:
        if stmt.startswith("--") or stmt.startswith("/*"):
            # Clean comments
            lines = [l for l in stmt.split("\n") if not l.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if not stmt:
                continue
        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"Notice executing standard statement: {e}\nStatement snippet: {stmt[:100]}")

    # Now execute DELIMITER blocks
    for sec in sections[1:]:
        sub_parts = sec.split("DELIMITER ;")
        proc_block = sub_parts[0]
        # Inside proc_block, routines end with //
        routines = [r.strip() for r in proc_block.split("//") if r.strip()]
        for r in routines:
            if r.startswith("--") or r.startswith("/*"):
                lines = [l for l in r.split("\n") if not l.strip().startswith("--")]
                r = "\n".join(lines).strip()
                if not r:
                    continue
            try:
                cursor.execute(r)
            except Exception as e:
                print(f"Notice executing routine: {e}\nRoutine snippet: {r[:100]}")

        # The remainder after DELIMITER ; is standard SQL
        if len(sub_parts) > 1:
            rest = sub_parts[1]
            rest_stmts = [s.strip() for s in rest.split(";") if s.strip()]
            for s in rest_stmts:
                if s.startswith("--"):
                    lines = [l for l in s.split("\n") if not l.strip().startswith("--")]
                    s = "\n".join(lines).strip()
                    if not s:
                        continue
                try:
                    cursor.execute(s)
                except Exception as e:
                    print(f"Notice executing rest statement: {e}\nStatement snippet: {s[:100]}")

    cursor.execute("SHOW TABLES;")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n[OK] Database initialized successfully! Total tables created: {len(tables)}")
    print("Tables:", ", ".join(tables))

    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW';")
    views = [row[0] for row in cursor.fetchall()]
    print(f"[OK] Total Views created: {len(views)}")
    print("Views:", ", ".join(views))

    conn.close()

if __name__ == "__main__":
    init_database()
