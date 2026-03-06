import sys
import json
from pathlib import Path
from db.database import engine, init_db, SessionLocal
from db.models import Base
from parser.replay_importer import import_replay, parse_replay_blocks
from parser.liquipedia_sync import sync_tournament


def create_tables():
    init_db()
    print("Database tables created.")


def drop_tables():
    confirm = input("Are you sure you want to drop all tables? This action cannot be undone! (yes/no): ")
    if confirm.lower() == "yes":
        Base.metadata.drop_all(engine)
        print("All database tables dropped.")
    else:
        print("Drop tables cancelled.")


def recreate_tables():
    drop_tables()
    create_tables()
    print("Database tables recreated.")


def import_one(replay_path: str):
    session = SessionLocal()
    try:
        import_replay(replay_path, session)
        print(f"Replay imported successfully: {replay_path}")
    except Exception as e:
        print(f"Error importing replay: {e}")
        session.rollback()
    finally:
        session.close()

def import_directory(directory: str):
    replays = list(Path(directory).glob("*.wotreplay"))
    print(f"Found {len(replays)} replays in directory: {directory}")
    session = SessionLocal()
    for replay in replays:
        print(f"Processing: {replay}")
        try:
            import_replay(str(replay), session)
        except Exception as e:
            print(f"Error importing {replay}: {e}")
            session.rollback()
    session.close()
    print("Finished importing replays.")


def export_to_json(replay_path: str, output_path: str, block: str = None):
    path = Path(replay_path)
    if not path.exists():
        print(f"Error: file not found: {replay_path}")
        sys.exit(1)

    try:
        blocks = parse_replay_blocks(replay_path)
    except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    if block is not None:
        block_idx = int(block)
        if block_idx >= len(blocks):
            print(f"Error: replay only has {len(blocks)} block(s)")
            sys.exit(1)
        output_data = blocks[block_idx]
        label = f"block {block_idx}"
    else:
        output_data = blocks
        label = "all blocks"

    json_str = json.dumps(output_data, indent=2, ensure_ascii=False)

    if output_path:
        Path(output_path).write_text(json_str, encoding="utf-8")
        print(f"Saved {label} to {output_path}")
    else:
        print(json_str)

def sync_liquipedia(tournament_name: str):
    sync_tournament(tournament_name)


COMMANDS = {
    "create":    (create_tables,   "Create tables"),
    "drop":      (drop_tables,     "Drop all tables"),
    "recreate":  (recreate_tables, "Drop and recreate tables"),
    "import":    (import_one,      "Import one replay:    import <path>"),
    "importall": (import_directory,   "Import whole directory:  importall <path>"),
    "export":    (export_to_json,   "Export replay to JSON:  export <replay_path> <output_path> [block]"),
    "sync":      (sync_liquipedia, "Sync tournament from Liquipedia: sync <tournament_pagename>"),
}


def usage():
    print("Usage: python manage.py <command> [args]\n")
    print("Commands:")
    for cmd, (_, desc) in COMMANDS.items():
        print(f"  {cmd:<12} {desc}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        usage()
        sys.exit(1)

    cmd  = sys.argv[1]
    args = sys.argv[2:]
    fn   = COMMANDS[cmd][0]
    fn(*args) if args else fn()
