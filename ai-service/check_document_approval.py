"""Check that a document has an approved review and matches the reviewed file."""

import argparse

from app.documents.approval_gate import ApprovalGateError, require_approved_document


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check approval and file identity before a future indexing step."
    )
    parser.add_argument("document", help="Path to the reviewed PDF or TXT file")
    parser.add_argument("review_record", help="Path to its saved JSON review record")
    args = parser.parse_args()

    try:
        document = require_approved_document(args.document, args.review_record)
    except ApprovalGateError as error:
        parser.exit(status=1, message=f"Approval gate blocked the document: {error}\n")

    print("Approval gate passed.")
    print(f"File: {document.path.name}")
    print(f"SHA-256: {document.sha256}")
    print("No text was extracted, saved, or indexed by this check.")


if __name__ == "__main__":
    main()
