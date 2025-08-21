# Core Flask modules
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash

# MySQL integration
from flask_mysqldb import MySQL
import MySQLdb.cursors

# Utility modules
from datetime import datetime, timedelta
import os
import json
import base64
import random
import re
import requests
import smtplib
import uuid

# Email handling
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Environment variable loader
from dotenv import load_dotenv
load_dotenv()

# Security
from itsdangerous import URLSafeTimedSerializer

# Flask-Login
from flask_login import LoginManager

# Flask-Mail setup
from flask_mail import Mail, Message
from extensions import mail  # Custom mail extension
from flask import url_for

# Custom utility functions
from utils import send_verification_email, verify_token


app = Flask(__name__)
app.secret_key = 'your_secret_key'
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
serializer = URLSafeTimedSerializer(app.secret_key)
 
app.config['EMAIL_HOST'] = os.getenv('EMAIL_HOST')
app.config['EMAIL_PORT'] = int(os.getenv('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['EMAIL_USERNAME'] = os.getenv('EMAIL_USERNAME')
app.config['EMAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['EMAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_DEFAULT_SENDER')

mail = Mail(app)
mail.init_app(app)

PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY")

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(f"{PAYMONGO_SECRET_KEY}:".encode()).decode(),
    "Content-Type": "application/json" 
    }

#MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Kitty_909'
#app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'staff_portal'

login_manager = LoginManager(app)
login_manager.login_view = 'login'
mysql = MySQL(app)

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    return cursor.fetchone()

def generate_verification_token():
    return str(uuid.uuid4())

def send_verification_email(email, username, verification_token):
    verification_url = f"{request.url_root.rstrip('/')}/verify_email/{verification_token}"
    subject = "Verify your email"
    body = f"Hi {username},\n\nClick the link below to verify your email:\n{verification_url}\n\nThis link will expire in 24 hours."

    message = f"Subject: {subject}\n\n{body}"

    try:
        server = smtplib.SMTP(app.config['EMAIL_HOST'], app.config['EMAIL_PORT'])
        server.starttls()
        server.login(app.config['EMAIL_USERNAME'], app.config['EMAIL_PASSWORD'])  # must be Gmail App Password
        server.sendmail(app.config['EMAIL_USERNAME'], email, message)
        server.quit()
        return True
    except Exception as e:
        print("❌ Email send failed:", e)
        return False
    
@app.context_processor
def inject_user_details():
    return {
        'username': session.get('username'),
        'role': session.get('role'),
        'department': session.get('department')
    }

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'login_attempts' not in session:
        session['login_attempts'] = 0

    #Check for lockout
    lockout_until = session.get('lockout_until')
    if lockout_until:
        lockout_until_dt = datetime.strptime(lockout_until, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < lockout_until_dt:
            remaining = (lockout_until_dt - datetime.now()).seconds
            return render_template(
                'login.html',
                lockout_remaining=remaining,
                error="Maximum login attempts reached. Try again in {minutes}m {seconds}s."
            )
        else:
            session.pop('lockout_until')
            session['login_attempts'] = 0

    if request.method == 'POST':
        if session['login_attempts'] >= 3:
            #Set lockout for 3 minutes
            lockout_time = datetime.now() + timedelta(minutes=3)
            session['lockout_until'] = lockout_time.strftime("%Y-%m-%d %H:%M:%S")
            return render_template('login.html', error="Maximum login attempts reached. Please try again in 3 minutes.")

        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        if user:
    
         session['username'] = user['username']
         session['role'] = user['role']
         session['department'] = user['department']
         session['login_attempts'] = 0
         session.pop('lockout_until', None)
         flash(f"Welcome back, {user['username']}!", "success")
         return redirect(url_for('dashboard'))
        else:
            session['login_attempts'] += 1
            attempts_left = 3 - session['login_attempts']
            error_msg = "Invalid credentials"
            if attempts_left > 0:
                error_msg += f". Attempts left: {attempts_left}"
            else:
                error_msg = "Maximum login attempts reached. Please try again in 3 minutes."
            return render_template('login.html', error=error_msg)
    return render_template('login.html')

# Route to initiate password reset and send OTP
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_email'] = email
            session['otp'] = otp

            # Send OTP via email
            subject = "Your Password Reset OTP"
            body = f"Hello,\n\nYour OTP for password reset is: {otp}\n\nIf you did not request this, please ignore this email."
            message = f"Subject: {subject}\n\n{body}"

            try:
                server = smtplib.SMTP(app.config['EMAIL_HOST'], app.config['EMAIL_PORT'])
                server.starttls()
                server.login(app.config['EMAIL_USERNAME'], app.config['EMAIL_PASSWORD'])
                server.sendmail(app.config['EMAIL_USERNAME'], email, message)
                server.quit()
            except Exception as e:
                print("❌ Failed to send OTP email:", e)
                return render_template('forgot_password.html', error="Failed to send OTP email. Please try again.")

            return redirect(url_for('verify_otp'))  # Redirect to OTP verification
        else:
            return render_template('forgot_password.html', error="Email not found")
    
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            return render_template('reset_password.html', error="Passwords do not match")

        raw_password = new_password  # For testing only

        try:
            # Always create cursor BEFORE the try block if you will use it later
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (raw_password, session['reset_email']))
            mysql.connection.commit()
            cursor.close()

            session.pop('reset_email', None)
            flash("Password has been reset. You can now log in.")
            return redirect(url_for('login'))

        except Exception as e:
            print("❌ Error updating password:", str(e))
            return render_template('reset_password.html', error="Something went wrong. Please try again.")

    return render_template('reset_password.html')

from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
import MySQLdb

serializer = URLSafeTimedSerializer(app.secret_key)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cursor = mysql.connection.cursor()

        # Check existing username
        cursor.execute("SELECT username FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            flash("Username already taken.", "danger")
            return redirect(url_for('signup'))

        # Check existing email
        cursor.execute("SELECT email FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('signup'))

        # Generate token + expiry
        verification_token = generate_verification_token()
        token_expires_at = datetime.now() + timedelta(hours=24)

        # Save user with email_verified=False
        cursor.execute("""
            INSERT INTO users (username, email, password, role, email_verified, verification_token, token_expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, email, password, role, False, verification_token, token_expires_at))
        mysql.connection.commit()

        # Send email
        if send_verification_email(email, username, verification_token):
            flash("Check your email for a verification link.", "success")
            return redirect(url_for('verification_pending'))
        else:
            flash("Could not send email. Contact support.", "danger")

    return render_template('signup.html')

@app.route('/verify_email/<verification_token>')
def verify_email_token(verification_token):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # <-- FIXED

    # Find user with valid token
    cursor.execute("""
        SELECT user_id FROM users 
        WHERE verification_token = %s 
        AND email_verified = False 
        AND token_expires_at > NOW()
    """, (verification_token,))
    user = cursor.fetchone()

    if user:
        # Mark as verified
        cursor.execute("""
            UPDATE users 
            SET email_verified = True, verification_token = NULL 
            WHERE user_id = %s
        """, (user['user_id'],))
        mysql.connection.commit()
        flash("✅ Email verified successfully! You can now log in.", "success")
        return redirect(url_for('login'))
    else:
        flash("⚠️ Invalid or expired verification link.", "danger")
        return redirect(url_for('signup'))

@app.route('/verification_pending')
def verification_pending():
    return render_template('verification_pending.html')

@app.route('/dashboard')
def dashboard():

    if 'username' not in session or 'role' not in session:
        return redirect(url_for('login'))

    role = session['role']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    def get_stats_and_charts():
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Housekeeping'
        """)
        housekeeping = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Dining'
        """)
        food = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Laundry'
        """)
        laundry = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Massage'
        """)
        spa = cursor.fetchone()['count']

        cursor.execute("""
            SELECT service_type, COUNT(*) AS count
            FROM services s
            JOIN requests r ON s.service_id = r.service_id
            GROUP BY service_type
        """)
        service_data = cursor.fetchall()

        cursor.execute("""
            SELECT s.first_name AS staff, 
                   COUNT(r.request_id) AS requests,
                   SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) AS completed
            FROM requests r
            JOIN staff s ON r.staff_id = s.staff_id
            GROUP BY s.first_name
        """)
        staff_data = cursor.fetchall()

        return {
            "housekeeping": housekeeping,
            "food": food,
            "laundry": laundry,
            "spa": spa
        }, service_data, staff_data

    #Admin, Manager, Supervisor see stats and charts
    if role in ['admin', 'manager', 'supervisor']:
        stats, service_data, staff_data = get_stats_and_charts()
        cursor.close()
        return render_template('dashboard.html', role=role, stats=stats, service_data=service_data, staff_data=staff_data)

    #User role: no charts/stats, but allow booking/payment features
    elif role == 'user':
        cursor.close()
        return render_template('dashboard.html', role=role, stats={}, service_data=[], staff_data=[])

    #Default fallback
    cursor.close()
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        flash("⚠️ You must be logged in.")
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        flash("⚠️ User not found.")
        return redirect(url_for('login'))

    return render_template('profile.html', user=user, role=user['role'])

@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    new_username = request.form['username']
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE users SET username = %s WHERE user_id = %s", (new_username, user_id))
        mysql.connection.commit()
        flash("✅ Username updated successfully!")
    except Exception as e:
        print("❌ Error updating username:", e)
        flash("❌ Failed to update username.")
    finally:
        cursor.close()
    return redirect(url_for('profile'))

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    new_username = request.form['username']
    current_username = session['username']

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE users SET username = %s WHERE username = %s", (new_username, current_username))
        mysql.connection.commit()
        session['username'] = new_username  #Update session
        flash("✅ Username updated successfully!")
    except Exception as e:
        print("❌ Error updating username:", e)
        flash("❌ Failed to update username.")
    finally:
        cursor.close()

    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

#Called by STAFF Menu - display staff
@app.route('/staff')
def view_staffs():
    selected_staff = request.args.get('staff_id', '') #Get the id of the selected staff
    search = request.args.get('search', '') #Get the value of the entered text in search
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search:
        like = f"%{search}%"
        query = """
        SELECT *
        FROM staff
        WHERE 
            first_name LIKE %s OR
            last_name LIKE %s OR
            role LIKE %s OR
            email LIKE %s OR
            phone LIKE %s
    """
        cursor.execute(query, (like,) * 5) #Execute. 5 for 5 search criteria (fname, lname, role, email, phone)
    else:
        cursor.execute("""
            SELECT * FROM staff ORDER BY last_name, first_name
        """)
    staffs = cursor.fetchall() #Fetch results
    return render_template('staff.html', staffs=staffs) #pass the contents of staffs to staff.html

#Called by STAFF Menu - check if staff exist in requests
@app.route('/checkStaff/<int:staff_id>')
def check_staff(staff_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS count FROM requests WHERE staff_id = %s", (staff_id,)) #Count how many staff id in requests
    result = cursor.fetchone()
    cursor.close()
    return jsonify({"in_use": result['count'] > 0}) #Return to staff; set "in_use" to true if count> 0

@app.route('/delete/<int:guest_id>')
def delete_guest(guest_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM Guest WHERE guest_id = %s", (guest_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/guests')

@app.route('/edit/<int:guest_id>', methods=['GET', 'POST'])
def editGuest(guest_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form.get('middle_name', '')
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']

        cursor.execute("""
            UPDATE Guest SET first_name = %s, middle_name = %s,
            last_name = %s, email = %s, phone = %s
            WHERE guest_id = %s
        """, (first_name, middle_name, last_name, email, phone, guest_id))
        mysql.connection.commit()
        cursor.close()
        return redirect('/guests')

    #GET method - show the edit form
    cursor.execute("SELECT * FROM Guest WHERE guest_id = %s", (guest_id,))
    guest = cursor.fetchone()
    cursor.close()

    if not guest:
        #Instead of redirecting, render the template with guest=None or show an error
        return render_template('editGuest.html', guest=None, error="Guest not found")
    return render_template('editGuest.html', guest=guest)

@app.route('/requests')
def show_requests():
    query = request.args.get('search', '')
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    #Fetch all staff for the dropdown
    cursor.execute("SELECT * FROM staff")
    staff_list = cursor.fetchall()
    
    #Fetch all services for the dropdown
    cursor.execute("SELECT * FROM services")
    service_list = cursor.fetchall()
    
    #Fetch all bookings for the dropdown
    sql = """
            SELECT
            b.*,
            r.room_number
            FROM bookings b
            JOIN room r ON b.room_id = r.room_id
            """
    cursor.execute(sql)
    booking_list = cursor.fetchall()

    if query:
        search_pattern = f"%{query}%"
        sql = """
            SELECT 
                r.*,
                s.item,
                st.first_name,
                st.last_name,
                st.staff_id
            FROM requests r
            JOIN services s ON r.service_id = s.service_id
            LEFT JOIN staff st ON r.staff_id = st.staff_id
            WHERE 
                CAST(r.request_id AS CHAR) LIKE %s OR
                CAST(r.booking_id AS CHAR) LIKE %s OR
                CAST(r.service_id AS CHAR) LIKE %s OR
                CAST(r.quantity AS CHAR) LIKE %s OR
                CAST(r.unitCost AS CHAR) LIKE %s OR
                CAST(r.totalCost AS CHAR) LIKE %s OR
                CAST(r.status AS CHAR) LIKE %s OR
                CAST(r.request_time AS CHAR) LIKE %s OR
                CAST(r.completionTime AS CHAR) LIKE %s OR
                CAST(r.staff_id AS CHAR) LIKE %s OR
                CAST(s.item AS CHAR) LIKE %s
        """
        cursor.execute(sql, (search_pattern,) * 11)
    else:
        cursor.execute("""
            SELECT 
                r.*,
                s.item,
                st.first_name,
                st.last_name,
                st.staff_id
            FROM requests r
            JOIN services s ON r.service_id = s.service_id
            LEFT JOIN staff st ON r.staff_id = st.staff_id
        """)

    requests = cursor.fetchall()
    cursor.close()
    return render_template('requests.html', requests=requests, staff_list=staff_list, current_time=current_time, service_list=service_list, booking_list=booking_list)

@app.route('/assignTask', methods=['POST'])
def assigntask():
    request_id = request.form['assignTask_request_id']
    staff_id = request.form['assignTask_staff_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "UPDATE requests SET staff_id = %s WHERE request_id = %s",
        (staff_id, request_id)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect('/requests')

#Called by ROOMS Menu - display list of rooms
@app.route('/rooms')
def view_rooms():
    search = request.args.get('search', '')   #Get the value entered in search
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to the database

    if search:
        like = f"%{search}%"
        query = """
            SELECT *
            FROM room
            WHERE 
                room_number LIKE %s OR
                room_type LIKE %s OR
                room_status LIKE %s
        """
        cursor.execute(query, (like,) * 3)  #Execute. 3 for 3 search criteria (room_number, room_type, room_status)
    else:
        cursor.execute("""
            SELECT * FROM room ORDER BY room_number
        """)

    rooms = cursor.fetchall()  #After executing sql, fetch results
    return render_template('rooms.html', rooms=rooms) #pass the contents of rooms to rooms.html
  
#Called by SERVICES Menu - display list of services
@app.route('/services')
def view_services():
    search = request.args.get('search', '')  #Get the value entered in search 
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to the database

    if search:
        like = f"%{search}%"
        query = """
            SELECT *
            FROM services
            WHERE 
                service_type LIKE %s OR
                item LIKE %s 
        """
        cursor.execute(query, (like,) * 2)  #Execute for search criteria - type and item
    else:
        cursor.execute("""
            SELECT * FROM services ORDER BY service_type, item
        """)

    services = cursor.fetchall() #After executing sql; fetch results
    return render_template('services.html', services=services) #pass the contents of services to services.html
 
#Called by GUESTS Menu - display list of guests
@app.route('/guests')
def view_guests():
    selected_guest = request.args.get('guest_id', '')  #Get the id of the selected guest
    search = request.args.get('search', '')  #Get the value entered in search
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db

    if search:
        like = f"%{search}%"
        query = """
        SELECT *
        FROM guest
        WHERE 
            first_name LIKE %s OR
            middle_name LIKE %s OR
            last_name LIKE %s OR
            email LIKE %s OR
            phone LIKE %s
    """
        cursor.execute(query, (like,) * 5) #Execute. 5 for 5 search criteria (first, middle, last, email, phone)
    else:
        cursor.execute("""
            SELECT * FROM guest ORDER BY last_name, first_name
        """)
    guests = cursor.fetchall() #After executing; fetch results
    return render_template('guests.html', guests=guests) #pass the contents of guests to guests.html

#Called by CHECKIN / CHECKOUT MENU - display bookings
@app.route('/roomGuest')
def show_roomGuest():
    query = request.args.get('search', '') #Get the value entered in search
    selected_room = request.args.get('room_id', '') #Get the roomid of the selected booking
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db

    #Get all guests
    cursor.execute("SELECT * FROM guest")
    guests = cursor.fetchall()

    #Get rooms 
    cursor.execute("SELECT * FROM room")
    rooms = cursor.fetchall()

    if query:
        search_pattern = f"%{query}%"
        query = """
            SELECT 
                b.*,
                r.room_number as room_number,
                g.last_name as last_name,
                g.first_name as first_name 
            FROM bookings b
            JOIN room r ON b.room_id = r.room_id
            JOIN guest g ON b.guest_id = g.guest_id
            WHERE 
                booking_id LIKE %s OR
                room_number LIKE %s OR
                last_name LIKE %s OR
                first_name LIKE %s OR
                exp_check_in LIKE %s OR
                exp_check_out LIKE %s OR
                actual_check_in LIKE %s OR
                actual_check_out LIKE %s
        """
        cursor.execute(query, (search_pattern,) * 8) #Execute 8 for 8 search criteria
    else:
        cursor.execute("""
                SELECT 
                    b.*, 
                    g.first_name,
                    g.last_name,
                    r.room_number
                FROM bookings b
                JOIN guest g ON b.guest_id = g.guest_id
                JOIN room r ON b.room_id = r.room_id
            """)
    bookings = cursor.fetchall() #After executing sql; fetch results
    cursor.close() #Close db connection
    return render_template('roomGuest.html', bookings=bookings) #Pass the contents of bookings to roomGuest.html

#Called by ROOMS Menu; Add a new room
@app.route('/addRoom', methods=['POST'])
def add_rooms():
    
    #Get the values entered in Add Form
    roomNumber = request.form['room_number']
    roomType = request.form['room_type']
    roomStatus = request.form['room_status']
        
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
        cursor.execute(
            "INSERT INTO room (room_number, room_type, room_status) VALUES (%s, %s, %s)",
            (roomNumber, roomType, roomStatus)
        ) 
        mysql.connection.commit()  #Save to database
    except MySQLdb.IntegrityError: #Trap error; display if room number is duplicate
        flash("Room number already exists. Please enter a unique room number.", "danger")
    finally:
        cursor.close() #Close db connection
        return redirect('/rooms') 


#Called by ROOMS Menu - edit a room
@app.route('/updateRoom', methods=['POST'])
def updateRoom():
    
    #Get the values entered in the Edit Form
    room_id = int(request.form['edit_room_id'])
    room_number = request.form['edit_room_number']
    room_type = request.form['edit_room_type']
    room_status = request.form['edit_room_status']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute(
        """
        UPDATE room
        SET room_number = %s, room_type = %s, room_status = %s
        WHERE room_id = %s
        """,
        (room_number, room_type, room_status, room_id)
    )
    mysql.connection.commit() #Save to db
    cursor.close() #Close connection
    return redirect('/rooms') #Return to rooms

#Called by ROOMS Menu - delete a room
@app.route('/deleteRoom/<int:room_id>', methods=['GET'])
def deleteRoom(room_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute("DELETE FROM room WHERE room_id = %s", (room_id,)) #Execute
    mysql.connection.commit() #Save to db
    cursor.close() #Close connection
    return redirect('/rooms') #Return to rooms

#Called by ROOMS Menu - check if room exists in bookngs
@app.route('/checkRoomBooking/<int:room_id>')
def check_room_booking(room_id):
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE room_id = %s", (room_id,)) #Count how many room_id are there in bookings
    result = cursor.fetchone() #Fetch results
    cursor.close() #Close db connection
    return jsonify({"in_use": result['count'] > 0}) #Return to rooms; set "in_use" to TRUE if count > 0;  if in_use is TRUE (meaning, the room_id is used in bookings), then it will tell rooms.html that the room cannot be deleted

#Called by GUESTS Menu - add a new guest
@app.route('/addGuests', methods=['POST'])
def add_guests():
    
    #Get the values entered in Add Form
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  #Connect to db
    cursor.execute("""
        INSERT INTO Guest (first_name, middle_name, last_name, email, phone)
        VALUES (%s, %s, %s, %s, %s)
    """, (first_name, middle_name, last_name, email, phone))
    mysql.connection.commit() #Save to db
    cursor.close() #Close connection

    return redirect('/guests')

#Called by GUESTS Menu - edit a guest
@app.route('/updateGuests', methods=['POST'])
def updateGuests():
    
    #Get the values entered in the Edit Form
    guest_id = int(request.form['edit_guest_id'])
    first_name = request.form['edit_first_name']
    middle_name = request.form['edit_middle_name']
    last_name = request.form['edit_last_name']
    email = request.form['edit_email']
    phone = request.form['edit_phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute("""
        UPDATE Guest 
        SET first_name = %s, middle_name = %s, last_name = %s, email = %s, phone = %s 
        WHERE guest_id = %s
    """, (first_name, middle_name, last_name, email, phone, guest_id))
    mysql.connection.commit() #Save to db
    cursor.close() #Close connection

    return redirect('/guests')

@app.route('/addRequest', methods=['POST'])
def add_request():
    booking_id = request.form['booking_id']
    service_id = request.form['service_id']
    quantity = int(request.form['quantity'])
    unitCost = float(request.form['unitCost'])
    status = request.form['status']
    request_time = datetime.strptime(request.form['request_time'], '%Y-%m-%dT%H:%M')

    totalCost = quantity * unitCost

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        INSERT INTO Requests (booking_id, service_id, quantity, unitCost, totalCost, status, request_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (booking_id, service_id, quantity, unitCost, totalCost, status, request_time))
    mysql.connection.commit()
    cursor.close()

    return redirect('/requests')

from datetime import datetime
from flask import request, redirect

@app.route('/updateRequest', methods=['POST'])
def update_request():
    request_id = request.form.get('edit_request_id')
    booking_id = request.form.get('edit_booking_id')
    service_id = request.form.get('edit_service_id')
    quantity = request.form.get('edit_quantity')
    status = request.form.get('edit_status')
    request_time = request.form.get('edit_request_time')

    print("FORM DATA:", request.form)

    if not booking_id or not request_id or not service_id or not quantity or not status or not request_time:
        return "Missing required fields", 400

    try:
        quantity = int(quantity)
    except ValueError:
        return "Invalid quantity", 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch correct unit cost based on service_id
    cursor.execute("SELECT amount FROM services WHERE service_id = %s", (service_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        return "Service not found", 404

    unitCost = float(result['amount'])
    totalCost = unitCost * quantity

    # Update the request with verified and recalculated values
    cursor.execute("""
        UPDATE requests
        SET booking_id = %s, service_id = %s, quantity = %s,
            unitCost = %s, totalCost = %s, status = %s, request_time = %s
        WHERE request_id = %s
    """, (booking_id, service_id, quantity, unitCost, totalCost, status, request_time, request_id))
    
    mysql.connection.commit()
    cursor.close()

    return redirect('/requests')

@app.route('/deleteRequest/<int:request_id>', methods=['GET'])
def deleteRequest(request_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #Delete assignments first
    cursor.execute("DELETE FROM StaffAssignments WHERE request_id = %s", (request_id,))
    #Then delete the request
    cursor.execute("DELETE FROM Requests WHERE request_id = %s", (request_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/requests')

#Called by SERVICES Menu - add new service
@app.route('/addService', methods=['POST'])
def add_service():
    
    #Get the values entered in Add Form
    service_type = request.form['service_type']
    item = request.form['item']
    amount = float(request.form['amount'])

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute(
        "INSERT INTO Services (service_type, item, amount) VALUES (%s, %s, %s)",
        (service_type, item, amount)
    )
    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection

    return redirect('/services')

#Called by STAFF Menu - add a new staff
@app.route('/addStaff', methods=['POST'])
def add_staff():
    
    #Get the values entered in the Add Form
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    role = request.form['role']
    email = request.form['email']
    phone = request.form['phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute(
        "INSERT INTO Staff (first_name, last_name, role, email, phone) VALUES (%s, %s, %s, %s, %s)",
        (first_name, last_name, role, email, phone)
    )
    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection

    return redirect('/staff')

#Called by STAFF Menu - edit a staff
@app.route('/updateStaff', methods=['POST'])
def updateStaff():
    
    #Get the values entered in the Edit Form
    staff_id = int(request.form['edit_staff_id'])
    first_name = request.form['edit_first_name']
    last_name = request.form['edit_last_name']
    role = request.form['edit_role']
    email = request.form['edit_email']
    phone = request.form['edit_phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute(
        """
        UPDATE Staff 
        SET first_name = %s, last_name = %s, role = %s, email = %s, phone = %s 
        WHERE staff_id = %s
        """,
        (first_name, last_name, role, email, phone, staff_id)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect('/staff')

#Called by STAFF Menu - delete a staff
@app.route('/deleteStaff/<int:staff_id>', methods=['GET'])
def deleteStaff(staff_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM Staff WHERE staff_id = %s", (staff_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/staff')

#Called by SERVICES Menu - check if service exist in requests
@app.route('/checkServices/<int:service_id>')
def check_services(service_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS count FROM requests WHERE service_id = %s", (service_id,)) #Count how many service id in requests
    result = cursor.fetchone()
    cursor.close()
    return jsonify({"in_use": result['count'] > 0}) #Return to services; set "in_use" to true if count> 0

#Called by SERVICES Menu - edit a service
@app.route('/updateServices', methods=['POST'])
def updateServices():
    
    #Get the values entered in Edit Form
    service_id = int(request.form['edit_service_id'])
    service_type = request.form['edit_service_type']
    item = request.form['edit_item']
    amount = float(request.form['edit_amount'])

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute(
        """
        UPDATE Services 
        SET service_type = %s, item = %s, amount = %s 
        WHERE service_id = %s
        """,
        (service_type, item, amount, service_id)
    )
    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection

    return redirect('/services')

#Called by SERVICES Menu - delete a service
@app.route('/deleteServices/<int:service_id>', methods=['GET'])
def deleteServices(service_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM Services WHERE service_id = %s", (service_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/services')

@app.route('/addRoomGuest', methods=['POST'])
def add_room_guest():
    room_id = request.form['room_id']
    guest_id = request.form['guest_id']
    checkin_date = request.form['checkin_date']
    checkout_date = request.form['checkout_date']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO RoomGuest (room_id, guest_id, checkin_date, checkout_date) VALUES (%s, %s, %s, %s)",
        (room_id, guest_id, checkin_date, checkout_date)
    )
    mysql.connection.commit()
    cursor.close()
    return redirect('/roomGuest')

#Called by GUESTS Menu - check if guest exists in bookings
@app.route('/checkGuests/<int:guest_id>')
def check_guests(guest_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE guest_id = %s", (guest_id,)) #Count how many times guest_id appeared in bookings
    result = cursor.fetchone()
    cursor.close()
    return jsonify({"in_use": result['count'] > 0}) #Return to guests; set "in_use" to TRUE if count > 0

#Called by GUESTS Menu - delete a guest
@app.route('/deleteGuest/<int:guest_id>', methods=['GET'])
def deleteGuest(guest_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute("DELETE FROM guest WHERE guest_id = %s", (guest_id,)) #Execute
    mysql.connection.commit() #Save to db
    cursor.close() #Close connection
    return redirect('/guests') #Return to rooms

#Called by BOOKINGS Menu - display bookings
@app.route('/bookings')
def view_bookings():
    search = request.args.get('search', '')  #Get value of the search
    selected_type = request.args.get('room_type', '')  #Get id of the selected room

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    #Get all guests
    cursor.execute("SELECT * FROM guest")
    guests = cursor.fetchall()

    #Get rooms (with optional room type filter)
    if selected_type:
        cursor.execute("SELECT * FROM room WHERE room_type = %s", (selected_type,))
    else:
        cursor.execute("SELECT * FROM room")
    rooms = cursor.fetchall()

    #Get bookings with guest name and room number using JOIN
    if search:
        like = f"%{search}%"
        query = """
            SELECT 
                b.*, 
                g.first_name AS first_name,
                g.last_name AS last_name,
                r.room_number AS room_number
            FROM bookings b
            JOIN guest g ON b.guest_id = g.guest_id
            JOIN room r ON b.room_id = r.room_id
            WHERE 
                b.booking_id LIKE %s OR
                b.guest_id LIKE %s OR
                b.room_type LIKE %s OR
                b.room_id LIKE %s OR
                b.exp_check_in LIKE %s OR
                b.exp_check_out LIKE %s OR
                b.status LIKE %s OR
                g.first_name LIKE %s OR
                g.last_name LIKE %s OR
                r.room_number LIKE %s
        """
        cursor.execute(query, (like,) * 10) #Execute sql; 10 for 10 search criteria
    else:
        cursor.execute("""
            SELECT 
                b.*, 
                g.first_name AS first_name,
                g.last_name AS last_name,
                r.room_number AS room_number
            FROM bookings b
            JOIN guest g ON b.guest_id = g.guest_id
            JOIN room r ON b.room_id = r.room_id
        """)
    
    bookings = cursor.fetchall()
    cursor.close()

    return render_template('bookings.html', bookings=bookings, guests=guests, rooms=rooms, selected_type=selected_type) #Go to bookings; pass the data

#Called by BOOKINGS Menu - add a new booking
@app.route('/addBooking', methods=['POST'])
def add_booking():
    
    #Get the values entered in the Add Form
    guest_id = request.form.get('guest_id')
    room_type = request.form.get('room_type')
    room_id = request.form.get('room_id')
    exp_check_in = request.form.get('exp_check_in')
    exp_check_out = request.form.get('exp_check_out')
    status = request.form.get('status')

    #Validate dates before inserting
    if not exp_check_in or not exp_check_out:
        flash("Check-in and check-out dates are required.", "danger")
        return redirect('/bookings')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        INSERT INTO Bookings (guest_id, room_type, room_id, exp_check_in, exp_check_out, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (guest_id, room_type, room_id, exp_check_in, exp_check_out, status))
    mysql.connection.commit()
    cursor.close()
    return redirect('/bookings')

#Called by BOOKINGS Menu - edit a booking
@app.route('/updateBooking', methods=['POST'])
def updateBooking():
    
    #Get the values entered in the Edit Form
    booking_id = int(request.form['edit_booking_id'])
    guest_id = request.form['edit_guest_id']
    room_type = request.form['edit_room_type']
    room_id = request.form['edit_room_id']
    exp_check_in = request.form['edit_exp_check_in']
    exp_check_out = request.form['edit_exp_check_out']
    status = request.form['edit_status']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        UPDATE Bookings
        SET guest_id=%s, room_type=%s, room_id=%s, exp_check_in=%s, exp_check_out=%s, status=%s
        WHERE booking_id=%s
    """, (guest_id, room_type, room_id, exp_check_in, exp_check_out, status, booking_id))
    mysql.connection.commit()
    cursor.close()
    return redirect('/bookings')

#Called by BOOKINGS Menu - check if booking id is used in requests
@app.route('/checkBookingUsage/<int:booking_id>')
def check_booking_usage(booking_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM requests WHERE booking_id = %s", (booking_id,)) #Count how many booking_id
    count = cursor.fetchone()[0]
    cursor.close()
    return jsonify({'in_use': count > 0}) #Go bookings; set in_use if > 0; it in_use is true, it means that the booking cannot be deleted because it exists in requests

#Called by BOOKINGS Menu - delete a booking
@app.route('/deleteBooking/<int:booking_id>')
def delete_booking(booking_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
    mysql.connection.commit()
    cursor.close()
    flash('Booking deleted successfully', 'success')
    return redirect(url_for('view_bookings'))

#Route for Check-in/Check-out
@app.route('/checkin', methods=['POST'])
def checkin():
    booking_id = request.form['booking_id']
    actual_check_in = request.form['actual_check_in']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #Update booking table
    cursor.execute("""
        UPDATE Bookings
        SET actual_check_in = %s, status='Checked-in'
        WHERE booking_id = %s
    """, (actual_check_in, booking_id))

    #Get room_id and update room status
    cursor.execute("SELECT room_id FROM Bookings WHERE booking_id = %s", (booking_id,))
    room = cursor.fetchone()
    if room:
        cursor.execute("UPDATE Room SET room_status = 'Occupied' WHERE room_id = %s", (room['room_id'],))
    else:
        return "Room not found", 404

    mysql.connection.commit()
    cursor.close()
    return redirect('/roomGuest')

@app.route('/checkout', methods=['POST'])
def checkout():
    booking_id = request.form['booking_id']
    actual_check_out = request.form['actual_check_out']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #Update booking
    cursor.execute("""
        UPDATE Bookings
        SET actual_check_out = %s, status='Checked-out'
        WHERE booking_id = %s
    """, (actual_check_out, booking_id))

    #Get room_id and update status to Vacant
    cursor.execute("SELECT room_id FROM Bookings WHERE booking_id = %s", (booking_id,))
    room = cursor.fetchone()
    if room:
        cursor.execute("UPDATE Room SET room_status = 'Vacant' WHERE room_id = %s", (room['room_id'],))
    else:
        return "Room not found", 404

    mysql.connection.commit()
    cursor.close()
    return redirect('/roomGuest')

@app.route('/bill/<int:booking_id>')
def view_bill(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #Get all requests for this booking
    cursor.execute("""
        SELECT r.*, s.item, s.amount
        FROM Requests r
        JOIN Services s ON r.service_id = s.service_id
        WHERE r.booking_id = %s
    """, (booking_id,))
    requests = cursor.fetchall()
    total_bill = sum(r['totalCost'] for r in requests)
    cursor.close()
    return render_template('bill.html', requests=requests, total_bill=total_bill, booking_id=booking_id)

@app.route('/users')
def users_page():
    search = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search:
        like = f"%{search}%"
        cursor.execute("""
            SELECT * FROM users
            WHERE username LIKE %s OR email LIKE %s OR role LIKE %s OR department LIKE %s
        """, (like, like, like, like))
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()
    cursor.close()
    return render_template('users.html', users=users)

@app.route('/addUser', methods=['POST'])
def add_user():
    username = request.form['username']
    email = request.form['email']
    role = request.form['role']
    department = request.form.get('department')

    #Set department to None if user is admin/supervisor
    if role in ['admin', 'supervisor']:
        department = None

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO users (username, email, role, department, verified) VALUES (%s, %s, %s, %s, %s)",
        (username, email, role, department, True)
    )
    mysql.connection.commit()
    cursor.close()
    return redirect('/users')

@app.route('/deleteUser/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/users')

@app.route('/updateUser', methods=['POST'])
def update_user():
    user_id = request.form['edit_user_id']
    username = request.form['edit_username']
    email = request.form['edit_email']
    role = request.form['edit_role']
    department = request.form.get('edit_department')

    #Remove department (housekeeping, laundry, dining, massage)  if admin or supervisor
    if role in ['admin', 'supervisor', 'user']:
        department = None

    print("🟡 Department submitted:", department)  #Check what’s being submitted

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            UPDATE users 
            SET username=%s, email=%s, role=%s, department=%s 
            WHERE user_id=%s
        """, (username, email, role, department, user_id))
        mysql.connection.commit()
        flash("✅ User updated successfully!")
    except Exception as e:
        print("❌ Update error:", e)
        flash("❌ Failed to update user.")
    finally:
        cursor.close()

    return redirect('/users')

@app.route('/checkout/<int:booking_id>', methods=['GET'])
def show_checkout(booking_id):
    #Fetch booking info if needed
    return render_template('checkout_form.html', booking_id=booking_id)


@app.route('/pay', methods=['POST'])
def pay():
    booking_id = request.form['booking_id']
    amount = int(request.form['amount'])
    method = "card"  #Always use 'card' for PayMongo links

    HEADERS = {
        "Authorization": "Basic " + base64.b64encode(f"{PAYMONGO_SECRET_KEY}:".encode()).decode(),
        "Content-Type": "application/json"
    }

    #Create payment intent
    intent_payload = {
        "data": {
            "attributes": {
                "amount": amount,
                "currency": "PHP",
                "description": f"Booking #{booking_id} Payment",
                "payment_method_allowed": ["card", "gcash", "grab_pay"],  #Show all options
                "payment_method_options": {
                    "card": {"request_three_d_secure": "any"}
                }
            }
        }
    }
    intent_response = requests.post("https://api.paymongo.com/v1/payment_intents", headers=HEADERS, json=intent_payload)
    intent_data = intent_response.json()
    if "data" not in intent_data:
        return "<h3>❌ Error creating payment intent.</h3><pre>{}</pre>".format(json.dumps(intent_data, indent=2))
    intent_id = intent_data["data"]["id"]

    #Create checkout link
    checkout_payload = {
        "data": {
            "attributes": {
                "billing": {"name": "ezStay Guest"},
                "payment_intent": intent_id,
                "description": f"Booking #{booking_id} Payment",
                "amount": amount,
                "currency": "PHP",
                "success_url": url_for('success', _external=True),
                "cancel_url": url_for('failed', _external=True)
            }
        }
    }
    checkout_response = requests.post("https://api.paymongo.com/v1/links", headers=HEADERS, json=checkout_payload)
    checkout_data = checkout_response.json()
    if "data" not in checkout_data:
        return "<h3>❌ Error creating checkout link.</h3><pre>{}</pre>".format(json.dumps(checkout_data, indent=2))
    return redirect(checkout_data["data"]["attributes"]["checkout_url"])

@app.route('/success')
def success():
    return render_template("bill.html")

@app.route('/failed')
def failed():
    return "<h1 style='color:red;'>❌ Payment Failed or Cancelled.</h1>"

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp' not in session or 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form['otp']
        if entered_otp == session['otp']:
            # OTP correct, allow password reset
            return redirect(url_for('reset_password'))
        else:
            return render_template('verify_otp.html', error="Invalid OTP. Please try again.")

    return render_template('verify_otp.html')

if __name__ == '__main__':
    app.run(debug=True)