import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

# Load dataset
df = pd.read_csv('dataset.csv')

# Remove URL column — not needed for ML
df = df.drop('url', axis=1)

# Split features and label
X = df.drop('status', axis=1)
y = df['status']

# Train test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42)

# Train model
print("Training model... please wait...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Check accuracy
pred = model.predict(X_test)
accuracy = accuracy_score(y_test, pred)
print(f"Model Accuracy: {accuracy * 100:.2f}%")

# Save model
pickle.dump(model, open('model.pkl', 'wb'))
print("Model saved as model.pkl ✅")