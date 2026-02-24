import sys
from pathlib import Path

def import_folder(replay_dir: str):
    init_db()
    session = SessionLocal()
    replay_files = list(Path(replay_dir).glob("*.wotreplay"))
    print(f"Found {len(replay_files)} replay files in {replay_dir}")
    for f in replay_files:
        print(f"Processing: {f.name}")
        try:
            import_replay(str(f), session)
        except Exception as e:
            print(f"  ERROR: {e}")
            session.rollback()
    session.close()

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    import_folder(folder)
