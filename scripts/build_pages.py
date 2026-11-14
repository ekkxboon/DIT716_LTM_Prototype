"""Stage a safe static GitHub Pages bundle; evaluator-only labels are never copied."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_site(destination: Path) -> Path:
    destination = destination.resolve()
    web_dir = ROOT / "web"
    if destination == ROOT or destination == ROOT / "evaluation_labels.json":
        raise ValueError("Refusing to build over a project source path")
    if destination == (ROOT / "dist").resolve() and destination.exists():
        shutil.rmtree(destination)
    elif destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Build destination must be empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(web_dir, destination, dirs_exist_ok=True)
    data_dir = destination / "data"
    data_dir.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "fixtures.json", data_dir / "fixtures.json")
    shutil.copy2(ROOT / "results" / "policy_results.csv", data_dir / "policy_results.csv")
    if any(path.name == "evaluation_labels.json" for path in destination.rglob("*")):
        raise RuntimeError("Evaluator-only labels must never be deployed")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    result = build_site(args.output)
    print(f"GitHub Pages bundle ready: {result}")
    print("Included: web UI, synthetic fixture corpus, and policy result CSVs.")
    print("Excluded: evaluator labels and Python database/runtime files.")


if __name__ == "__main__":
    main()
