from pathlib import Path
import argparse
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "mock_roaming_cdrs.csv"


def run_step(script_name: str) -> None:
    script_path = PROJECT_ROOT / "src" / script_name

    print(f"\nRunning: {sys.executable} {script_path}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(f"Step failed: {script_name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the roaming billing CDR validation lab."
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to input roaming CDR CSV file. Default: data/mock_roaming_cdrs.csv",
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    if input_path.resolve() != DEFAULT_INPUT.resolve():
        print(f"Using custom input file: {input_path}")
        print(f"Copying it to project working input: {DEFAULT_INPUT}")
        shutil.copyfile(input_path, DEFAULT_INPUT)
    else:
        print(f"Using default input file: {DEFAULT_INPUT}")

    run_step("validator.py")
    run_step("reconcile.py")
    run_step("generate_report.py")

    print("\nDone. Check the reports/ folder.")


if __name__ == "__main__":
    main()