"""Compare baseline classifiers and evaluate the selected model once."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold, cross_validate

from app.classification.data import LABELS, load_rows, validate_train_test
from app.classification.models import make_models

AI_SERVICE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AI_SERVICE_DIR.parent
TRAIN_FILE = PROJECT_DIR / "data" / "query_train.csv"
TEST_FILE = PROJECT_DIR / "data" / "query_test.csv"
MODEL_FILE = AI_SERVICE_DIR / "models" / "query_classifier.joblib"
REPORT_FILE = AI_SERVICE_DIR / "reports" / "query_classifier_metrics.json"
ERROR_FILE = AI_SERVICE_DIR / "reports" / "query_classifier_test_errors.csv"


def main() -> None:
    train_rows = load_rows(TRAIN_FILE)
    test_rows = load_rows(TEST_FILE)
    validate_train_test(train_rows, test_rows)

    train_text = [row["query"] for row in train_rows]
    train_labels = [row["label"] for row in train_rows]
    train_groups = [row["topic_group"] for row in train_rows]
    test_text = [row["query"] for row in test_rows]
    test_labels = [row["label"] for row in test_rows]

    # Keep related questions together so near-identical topic variants do not
    # appear in both sides of a validation fold.
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ["accuracy", "precision_macro", "recall_macro", "f1_macro"]
    comparison = {}

    for name, model in make_models().items():
        scores = cross_validate(
            model,
            train_text,
            train_labels,
            groups=train_groups,
            cv=folds,
            scoring=scoring,
            error_score="raise",
            n_jobs=1,
        )
        comparison[name] = {
            metric: {
                "fold_scores": [float(value) for value in scores[f"test_{metric}"]],
                "mean": float(scores[f"test_{metric}"].mean()),
                "std": float(scores[f"test_{metric}"].std()),
            }
            for metric in scoring
        }

    # Select using training-only cross-validation. The held-out test set is
    # not used to pick the winner.
    selected_name = max(
        comparison,
        key=lambda name: (
            comparison[name]["f1_macro"]["mean"],
            comparison[name]["accuracy"]["mean"],
        ),
    )
    selected_model = make_models()[selected_name]
    selected_model.fit(train_text, train_labels)
    predictions = selected_model.predict(test_text)

    test_report = classification_report(
        test_labels,
        predictions,
        labels=list(LABELS),
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(test_labels, predictions, labels=list(LABELS))

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_model, MODEL_FILE)

    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scikit_learn_version": sklearn.__version__,
        "dataset_note": (
            "Synthetic questions with held-out topic groups. Prompt styles are represented "
            "in training; results do not estimate real-user routing accuracy."
        ),
        "training_rows": len(train_rows),
        "training_class_counts": dict(Counter(train_labels)),
        "test_rows": len(test_rows),
        "test_class_counts": dict(Counter(test_labels)),
        "cross_validation": {
            "folds": 5,
            "splitter": "StratifiedGroupKFold",
            "selection_metric": "macro F1, with accuracy as tie-breaker",
            "models": comparison,
        },
        "selected_model": selected_name,
        "held_out_test": {
            "accuracy": float(accuracy_score(test_labels, predictions)),
            "classification_report": test_report,
            "confusion_matrix_labels": list(LABELS),
            "confusion_matrix_rows_true_columns_predicted": matrix.tolist(),
        },
        "saved_model": str(MODEL_FILE.relative_to(PROJECT_DIR)),
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with ERROR_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        import csv

        writer = csv.DictWriter(
            file,
            fieldnames=["query_id", "query", "actual_label", "predicted_label"],
        )
        writer.writeheader()
        for row, actual, predicted in zip(test_rows, test_labels, predictions):
            if actual != predicted:
                writer.writerow(
                    {
                        "query_id": row["query_id"],
                        "query": row["query"],
                        "actual_label": actual,
                        "predicted_label": predicted,
                    }
                )

    print(f"Training examples: {len(train_rows)}")
    print(f"Test examples: {len(test_rows)}")
    print("\nGrouped cross-validation (mean macro F1):")
    for name, metrics in comparison.items():
        print(f"  {name}: {metrics['f1_macro']['mean']:.3f}")
    print(f"\nSelected by cross-validation: {selected_name}")
    print(f"Held-out synthetic test accuracy: {report['held_out_test']['accuracy']:.3f}")
    print(f"Held-out macro F1: {test_report['macro avg']['f1-score']:.3f}")
    print(f"Metrics saved to: {REPORT_FILE}")
    print(f"Model saved to: {MODEL_FILE}")
    print(f"Test errors saved to: {ERROR_FILE}")


if __name__ == "__main__":
    main()
