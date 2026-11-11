"""Classify one question with the saved MediScope baseline model."""

import argparse
from pathlib import Path

import joblib

MODEL_FILE = Path(__file__).resolve().parent / "models" / "query_classifier.joblib"
ROUTE_DESCRIPTIONS = {
    "KNOWLEDGE_RAG": "Search approved medical documents for supporting evidence.",
    "LITERATURE_CONTEXT": "Search research papers and summarize study-level evidence.",
    "GENERAL_INFORMATION": "Give a brief, low-risk educational explanation.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a MediScope question.")
    parser.add_argument("question", help="A question to classify")
    args = parser.parse_args()

    if not MODEL_FILE.exists():
        raise SystemExit(
            "Trained model not found. Run `py train_query_classifier.py` first."
        )

    model = joblib.load(MODEL_FILE)
    route = model.predict([args.question])[0]
    print(f"Question: {args.question}")
    print(f"Route: {route}")
    print(f"Next action: {ROUTE_DESCRIPTIONS[route]}")
    print("Note: routing only; medical safety checks are not implemented here yet.")


if __name__ == "__main__":
    main()
