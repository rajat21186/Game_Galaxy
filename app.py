from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import uuid

app = Flask(__name__)

app.secret_key = 'your_secret_key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'rajat123'
app.config['MYSQL_DB'] = 'game_galaxy'

mysql = MySQL(app)

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Authentication WHERE Email = %s AND Customer_Password = %s', (email, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['Customer_ID']
            session['username'] = email

            # Check if user already has a profile
            cursor.execute('SELECT * FROM Customer WHERE Customer_ID = %s', (account['Customer_ID'],))
            customer_profile = cursor.fetchone()
            if customer_profile:
                return redirect(url_for('games'))
            else:
                return redirect(url_for('profile'))
        else:
            msg = 'Incorrect email / password!'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Authentication WHERE Email = %s', (email,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            customer_id = str(uuid.uuid4())
            cursor.execute('INSERT INTO Authentication (Customer_ID, Email, Customer_Password) VALUES (%s, %s, %s)', (customer_id, email, password,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'

            # Set session and redirect to profile creation
            session['loggedin'] = True
            session['id'] = customer_id
            session['username'] = email
            return redirect(url_for('profile'))
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    msg = ''
    if request.method == 'POST' and 'first_name' in request.form and 'last_name' in request.form and 'phone' in request.form and 'dob' in request.form:
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        dob = request.form['dob']
        email = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT Customer_ID FROM Authentication WHERE Email = %s', (email,))
        account = cursor.fetchone()
        if account:
            customer_id = account['Customer_ID']
            cursor.execute('INSERT INTO Customer (Customer_ID, FirstName, LastName, PhoneNo, Email, DOB) VALUES (%s, %s, %s, %s, %s, %s)', 
                           (customer_id, first_name, last_name, phone, email, dob,))
            mysql.connection.commit()
            msg = 'Profile created successfully!'
            return redirect(url_for('games'))
        else:
            msg = 'Account not found!'
    return render_template('profile.html', msg=msg)

@app.route('/games', methods=['GET', 'POST'])
def games():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'game_id' in request.form:
        game_id = request.form['game_id']
        customer_id = session['id']
        
        # Check if the game is already in the cart
        cursor.execute('SELECT * FROM Cart WHERE Customer_ID = %s AND Game_ID = %s', (customer_id, game_id))
        cart_item = cursor.fetchone()
        if cart_item:
            flash('Game already added to cart')
        else:
            cursor.execute('INSERT INTO Cart (Customer_ID, Game_ID, Quantity) VALUES (%s, %s, %s)', (customer_id, game_id, 1))
            mysql.connection.commit()
            flash('Game added to cart successfully')
        
        # Redirect to the cart page
        return redirect(url_for('cart'))

    cursor.execute('SELECT * FROM Game')
    games = cursor.fetchall()
    return render_template('games.html', games=games)

@app.route('/cart', methods=['GET', 'POST'])
def cart():
    customer_id = session.get('id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT Cart.*, Game.Title, Game.Price FROM Cart JOIN Game ON Cart.Game_ID = Game.Game_ID WHERE Cart.Customer_ID = %s', (customer_id,))
    cart_items = cursor.fetchall()

    total_amount = sum(item['Price'] * item['Quantity'] for item in cart_items)

    if request.method == 'POST' and 'game_id' in request.form:
        game_id = request.form['game_id']
        cursor.execute('DELETE FROM Cart WHERE Customer_ID = %s AND Game_ID = %s', (customer_id, game_id))
        mysql.connection.commit()
        flash('Item removed from cart!')
        return redirect(url_for('cart'))

    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'game_id' in request.form:
        game_id = request.form['game_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        customer_id = session.get('id')
        cursor.execute('DELETE FROM Cart WHERE Customer_ID = %s AND Game_ID = %s', (customer_id, game_id))
        mysql.connection.commit()
        flash('Item removed from cart!')
    return redirect(url_for('cart'))
@app.route('/place_order', methods=['POST'])
def place_order():
    customer_id = session.get('id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get the cart items with their prices
    cursor.execute('SELECT Cart.*, Game.Price FROM Cart JOIN Game ON Cart.Game_ID = Game.Game_ID WHERE Cart.Customer_ID = %s', (customer_id,))
    cart_items = cursor.fetchall()

    # Debugging: print cart items to check their contents
    print("Cart Items:", cart_items)

    try:
        # Calculate the total amount to be paid
        total_amount = sum(item['Price'] * item['Quantity'] for item in cart_items if 'Price' in item and 'Quantity' in item)
    except Exception as e:
        print("Error calculating total amount:", e)
        flash('An error occurred while calculating the total amount.')
        return redirect(url_for('cart'))

    # Store the total amount to be paid in the session and redirect to the wallet page
    session['amount_to_pay'] = total_amount
    return redirect(url_for('wallet'))

@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    if 'id' not in session:
        return redirect(url_for('login'))

    customer_id = session['id']
    amount_to_pay = session.get('amount_to_pay', 0)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get Wallet_ID associated with the Customer_ID
    cursor.execute('SELECT Wallet_ID, Balance FROM Wallet WHERE Customer_ID = %s', (customer_id,))
    wallet_data = cursor.fetchone()

    if wallet_data:
        wallet_id = wallet_data['Wallet_ID']
        balance = wallet_data['Balance']
    else:
        # If the wallet does not exist, create a new wallet entry
        cursor.execute('INSERT INTO Wallet (Customer_ID, Balance) VALUES (%s, %s)', (customer_id, 0))
        mysql.connection.commit()
        cursor.execute('SELECT Wallet_ID, Balance FROM Wallet WHERE Customer_ID = %s', (customer_id,))
        wallet_data = cursor.fetchone()
        wallet_id = wallet_data['Wallet_ID']
        balance = wallet_data['Balance']

    if request.method == 'POST':
        if 'add_money' in request.form:
            amount = request.form['amount']
            try:
                amount = int(amount)  # Ensure the amount is a valid integer
                new_balance = balance + amount
                cursor.execute('UPDATE Wallet SET Balance = %s WHERE Wallet_ID = %s', (new_balance, wallet_id))
                mysql.connection.commit()
                balance = new_balance
                flash('Money added successfully!')
            except ValueError:
                flash('Invalid amount. Please enter a number.')
            except MySQLdb.Error as e:
                flash(f'Database error: {str(e)}')
        elif 'pay_order' in request.form:
            if balance >= amount_to_pay:
                new_balance = balance - amount_to_pay
                cursor.execute('UPDATE Wallet SET Balance = %s WHERE Wallet_ID = %s', (new_balance, wallet_id))
                cursor.execute('DELETE FROM Cart WHERE Customer_ID = %s', (customer_id,))
                mysql.connection.commit()
                flash('Order placed successfully!')
                balance = new_balance
                amount_to_pay = 0  # Clear the amount to pay after successful payment
                session.pop('amount_to_pay', None)
            else:
                flash('Insufficient balance. Please add more money.')

    return render_template('wallet.html', balance=balance, amount_to_pay=amount_to_pay)
