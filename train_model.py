import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

import pickle


# Dataset Load

data = pd.read_csv("job_dataset.csv")


# Features + Labels

X = data["title"] + " " + data["description"]

y = data["label"]


# Train/Test Split

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# ML Pipeline

model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", MultinomialNB())
])


# Train

model.fit(X_train, y_train)


# Accuracy

accuracy = model.score(X_test, y_test)

print("Model Accuracy:", accuracy)


# Save Model

with open("jobshield_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("Model Saved Successfully")