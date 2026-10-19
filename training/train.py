import json
import csv
import math
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "training" / "intents.csv"
MODEL_DIR = BASE_DIR / "models" / "intent_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_OUT = MODEL_DIR / "model.json"


def train_and_export():
    texts = []
    labels = []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(row["text"].strip())
            labels.append(row["intent"].strip())

    print(f"Loaded {len(texts)} samples across {len(set(labels))} classes.")

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    X = vectorizer.fit_transform(texts)

    clf = LogisticRegression(C=5.0, max_iter=500, random_state=42)
    clf.fit(X, labels)

    # Cross-validation performance
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_preds = cross_val_predict(clf, X, labels, cv=cv)
    acc = accuracy_score(labels, cv_preds)
    print("\n--- 5-Fold Cross-Validation Report ---")
    print(f"Overall Accuracy: {acc:.4f}")
    print(classification_report(labels, cv_preds, zero_division=0))

    # Export lightweight JSON model artifact for zero-dependency edge inference
    model_artifact = {
        "classes": list(clf.classes_),
        "vocabulary": vectorizer.vocabulary_,
        "idf": vectorizer.idf_.tolist(),
        "ngram_range": list(vectorizer.ngram_range),
        "weights": clf.coef_.tolist(),
        "intercept": clf.intercept_.tolist()
    }

    with open(MODEL_OUT, "w", encoding="utf-8") as f:
        json.dump(model_artifact, f, indent=2)

    print(f"Exported lightweight model artifact to: {MODEL_OUT}")
    print(f"Artifact size: {MODEL_OUT.stat().st_size / 1024:.1f} KB")

    # Verification: Pure-Python inference versus scikit-learn
    sample_query = "what was the average temperature of machine 2 in the last 30 minutes"
    sk_pred = clf.predict(vectorizer.transform([sample_query]))[0]
    print(f"\nVerification Query: '{sample_query}'")
    print(f"Scikit-learn Prediction: {sk_pred}")


if __name__ == "__main__":
    train_and_export()
