# Query-classifier dataset plan

**Status:** Dataset v1.0 assembled — synthetic baseline  
**Task:** Route an educational question to `KNOWLEDGE_RAG`, `LITERATURE_CONTEXT`, or `GENERAL_INFORMATION`.

## Accuracy: what we can and cannot promise

No fixed number of examples can guarantee “maximum accuracy.” Accuracy depends on how clearly the labels match real user intent, how varied the examples are, and whether the evaluation questions resemble future questions. More examples with repeated wording can make the score look better without making routing better.

The closest published medical resource-routing study we found labeled general-knowledge, research, patient-specific, and other questions. It reported 80.9%–92.8% accuracy across four datasets, and described the task as difficult. Its annotated corpora are available by request, not as a simple public download, and include patient-specific material. We will not copy those data into MediScope without access, permission, and a privacy review. We use the study as evidence that the task is real and challenging, not as a performance promise.

MedQuAD is a large medical question-answer dataset with a CC BY 4.0 license, but its labels describe medical question types rather than MediScope's three routing labels. It cannot be treated as a ready-made route training set. If we adapt any of its questions later, we must retain attribution and have a human assign MediScope labels.

## Dataset we will build

We will create a balanced, MediScope-specific dataset, with original or explicitly reusable question text. Each example will have one label and a short reason. Safety-sensitive personal/urgent questions are handled before this classifier; they should be evaluated separately and must not be silently labeled as ordinary general questions.

### Size target for a first useful experiment

- **Training pool:** at least 300 reviewed examples per class (900 total).
- **Final held-out test set:** 100 reviewed examples per class (300 total), written/selected separately and kept untouched until model selection is finished.
- Use cross-validation on the training pool for comparing Logistic Regression, Multinomial Naive Bayes, and Linear SVM; do not tune on the final test set.

These are practical project targets, not a guarantee that the model is accurate enough. If the data is ambiguous or metrics are unstable, we improve the labels/data and report the limitation. A learning-curve check can tell us whether adding more examples is helping.

### Variety and quality rules

- Keep the classes balanced for the first comparison and report macro-F1 as well as per-class precision/recall/F1 and the confusion matrix.
- Vary wording, length, medical topic, and explicit/implicit source requests. Avoid making every label identifiable by one phrase such as “using our approved sources.”
- Include borderline pairs so annotators learn the boundary (for example, a simple definition versus a request for evidence; a general fact versus a comparison of studies).
- Keep paraphrases of the same underlying question in one split. Split by example-family/topic, not randomly by row, to reduce leakage.
- Have a human review every label. If two reviewers are available, compare their labels on a sample and discuss disagreements before expanding.
- Do not include private patient details or real user query logs without consent and a privacy plan.
- Keep a separate set of safety examples for the safety pre-check. It is not a fourth route class.

## Dataset v1.0 files

- `data/query_train.csv`: 900 questions, balanced at 300 per route. It includes the 30 project-owner-approved examples and 870 original synthetic examples.
- `data/query_test.csv`: 300 separate synthetic questions, balanced at 100 per route. It uses separate question templates and topic groups and has no exact query overlap with training. Keep it untouched while fitting or tuning models.
- Both files include query ID, text, label, topic group, origin/review status, and a short label rationale.

The 30 examples in `data/query_examples_batch_1.csv` were approved and merged into training. The earlier 12-row `data/query_examples_seed.csv` was not merged because it was an earlier draft and could introduce duplicates.

## Limits of this first dataset

The remaining training examples and the complete test set are assistant-authored synthetic questions labeled from the approved rules. There are no real user queries or private medical details. This makes a balanced baseline that can be used to teach the model-comparison workflow, but its test score will measure performance on this synthetic writing style, not on real MediScope users. Before claiming real-world accuracy, we need a separately collected and human-labeled set of natural questions, with no personal health details and appropriate consent. Report the dataset as synthetic in academic work.

## Source notes

- [Roberts et al., Resource Classification for Medical Questions](https://pmc.ncbi.nlm.nih.gov/articles/PMC5333297/) — resource-routing task and annotation challenges; the paper says its annotated corpora are available by request.
- [MedQuAD official repository](https://github.com/abachaa/MedQuAD) — 47,457 medical QA pairs and a CC BY 4.0 notice; useful as a possible attributed source of question phrasing, but it does not supply MediScope route labels.

