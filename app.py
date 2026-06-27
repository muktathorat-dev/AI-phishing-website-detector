from flask_cors import CORS
from flask import Flask, request, render_template, jsonify
import pickle
import pandas as pd
import re
import tldextract
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# Load trained model
model = pickle.load(open('model.pkl', 'rb'))

# Load dataset columns
df = pd.read_csv('dataset.csv')
df = df.drop(['url', 'status'], axis=1)
feature_columns = df.columns.tolist()

# Load history from file
HISTORY_FILE = 'history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

def get_features(url):
    features = {}
    for col in feature_columns:
        features[col] = 0
    features['length_url'] = len(url)
    features['https_token'] = 1 if url.startswith('https') else 0
    features['nb_dots'] = url.count('.')
    features['nb_hyphens'] = url.count('-')
    features['nb_at'] = url.count('@')
    features['nb_qm'] = url.count('?')
    features['nb_and'] = url.count('&')
    features['nb_eq'] = url.count('=')
    features['nb_underscore'] = url.count('_')
    features['nb_slash'] = url.count('/')
    features['nb_colon'] = url.count(':')
    features['nb_percent'] = url.count('%')
    features['nb_www'] = 1 if 'www' in url else 0
    features['nb_com'] = 1 if '.com' in url else 0
    features['http_in_path'] = 1 if 'http' in url[8:] else 0
    features['ip'] = 1 if re.match(
        r'\d+\.\d+\.\d+\.\d+', url) else 0
    ext = tldextract.extract(url)
    features['nb_subdomains'] = len(
        ext.subdomain.split('.')) if ext.subdomain else 0
    digits = sum(c.isdigit() for c in url)
    features['ratio_digits_url'] = digits / len(url) if len(url) > 0 else 0
    return features

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/history')
def history_page():
    history = load_history()
    return render_template('history.html', history=history)

@app.route('/stats')
def stats():
    history = load_history()
    return render_template('stats.html', history=history)
@app.route('/get_stats')
def get_stats():
    history = load_history()
    total = len(history)
    safe = sum(1 for h in history if h['result'] == 'Safe')
    phishing = sum(1 for h in history if h['result'] == 'Phishing')
    return jsonify({
        'total': total,
        'safe': safe,
        'phishing': phishing
    })

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/predict', methods=['POST'])
def predict():
    url = request.form['url']
    features = get_features(url)
    input_df = pd.DataFrame([features])
    result = model.predict(input_df)[0]
    probability = model.predict_proba(input_df)[0]

    if result == 'phishing':
        label = "🔴 PHISHING WEBSITE - DANGER!"
        score = round(probability[0] * 100, 2)
        status = "Phishing"
    else:
        label = "🟢 SAFE WEBSITE"
        score = round(probability[1] * 100, 2)
        status = "Safe"

    # Load, update and save history
    history = load_history()
    history.append({
        'url': url,
        'result': status,
        'confidence': f"{score}%",
        'time': datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    })
    save_history(history)

    return jsonify({
        'result': label,
        'confidence': f"{score}%",
        'url': url
    })

if __name__ == '__main__':
    app.run(debug=True)