"""Seed and evaluate from the terminal: python -m atlas.cli seed|eval."""
import argparse
import asyncio
import os
from pathlib import Path

from atlas.config import DEFAULT_MODELS
from atlas.evaluation import evaluate
from atlas.store import Store

ROOT = Path(os.getenv("ATLAS_PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))


def seed(store: Store) -> int:
    count = 0
    for path in (ROOT / "examples" / "knowledge").glob("*.md"):
        result = store.add_document(path.stem.replace("_", " ").title(),
                                    path.read_text(encoding="utf-8"))
        count += int(not result["duplicate"])
    return count


def main():
    parser = argparse.ArgumentParser(description="ATLAS local developer utilities")
    parser.add_argument("command", choices=["seed", "eval", "serve", "index-semantic"])
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-chunks", type=int, default=256)
    parser.add_argument("--provider", default="demo", choices=list(DEFAULT_MODELS))
    args = parser.parse_args()
    store = Store()
    if args.command == "seed":
        print(f"Seeded {seed(store)} new knowledge documents")
    elif args.command == "index-semantic":
        import json
        print(json.dumps(store.index_semantic(args.batch_size, args.max_chunks), indent=2))
    elif args.command == "eval":
        import json
        print(json.dumps(asyncio.run(evaluate(store, args.provider,
                                            DEFAULT_MODELS[args.provider])), indent=2))
    else:
        import uvicorn
        uvicorn.run("atlas.api:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
