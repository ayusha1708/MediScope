# Query classification specification

**Status:** Approved for initial implementation  
**Version:** 1.0  
**Purpose:** Route a user question to the right answer workflow; this is not a medical diagnosis model.

## What the classifier decides

The classifier assigns one of the three labels in the project brief. It chooses how the application handles the question; it does not decide what is medically true.

### `KNOWLEDGE_RAG`

Use when the user asks a general medical or health-education question that should be answered from relevant approved documents in the MediScope repository.

**Route:** search the approved knowledge collection, check whether useful evidence was found, then generate a cited answer or a no-evidence fallback.

### `LITERATURE_CONTEXT`

Use when the user specifically asks about research literature: study methods, results, limitations, comparisons between papers, or what a named/identified study reported.

**Route:** search the approved repository with priority for research papers and reviews, then answer with study-level citations and limitations where available.

### `GENERAL_INFORMATION`

Use for low-risk, general educational explanations or conversational questions that do not specifically ask for evidence from the repository or research-paper analysis.

**Route:** give a brief educational response. If the question needs evidence, the response should use repository retrieval when suitable sources exist. If evidence is unavailable, say so; do not invent citations.

## Keep safety and uncertainty outside these three labels

A separate safety check runs before ordinary classification. A request for a personal diagnosis, medication choice/dose, or urgent symptom response must not be treated as an ordinary general-information question. Urgent symptoms get a safety-oriented response advising professional/emergency care. Other personal medical requests get a safe boundary response and, when appropriate, an invitation to ask a qualified professional. This project does not diagnose or prescribe.

If a question is unclear or the classifier is uncertain, the system should ask a short clarifying question or use the safer evidence-retrieval path. It must not silently route an uncertain medical question to an unsupported answer. We will choose and evaluate any confidence threshold later; we will not invent one now.

## Operational tie-breakers for labels

Use the kind of answer the user is asking for:

- `LITERATURE_CONTEXT` only when the question explicitly asks about research papers, studies, trials, reviews, their methods/results/limitations, or comparison of published findings.
- `KNOWLEDGE_RAG` for medical facts, causes, mechanisms, symptoms, classifications, or guidance that should be supported by the approved repository. Asking for a source, evidence, or the MediScope library does **not by itself** make a question literature-focused.
- `GENERAL_INFORMATION` for a simple, low-risk definition or basic concept explanation without a request for research analysis or deeper evidence.

If the wording is ambiguous between general information and RAG, route to RAG so medical claims can be supported. A separate safety check still runs first for personal diagnosis, medication decisions/doses, and urgent symptoms.

Examples: “What does inflammation mean?” → `GENERAL_INFORMATION`; “What causes anemia?” → `KNOWLEDGE_RAG`; “Explain anemia using approved sources” → `KNOWLEDGE_RAG`; “Compare the findings of two anemia trials” → `LITERATURE_CONTEXT`.

## Dataset and initial model comparison

`data/query_train.csv` and `data/query_test.csv` contain the current balanced synthetic dataset. `data/query_examples_batch_1.csv` holds 30 examples approved by the project owner and included in training. `data/query_examples_seed.csv` is an earlier seed and is not merged. The v1 test set was inspected for error analysis and is now development data in `data/query_dev_v1.csv`; it is not a final test set.

The first experiment compares TF-IDF with Logistic Regression, Multinomial Naive Bayes, and Linear SVM using topic-grouped cross-validation, then evaluates the selected model on the fresh v2 test set. Results are saved in `ai-service/reports/query_classifier_metrics.json`. Because the corpus is synthetic, these metrics do not estimate performance on real user questions.

No real user health queries are included. Before claiming real-world performance, collect and label a separate natural-question set without personal health details and with appropriate consent.

## Approval

The project owner approved the operational tie-breakers in Version 1.0: explicit study/paper/trial/review analysis routes to Literature Context; medical facts and evidence/source requests route to Knowledge RAG; simple definitions route to General Information.

