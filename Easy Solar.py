import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import stripe
import requests
import datetime

app = Flask(__name__)
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

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)

# Routes
@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/')
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    new_cart_item = Cart(user_id=session['user_id'], product_id=product_id)
    db.session.add(new_cart_item)
    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    products = Product.query.all()
    return render_template('cart.html', cart_items=cart_items, products=products)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch cart items for the current user
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    products = Product.query.all()

    # Prepare line items for Stripe
    line_items = []
    for item in cart_items:
        product = products[item.product_id - 1]
        line_items.append({
            'price_data': {
                'currency': 'naira',
                'product_data': {
                    'name': product.name,
                },
                'unit_amount': int(product.price * 100),  # Amount in cents
            },
            'quantity': item.quantity,
        })

    # Create a Stripe checkout session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=url_for('success', _external=True),
        cancel_url=url_for('cancel', _external=True),
    )
    return redirect(checkout_session.url, code=303)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

# Initialize and add products
@app.before_first_request
def create_tables():
    db.create_all()
    if not Product.query.first():
        products = [Product(name="Solar Light A", price=25.00),
                    Product(name="Solar Light B", price=40.00),
                    Product(name="Solar Light C", price=60.00)]
        db.session.bulk_save_objects(products)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
