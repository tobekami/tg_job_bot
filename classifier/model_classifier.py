import joblib

vectorizer = joblib.load('models/tfidf_vectorizer.pkl')
model = joblib.load('models/message_classifier_model.pkl')


def classify_message_model(text):
    vectorized = vectorizer.transform([text])
    return model.predict(vectorized)[0]
