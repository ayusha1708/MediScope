"""Validate human-entered document review records against MediScope policy."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CheckStatus(StrEnum):
    PASS = "PASS"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    NEEDS_REVISION = "NEEDS_REVISION"
    PENDING_ADMIN_REVIEW = "PENDING_ADMIN_REVIEW"
    REJECTED = "REJECTED"


REQUIRED_CHECKS = (
    "free_online_access",
    "reuse_permission",
    "traceable_identity",
    "scope_and_document_type",
    "file_usability_and_privacy",
    "publication_status",
)


class ApprovalRecordError(ValueError):
    """Raised when a review record is incomplete or inconsistent."""


@dataclass(frozen=True)
class ApprovalRecord:
    """A human review and the evidence supporting its final decision."""

    document: dict[str, Any]
    reviewer_id: str
    reviewed_at: str
    decision: ReviewDecision
    decision_reason: str
    checks: dict[str, dict[str, str]]
    ai_screening_report: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRecord":
        if not isinstance(data, dict):
            raise ApprovalRecordError("The review form must contain a JSON object.")

        required_fields = (
            "document",
            "reviewer_id",
            "reviewed_at",
            "decision",
            "decision_reason",
            "checks",
        )
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ApprovalRecordError(
                "Missing required fields: " + ", ".join(missing_fields)
            )

        document = data["document"]
        checks = data["checks"]
        if not isinstance(document, dict) or not document:
            raise ApprovalRecordError("'document' must be a non-empty object.")
        if not isinstance(checks, dict):
            raise ApprovalRecordError("'checks' must be an object.")

        missing_checks = [name for name in REQUIRED_CHECKS if name not in checks]
        if missing_checks:
            raise ApprovalRecordError(
                "Missing checklist items: " + ", ".join(missing_checks)
            )

        normalized_checks: dict[str, dict[str, str]] = {}
        for name in REQUIRED_CHECKS:
            result = checks[name]
            if not isinstance(result, dict) or "status" not in result:
                raise ApprovalRecordError(f"Check '{name}' needs a status and note.")
            try:
                status = CheckStatus(result["status"])
            except ValueError as error:
                allowed = ", ".join(item.value for item in CheckStatus)
                raise ApprovalRecordError(
                    f"Check '{name}' status must be one of: {allowed}."
                ) from error
            note = result.get("note", "")
            if not isinstance(note, str):
                raise ApprovalRecordError(f"Check '{name}' note must be text.")
            if not note.strip():
                raise ApprovalRecordError(
                    f"Check '{name}' needs a note describing its evidence or outcome."
                )
            normalized_checks[name] = {"status": status.value, "note": note.strip()}

        try:
            decision = ReviewDecision(data["decision"])
        except ValueError as error:
            allowed = ", ".join(item.value for item in ReviewDecision)
            raise ApprovalRecordError(
                f"Decision must be one of: {allowed}."
            ) from error

        reviewer_id = _required_text(data, "reviewer_id")
        reviewed_at = _required_text(data, "reviewed_at")
        decision_reason = _required_text(data, "decision_reason")
        ai_report = data.get("ai_screening_report")
        if ai_report is not None and not isinstance(ai_report, dict):
            raise ApprovalRecordError("'ai_screening_report' must be an object or null.")

        record = cls(
            document=document,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            decision=decision,
            decision_reason=decision_reason,
            checks=normalized_checks,
            ai_screening_report=ai_report,
        )
        record.validate_decision()
        return record

    def validate_decision(self) -> None:
        """Ensure the admin's chosen status agrees with the recorded checklist."""
        statuses = [CheckStatus(item["status"]) for item in self.checks.values()]
        if self.decision == ReviewDecision.APPROVED:
            if any(status not in (CheckStatus.PASS, CheckStatus.NOT_APPLICABLE) for status in statuses):
                raise ApprovalRecordError(
                    "APPROVED requires every applicable check to PASS; "
                    "NOT_APPLICABLE results need a written justification."
                )
            approval_fields = (
                "title",
                "authors_or_organization",
                "publication_date",
                "publisher_or_journal",
                "document_type",
                "source_locator",
                "full_text_url",
                "full_text_access_checked_on",
                "license_or_permission",
                "permission_evidence_url",
                "permission_conditions",
                "scope_reason",
                "file_sha256",
            )
            missing_fields = [
                field
                for field in approval_fields
                if not isinstance(self.document.get(field), str)
                or not self.document[field].strip()
            ]
            if missing_fields:
                raise ApprovalRecordError(
                    "APPROVED needs these document details filled in: "
                    + ", ".join(missing_fields)
                )
        elif self.decision == ReviewDecision.REJECTED:
            if CheckStatus.FAIL not in statuses:
                raise ApprovalRecordError("REJECTED requires at least one failed check.")
        elif self.decision == ReviewDecision.NEEDS_REVISION:
            if (
                CheckStatus.NEEDS_INFORMATION not in statuses
                or CheckStatus.FAIL in statuses
            ):
                raise ApprovalRecordError(
                    "NEEDS_REVISION requires missing information and no failed checks. "
                    "A failed mandatory check requires REJECTED."
                )
        elif self.decision == ReviewDecision.PENDING_ADMIN_REVIEW:
            if CheckStatus.FAIL in statuses:
                raise ApprovalRecordError(
                    "A failed mandatory check requires REJECTED, not PENDING_ADMIN_REVIEW."
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable copy of this record."""
        return {
            "document": self.document,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "decision": self.decision.value,
            "decision_reason": self.decision_reason,
            "checks": self.checks,
            "ai_screening_report": self.ai_screening_report,
        }


def _required_text(data: dict[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ApprovalRecordError(f"'{field}' must be non-empty text.")
    return value.strip()
