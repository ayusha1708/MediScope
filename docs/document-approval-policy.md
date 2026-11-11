# MediScope document approval policy (draft)

**Status:** Approved for initial implementation  
**Decision owner:** Human administrator  
**Policy version:** 1.0

## 1. Purpose and meaning of approval

This policy decides whether a submitted document may enter MediScope's searchable educational collection, and records why.

`APPROVED` means the document passed MediScope's eligibility, access, reuse, and traceability checks. It does **not** mean MediScope independently proved every medical claim or certified the document as clinically reliable. The AI may extract details and flag concerns; a human administrator checks the evidence and makes the decision.

This is a repository-admission policy, not a clinical evidence appraisal. The U.S. National Library of Medicine says that inclusion in its databases does not mean it reviews, evaluates, or judges the quality of each individual article. MediScope will make an even narrower claim about its own approvals.

## 2. Proposed initial collection scope

Accept material that supports medical, healthcare, or medical-education learning, such as:

- Peer-reviewed original research papers and review articles with an identifiable publication source.
- Clinical guidelines or recommendations from an identifiable professional, academic, or public-health organization.
- Educational resources from an identifiable academic, professional, or public-health source.
- Case studies with an identifiable publication source and no identifiable private patient information.

Do not index advertisements, product promotion, personal medical records, unsourced web text, or material unrelated to the project's scope.

**Agreed initial rule:** exclude preprints from the first version. This is a scope choice, not a claim that every preprint is poor quality. Preprints may be considered later as a separate, clearly labeled type.

## 3. Admin decision checklist

For every submission, the administrator records each check as **PASS**, **NEEDS INFORMATION**, **FAIL**, or **NOT APPLICABLE** and adds a brief note or source. There is no combined numeric score.

### Check 1 — Free online access

- The full text is available from a source URL without payment or an account/login.
- Record the URL and the date it was checked.
- An abstract-only page does not pass; MediScope needs access to the document text it will process.

If full text is not freely accessible, the document does not meet the initial collection rule.

### Check 2 — Permission to use the text in MediScope

Free-to-read and permission-to-reuse are separate checks. A free webpage does not automatically grant permission to copy or process the document.

The administrator records the license or permission evidence and verifies that it covers the intended project actions:

- Keep a local copy for the academic project.
- Extract text, split it into passages, and create/store embeddings for search.
- Return citations and short attributed excerpts to users.

Follow license conditions such as attribution or non-commercial-use limits. Do not publish or redistribute the full document unless its terms allow it. If no clear reuse permission is visible, or the reviewer cannot tell whether the intended processing is allowed, mark **NEEDS INFORMATION** and do not index it until clarified. This is an operational safeguard; unclear rights should be checked with the rights holder or instructor rather than guessed.

### Check 3 — Source and document identity are traceable

- Record a source locator: DOI, PMID, publisher/issuing-organization page, stable URL, or catalog record.
- Confirm that the source's title and publication details match the submitted document.
- Record available title, author(s) or issuing organization, date, journal/publisher, document type, and version/edition.

A DOI or PMID is helpful for finding a record, but it is not proof that the findings are correct. A missing DOI/PMID is not an automatic failure if a credible source and identity can still be checked. If the source cannot be established, request information or reject it.

### Check 4 — Scope and document type

- Confirm that it is about medicine, healthcare, or medical education.
- Select the type: research paper, review, guideline, educational resource, case study, or other (explain).
- Write one sentence explaining why it belongs in the collection.

The AI's relevance/type prediction is only a suggestion. The administrator checks it and records the final category.

### Check 5 — File usability and privacy

- Confirm that the PDF or TXT opens, is not empty/corrupt, and has enough readable text to search and cite.
- Check for an exact duplicate already in the collection.
- Do not accept identifiable private patient records or case-study details. For the initial project, reject files with identifiable patient information rather than trying to automatically de-identify them.

A fixable upload or metadata problem can be returned for revision. An unusable or privacy-inappropriate document fails this check.

### Check 6 — Publication status and currency

