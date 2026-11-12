"""Validate and save a human-completed MediScope document review form."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from app.documents.approval import ApprovalRecord, ApprovalRecordError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW_RECORDS_DIR = PROJECT_ROOT / "data" / "document_reviews"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and save an admin-completed document review JSON form."
    )
    parser.add_argument("review_form", help="Path to the completed review JSON file")
    args = parser.parse_args()

    form_path = Path(args.review_form)
    try:
        form = json.loads(form_path.read_text(encoding="utf-8"))
        record = ApprovalRecord.from_dict(form)
    except (OSError, json.JSONDecodeError, ApprovalRecordError) as error:
        parser.exit(status=1, message=f"Could not save review: {error}\n")

    document_id = str(record.document.get("document_id", "")).strip()
    if not document_id:
        document_id = str(uuid4())
        record.document["document_id"] = document_id

    # Keep the filename safe and portable; preserve the full ID in the record.
    safe_id = "".join(char for char in document_id if char.isalnum() or char in "-_")
    if not safe_id:
        parser.exit(status=1, message="Could not save review: invalid document_id.\n")

    REVIEW_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REVIEW_RECORDS_DIR / f"{safe_id}.json"
    if output_path.exists():
        parser.exit(
            status=1,
            message=(
                f"Could not save review: {output_path.name} already exists. "
                "Use a new document_id so an earlier decision is not overwritten.\n"
            ),
        )

    output_path.write_text(
        json.dumps(record.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Decision: {record.decision.value}")
    print("This is an admin-recorded repository decision, not a medical-quality certification.")
    print(f"Review record saved to: {output_path}")


if __name__ == "__main__":
    main()
