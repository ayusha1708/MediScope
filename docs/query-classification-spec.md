# Query classification specification (draft)

**Status:** Draft for review  
**Version:** 0.1  
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

## Labeling rule for borderline questions

Use the user's requested *kind of answer* as the deciding clue:

- General medical explanation backed by the repository → `KNOWLEDGE_RAG`.
- Explicit focus on published studies or comparisons → `LITERATURE_CONTEXT`.
- Simple, low-risk definition/explanation without a request for repository evidence or study analysis → `GENERAL_INFORMATION`.

For example, “Explain asthma using our approved sources” is `KNOWLEDGE_RAG`; “Compare the methods and results of two asthma trials” is `LITERATURE_CONTEXT`; “What does the word inflammation mean?” is `GENERAL_INFORMATION`.

## Seed examples

`data/query_examples_seed.csv` contains four illustrative examples per label. It is a teaching/review seed only. It is **not enough to train or evaluate a model**, and no performance claim should be made from it. The examples should be reviewed and corrected before we expand the dataset.

When we build the real dataset, each row will have one primary label assigned by a human. We will collect varied wording, remove duplicates and near-duplicates before splitting, and keep a separate held-out test set. We should not put private user health questions into the dataset without a clear consent and privacy plan.

## Planned model experiment (later step)

Once we have enough reviewed examples, we will use TF-IDF text features and compare Logistic Regression, Multinomial Naive Bayes, and Linear SVM as stated in the brief. We will select based on held-out precision, recall, F1-score, and confusion matrix—not training accuracy alone. If the dataset is too small or labels are unclear, we will improve the dataset before claiming a useful classifier.

## Questions to review

Please check that the three definitions match how you want MediScope to route questions. In particular, confirm that the default/general path stays limited to low-risk education and that personal or urgent medical questions go through the separate safety handling described above.
