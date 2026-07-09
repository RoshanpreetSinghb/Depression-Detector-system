from flask import Flask, request, render_template, flash, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from models import Model
from depression_detection_tweets import DepressionDetection
from TweetModel import process_message
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------------- Helper Functions ----------------
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create users table (run once)
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Routes ----------------

@app.route('/')
def root():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return render_template('index.html', username=session.get('username'))

# ---------------- Signup ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                         (username, hashed_password))
            conn.commit()
            flash('Signup successful! Please login.')
            return redirect('/')
        except sqlite3.IntegrityError:
            flash('Username already exists!')
        finally:
            conn.close()
    return render_template('signup.html')

# ---------------- Login ----------------
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password'], password):
        session['logged_in'] = True
        session['username'] = username
        flash(f'Welcome {username}!')
        return redirect('/')
    else:
        flash('Incorrect username or password!')
        return redirect('/')

# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect('/')

# ---------------- Sentiment Analysis Page ----------------
@app.route("/sentiment")
def sentiment():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template("sentiment.html")

# ---------------- Predict Tweet Sentiment ----------------
@app.route("/predictSentiment", methods=["POST"])
def predictSentiment():
    if not session.get('logged_in'):
        return redirect('/')
    message = request.form['form10']
    pm = process_message(message)
    result = DepressionDetection.classify(pm, 'bow') or DepressionDetection.classify(pm, 'tf-idf')
    return render_template("tweetresult.html", result=result)

# ---------------- Predict Survey Depression ----------------
@app.route('/predict', methods=["POST"])
def predict():
    if not session.get('logged_in'):
        return redirect('/')
    
    values = [int(request.form[f'a{i}']) for i in range(1, 11)]
    model = Model()
    classifier = model.svm_classifier()
    prediction = classifier.predict([values])

    result_map = {
        0: 'No Depression',
        1: 'Mild Depression',
        2: 'Moderate Depression',
        3: 'Moderately severe Depression',
        4: 'Severe Depression'
    }

    result = f'Your Depression test result: {result_map.get(prediction[0], "Unknown")}'
    return render_template("result.html", result=result)
@app.route('/help')
def help_page():
    return render_template('help.html')

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(port=5987, host='0.0.0.0', debug=True)