- Check the publisher/issuing organization and a relevant bibliographic record when available for retraction, withdrawal, correction, or a newer version.
- Do not index a retracted or withdrawn item as ordinary evidence. Record the notice and reject it from the active collection.
- If a correction changes the document, review the corrected version and link it to the record; do not present an outdated copy as current.
- If the status check is inconclusive, mark **NEEDS INFORMATION** or keep it pending; “not found” does not mean “verified clean.”
- Use no fixed age cutoff by default. Record the publication/update date. For current guidelines, check whether the issuing organization has replaced the version. Older documents may be included as historical/foundational material when labeled.

A correction or expression of concern is a reason to inspect the record and explain the decision. It does not automatically prove that every part of a document is unusable. COPE describes retractions as a way to correct the scholarly record; PubMed also identifies retraction notices and errata.

## 4. How checklist results determine the decision

- **APPROVED:** all applicable mandatory checks pass; the reviewer records a reason. Only this status may enter indexing.
- **NEEDS_REVISION:** a fixable detail or evidence is missing, including unclear source/version or reuse terms. The document stays out of retrieval until resolved.
- **PENDING_ADMIN_REVIEW:** screening is incomplete or the human decision has not been made. The document stays out of retrieval.
- **REJECTED:** a mandatory check fails—for example, no free full text, reuse permission does not cover the project use, the document is out of scope, it is unusable or privacy-inappropriate, or it is retracted/withdrawn for active evidence use. Record the specific reason.

If an approved document is later found to be superseded, corrected, or retracted, remove or update its indexed passages and preserve the status-change reason in the audit history.

## 5. What the AI screening report may do

The AI service may help by reporting observable items: extraction success/page count, possible duplicate and matched record, predicted relevance/type, extracted metadata, source lookup performed, a possible correction/retraction notice and link, or missing fields.

It must not mark a document approved or claim it is “medically accurate,” “safe to follow,” or “clinically reliable.” The administrator verifies important details and writes the decision reason. The AI output is stored separately from the human decision.

## 6. Review record to keep

For every decision, retain:

- Submission/document ID and version.
- Reviewer ID, decision time, final status, and reviewer-written reason.
- Result and notes for each applicable checklist item.
- Full-text source URL and date checked.
- License/permission type, evidence URL or record, and conditions that apply.
- Publication/source locators checked and date checked.
- AI screening report, clearly separate from the human decision.
- Contributor visibility choice separate from public citation fields.
- Requested corrections, replacement versions, and later status changes.

For anonymous contributions, public citation fields must not reveal the contributor's internal identity.

## 7. Example explanation for an instructor

“We included this document because its full text was freely available online, its license allowed our project to store and process it for search, the source and publication details matched, it fit our medical-education scope, and it passed the usability and publication-status checks. The administrator recorded the evidence and rationale. AI helped extract details and flag issues, but did not approve it. Approval means it met our repository rules; it does not mean we independently certified every medical claim. Pending and rejected documents are excluded from search.”

If a document is held or rejected, state which check needs information or failed and show that its status kept it out of retrieval.

## 8. Limits of the rubric

This checklist is meant to make repository decisions consistent and explainable. It is not a validated clinical evidence-appraisal tool. MediScope will not claim that it performs full risk-of-bias assessment, guideline appraisal, or clinical recommendation grading. Peer review, indexing, a DOI, and a reputable publisher can support traceability but do not alone prove a result is true. Until a separate validated evaluation exists, report source details and flags rather than a misleading quality/trust score.

## 9. Agreed defaults for initial implementation

1. **Preprints:** exclude from initial indexing.
2. **Language:** English-only initially, to keep extraction and evaluation manageable.
3. **Age:** no fixed cutoff; record dates and check whether current guidance has been replaced.
4. **Audience:** general medical education and student learning; no diagnosis or treatment advice (from the project brief).
5. **Document types:** the types listed in Section 2.

These defaults are approved for the initial upload and review workflow.

## References

- [NLM/PubMed disclaimer](https://pubmed.ncbi.nlm.nih.gov/disclaimer/) — inclusion does not mean NLM evaluates each individual article's quality.
- [COPE Retraction Guidelines](https://publicationethics.org/sites/default/files/retraction-guidelines-cope.pdf) — retractions and correction of the scholarly record.
- [PubMed Help](https://pubmed.ncbi.nlm.nih.gov/help/) — retraction notice, retracted publication, and erratum publication types.
- [Creative Commons FAQ](https://creativecommons.org/faq/) — reuse depends on the applicable license and its conditions.

