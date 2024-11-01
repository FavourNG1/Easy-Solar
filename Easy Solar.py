import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, timedelta
import stripe
import sqlite3
import requests
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key for session management.
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()  # Initialize the database when the app starts.

# Route to home page after login
@app.route('/home')
def home():
    if 'user_id' in session:
        return render_template('home.html')
    else:
        return redirect('login.html')

# Route to sign-up page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
            conn.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect('login.html')
        except sqlite3.IntegrityError:
            flash('Email already exists. Please use a different email.', 'danger')
        finally:
            conn.close()
    return render_template('signup.html')

# Route to login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect('home.html')  # Redirect to home page on successful login
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

# Route to logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect('login.html')
        
# Database helper function
def query_database(query, args=(), one=False):
    con = sqlite3.connect("data.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    con.close()
    return (rv[0] if rv else None) if one else rv

def add_payment(user_id, amount):
    # Record a payment in the database
    query_database("INSERT INTO payments (user_id, amount, status) VALUES (?, ?, ?)", (user_id, amount, "pending"))

def update_user_balance(user_id, amount):
    # Update user balance after payment confirmation
    query_database("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))

# Initiate a mobile money payment
@app.route('/initiate-payment', methods=['POST'])
def initiate_payment():
    user_id = request.form['user_id']
    amount = request.form['amount']
    
    # Mock API call to a Mobile Money provider
    # In reality, you’d need provider-specific code, including authorization and unique payment requests
    mobile_money_api_url = "https://mobilemoneyapi.example.com/initiate_payment"
    response = requests.post(mobile_money_api_url, json={
        "user_id": user_id,
        "amount": amount,
        # Add additional fields required by your mobile money API
    })
    
    # If API call is successful
    if response.status_code == 200 and response.json().get("status") == "success":
        add_payment(user_id, amount)
        return jsonify({"status": "success", "message": "Payment initiated successfully"})
    else:
        return jsonify({"status": "error", "message": "Payment initiation failed"}), 400

# Verify payment status (using a webhook or manual check)
@app.route('/verify-payment/<int:payment_id>', methods=['GET'])
def verify_payment(payment_id):
    # Placeholder for mobile money payment verification
    # Here you would interact with the Mobile Money provider's API to check payment status
    payment_status = "confirmed"  # Example status
    
    # Update payment status in the database
    if payment_status == "confirmed":
        # Mark the payment as complete and activate the service
        query_database("UPDATE payments SET status = ? WHERE id = ?", ("confirmed", payment_id))
        return jsonify({"status": "success", "message": "Payment verified"})
    else:
        return jsonify({"status": "error", "message": "Payment verification failed"}), 400
        
# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/subscription')
def subscription():
    if 'user_id' in session:
        return render_template('subscription.html')
    else:
        return redirect('login.html')

# Check if user’s subscription is active based on last payment
@app.route('/check-subscription/<int:user_id>')
def check_subscription(user_id):
    user = query_database("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if user and user['balance'] > 0:
        return jsonify({"status": "active"})
    else:
        return jsonify({"status": "inactive"})
        
@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

@app.route('/about')
def about():
    return render_template('about.html')  # This is your about page HTML file
    
if __name__ == '__main__':
    app.run(debug=True)
