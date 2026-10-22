import sys
from tokeniser import tokenize_file
from parser import parse
from main_engine import execute


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <script_file>")
        print("Example: python run.py automation.txt")
        sys.exit(1)

    filepath = sys.argv[1]

    print(f"[1/3] Tokenising '{filepath}' ...")
    tokens = tokenize_file(filepath)
    if not tokens:
        sys.exit(1)

    print("[2/3] Parsing ...")
    ast = parse(tokens)

    print(f"[3/3] Running ({len(ast)} top-level statements) ...\n")
    execute(ast)

    print("\n[OK] Script finished.")


if __name__ == "__main__":
    main()
