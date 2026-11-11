# Query-classifier dataset plan

**Status:** Approved routing rules; dataset v1.1 synthetic baseline  
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

- `data/query_train.csv`: 1,200 questions, balanced at 400 per route. It includes the original training rows and the inspected v1 test rows, now used as development data.
- `data/query_dev_v1.csv`: the prior 300-row test set. Because we inspected its errors, it is now development data and is not a final test.
- `data/query_test.csv`: a fresh 300-row holdout, balanced at 100 per route, with new topic groups and no exact query or topic-group overlap. Its question styles are represented in training so it measures generalization to new topics.
- Both files include query ID, text, label, topic group, origin/review status, and a short label rationale.

The 30 examples in `data/query_examples_batch_1.csv` were approved and merged into training. The earlier 12-row `data/query_examples_seed.csv` was not merged because it was an earlier draft and could introduce duplicates.

## Limits of this first dataset

Apart from the 30 examples approved by the project owner, the data is assistant-authored synthetic text labeled from the agreed rules. The v1 test is now development data. The v2 holdout tests new topics using question styles represented in training; it remains synthetic and does not estimate performance on real MediScope users. Before claiming real-world accuracy, collect a separate human-labeled set of natural questions without personal health details and with appropriate consent. Report the dataset as synthetic in academic work.

## Source notes

- [Roberts et al., Resource Classification for Medical Questions](https://pmc.ncbi.nlm.nih.gov/articles/PMC5333297/) — resource-routing task and annotation challenges; the paper says its annotated corpora are available by request.
- [MedQuAD official repository](https://github.com/abachaa/MedQuAD) — 47,457 medical QA pairs and a CC BY 4.0 notice; useful as a possible attributed source of question phrasing, but it does not supply MediScope route labels.



## What v1 error review changed

The v1 test had 84 errors: 50 simple definitions were sent to RAG, 23 RAG questions mentioning evidence/sources were sent to Literature, 10 RAG questions were sent to General Information, and 1 Literature question was sent to RAG. Those examples were moved to `query_dev_v1.csv` and added to training. The label guide now says that a source/evidence request alone does not mean Literature; Literature requires an explicit research-paper/study/trial/review focus. Ambiguous medical fact questions default to RAG.
