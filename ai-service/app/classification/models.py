"""TF-IDF pipelines for the three baseline text classifiers."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


def make_models() -> dict[str, Pipeline]:
    """Build the three comparable models specified in the project brief."""
    classifiers = {
        "Logistic Regression": LogisticRegression(max_iter=2000, random_state=42),
        "Multinomial Naive Bayes": MultinomialNB(),
        "Linear SVM": LinearSVC(random_state=42),
    }
    models = {}
    for name, classifier in classifiers.items():
        models[name] = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        lowercase=True,
                        strip_accents="unicode",
                        ngram_range=(1, 2),
                        sublinear_tf=True,
                    ),
                ),
                ("classifier", classifier),
            ]
        )
    return models
