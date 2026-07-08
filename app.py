from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import pandas as pd
import re
import tldextract
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)
app.secret_key = 'phishguard_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///phishguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from database import db, User, History
db.init_app(app)

# Load trained model
model = pickle.load(open('model.pkl', 'rb'))

# Load dataset columns
df = pd.read_csv('dataset.csv')
df = df.drop(['url', 'status'], axis=1)
feature_columns = df.columns.tolist()

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

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# =================== ROUTES ===================

@app.route('/')
@login_required
def home():
    return render_template('index.html',
        username=session.get('username'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing = User.query.filter_by(username=username).first()
        if existing:
            return render_template('register.html',
                error='Username already exists!')
        hashed = generate_password_hash(password)
        user = User(username=username, password=hashed)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
        return render_template('login.html',
            error='Wrong username or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/history')
@login_required
def history_page():
    history = History.query.filter_by(
        user_id=session['user_id']).all()
    return render_template('history.html', history=history)

@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html')

@app.route('/get_stats')
@login_required
def get_stats():
    history = History.query.filter_by(
        user_id=session['user_id']).all()
    total = len(history)
    safe = sum(1 for h in history if h.result == 'Safe')
    phishing = sum(1 for h in history if h.result == 'Phishing')
    return jsonify({
        'total': total,
        'safe': safe,
        'phishing': phishing
    })

@app.route('/delete/<int:index>')
@login_required
def delete_history(index):
    history = History.query.filter_by(
        user_id=session['user_id']).all()
    if 0 <= index < len(history):
        db.session.delete(history[index])
        db.session.commit()
    return redirect(url_for('history_page'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/predict', methods=['POST'])
@login_required
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

    # Save to database
    entry = History(
        user_id=session['user_id'],
        url=url,
        result=status,
        confidence=f"{score}%",
        time=datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({
        'result': label,
        'confidence': f"{score}%",
        'url': url
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)