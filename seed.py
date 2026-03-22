from database import SessionLocal, Word, engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import text
import time

#citim din fisierul de populare, si dacem un window de cuvinte
def seed_data(file_path="cuvinte.txt"):
    db = SessionLocal()
    with engine.connect() as conn:
        conn.execute(text("PRAGMA synchronous = OFF"))
        conn.execute(text("PRAGMA journal_mode = MEMORY"))
        conn.execute(text("PRAGMA cache_size = -100000"))
        conn.commit()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            words = list(set(line.strip().lower() for line in f if line.strip()))
        print(f"{len(words)} cuvinte...")
        batch_size = 10000
        for i in range(0, len(words), batch_size):
            batch = words[i : i + batch_size]
            data = [{"original_word": w, "sorted_word": "".join(sorted(w))} for w in batch]
            stmt = sqlite_insert(Word).values(data).on_conflict_do_nothing()
            db.execute(stmt)
            db.commit()
    except FileNotFoundError:
        print("Creeaza fisierul cuvinte.txt!!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()