import json
import sys
from parser.liquipedia_sync import sync_tournament
from parser.replay_importer import import_replay
from parser.utils import list_all_replay_maps, parse_replay_blocks
from pathlib import Path
from typing import Optional

from db.database import SessionLocal, engine, init_db
from db.models import Base, Tournament, TournamentMode
from logging_config import get_logger

logger = get_logger(__name__)


def create_tables():
    init_db()
    logger.info("Database tables created.")


def drop_tables():
    confirm = input(
        "Are you sure you want to drop all tables? This action cannot be undone! (yes/no): "
    )
    if confirm.lower() == "yes":
        Base.metadata.drop_all(engine)
        logger.info("All database tables dropped.")
    else:
        logger.info("Drop tables cancelled.")


def recreate_tables():
    drop_tables()
    create_tables()
    logger.info("Database tables recreated.")


def import_one(replay_path: str):
    session = SessionLocal()
    try:
        import_replay(replay_path, session)
        logger.info(f"Replay imported successfully: {replay_path}")
    except Exception as e:
        logger.error(f"Error importing replay: {e}")
        session.rollback()
    finally:
        session.close()


def import_directory(directory: str):
    replays = list(Path(directory).rglob("*.wotreplay"))
    logger.info(f"Found {len(replays)} replays in directory: {directory}")
    session = SessionLocal()
    for replay in replays:
        logger.debug(f"Processing: {replay}")
        try:
            import_replay(str(replay), session)
        except Exception as e:
            logger.error(f"Error importing {replay}: {e}")
            session.rollback()
    session.close()
    logger.info("Finished importing replays.")


def export_to_json(
    replay_path: str, output_path: str, block: Optional[str] = None
) -> None:
    path = Path(replay_path)
    if not path.exists():
        logger.error(f"File not found: {replay_path}")
        sys.exit(1)

    try:
        blocks = parse_replay_blocks(replay_path)
    except ValueError as e:
        logger.error(f"Error parsing replay blocks: {e}")
        sys.exit(1)

    if block is not None:
        try:
            block_idx = int(block)
        except ValueError:
            logger.error(f"Block must be an integer, got: {block!r}")
            sys.exit(1)
        if block_idx >= len(blocks):
            logger.error(f"Replay only has {len(blocks)} block(s)")
            sys.exit(1)
        output_data = blocks[block_idx]
        label = f"block {block_idx}"
    else:
        output_data = blocks
        label = "all blocks"

    json_str = json.dumps(output_data, indent=2, ensure_ascii=False)

    if output_path:
        Path(output_path).write_text(json_str, encoding="utf-8")
        logger.info(f"Saved {label} to {output_path}")
    else:
        logger.info(json_str)


def sync_liquipedia(tournament_pagename: str):
    sync_tournament(tournament_pagename)


def set_tournament_mode(liquipedia_id: int, mode: str):
    try:
        parsed_mode = TournamentMode(mode)
    except ValueError:
        valid = ", ".join(m.value for m in TournamentMode)
        logger.error(f"Invalid mode: {mode!r}. Valid modes are: {valid}")
        sys.exit(1)

    with SessionLocal() as session:
        tournament = (
            session.query(Tournament).filter_by(liquipedia_id=liquipedia_id).first()
        )
        if not tournament:
            logger.error(f"Tournament not found with Liquipedia ID: {liquipedia_id}")
            sys.exit(1)

        tournament.mode = parsed_mode
        session.commit()

    logger.info(
        f"Updated tournament '{tournament.name}' (Liquipedia ID: {liquipedia_id}) with mode: {parsed_mode.value}"
    )


def discover_maps(directory: str):
    maps = list_all_replay_maps(directory)

    if not maps:
        logger.warning("No replays found or no map data extracted.")
        return

    lines = [f'  "{k}": "{v}",' for k, v in maps.items()]
    output = "MAPS = {\n" + "\n".join(lines) + "\n}"

    logger.info(output)
    logger.info(f"{len(maps)} unique maps found")


COMMANDS = {
    "create": (create_tables, "Create tables"),
    "drop": (drop_tables, "Drop all tables"),
    "recreate": (recreate_tables, "Drop and recreate tables"),
    "import": (import_one, "Import one replay:    import <path>"),
    "importall": (import_directory, "Import whole directory:  importall <path>"),
    "export": (
        export_to_json,
        "Export replay to JSON:  export <replay_path> <output_path> [block]",
    ),
    "sync": (
        sync_liquipedia,
        "Sync tournament from Liquipedia: sync <tournament_pagename>",
    ),
    "set-mode": (
        set_tournament_mode,
        "Set tournament mode: set-mode <liquipedia_id> <mode>",
    ),
    "discover-maps": (discover_maps, "Discover maps from replays: discover-maps <dir>"),
}


def usage():
    logger.info("Usage: python mammoth.py <command> [args]")
    logger.info("Commands:")
    for cmd, (_, desc) in COMMANDS.items():
        logger.info(f"  {cmd:<12} {desc}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        usage()
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    fn = COMMANDS[cmd][0]
    fn(*args) if args else fn()
