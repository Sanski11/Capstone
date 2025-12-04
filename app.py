# Core Flask modules
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from flask_login import LoginManager, current_user

# MySQL integration
from flask_mysqldb import MySQL
import MySQLdb.cursors

# Utility modules
from datetime import datetime, timedelta
import hmac
import hashlib
import os
import json
import base64
import random
import re
import requests
import smtplib
import random, string
import uuid

# Email handling
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Environment variable loader
from dotenv import load_dotenv

# Security
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from werkzeug.utils import secure_filename

# Flask-Mail setup
from flask_mail import Mail, Message
from extensions import mail  # Custom mail extension

# Custom utility functions
from utils import send_verification_email, verify_token


app = Flask(__name__)
app.secret_key = 'your_secret_key'
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
serializer = URLSafeTimedSerializer(app.secret_key)
STAFF_SIGNUP_CODE = "EzStayStaff2025"  # Change this to your secure code
 
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

#MySQL AivenMySQL
app.config['MYSQL_HOST'] = 'mysql-3dabe135-benilde-ac16.k.aivencloud.com'
app.config['MYSQL_PORT'] = 17710
app.config['MYSQL_USER'] = 'avnadmin'
app.config['MYSQL_PASSWORD'] = 'AVNS_4XNIj2-qNxSTo-HJlgi'
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
        server.login(app.config['EMAIL_USERNAME'], app.config['EMAIL_PASSWORD'])
        server.sendmail(app.config['EMAIL_USERNAME'], email, message)
        server.quit()
        return True
    except Exception as e:
        print("❌ Email send failed:", e)
        return False
    
    # Utility function to send email
def send_email(recipient, subject, body):
    try:
        # Use smtplib directly (not Flask-Mail) for custom SMTP
        server = smtplib.SMTP(app.config['EMAIL_HOST'], app.config['EMAIL_PORT'])
        server.starttls()
        server.login(app.config['EMAIL_USERNAME'], app.config['EMAIL_PASSWORD'])
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(app.config['EMAIL_USERNAME'], recipient, message)
        server.quit()
        return True
    except Exception as e:
        print("Email error:", e)
        return False

def send_reset_otp(email):
    otp = random.randint(100000, 999999)
    session['reset_otp'] = otp
    session['reset_email'] = email
    # Here, send the OTP via email (SMTP / Mailtrap / SendGrid)
    print(f"OTP for {email}: {otp}")  # for testing
    flash("A verification code has been sent to your email.", "info")
    
@app.context_processor
def inject_user_details():
    return {
        'username': session.get('username'),
        'role': session.get('role'),
        'department': session.get('department')
    }

@app.context_processor
def inject_current_booking():
    user_id = session.get('user_id')
    role = session.get('role')
    current_booking_id = None
    if role in ['user', 'guest'] and user_id:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT booking_id 
            FROM bookings 
            WHERE guest_id = %s AND status = 'Checked-in' 
            LIMIT 1
        """, (user_id,))
        booking = cursor.fetchone()
        cursor.close()
        if booking:
            current_booking_id = booking['booking_id']
    return dict(current_booking_id=current_booking_id)

@app.route('/')
def home():
    return redirect(url_for('index'))

# Fetch notifications for dropdown
@app.route('/notifications_dropdown')
def notifications_dropdown():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT log_id, timestamp, record_id, CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message
        FROM audit_log
        WHERE read_status = 0
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    notifications = cursor.fetchall()
    cursor.close()
    return notifications  # You can render via context or JSON for AJAX

# View all notifications
@app.route('/notifications')
def notifications():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    ORDER BY timestamp DESC
""")
    notifications = cursor.fetchall()

    cursor.close()
    return render_template('notifications.html', notifications=notifications)

# return unread count
@app.route('/notifications/unread_count')
def unread_count():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    row = cur.fetchone()
    cur.close()
    count = int(row['count'] if row and 'count' in row else 0)
    return jsonify({'unread_count': count})

# mark all as read (AJAX POST)
@app.route('/mark_read', methods=['POST'])
def mark_read():
    log_id = request.form.get('log_id')

    cursor = mysql.connection.cursor()

    if log_id:
        # Mark single notification
        cursor.execute(
        "UPDATE audit_log SET read_status = 1 WHERE log_id = %s AND username = %s",
        (log_id, session['username'])
    )
    else:
        # Mark all notifications for current user
        cursor.execute("UPDATE audit_log SET read_status = 1 WHERE username = %s AND read_status = 0", (session['username'],))

    mysql.connection.commit()

    # Count unread notifications
    cursor.execute("SELECT COUNT(*) FROM audit_log WHERE username = %s AND read_status = 0", (session['username'],))
    unread_count = cursor.fetchone()[0]
    cursor.close()

    return jsonify({'status': 'success', 'unread_count': unread_count})

BOOKING_LABELS = [
    "Booking Id",
    "Room Number",
    "Room Type",
    "Guests",
    "Exp Check In",
    "Exp Check Out",
    "Field 7",
    "Field 8",
    "Status",
    "Random Booking Ref",
    "Created By",
    "Created At"
]

def format_value(value, list_labels=None):
    """Formats a value, either dict, list, or plain text."""
    if not value or value == "-":
        return "-"

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            html = ""
            for k, v in parsed.items():
                html += f"<b>{k.replace('_',' ').title()}:</b> {v}<br>"
            return html
        elif isinstance(parsed, list):
            html = ""
            for i, v in enumerate(parsed):
                label = list_labels[i] if list_labels and i < len(list_labels) else f"Field {i}"
                html += f"<b>{label}:</b> {v}<br>"
            return html
        else:
            return str(parsed)
    except Exception:
        lines = value.split("\n")
        html = ""
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                html += f"<b>{key.strip()}:</b> {val.strip()}<br>"
            else:
                html += line + "<br>"
        return html

def format_audit(old_value, new_value=None, list_labels=None):
    """Formats old and new values side by side; new_value is optional."""
    old_html = format_value(old_value, list_labels=list_labels)
    new_html = format_value(new_value, list_labels=list_labels) if new_value is not None else "-"
    
    return f"<div style='display:flex; gap:20px;'><div><b>Old Value:</b><br>{old_html}</div>" \
           f"<div><b>New Value:</b><br>{new_html}</div></div>"

# Register in Jinja
app.jinja_env.globals.update(format_value=format_value)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'login_attempts' not in session:
        session['login_attempts'] = 0

    # Check for lockout
    lockout_until = session.get('lockout_until')
    if lockout_until:
        lockout_until_dt = datetime.strptime(lockout_until, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < lockout_until_dt:
            remaining = (lockout_until_dt - datetime.now()).seconds
            return render_template(
                'login.html',
                lockout_remaining=remaining,
                error=f"Maximum login attempts reached. Try again in {remaining//60}m {remaining%60}s."
            )
        else:
            session.pop('lockout_until')
            session['login_attempts'] = 0

    if request.method == 'POST':
        if session['login_attempts'] >= 3:
            lockout_time = datetime.now() + timedelta(minutes=3)
            session['lockout_until'] = lockout_time.strftime("%Y-%m-%d %H:%M:%S")
            return render_template(
                'login.html',
                error="Maximum login attempts reached. Please try again in 3 minutes."
            )

        username_or_email = request.form.get('username') or request.form.get('username_or_email')
        password = request.form.get('password')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Updated: allow login with either username or email
        cursor.execute(
            'SELECT * FROM users WHERE (username = %s OR email = %s) AND password = %s',
            (username_or_email, username_or_email, password)
        )
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Generate OTP valid for 5 minutes
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            session['pending_user'] = {
                "username": user['username'],
                "role": user['role'],
                "department": user['department'],
                "email": user['email']
            }

            # Send OTP to user’s email
            send_email(user['email'], "EzStay Login OTP", f"Your OTP is {otp}. It expires in 5 minutes.")

            # Reset failed attempts after successful login
            session['login_attempts'] = 0
            session.pop('lockout_until', None)

            flash("An OTP has been sent to your email. Please verify.", "info")
            return redirect(url_for('verify_otp'))
        else:
            session['login_attempts'] += 1
            attempts_left = 3 - session['login_attempts']
            if attempts_left > 0:
                flash(f"Invalid username/email or password. Attempts left: {attempts_left}", "danger")
            else:
                lockout_time = datetime.now() + timedelta(minutes=3)
                session['lockout_until'] = lockout_time.strftime("%Y-%m-%d %H:%M:%S")
                flash("Maximum login attempts reached. Please try again in 3 minutes.", "danger")

    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Please provide an email address.", "danger")
            return render_template('forgot_password.html')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s LIMIT 1", (email,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            flash("Email not found.", "danger")
            return render_template('forgot_password.html')

        otp = str(random.randint(100000, 999999))
        session['reset_email'] = email
        session['otp'] = otp
        session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

        # send OTP (best-effort)
        try:
            send_email(email, "ezStay Password Reset OTP", f"Your OTP is {otp}. It expires in 5 minutes.")
        except Exception as e:
            app.logger.warning("Failed to send reset OTP: %s", e)
            # still proceed so admin/dev can see OTP in logs during dev
            print(f"[DEV] OTP for {email}: {otp}")

        flash("A verification code has been sent to your email.", "info")
        return redirect(url_for('verify_otp'))

    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

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

@app.route('/change_password', methods=['POST'])
def change_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    username = session['username']

    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "danger")
        return redirect('/profile')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user or user['password'] != current_password:
        flash("Current password is incorrect.", "danger")
        return redirect('/profile')

    # Directly store the new password as plain text
    cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
    mysql.connection.commit()
    cursor.close()

    flash("Password updated successfully.", "success")
    return redirect('/profile')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        selected_role = request.form.get('role', 'user').lower()

        # Define allowed roles
        allowed_roles = ['admin', 'manager', 'supervisor', 'user']

        # Security: Only admins can create privileged roles
        if selected_role in ['admin', 'manager', 'supervisor']:
            if 'role' not in session or session.get('role', '').lower() != 'admin':
                flash("Only administrators can create admin, manager, or supervisor accounts.", "danger")
                return redirect(url_for('signup'))
        else:
            selected_role = 'user'  # Force default for public signup

        status = 1  # Active by default
        account_status = 'Pending'  # Account status starts as Pending

        # Safe defaults for all user info fields
        department = None
        verified = False
        email_verified = False
        verification_token = generate_verification_token()
        token_expires_at = datetime.now() + timedelta(hours=24)
        created_at = datetime.now()

        first_name = request.form.get('first_name', '')
        middle_name = request.form.get('middle_name', '')
        last_name = request.form.get('last_name', '')
        name = f"{first_name} {middle_name} {last_name}".strip()
        phone = request.form.get('phone', '')

        reset_token = None
        reset_token_expiry = None

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check for duplicates
        cursor.execute("SELECT username FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            flash("Username already taken.", "danger")
            return redirect(url_for('signup'))

        cursor.execute("SELECT email FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('signup'))

        # Insert safely
        cursor.execute("""
            INSERT INTO users (
                username, email, password, role, status, department,
                verified, email_verified, verification_token, token_expires_at,
                account_status, created_at, first_name, last_name, middle_name,
                name, phone, reset_token, reset_token_expiry
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """, (
            username, email, password, selected_role, status, department,
            verified, email_verified, verification_token, token_expires_at,
            account_status, created_at, first_name, last_name, middle_name,
            name, phone, reset_token, reset_token_expiry
        ))
        mysql.connection.commit()

        # Send verification email
        if send_verification_email(email, username, verification_token):
            flash("Check your email for a verification link.", "success")
            return redirect(url_for('verification_pending'))
        else:
            flash("Could not send email. Please contact support.", "danger")

    return render_template('signup.html')

@app.route('/staff_signup', methods=['GET', 'POST'])
def staff_signup():
    if request.method == 'POST':
        code = request.form.get('staff_code', '').strip()  # Get code from form
        if code != STAFF_SIGNUP_CODE:
            flash("Invalid signup code. Access denied.", "danger")
            return redirect(url_for('staff_signup'))

        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role')  # supervisor, manager, staff

        # Only allow specific roles
        if role not in ['staff', 'supervisor', 'manager']:
            flash("Invalid role selected.", "danger")
            return redirect(url_for('staff_signup'))

        # Staff accounts start inactive until admin approval
        status = 0
        account_status = 'Pending Approval'

        first_name = request.form.get('first_name', '')
        middle_name = request.form.get('middle_name', '')
        last_name = request.form.get('last_name', '')
        name = f"{first_name} {middle_name} {last_name}".strip()
        phone = request.form.get('phone', '')

        verified = False
        email_verified = False
        verification_token = generate_verification_token()
        token_expires_at = datetime.now() + timedelta(hours=24)
        created_at = datetime.now()
        department = request.form.get('department', None)
        reset_token = None
        reset_token_expiry = None

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check for duplicates
        cursor.execute("SELECT username FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            flash("Username already taken.", "danger")
            return redirect(url_for('staff_signup'))

        cursor.execute("SELECT email FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('staff_signup'))

        # Insert staff account
        cursor.execute("""
            INSERT INTO users (
                username, email, password, role, status, department,
                verified, email_verified, verification_token, token_expires_at,
                account_status, created_at, first_name, last_name, middle_name,
                name, phone, reset_token, reset_token_expiry
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """, (
            username, email, password, role, status, department,
            verified, email_verified, verification_token, token_expires_at,
            account_status, created_at, first_name, last_name, middle_name,
            name, phone, reset_token, reset_token_expiry
        ))
        mysql.connection.commit()

        # Send verification email (optional)
        if send_verification_email(email, username, verification_token):
            flash("Staff account created! Pending admin approval.", "success")
            return redirect(url_for('staff_signup'))
        else:
            flash("Could not send email. Please contact support.", "danger")

    return render_template('staff_signup.html')

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
    # auth
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_id = session.get('user_id')
    role = session['role']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()

    # fetch user record, if missing redirect to login
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        return redirect(url_for('login'))

    # helper to safely fetch count like SELECT ... AS count
    def fetch_count(default=0):
        row = cursor.fetchone()
        if not row:
            return default
        # support both dict and tuple row shapes
        if isinstance(row, dict):
            return int(row.get('count', default) or default)
        try:
            return int(row[0] or default)
        except Exception:
            return default

    # get current booking id for user (optional)
    current_booking_id = None
    if role == 'user' and user_id:
        cursor.execute("""
            SELECT booking_id
            FROM bookings
            WHERE guest_id = %s
            ORDER BY booking_id DESC
            LIMIT 1
        """, (user_id,))
        rb = cursor.fetchone()
        current_booking_id = rb['booking_id'] if rb and 'booking_id' in rb else (rb[0] if rb and len(rb) > 0 else None)

    # collect stats
    stats = {}

    # Housekeeping: totals, pending, completed, total services
    cursor.execute("""
        SELECT
            COUNT(*) AS count,
            SUM(CASE WHEN UPPER(r.status) IN ('PENDING','PROCESSING') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE r.service_id IN (
            SELECT service_id FROM hotel_services WHERE category = 'Housekeeping'
        )
        AND LOWER(b.status) = 'checked-in'
    """)
    row = cursor.fetchone() or {}
    stats['housekeeping_total_requests'] = row.get('count', 0) or 0
    stats['housekeeping_pending'] = row.get('pending', 0) or 0
    stats['housekeeping_completed'] = row.get('completed', 0) or 0

    # Dining: total menu items, requests, pending, completed
    # Laundry
    cursor.execute("""
        SELECT
            COUNT(*) AS count,
            SUM(CASE WHEN UPPER(r.status) IN ('PENDING','PROCESSING') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE r.service_id IN (
            SELECT service_id FROM hotel_services WHERE category = 'Laundry'
        )
        AND LOWER(b.status) = 'checked-in'
    """)
    row = cursor.fetchone() or {}
    stats['laundry_total_requests'] = row.get('count', 0) or 0
    stats['laundry_pending'] = row.get('pending', 0) or 0
    stats['laundry_completed'] = row.get('completed', 0) or 0

    # Dining
    cursor.execute("""
        SELECT
            COUNT(*) AS count,
            SUM(CASE WHEN UPPER(r.status) IN ('PENDING','PROCESSING') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE r.item_id IN (
            SELECT item_id FROM food_items WHERE type = 'food'
        )
        AND LOWER(b.status) = 'checked-in'
    """)
    row = cursor.fetchone() or {}
    stats['dining_total_requests'] = row.get('count', 0) or 0
    stats['dining_pending'] = row.get('pending', 0) or 0
    stats['dining_completed'] = row.get('completed', 0) or 0

    # Massage / Spa
    cursor.execute("""
        SELECT
            COUNT(*) AS count,
            SUM(CASE WHEN UPPER(r.status) IN ('PENDING','PROCESSING') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE r.service_id IN (
            SELECT service_id FROM hotel_services WHERE category = 'Massage'
        )
        AND LOWER(b.status) = 'checked-in'
    """)
    row = cursor.fetchone() or {}
    stats['spa_total_requests'] = row.get('count', 0) or 0
    stats['spa_pending'] = row.get('pending', 0) or 0
    stats['spa_completed'] = row.get('completed', 0) or 0


    # Global booking and user counts
    cursor.execute("SELECT COUNT(*) AS count FROM users WHERE status = 1")
    stats['active_users'] = fetch_count(0)

    cursor.execute("SELECT COUNT(*) AS count FROM users")
    stats['total_users'] = fetch_count(0)

    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE status = 'Checked-in'")
    stats['active_bookings'] = fetch_count(0)

    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE status IN ('Active','Confirmed')")
    stats['current_bookings'] = fetch_count(0)

    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE DATE(actual_check_in) = CURDATE()")
    stats['checkins_today'] = fetch_count(0)

    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE DATE(actual_check_out) = CURDATE()")
    stats['checkouts_today'] = fetch_count(0)

    cursor.execute("SELECT COUNT(DISTINCT guest_id) AS count FROM bookings WHERE status = 'Checked-in'")
    stats['guests_checked_in'] = fetch_count(0)

    cursor.execute("""
        SELECT COUNT(DISTINCT guest_id) AS count
        FROM bookings
        WHERE status = 'Checked-out' AND DATE(actual_check_out) = CURDATE()
    """)
    stats['guests_checked_out'] = fetch_count(0)

    # Build service_data list for pie chart, grouping by hotel_services.category
    cursor.execute("""
        SELECT COALESCE(s.category, 'Other') AS service_type, COUNT(*) AS count
        FROM hotel_services s
        JOIN requests r ON r.service_id = s.service_id
        GROUP BY s.category
        ORDER BY count DESC
    """)
    service_data = cursor.fetchall() or []
    # ensure it's a list of dicts (fetchall with DictCursor already returns list of dicts)
    if not isinstance(service_data, list):
        service_data = list(service_data)

    # Add dining as a service_type if there are dining requests via food_items
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM requests r
        JOIN food_items f ON r.item_id = f.item_id
        WHERE f.type = 'food'
    """)
    dining_row = cursor.fetchone()
    dining_count = 0
    if dining_row:
        dining_count = int(dining_row.get('count', 0) if isinstance(dining_row, dict) else (dining_row[0] or 0))
    # if there are dining requests, append or merge with service_data
    if dining_count > 0:
        # try to merge into existing service_data entry 'In-Room Dining' if present
        merged = False
        for sd in service_data:
            if sd.get('service_type') in ('In-Room Dining', 'Dining', 'In Room Dining'):
                sd['count'] = sd.get('count', 0) + dining_count
                merged = True
                break
        if not merged:
            service_data.append({'service_type': 'In-Room Dining', 'count': dining_count})

    # Staff activity for bar chart
    cursor.execute("""
        SELECT
            COALESCE(s.first_name, 'None') AS staff,
            COUNT(r.request_id) AS requests,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        LEFT JOIN staff s ON r.staff_id = s.staff_id
        LEFT JOIN bookings b ON r.booking_id = b.booking_id
        WHERE b.status = 'Checked-in' OR b.status IS NULL
        GROUP BY s.first_name
        ORDER BY requests DESC
        LIMIT 20
    """)
    staff_data = cursor.fetchall() or []
    if not isinstance(staff_data, list):
        staff_data = list(staff_data)

    # Remove unassigned (None) staff entries so they don't appear in the chart
    staff_data = [s for s in staff_data if s.get('staff') not in (None, 'None', '', 'null')]

    # Make high level fields that your template expects
    # top cards use these keys: housekeeping, food, laundry, spa
    stats['housekeeping'] = stats.get('housekeeping_total_requests', 0)
    stats['food'] = stats.get('dining_total_requests', 0)
    stats['laundry'] = stats.get('laundry_total_requests', 0)
    stats['spa'] = stats.get('spa_total_requests', 0)

    # user small dashboard keys if role == 'user'    # user small dashboard keys if role == 'user'
    # compute pending requests for that user
    if role == 'user' and user_id:
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM requests r
            JOIN bookings b ON r.booking_id = b.booking_id
            WHERE b.guest_id = %s AND UPPER(r.status) IN ('PENDING','PROCESSING')
        """, (user_id,))
        stats['pending_requests'] = fetch_count(0)

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM bookings
            WHERE guest_id = %s AND status IN ('Active','Confirmed','Checked-in')
        """, (user_id,))
        stats['active_bookings'] = fetch_count(0)

    # --- Staff-specific dashboard ---    # --- Staff-specific dashboard ---
    if role == 'staff' and user_id:
    # Assigned requests: pending + processing
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM requests
            WHERE staff_id = %s AND UPPER(status) IN ('PENDING','PROCESSING')
        """, (user_id,))
        stats['assigned_requests'] = fetch_count(0)

        # Completed tasks
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM requests
            WHERE staff_id = %s AND UPPER(status) = 'COMPLETED'
        """, (user_id,))
        stats['completed_tasks'] = fetch_count(0)

        # Pending tasks (same as assigned_requests, could adjust if you want separate logic)
        stats['pending_tasks'] = stats['assigned_requests']

        # Optional: fetch breakdown for daily staff activity chart
        cursor.execute("""
            SELECT
                COALESCE(b.first_name, 'None') AS staff_name,
                COUNT(r.request_id) AS total_requests,
                SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
            FROM requests r
            LEFT JOIN staff b ON r.staff_id = b.staff_id
            WHERE r.staff_id = %s
            GROUP BY b.first_name
            ORDER BY total_requests DESC
            LIMIT 20
        """, (user_id,))
        staff_chart_data = cursor.fetchall() or []
        # Filter out unassigned
        staff_chart_data = [s for s in staff_chart_data if s.get('staff_name') not in (None, 'None', '', 'null')]

    # Close cursor
    cursor.close()

    # Render dashboard template    
    return render_template(
        'dashboard.html',       
        role=role,
        stats=stats,
        service_data=service_data,
        staff_data=staff_data,
        current_booking_id=current_booking_id,
        user=user,
        notifications=notifications,
        unread_count=unread_count
    )

@app.route('/calendar')
def calendar():
    # 1. AUTHENTICATION CHECK
    username = session.get('username')
    if not username:
        flash("⚠️ You must be logged in to view the calendar.")
        return redirect(url_for('login'))

    # 2. FETCH USER & ROLE
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user:
            flash("⚠️ User data not found. Please log in again.")
            return redirect(url_for('login'))
        user_role = user.get('role', 'user')

        # 3. FETCH UNREAD NOTIFICATIONS
        cursor.execute("""
            SELECT log_id, timestamp,
                   CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
                   read_status
            FROM audit_log
            WHERE read_status = 0
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        notifications = cursor.fetchall()

        # 4. FETCH UNREAD COUNT FOR BADGE
        cursor.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
        unread_count = cursor.fetchone()['count']

    # 5. RENDER TEMPLATE
    return render_template(
        'calendar.html',
        role=user_role,
        user=user,
        notifications=notifications,
        unread_count=unread_count
    )

@app.route('/upcoming_events')
def upcoming_events():
    return render_template('upcoming_events.html')

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        flash("⚠️ You must be logged in.")
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch user information
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        flash("⚠️ User not found.")
        return redirect(url_for('login'))

    # ===============================
    # 1. USER STATISTICS
    # ===============================

    # Completed requests
    cursor.execute("""
        SELECT COUNT(*) AS completed_tasks
        FROM requests r
        JOIN bookings b ON r.booking_id = b.booking_id
        WHERE b.guest_id = %s AND r.status = 'Completed'
    """, (user['user_id'],))
    completed_tasks = cursor.fetchone()['completed_tasks']

    # Total bookings handled (for staff/admin)
    cursor.execute("""
        SELECT COUNT(*) AS total_bookings
        FROM bookings
        WHERE last_update = %s
    """, (username,))
    total_bookings = cursor.fetchone()['total_bookings']

    # ===============================
    # 2. RECENT ACTIVITY (AUDIT LOG)
    # ===============================
    cursor.execute("""
        SELECT table_name, action_type, timestamp
        FROM audit_log
        WHERE username = %s
        ORDER BY timestamp DESC
        LIMIT 5
    """, (username,))
    logs = cursor.fetchall()

    # Convert to display-friendly structure
    activities = [
        {
            "description": f"{log['action_type']} action on {log['table_name']}",
            "timestamp": log['timestamp']
        }
        for log in logs
    ]

    cursor.close()

    # ===============================
    # 3. RENDER PAGE
    # ===============================
    return render_template(
        'profile.html',
        user=user,
        role=user['role'],
        completed_tasks=completed_tasks,
        total_bookings=total_bookings,
        activities=activities
    )


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
    return redirect(url_for('index'))

#Called by STAFF Menu - display staff
@app.route('/staff')
def view_staffs():
    selected_staff = request.args.get('staff_id', '')  # Get the id of the selected staff
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    
    department = session.get('department') or ''
    
    # Fetch staff from 'staff' table
    cursor.execute("""
        SELECT staff_id AS id,
               first_name,
               last_name,
               role,
               email,
               last_update,
               timestamp,
               COALESCE(phone, '') AS phone,
               'staff_table' AS source
        FROM staff
        WHERE role LIKE %s
            OR role IS NULL
            OR role = ''
        ORDER BY last_name, first_name
    """, ('%' + department + '%',))
    staff_table = list(cursor.fetchall())

    # Fetch users who are staff from 'users' table
    cursor.execute("""
        SELECT user_id AS id,
               username AS first_name,
               '' AS last_name,
               role,
               email,
               last_update,
               timestamp,
               '' AS phone,
               'users_table' AS source
        FROM users
        WHERE (role LIKE %s OR role IS NULL OR role = '')
            AND role NOT IN ('admin', 'guest', 'manager', 'user', 'supervisor')
        """, ('%' + department + '%',))
    user_staff = list(cursor.fetchall())

    # Merge both lists
    combined_staffs = staff_table + user_staff

    # Sort by last_name then first_name (optional since staff_table is already ordered)
    combined_staffs.sort(key=lambda x: (x['last_name'] or '', x['first_name']))

    return render_template('staff.html', staffs=combined_staffs, selected_staff=selected_staff, notifications=notifications,
        unread_count=unread_count)

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
    cursor.execute("DELETE FROM guest WHERE guest_id = %s", (guest_id,))
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
            UPDATE guest SET first_name = %s, middle_name = %s,
            last_name = %s, email = %s, phone = %s
            WHERE guest_id = %s
        """, (first_name, middle_name, last_name, email, phone, guest_id))
        mysql.connection.commit()
        cursor.close()
        return redirect('/guests')

    #GET method - show the edit form
    cursor.execute("SELECT * FROM guest WHERE guest_id = %s", (guest_id,))
    guest = cursor.fetchone()
    cursor.close()

    if not guest:
        #Instead of redirecting, render the template with guest=None or show an error
        return render_template('editGuest.html', guest=None, error="Guest not found")
    return render_template('editGuest.html', guest=guest)

# Flask route: app.py
@app.route("/requests")
def show_requests():
    # --- main cursor for requests and related data ---
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cursor.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cursor.fetchone()['count']
    
    selectedCategory = request.args.get('category', '')
    status_filter = request.args.get('status', 'all').lower()  # 'pending', 'completed', 'all'

    department = session.get('department') or ''
    
    # Base query
    query = """
        SELECT r.*,
            s.name AS service_name,
            f.name AS food_name,
            s.category AS service_category,
            f.category AS food_category,
            s.type AS service_type,
            f.type AS food_type,
            st.first_name AS staff_first_name,
            st.last_name  AS staff_last_name,
            g.last_name AS guest_last_name,
            g.first_name AS guest_first_name
        FROM requests r
        LEFT JOIN hotel_services s ON r.service_id = s.service_id
        LEFT JOIN food_items f ON r.item_id = f.item_id
        LEFT JOIN staff st ON st.staff_id = r.staff_id
        LEFT JOIN guest g ON g.guest_id = r.guest_id
        LEFT JOIN bookings b ON b.booking_id = r.booking_id
        WHERE b.status = 'Checked-in'
    """

    # Department-specific filtering
    if department == 'Dining':
        query += " AND r.item_id IS NOT NULL"
    elif department in ['Housekeeping', 'Massage', 'Laundry']:
        query += " AND s.category LIKE %s"

    if status_filter == 'pending':
        query += " AND r.status = 'pending'"
    elif status_filter == 'completed':
        query += " AND r.status = 'completed'"
    # 'all' → no filter needed

    # Execute the query
    if department in ['Housekeeping', 'Massage', 'Laundry']:
        cursor.execute(query, ('%' + department + '%',))
    else:
        cursor.execute(query)

    requests = cursor.fetchall()

    cursor.execute("SELECT * FROM hotel_services")
    service_list = cursor.fetchall()

  # Get names (service or food) based on request_type or selectedCategory
    request_type = request.args.get('request_type', '').lower()
    service_names = []
    food_names = []

    if request_type == 'food':
        cursor.execute("""
            SELECT item_id, price, name, category
            FROM food_items
            WHERE (%s = '' OR category = %s)
            ORDER BY name
        """, (selectedCategory, selectedCategory))
        food_names = cursor.fetchall()

    elif request_type == 'service':
        cursor.execute("""
            SELECT service_id, price, name, category
            FROM hotel_services
            WHERE (%s = '' OR category = %s)
            ORDER BY name
        """, (selectedCategory, selectedCategory))
        service_names = cursor.fetchall()

    else:
        # Default: load all for admins or when request_type not specified
        cursor.execute("SELECT service_id, price, name, category FROM hotel_services ORDER BY name")
        service_names = cursor.fetchall()

        cursor.execute("SELECT item_id, price, name, category FROM food_items ORDER BY name")
        food_names = cursor.fetchall()    

    cursor.execute("SELECT * FROM food_items")
    item_list = cursor.fetchall()

    cursor.execute("""
        SELECT b.*, r.room_number 
        FROM bookings b 
        LEFT JOIN room r ON b.room_id = r.room_id 
        WHERE b.status='Checked-in'
    """)
    booking_list = cursor.fetchall()

    cursor.execute("SELECT * FROM staff")
    staff_table = list(cursor.fetchall())

    cursor.execute("""
        SELECT user_id AS id,
               username AS first_name,
               '' AS last_name,
               role,
               department,
               'users_table' AS source
        FROM users
        WHERE role='staff'
    """)
    user_staff = list(cursor.fetchall())

    staff_list = staff_table + user_staff
    staff_list.sort(key=lambda x: (x['last_name'] or '', x['first_name']))

 #cursor.execute("SELECT DISTINCT category FROM food_items")
    #food_category_list = cursor.fetchall()

    #cursor.execute("SELECT DISTINCT category FROM hotel_services")
    #service_category_list = cursor.fetchall()

    # --- FOOD CATEGORIES ---
    # Show if: department == 'Dining' OR role is admin/supervisor
    #if department == 'Dining' or role in ['admin', 'manager']:
    cursor.execute("""
        SELECT DISTINCT category
        FROM food_items
        ORDER BY category
    """)
    food_category_list = cursor.fetchall()

    # --- SERVICE CATEGORIES ---
    # Show if: department is NOT dining, NOT empty, OR role is admin/supervisor
    if (department and department != 'Dining'):
        # Limit by department
        cursor.execute("""
            SELECT DISTINCT category
            FROM hotel_services
            WHERE category LIKE %s
            ORDER BY category
        """, ('%' + department + '%',))
    else:
        # Admin/supervisor or no department → show all
        cursor.execute("""
            SELECT DISTINCT category
            FROM hotel_services
            ORDER BY category
        """)
    service_category_list = cursor.fetchall()   

    cursor.close()

    return render_template(
        "requests.html",
        requests=requests,
        service_list=service_list,
        item_list=item_list,
        booking_list=booking_list,
        staff_list=staff_list,
        food_category_list=food_category_list,
        service_category_list=service_category_list,
        service_names=service_names,
        food_names=food_names,
        status_filter=status_filter,
        notifications=notifications,
        unread_count=unread_count
    )

#Called by ROOMS Menu - display list of rooms
@app.route('/rooms')
def view_rooms():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to the database
    
    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    
    cursor.execute("""
        SELECT * FROM room ORDER BY room_number
    """)

    rooms = cursor.fetchall()  #After executing sql, fetch results
    return render_template('rooms.html', rooms=rooms, notifications=notifications, unread_count=unread_count) #pass the contents of rooms to rooms.html
  
 
#Called by GUESTS Menu - display list of guests
@app.route('/guests')
def view_guests():
    selected_guest = request.args.get('guest_id', '')  #Get the id of the selected guest
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    
    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    cursor.execute("""
        SELECT * FROM guest ORDER BY last_name, first_name
    """)
    guests = cursor.fetchall() #After executing; fetch results
    return render_template('guests.html', guests=guests, notifications=notifications,
        unread_count=unread_count) #pass the contents of guests to guests.html

#Called by CHECKIN / CHECKOUT MENU - display bookings
@app.route('/roomGuest')
def show_roomGuest():
    selected_room = request.args.get('room_id', '') #Get the roomid of the selected booking
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db

    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    #Get all guests
    cursor.execute("SELECT * FROM guest")
    guests = cursor.fetchall()

    #Get rooms 
    cursor.execute("SELECT * FROM room")
    rooms = cursor.fetchall()

    cursor.execute("""
            SELECT 
                b.*, 
                g.first_name,
                g.last_name,
                r.room_number,
                COALESCE((
                        SELECT SUM(req.total_cost)
                        FROM requests req
                        WHERE req.booking_id = b.booking_id
                    ), 0) AS total_bill,
                    COALESCE((
                        SELECT SUM(p.amount)
                        FROM payment p
                        WHERE p.booking_id = b.booking_id
                    ), 0) AS total_payment                
            FROM bookings b
            JOIN guest g ON b.guest_id = g.guest_id
            JOIN room r ON b.room_id = r.room_id
            WHERE upper(b.status) != 'CHECKED-OUT'
        """)
    bookings = cursor.fetchall() #After executing sql; fetch results
    cursor.close() #Close db connection
    return render_template('roomGuest.html', bookings=bookings, rooms=rooms,guests=guests, notifications=notifications,
        unread_count=unread_count) #Pass the contents of bookings to roomGuest.html

#Audit logs
@app.route('/auditlogs')
def view_auditlogs():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to the database
    
    cursor.execute("""
                   SELECT * FROM audit_log ORDER BY log_id DESC
                   """)
    logs = cursor.fetchall() #After executing sql, fetch results
    return render_template('auditlogs.html', logs=logs) #pass the contents of logs to auditlogs.html

#Called by ROOMS Menu; Add a new room
@app.route('/addRoom', methods=['POST'])
def add_rooms():
    
    #Get the values entered in Add Form
    roomNumber = request.form['room_number']
    roomType = request.form['room_type']
    roomStatus = request.form['room_status']
    last_update = session['username']
    timestamp = datetime.now()
        
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
        new_room_id = None   #change room_id
        cursor.execute(
            "INSERT INTO room (room_number, room_type, room_status, last_update, timestamp) VALUES (%s, %s, %s, %s, %s)",
            (roomNumber, roomType, roomStatus, last_update, timestamp)
        )
        new_room_id = cursor.lastrowid #Get the ID of the newly inserted record; change room_id
        mysql.connection.commit()  #Save to database
        
        #Get new data and save logs
        if new_room_id:  #change room_id
            new_data_for_log = {
                'room_number': roomNumber,  #change field names
                'room_type': roomType,
                'room_status': roomStatus,
                'room_id': new_room_id,
                'last_update': last_update,
                'timestamp': timestamp
            }
            log_audit_event(
                actor_id = session['username'],
                timestamp=timestamp,
                table_name='room',  #change 
                action_type='INSERT', 
                record_id=str(new_room_id),  #change
                old_data=None,           # Record did not exist, so old_data is None
                new_data=new_data_for_log 
            )
          
    except MySQLdb.IntegrityError: #Trap error; display if room number is duplicate
        flash("Room number already exists. Please enter a unique room number.", "danger")
    finally:
        cursor.close() #Close db connection
        flash('Room added successfully', 'success')
        return redirect('/rooms') 


#Called by ROOMS Menu - edit a room
@app.route('/updateRoom', methods=['POST'])
def updateRoom():
    
    #Get the values entered in the Edit Form
    room_id = int(request.form['edit_room_id'])
    room_number = request.form['edit_room_number']
    room_type = request.form['edit_room_type']
    room_status = request.form['edit_room_status']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    
    #Get old data
    cursor.execute("SELECT * FROM room WHERE room_id = %s", (room_id,)) #change table and field names
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Room not found", 404 #change message
    
    #Get new data 
    new_data = old_data.copy()
    new_data['room_id'] = room_id  #change ALL field names (should be similar to the table)
    new_data['room_number'] = room_number
    new_data['room_type'] = room_type
    new_data['room_status'] = room_status
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp
    
    cursor.execute(
        """
        UPDATE room
        SET room_number = %s, room_type = %s, room_status = %s, timestamp = %s, last_update= %s
        WHERE room_id = %s
        """,
        (room_number, room_type, room_status, timestamp, last_update, room_id)
    )
    mysql.connection.commit() #Save to db
    
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='room',  #change table name
        action_type='UPDATE', 
        record_id=str(room_id), #change field name
        old_data=old_data, 
        new_data=new_data 
    )
    
    cursor.close() #Close connection
    flash('Room updated successfully', 'success')
    return redirect('/rooms') #Return to rooms

#Called by ROOMS Menu - delete a room
@app.route('/deleteRoom/<int:room_id>', methods=['GET'])
def deleteRoom(room_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    
    #Get old data
    cursor.execute("SELECT * FROM room WHERE room_id =%s", (room_id,)) #change table and field name
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the room ID doesn't exist
        return "Room not found or already deleted", 404 #change message
    
    cursor.execute("DELETE FROM room WHERE room_id = %s", (room_id,)) #Execute
    
    #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='room',  #change
        action_type='DELETE', 
        record_id=str(room_id), #change
        old_data=old_data, 
        new_data=None 
    )
    mysql.connection.commit() #Save to db
    cursor.close() #Close connection
    flash('Room deleted successfully', 'success')
    return redirect('/rooms') #Return to rooms

#Called by ROOMS Menu - check if room exists in bookngs
@app.route('/checkRoomBooking/<int:room_id>')
def check_room_booking(room_id):
    cursor  = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE room_id = %s", (room_id,)) #Count how many room_id are there in bookings
    result = cursor.fetchone() #Fetch results
    cursor.close() #Close db connection
    return jsonify({"in_use": result['count'] > 0}) #Return to rooms; set "in_use" to TRUE if count > 0;  if in_use is true, it means that the room cannot be deleted

#Called by GUESTS Menu - add a new guest
@app.route('/addGuests', methods=['POST'])
def add_guests():
    
    #Get the values entered in Add Form
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']
    timestamp = datetime.now()
    last_update = session['username']
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  #Connect to db
    new_guest_id = None
    cursor.execute("""
        INSERT INTO guest (first_name, middle_name, last_name, email, phone, timestamp, last_update)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (first_name, middle_name, last_name, email, phone, timestamp, last_update))
    new_guest_id = cursor.lastrowid #Get the ID of the newly inserted record
    mysql.connection.commit() #Save to db
    
    #get new data and save logs
    if new_guest_id:
        new_data_for_log = {
            'guest_id': new_guest_id,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp  = timestamp,
            table_name='guest',
            action_type='INSERT',
            record_id=str(new_guest_id),
            old_data=None, # Record did not exist, so old_data is None
            new_data=new_data_for_log
        )
    cursor.close() #Close connection
    flash('Guest added successfully', 'success')
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
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
        
    #Get old data
    cursor.execute("SELECT * FROM guest WHERE guest_id = %s", (guest_id,))
    old_data = cursor.fetchone()

    if not old_data:
    # Handle error: record not found
        return "Guest not found", 404

    #Get new data
    new_data = old_data.copy()
    new_data['guest_id'] = guest_id
    new_data['first_name'] = first_name
    new_data['middle_name'] = middle_name
    new_data['last_name'] = last_name
    new_data['email'] = email
    new_data['phone'] = phone
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp
    
    cursor.execute("""
        UPDATE guest 
        SET first_name = %s, middle_name = %s, last_name = %s, email = %s, phone = %s , timestamp =%s, last_update =%s
        WHERE guest_id = %s
        """, (first_name, middle_name, last_name, email, phone, timestamp, last_update, guest_id))
        
    log_audit_event(
        actor_id = session['username'],
        timestamp  = timestamp,
        table_name='guest',
        action_type='UPDATE',
        record_id=str(guest_id),
        old_data=old_data,
        new_data=new_data
    )

    mysql.connection.commit() #Save to db
    cursor.close() #Close connection
    flash('Guest updated successfully', 'success')
    return redirect('/guests')

@app.route('/addRequest', methods=['POST'])
def add_request():
    booking_id = request.form['booking_id']
    service_id = request.form.get('service_id')
    item_id = request.form.get('item_id')
    quantity = int(request.form['quantity'])
    status = request.form['status']
    request_time = datetime.strptime(request.form['request_time'], '%Y-%m-%dT%H:%M')
    unit_cost = float(request.form['unit_cost'])
    total_cost = quantity * unit_cost
    notes = request.form['notes']
    status = request.form['status']
    last_update = session['username']
    timestamp = datetime.now()

      # Get the name value and parse it
    name_value = request.form.get('name')  # e.g., "service_11" or "food_5"

    service_id = None
    item_id = None
   
    if name_value:
            if name_value.startswith('service_'):
                service_id = name_value.replace('service_', '')
                item_id = None
            elif name_value.startswith('food_'):
                item_id = name_value.replace('food_', '')
                service_id = None

    # pull guest_id from bookings
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT b.guest_id, r.room_number FROM bookings b JOIN room r ON b.room_id = r.room_id WHERE booking_id = %s", (booking_id,))
    row = cursor.fetchone()
    guest_id = row['guest_id'] if row else None
    room_number = row['room_number'] if row else None

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_request_id = None #change 
    
    cursor.execute("""
    INSERT INTO requests (booking_id, guest_id, service_id, item_id, quantity, unit_cost, total_cost, status, request_time, room_number, notes, last_update, timestamp)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (booking_id, guest_id, service_id, item_id, quantity, unit_cost, total_cost, status, request_time, room_number, notes, last_update, timestamp))
    new_request_id = cursor.lastrowid #Get the ID of the newly inserted record; change room_id
    mysql.connection.commit()
    
    #Get new data and save logs
    if new_request_id:  #change room_id
        new_data_for_log = {
            'request_id': new_request_id,
            'booking_id': booking_id,  #change field names
            'guest_id': guest_id,
            'service_id': service_id,
            'item_id': item_id,
            'quantity': quantity,
            'unit_cost': unit_cost,
            'total_cost': total_cost,
            'status': status,
            'request_time': request_time,
            'room_number': room_number,
            'notes': notes,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='requests',  #change 
            action_type='INSERT', 
            record_id=str(new_request_id),  #change
            old_data=None,           # Record did not exist, so old_data is None
            new_data=new_data_for_log 
        )
    cursor.close()
    flash('Request added successfully', 'success')
    return redirect('/requests')

from datetime import datetime
from flask import request, redirect

@app.route('/updateRequest', methods=['POST'])
def update_request():
    request_id = request.form.get('edit_request_id')
    booking_id = request.form.get('edit_booking_id')
    service_id = request.form.get('edit_service_id') or None
    item_id = request.form.get('edit_item_id') or None
    quantity = int(request.form.get('edit_quantity'))
    status = request.form.get('edit_status')
    request_time = datetime.strptime(request.form['edit_request_time'], '%Y-%m-%dT%H:%M')
    unit_cost = float(request.form['edit_unit_cost'])
    total_cost = quantity * unit_cost
    notes = request.form['edit_notes']
    last_update = session['username']
    timestamp = datetime.now()
    read_status = 0

      # Get the name value and parse it
    name_value = request.form.get('edit_name')  # e.g., "service_11" or "food_5"

    service_id = None
    item_id = None
   
    if name_value:
            if name_value.startswith('service_'):
                service_id = name_value.replace('service_', '')
                item_id = None
            elif name_value.startswith('food_'):
                item_id = name_value.replace('food_', '')
                service_id = None

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    #Get old data
    cursor.execute("SELECT * FROM requests WHERE request_id = %s", (request_id,)) #change table and field names
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Request not found", 404 #change message
    
    #Get new data 
    new_data = old_data.copy()
    new_data['request_id'] = request_id  #change ALL field names (should be similar to the table)
    new_data['booking_id'] = booking_id
    new_data['service_id'] = service_id
    new_data['item_id'] = item_id
    new_data['quantity'] = quantity
    new_data['status'] = status
    new_data['request_time'] = request_time
    new_data['unit_cost'] = unit_cost
    new_data['total_cost'] = total_cost
    new_data['notes'] = notes
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp
    new_data['read_status'] = 0

    cursor.execute("""
    UPDATE requests
    SET booking_id = %s,
        service_id = %s,
        item_id = %s,
        quantity = %s,
        unit_cost = %s,
        total_cost = %s,
        status = %s,
        request_time = %s,
        notes = %s,
        last_update = %s,
        timestamp = %s,
        read_status = %s
    WHERE request_id = %s
""", (booking_id, service_id, item_id, quantity, unit_cost, total_cost, status, request_time, notes, last_update, timestamp, read_status, request_id))

    mysql.connection.commit()
    
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='requests',  #change table name
        action_type='UPDATE', 
        record_id=str(request_id), #change field name
        old_data=old_data, 
        new_data=new_data 
    )
    cursor.close()
    flash('Request updated successfully', 'success')
    return redirect('/requests')

@app.route('/deleteRequest/<int:request_id>', methods=['GET'])
def deleteRequest(request_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #Delete assignments first
    #cursor.execute("DELETE FROM StaffAssignments WHERE request_id = %s", (request_id,))
    #Then delete the request
    #Get old data
    cursor.execute("SELECT * FROM requests WHERE request_id =%s", (request_id,)) #change table and field name
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the room ID doesn't exist
        return "Request not found or already deleted", 404 #change message
    
    
    cursor.execute("DELETE FROM requests WHERE request_id = %s", (request_id,))
    
    #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='requests',  #change
        action_type='DELETE', 
        record_id=str(request_id), #change
        old_data=old_data, 
        new_data=None 
    )
    
    mysql.connection.commit()
    cursor.close()
    flash('Request deleted successfully', 'success')
    return redirect('/requests')

@app.route('/completedRequest', methods=['POST'])
def completed_request():
    request_id = request.form.get('completed_request_id')
    status = "completed"
    completion_time = datetime.strptime(request.form['completion_time'], '%Y-%m-%dT%H:%M')
    last_update = session['username']
    timestamp = datetime.now()
  
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    #Get old data
    cursor.execute("SELECT * FROM requests WHERE request_id = %s", (request_id,)) #change table and field names
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Request not found", 404 #change message
    
    #Get new data 
    new_data = old_data.copy()
    new_data['request_id'] = request_id  #change ALL field names (should be similar to the table)
    new_data['completion_time'] = completion_time
    new_data['status'] = status
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp

    cursor.execute("""
    UPDATE requests
    SET status = %s,
        completion_time = %s,
        last_update = %s,
        timestamp = %s
    WHERE request_id = %s
    """, (status, completion_time, last_update, timestamp, request_id))

    mysql.connection.commit()
    
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='requests',  #change table name
        action_type='UPDATE (Set Completion Date)', 
        record_id=str(request_id), #change field name
        old_data={},
        new_data={'Completion Date': completion_time.isoformat()}
    )
    cursor.close()

    return redirect('/requests')

#Called by HOUSEKEEPING Menu - display list of housekeeping
@app.route('/housekeeping')
def view_housekeeping():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Connect to DB

    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    # Fetch housekeeping services
    cursor.execute("""
        SELECT *
        FROM hotel_services
        WHERE category = 'Housekeeping'
        ORDER BY name
    """)
    hotel_services = cursor.fetchall()

    # ==========================
    # Fetch Housekeeping Stats
    # ==========================
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_requests,
            SUM(CASE WHEN upper(r.status) = 'PENDING' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN upper(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE service_id IN (
            SELECT service_id FROM hotel_services WHERE category = 'Housekeeping'
        ) AND LOWER(b.status) = 'checked-in'
    """)
    housekeeping_stats = cursor.fetchone()

    # Provide fallback values to avoid errors
    if not housekeeping_stats:
        housekeeping_stats = {
            'total_requests': 0,
            'pending': 0,
            'completed': 0
        }

    cursor.close()

    # Render housekeeping page with stats
    return render_template(
        'housekeeping.html',
        hotel_services=hotel_services,
        housekeeping_stats=housekeeping_stats, notifications=notifications,
        unread_count=unread_count
    )

#Called by LAUNDRY Menu - display list of laundry
@app.route('/laundry')
def view_laundry():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()

    # --- Fetch laundry services ---
    cursor.execute("""
        SELECT *
        FROM hotel_services
        WHERE category = 'Laundry'
        ORDER BY name
    """)
    laundry_services = cursor.fetchall()
    total_services = len(laundry_services)

    # --- Fetch laundry statistics (for summary cards) ---
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_requests,
            SUM(CASE WHEN UPPER(r.status) = 'PENDING' THEN 1 ELSE 0 END) AS pending_requests,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_requests
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE service_id IN (
            SELECT service_id FROM hotel_services WHERE category = 'Laundry'
        ) AND lower(b.status)= 'checked-in'
    """)
    laundry_stats = cursor.fetchone() or {}

    laundry_stats = {
        'total_requests': laundry_stats.get('total_requests', 0),
        'pending_requests': laundry_stats.get('pending_requests', 0),
        'completed_requests': laundry_stats.get('completed_requests', 0)
    }

    cursor.close()

    return render_template(
        'laundry.html',
        laundry_services=laundry_services,
        laundry_stats=laundry_stats,
        total_services=total_services, notifications=notifications,
        unread_count=unread_count
    )

#Called by DINING Menu - display list of dining
@app.route('/dining')
def view_dining():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()

    # Retrieve dining items
    cursor.execute("""
        SELECT item_id, name, description, price, category, type, last_update, timestamp
        FROM food_items
        WHERE type = 'food'
        ORDER BY name
    """)
    dining_services = cursor.fetchall()
    total_items = len(dining_services)

    # Retrieve dining request statistics
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_requests,
            SUM(CASE WHEN UPPER(r.status) = 'PENDING' THEN 1 ELSE 0 END) AS pending_requests,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_requests
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE item_id IN (
            SELECT item_id FROM food_items WHERE type = 'food'
        ) AND lower(b.status) = 'checked-in'
    """)
    dining_stats = cursor.fetchone() or {}

    dining_stats = {
        'total_requests': dining_stats.get('total_requests', 0),
        'pending_requests': dining_stats.get('pending_requests', 0),
        'completed_requests': dining_stats.get('completed_requests', 0)
    }

    cursor.close()

    return render_template(
        'dining.html',
        dining_services=dining_services,
        dining_stats=dining_stats,
        total_items=total_items,
        notifications=notifications,
        unread_count=unread_count
    )

#Called by MASSAGE Menu - display list of massage
@app.route('/massage')
def view_massage():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT log_id, timestamp,
            CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
            read_status
        FROM audit_log
        WHERE read_status = 0
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()

    # ==============================
    # 1. Query for massage services
    # ==============================
    cursor.execute("""
        SELECT *
        FROM hotel_services
        WHERE category = 'Massage'
        ORDER BY name
    """)
    massage_services = cursor.fetchall()

    total_services = len(massage_services)

    # ==============================
    # 2. Get Spa/Massage request stats
    # ==============================
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_requests,
            SUM(CASE WHEN UPPER(r.status) = 'PENDING' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN UPPER(r.status) = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
        FROM requests r
        JOIN bookings b ON b.booking_id = r.booking_id
        WHERE service_id IN (
            SELECT service_id 
            FROM hotel_services 
            WHERE category = 'Massage'
        ) AND lower(b.status) = 'checked-in'
    """)
    spa_stats = cursor.fetchone() or {}

    # Ensure default values if no data
    spa_stats = {
        'total_requests': spa_stats.get('total_requests', 0),
        'pending': spa_stats.get('pending', 0),
        'completed': spa_stats.get('completed', 0)
    }

    cursor.close()

    # Return consistent variable names for your template
    return render_template(
        'massage.html',
        massage_services=massage_services,
        total_services=total_services,
        spa_stats=spa_stats, notifications=notifications,
        unread_count=unread_count
    )

#Called by HOUSEKEEPING Menu - add new housekeeping
@app.route('/addHousekeeping', methods=['POST'])
def add_housekeeping():
    
    #Get the values entered in Add Form
    category = request.form['category']
    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    type = request.form['type']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_service_id = None
    cursor.execute(
        "INSERT INTO hotel_services (category, name, description, price, type, last_update, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (category, name, description, price, type, last_update, timestamp)
    )    
    new_service_id = cursor.lastrowid #Get the ID of the newly inserted record
    
    #Get new data and save logs
    if new_service_id:
        new_data_for_log = {
            'service_id': new_service_id,
            'category': category,
            'name': name,
            'description': description,
            'price': price,
            'type': type,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='hotel_services', 
            action_type='INSERT', 
            record_id=str(new_service_id), 
            old_data=None,           # Record did not exist, so old_data is None
            new_data=new_data_for_log 
        )
            
    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection
    flash('Housekeeping service added successfully', 'success')
    return redirect('/housekeeping')

#Called by DINING Menu - add new dining
@app.route('/addDining', methods=['POST'])
def add_dining():
    category = request.form['category']
    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    type = request.form['type']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_item_id = None

    cursor.execute(
        "INSERT INTO food_items (category, name, description, price, type, last_update, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (category, name, description, price, type, last_update, timestamp)
    )
    new_item_id = cursor.lastrowid
    mysql.connection.commit()

    if new_item_id:
        new_data_for_log = {
            'item_id': new_item_id,
            'category': category,
            'name': name,
            'description': description,
            'price': price,
            'type': type,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='food_items',
            action_type='INSERT',
            record_id=str(new_item_id),
            old_data=None,
            new_data=new_data_for_log
        )

    cursor.close()
    # use a dining-specific flash category and redirect to the dining view
    flash('Dining item added successfully', 'dining')
    return redirect('/dining')   # <-- use the actual view function name for /dining

#Called by LAUNDRY Menu - add new laundry
@app.route('/addLaundry', methods=['POST'])
def add_laundry():
    
    #Get the values entered in Add Form
    category = request.form['category']
    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    type = request.form['type']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_service_id = None
    cursor.execute(
        "INSERT INTO hotel_services (category, name, description, price, type, last_update, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (category, name, description, price, type, last_update, timestamp)
    )    
    new_service_id = cursor.lastrowid #Get the ID of the newly inserted record
    
    #Get new data and save logs
    if new_service_id:
        new_data_for_log = {
            'category': category,
            'name': name,
            'description': description,
            'price': price,
            'type': type,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='hotel_services', 
            action_type='INSERT', 
            record_id=str(new_service_id), 
            old_data=None,           # Record did not exist, so old_data is None
            new_data=new_data_for_log 
        )
    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection
    flash('Laundry service added successfully', 'success')
    return redirect('/laundry')

# #Called by MASSAGE Menu - add new massage
@app.route('/addMassage', methods=['POST'])
def add_massage():
    
    #Get the values entered in Add Form
    category = request.form['category']
    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    type = request.form['type']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_service_id = None #change 
    cursor.execute(
        "INSERT INTO hotel_services (category, name, description, price, type, last_update, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (category, name, description, price, type, last_update, timestamp)
    )    
    new_service_id = cursor.lastrowid #Get the ID of the newly inserted record; change room_id
    mysql.connection.commit() #Save to db
    #Get new data and save logs
    if new_service_id:  #change room_id
        new_data_for_log = {
            'service_id': new_service_id,
            'category': category,  #change field names
            'name': name,
            'description': description,
            'price': price,
            'type': type,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='hotel_services',  #change 
            action_type='INSERT', 
            record_id=str(new_service_id),  #change
            old_data=None,           # Record did not exist, so old_data is None
            new_data=new_data_for_log 
        )
    cursor.close() #Close db connection
    flash('Massage service added successfully', 'success')
    return redirect('/massage')

#Called by HOUSEKEEPING Menu - edit a housekeeping
@app.route('/updateHousekeeping', methods=['POST'])
def updateHousekeeping():
    
    #Get the values entered in the Edit Form
    service_id = int(request.form['service_id'])
    category = request.form['edit_category']
    name = request.form['edit_name']
    description = request.form['edit_description']
    type = request.form['edit_type']
    price = float(request.form['edit_price'])
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    
    #Get old data
    cursor.execute("SELECT * FROM hotel_services WHERE service_id = %s", (service_id,))
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Service not found", 404
    
    #Get new data 
    new_data = old_data.copy()
    new_data['service_id'] = service_id
    new_data['category'] = category
    new_data['name'] = name
    new_data['description'] = description
    new_data['type'] = type
    new_data['price'] = price
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp
    
    cursor.execute(
        """
        UPDATE hotel_services
        SET category = %s, name = %s, price = %s, description =%s, type =%s, last_update=%s, timestamp=%s
        WHERE service_id = %s
        """,
        (category, name, price, description, type, last_update, timestamp, service_id)
    )
        
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='hotel_services', 
        action_type='UPDATE', 
        record_id=str(service_id), 
        old_data=old_data, 
        new_data=new_data 
    )

    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection
    flash('Housekeeping item edited successfully', 'housekeeping')
    return redirect('/housekeeping')

#Called by DINING Menu - edit a dining
@app.route('/updateDining', methods=['POST'])
def updateDining():
    item_id = int(request.form['item_id'])
    category = request.form['edit_category']
    name = request.form['edit_name']
    description = request.form['edit_description']
    type = request.form['edit_type']
    price = float(request.form['edit_price'])
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM food_items WHERE item_id = %s", (item_id,))
    old_data = cursor.fetchone()
    if not old_data:
        cursor.close()
        return "Food not found", 404

    new_data = old_data.copy()
    new_data.update({'item_id': item_id, 'category': category, 'name': name, 'description': description, 'type': type, 'price': price, 'last_update': last_update, 'timestamp': timestamp})

    cursor.execute(
        """
        UPDATE food_items
        SET category = %s, name = %s, description = %s, type = %s, price = %s, last_update = %s, timestamp = %s
        WHERE item_id = %s
        """,
        (category, name, description, type, price, last_update, timestamp, item_id)
    )

    log_audit_event(
        actor_id = session['username'],
        timestamp = timestamp,
        table_name='food_items',
        action_type='UPDATE',
        record_id=str(item_id),
        old_data=old_data,
        new_data=new_data
    )

    mysql.connection.commit()
    cursor.close()
    # use a dining-specific flash category and redirect to the dining view
    flash('Dining item updated successfully', 'dining')
    return redirect('/dining')   # <-- use the actual view function name for /dining

#Called by LAUNDRY Menu - edit a service
@app.route('/updateLaundry', methods=['POST'])
def updateLaundry():
    
    #Get the values entered in the Edit Form
    service_id = int(request.form['service_id'])
    category = request.form['edit_category']
    name = request.form['edit_name']
    description = request.form['edit_description']
    type = request.form['edit_type']
    price = float(request.form['edit_price'])
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    
    #Get old data
    cursor.execute("SELECT * FROM hotel_services WHERE service_id = %s", (service_id,))
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Service not found", 404
    
    #Get new data 
    new_data = old_data.copy()
    new_data['service_id'] = service_id
    new_data['category'] = category
    new_data['name'] = name
    new_data['description'] = description
    new_data['type'] = type
    new_data['price'] = price
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp
    
    cursor.execute(
        """
        UPDATE hotel_services
        SET category = %s, name = %s, price = %s, description =%s, type =%s, last_update=%s, timestamp=%s
        WHERE service_id = %s
        """,
        (category, name, price, description, type, last_update, timestamp, service_id)
    )
    
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='hotel_services', 
        action_type='UPDATE', 
        record_id=str(service_id), 
        old_data=old_data, 
        new_data=new_data 
    )

    mysql.connection.commit() #Save to db
    cursor.close() #Close db connection
    flash('Laundry item updated successfully', 'laundry')
    return redirect('/laundry')

#Called by MASSAGE Menu - edit a massage
@app.route('/updateMassage', methods=['GET', 'POST'])
def updateMassage():
    
    #Get the values entered in Edit Form
    service_id = int(request.form['service_id'])
    category = request.form['edit_category']
    name = request.form['edit_name']
    description = request.form['edit_description']
    price = float(request.form['edit_price'])
    type = request.form['edit_type']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    #Get old data
    cursor.execute("SELECT * FROM hotel_services WHERE service_id = %s", (service_id,))
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Massage not found", 404
    
    #Get new data 
    new_data = old_data.copy()
    new_data['service_id'] = service_id
    new_data['category'] = category
    new_data['name'] = name
    new_data['description'] = description
    new_data['type'] = type
    new_data['price'] = price
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp

    cursor.execute(
        """
        UPDATE hotel_services
        SET category = %s, name = %s, description = %s, price =%s, type =%s, last_update=%s, timestamp=%s
        WHERE service_id = %s
        """,
        (category, name, description, price, type, last_update, timestamp, service_id)
    )
    mysql.connection.commit() #Save to db
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='hotel_services',  #change table name
        action_type='UPDATE', 
        record_id=str(service_id), #change field name
        old_data=old_data, 
        new_data=new_data 
    )
    
    cursor.close() #Close db connection
    flash('Massage item updated successfully', 'massage')
    return redirect('/massage')

#Called by HOUSEKEEPING Menu - delete a housekeeping
@app.route('/deleteHousekeeping/<int:service_id>', methods=['GET'])
def deleteHousekeeping(service_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    #Get old data
    cursor.execute("SELECT * FROM hotel_services WHERE service_id =%s", (service_id,))
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the service ID doesn't exist
        return "Housekeeping service not found or already deleted", 404
    
    cursor.execute("DELETE FROM hotel_services WHERE service_id = %s", (service_id,))
    
    #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='hotel_services', 
        action_type='DELETE', 
        record_id=str(service_id), 
        old_data=old_data, 
        new_data=None 
    )

    mysql.connection.commit()
    cursor.close()
    flash('Housekeeping service deleted successfully', 'success')
    return redirect('/housekeeping')

#Called by DINING Menu - delete a dining
@app.route('/deleteDining/<int:item_id>', methods=['GET'])
def deleteDining(item_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM food_items WHERE item_id = %s", (item_id,))
    old_data = cursor.fetchone()
    timestamp = datetime.now()

    if not old_data:
        cursor.close()
        return "In room dining service not found or already deleted", 404

    cursor.execute("DELETE FROM food_items WHERE item_id = %s", (item_id,))

    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='food_items',
        action_type='DELETE',
        record_id=str(item_id),
        old_data=old_data,
        new_data=None
    )

    mysql.connection.commit()
    cursor.close()
    # use a dining-specific flash category and redirect to the dining view
    flash('Dining item deleted successfully', 'dining')
    return redirect('/dining')   # <-- use the actual view function name for /dining

#Called by LAUNDRY Menu - delete a laundry
@app.route('/deleteLaundry/<int:service_id>', methods=['GET'])
def deleteLaundry(service_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    #Get old data
    cursor.execute("SELECT * FROM hotel_services WHERE service_id =%s", (service_id,))
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the service ID doesn't exist
        return "Housekeeping service not found or already deleted", 404
    
    cursor.execute("DELETE FROM hotel_services WHERE service_id = %s", (service_id,))
    
    #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='hotel_services', 
        action_type='DELETE', 
        record_id=str(service_id), 
        old_data=old_data, 
        new_data=None 
    )

    mysql.connection.commit()
    cursor.close()
    flash('Laundry service deleted successfully', 'success')
    return redirect('/laundry')

#Called by MASSAGE Menu - delete a massage
@app.route('/deleteMassage/<int:service_id>', methods=['GET'])
def deleteMassage(service_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #Get old data
    cursor.execute("SELECT * FROM hotel_services WHERE service_id =%s", (service_id,)) #change table and field name
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the room ID doesn't exist
        return "Massage not found or already deleted", 404 #change message
    cursor.execute("DELETE FROM hotel_services WHERE service_id = %s", (service_id,))
    #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='hotel_services',  #change
        action_type='DELETE', 
        record_id=str(service_id), #change
        old_data=old_data, 
        new_data=None 
    )
    mysql.connection.commit()
    cursor.close()
    flash('Massage service deleted successfully', 'success')
    return redirect('/massage')

#Called by STAFF Menu - add a new staff
@app.route('/addStaff', methods=['POST'])
def add_staff():
    
    #Get the values entered in the Add Form
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    role = request.form['role']
    email = request.form['email']
    phone = request.form['phone']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to db
    new_staff_id = None #change room_id    
    cursor.execute(
        "INSERT INTO staff (first_name, last_name, role, email, phone, last_update, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (first_name, last_name, role, email, phone, last_update, timestamp)
    )
    new_staff_id = cursor.lastrowid #Get the ID of the newly inserted record; change room_id
    mysql.connection.commit() #Save to db
    #Get new data and save logs
    if new_staff_id:  #change room_id
        new_data_for_log = {
            'staff_id': new_staff_id,
            'first_name': first_name,  #change field names
            'last_name': last_name,
            'role': role,
            'email': email,
            'phone': phone,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='staff',  #change 
            action_type='INSERT', 
            record_id=str(new_staff_id),  #change
            old_data=None,           # Record did not exist, so old_data is None
            new_data=new_data_for_log 
        )
    
    cursor.close() #Close db connection
    flash('Staff added successfully', 'success')
    return redirect('/staff')

#Called by STAFF Menu - edit a staff
@app.route('/updateStaff', methods=['POST'])
def updateStaff():
    staff_id = int(request.form['edit_staff_id'])
    first_name = request.form['edit_first_name'].strip()
    last_name = request.form['edit_last_name'].strip()
    role = request.form['edit_role'].strip()
    email = request.form['edit_email'].strip()
    phone = request.form['edit_phone'].strip()
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # --- 1. Fetch staff record ---
    cursor.execute("SELECT * FROM staff WHERE staff_id = %s", (staff_id,))
    staff_data = cursor.fetchone()

    # --- 1a. If staff record doesn't exist, create it ---
    if not staff_data:
        # Try to fetch from users table first
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (staff_id,))
        user_data = cursor.fetchone()

        staff_insert_first_name = first_name or (user_data['first_name'] if user_data else '')
        staff_insert_last_name = last_name or (user_data['last_name'] if user_data else '')
        staff_insert_role = role or (user_data['role'] if user_data else 'staff')
        staff_insert_email = email or (user_data['email'] if user_data else '')
        staff_insert_phone = phone or ''

        cursor.execute("""
            INSERT INTO staff (staff_id, first_name, last_name, role, email, phone, last_update, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            staff_id, staff_insert_first_name, staff_insert_last_name, staff_insert_role,
            staff_insert_email, staff_insert_phone, last_update, timestamp
        ))
        mysql.connection.commit()

        cursor.execute("SELECT * FROM staff WHERE staff_id = %s", (staff_id,))
        staff_data = cursor.fetchone()

    old_staff_data = staff_data.copy()

    # --- 2. Update staff table ---
    cursor.execute("""
        UPDATE staff
        SET first_name=%s, last_name=%s, role=%s, email=%s, phone=%s, last_update=%s, timestamp=%s
        WHERE staff_id=%s
    """, (first_name, last_name, role, email, phone, last_update, timestamp, staff_id))

    # --- 3. Sync with users table ---
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (staff_id,))
    user_data = cursor.fetchone()

    middle_name = ''  # default
    account_status = 'active'  # default
    new_name = f"{first_name} {middle_name} {last_name}".strip()
    username = first_name.lower()

    # Ensure unique username
    cursor.execute("SELECT * FROM users WHERE username = %s AND user_id != %s", (username, staff_id))
    if cursor.fetchone():
        username = f"{username}{staff_id}"

    if user_data:
        old_user_data = user_data.copy()
        # Update existing user
        cursor.execute("""
            UPDATE users
            SET username=%s, first_name=%s, middle_name=%s, last_name=%s, name=%s,
                email=%s, role=%s, last_update=%s, timestamp=%s, account_status=%s
            WHERE user_id=%s
        """, (username, first_name, middle_name, last_name, new_name, email, role, last_update, timestamp, account_status, staff_id))

        # Audit log for users table
        log_audit_event(
            actor_id=session['username'],
            timestamp=timestamp,
            table_name='users',
            action_type='UPDATE',
            record_id=str(staff_id),
            old_data=old_user_data,
            new_data={
                **old_user_data,
                'username': username,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'name': new_name,
                'email': email,
                'role': role,
                'last_update': last_update,
                'timestamp': timestamp,
                'account_status': account_status
            }
        )
    else:
        # Insert new user if missing
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, middle_name, last_name, name, email, role, status, account_status, last_update, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (staff_id, username, first_name, middle_name, last_name, new_name, email, role, 1, account_status, last_update, timestamp))

        log_audit_event(
            actor_id=session['username'],
            timestamp=timestamp,
            table_name='users',
            action_type='INSERT',
            record_id=str(staff_id),
            old_data=None,
            new_data={
                'user_id': staff_id,
                'username': username,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'name': new_name,
                'email': email,
                'role': role,
                'status': 1,
                'account_status': account_status,
                'last_update': last_update,
                'timestamp': timestamp
            }
        )

    # --- 4. Commit all changes ---
    mysql.connection.commit()

    # --- 5. Audit log for staff ---
    new_staff_data = {
        **old_staff_data,
        'first_name': first_name,
        'last_name': last_name,
        'role': role,
        'email': email,
        'phone': phone,
        'last_update': last_update,
        'timestamp': timestamp
    }
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='staff',
        action_type='UPDATE',
        record_id=str(staff_id),
        old_data=old_staff_data,
        new_data=new_staff_data
    )

    cursor.close()
    flash("✅ Staff updated successfully and synced with user record.", "success")
    return redirect('/staff')

#Called by STAFF Menu - delete a staff
@app.route('/deleteStaff/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    staff_type = request.args.get('type', 'staff_table')
    cursor = mysql.connection.cursor()

    try:
        if staff_type == 'users_table':
            cursor.execute("DELETE FROM users WHERE user_id=%s AND role='staff'", (staff_id,))
        else:
            cursor.execute("DELETE FROM staff WHERE staff_id=%s", (staff_id,))
        
        mysql.connection.commit()
        flash("Staff deleted successfully.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting staff: {str(e)}", "danger")
    finally:
        cursor.close()

    return redirect(url_for('view_staffs'))

#Called by SERVICES Menu - check if service exist in requests
@app.route('/checkServices/<int:service_id>')
def check_services(service_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS count FROM requests WHERE service_id = %s", (service_id,)) #Count how many service id in requests
    result = cursor.fetchone()
    cursor.close()
    return jsonify({"in_use": result['count'] > 0}) #Return to services; set "in_use" to true if count> 0

@app.route('/addRoomGuest', methods=['POST'])
def add_room_guest():
    room_id = request.form['room_id']
    guest_id = request.form['guest_id']
    checkin_date = request.form['checkin_date']
    checkout_date = request.form['checkout_date']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO roomguest (room_id, guest_id, checkin_date, checkout_date) VALUES (%s, %s, %s, %s)",
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
    
    #Get old data
    cursor.execute("SELECT * FROM guest WHERE guest_id =%s", (guest_id,)) #change table and field name
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the room ID doesn't exist
        return "Guest not found or already deleted", 404 #change message
    
    cursor.execute("DELETE FROM guest WHERE guest_id = %s", (guest_id,)) #Execute
    
    #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='guest',  #change
        action_type='DELETE', 
        record_id=str(guest_id), #change
        old_data=old_data, 
        new_data=None 
    )

    mysql.connection.commit() #Save to db
    cursor.close() #Close connection
    flash('Guest deleted successfully', 'success')
    return redirect('/guests') #Return to rooms

#Called by BOOKINGS Menu - display bookings
@app.route('/bookings')
def view_bookings():
    selected_type = request.args.get('room_type', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT log_id, timestamp,
            CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
            read_status
        FROM audit_log
        WHERE read_status = 0
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    cursor.execute("SELECT * FROM guest")
    guests = cursor.fetchall()

    if selected_type:
        cursor.execute("SELECT * FROM room WHERE room_type = %s", (selected_type,))
    else:
        cursor.execute("SELECT * FROM room")
    rooms = cursor.fetchall()

    cursor.execute("""
        SELECT 
            b.*, 
            g.first_name AS first_name,
            g.last_name AS last_name,
            r.room_number AS room_number,
            COALESCE(SUM(p.amount), 0) AS total_payment,
            IFNULL(MAX(p.status), 'Pending') AS payment_status
        FROM bookings b
        JOIN guest g ON b.guest_id = g.guest_id
        JOIN room r ON b.room_id = r.room_id
        LEFT JOIN payment p ON b.booking_id = p.booking_id
        GROUP BY b.booking_id
    """)
    bookings = cursor.fetchall()

    cursor.close()

    return render_template('bookings.html', bookings=bookings, guests=guests, rooms=rooms, selected_type=selected_type, notifications=notifications,
        unread_count=unread_count)

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
    last_update = session['username']
    timestamp = datetime.now()

    #Validate dates before inserting
    if not exp_check_in or not exp_check_out:
        flash("Check-in and check-out dates are required.", "danger")
        return redirect('/bookings')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_booking_id = None #change 
    while True:
        random_booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        cursor.execute("SELECT * FROM bookings WHERE random_booking_ref=%s", (random_booking_ref,))
        if not cursor.fetchone(): #Still checking if any row exists
            break
    cursor.execute("""
        INSERT INTO bookings (guest_id, room_type, room_id, exp_check_in, exp_check_out, status, random_booking_ref, last_update, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (guest_id, room_type, room_id, exp_check_in, exp_check_out, status, random_booking_ref, last_update, timestamp))
    new_booking_id = cursor.lastrowid #Get the ID of the newly inserted record; change room_id
    mysql.connection.commit()
    
    #Get new data and save logs
    if new_booking_id:  #change room_id
        new_data_for_log = {
            'booking_id': new_booking_id,  #change field names
            'guest_id': guest_id,
            'room_type': room_type,
            'room_id': room_id,
            'exp_check_in': exp_check_in,
            'exp_check_out': exp_check_out,
            'random_booking_ref': random_booking_ref,
            'status': status,
            'last_update': last_update,
            'timestamp': timestamp
        }
        log_audit_event(
            actor_id = session['username'],
            timestamp=timestamp,
            table_name='bookings',  #change 
            action_type='INSERT', 
            record_id=str(new_booking_id),  #change
            old_data=None,           # Record did not exist, so old_data is None
            new_data=new_data_for_log 
        )
    cursor.close()
    flash('Booking added successfully', 'success')
    return redirect('/bookings', notifications=notifications,
        unread_count=unread_count)

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
    last_update = session['username']
    timestamp = datetime.now()


    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    #Get old data
    cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,)) #change table and field names
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "Booking not found", 404 #change message
    
    #Get new data 
    new_data = old_data.copy()
    new_data['booking_id'] = booking_id  #change ALL field names (should be similar to the table)
    new_data['guest_id'] = guest_id
    new_data['room_type'] = room_type
    new_data['room_id'] = room_id
    new_data['exp_check_in'] = exp_check_in
    new_data['exp_check_out'] = exp_check_out
    new_data['status'] = status
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp

    cursor.execute("""
        UPDATE bookings
        SET guest_id=%s, room_type=%s, room_id=%s, exp_check_in=%s, exp_check_out=%s, status=%s, last_update=%s, timestamp=%s
        WHERE booking_id=%s
    """, (guest_id, room_type, room_id, exp_check_in, exp_check_out, status, last_update, timestamp, booking_id))
    mysql.connection.commit()
    
    #Save logs
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='bookings',  #change table name
        action_type='UPDATE', 
        record_id=str(booking_id), #change field name
        old_data=old_data, 
        new_data=new_data 
    )

    cursor.close()
    flash('Booking updated successfully', 'success')
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
    
    #Get old data
    cursor.execute("SELECT * FROM bookings WHERE booking_id =%s", (booking_id,)) #change table and field name
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        #Handle case where the booking ID doesn't exist
        return "Booking not found or already deleted", 404 #change message

    cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
    
      #Save logs
    log_audit_event(
        actor_id = session['username'],
        timestamp=timestamp,
        table_name='bookings',  #change
        action_type='DELETE', 
        record_id=str(booking_id), #change
        old_data=old_data, 
        new_data=None 
    )

    mysql.connection.commit()
    cursor.close()
    flash('Booking deleted successfully', 'success')
    return redirect(url_for('view_bookings'))

#Route for Check-in/Check-out
@app.route('/checkin', methods=['POST'])
def checkin():
    booking_id = request.form['booking_id']
    actual_check_in = request.form['actual_check_in']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Get old data
    cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
    old_data = cursor.fetchone()
    if not old_data:
        cursor.close()
        return "Booking not found", 404

    # 2. Prepare new data
    new_data = old_data.copy()
    new_data['actual_check_in'] = actual_check_in
    new_data['status'] = 'Checked-in'
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp

    # 3. Update booking
    cursor.execute("""
        UPDATE bookings
        SET actual_check_in = %s, status = 'Checked-in', last_update = %s, timestamp = %s
        WHERE booking_id = %s
    """, (actual_check_in, last_update, timestamp, booking_id))

    # 4. Update room status to 'Occupied'
    cursor.execute("SELECT room_id FROM bookings WHERE booking_id = %s", (booking_id,))
    room = cursor.fetchone()
    if room:
        cursor.execute("UPDATE room SET room_status = 'Occupied' WHERE room_id = %s", (room['room_id'],))
    else:
        cursor.close()
        return "Room not found", 404

    mysql.connection.commit()

    # 5. Save audit log
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='bookings',
        action_type='UPDATE (Set Checkin Date)',
        record_id=str(booking_id),
        old_data=old_data,
        new_data=new_data
    )

    cursor.close()
    flash('Check-in successful.', 'success')
    return redirect('/roomGuest')


# ---------------------------
# CHECK-OUT MANAGEMENT
# ---------------------------
@app.route('/checkout', methods=['POST'])
def checkout():
    booking_id = request.form['booking_id']
    actual_check_out = request.form['actual_check_out']
    last_update = session['username']
    timestamp = datetime.now()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Get old data
    cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
    old_data = cursor.fetchone()
    if not old_data:
        cursor.close()
        return "Booking not found", 404

    # 2. Prepare new data
    new_data = old_data.copy()
    new_data['actual_check_out'] = actual_check_out
    new_data['status'] = 'Checked-out'
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp

    # 3. Update booking
    cursor.execute("""
        UPDATE bookings
        SET actual_check_out = %s, status = 'Checked-out', last_update = %s, timestamp = %s
        WHERE booking_id = %s
    """, (actual_check_out, last_update, timestamp, booking_id))

    # 4. Update room status to 'Vacant'
    cursor.execute("SELECT room_id FROM bookings WHERE booking_id = %s", (booking_id,))
    room = cursor.fetchone()
    if room:
        cursor.execute("UPDATE room SET room_status = 'Vacant' WHERE room_id = %s", (room['room_id'],))
    else:
        cursor.close()
        return "Room not found", 404

    mysql.connection.commit()

    # 5. Save audit log
    log_audit_event(
        actor_id=session['username'],
        timestamp=timestamp,
        table_name='bookings',
        action_type='UPDATE (Set Checkout Date)',
        record_id=str(booking_id),
        old_data=old_data,
        new_data=new_data
    )

    cursor.close()
    flash('Check-out successful.', 'success')
    return redirect('/roomGuest')

@app.route('/users')
def users_page():
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('login'))

    # Restrict access (optional)
    if session['role'].lower() not in ['admin', 'manager']:
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()
    
    # Search functionality
    cursor.execute("SELECT * FROM users ORDER BY user_id ASC")
    users = cursor.fetchall()

    # Summary counts
    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS active FROM users WHERE status = 1")
    active_users = cursor.fetchone()['active']

    cursor.execute("SELECT COUNT(*) AS inactive FROM users WHERE status = 0")
    inactive_users = cursor.fetchone()['inactive']

    cursor.execute("""
        SELECT COUNT(*) AS admins
        FROM users
        WHERE role IN ('admin', 'manager')
    """)
    total_admins = cursor.fetchone()['admins']

    cursor.close()

    return render_template(
        'users.html',
        users=users,
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_admins=total_admins,notifications=notifications,
        unread_count=unread_count,
        role=session['role']
    )

@app.route('/addUser', methods=['POST'])
def add_user():
    username = request.form['username']
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    department = request.form.get('department')
    status = int(request.form.get('status', 1))  # Default Active
    account_status = "" 
    name = f"{first_name} {middle_name} {last_name}".strip()
    last_update = session['username']
    timestamp = datetime.now()

    # Set department to None if user is admin/manager
    if role in ['admin', 'manager']:
        department = None

    # ✅ Hash the password before saving
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    new_user_id = None 
    
    try:
        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            flash("Username already taken.", "danger")
            return redirect('/users')

        # Check if email already exists
        cursor.execute("SELECT email FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered. Please log in.", "danger")
            return redirect('/users')

        # Generate verification token
        verification_token = generate_verification_token()
        token_expires_at = datetime.now() + timedelta(hours=24)
        
        # ✅ Use the hashed password instead of plain text
        cursor.execute("""
            INSERT INTO users (username, first_name, middle_name, last_name, name, email, password, role, department, status, email_verified, verification_token, token_expires_at, account_status, created_at, last_update, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (username, first_name, middle_name, last_name, name, email, hashed_password, role, department, status, False, verification_token, token_expires_at, account_status, datetime.now(), last_update, timestamp))
        new_user_id = cursor.lastrowid 
        mysql.connection.commit()
        
        # Log new user creation
        if new_user_id:
            new_data_for_log = {
                'user_id': new_user_id,
                'username': username,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'name': name,
                'email': email,
                'role': role,
                'department': department,
                'last_update': last_update,
                'timestamp': timestamp
            }
            
            log_audit_event(
                actor_id=session['username'],
                timestamp=timestamp,
                table_name='users',
                action_type='INSERT',
                record_id=str(new_user_id),
                old_data=None,
                new_data=new_data_for_log
            )

        flash("✅ User added successfully!", "success")
        
        # Send verification email
        if send_verification_email(email, username, verification_token):
            flash("Check your email for a verification link.", "success")
            return redirect(url_for('verification_pending'))
        else:
            flash("Could not send email. Contact support.", "danger")      
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"❌ Failed to add user: {str(e)}", "danger")
    finally:
        cursor.close()
        return redirect('/users')
    
#Called by USER Menu - check if user exist in requests
@app.route('/checkUser/<username>')
def check_user(username):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS count FROM audit_log WHERE username = %s", (username,)) #Count how many staff id in requests
    result = cursor.fetchone()
    cursor.close()
    return jsonify({"in_use": result['count'] > 0}) #Return to users; set "in_use" to true if count> 0

@app.route('/deleteUser/<int:user_id>', methods=['GET'], endpoint='delete_user_route')
def delete_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get old data for logging
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    old_data = cursor.fetchone()
    timestamp = datetime.now()
    
    if not old_data:
        cursor.close()
        return "User not found or already deleted", 404
    
    # Log before deletion
    log_audit_event(
        actor_id=session.get('username'),
        timestamp=timestamp,
        table_name='users',
        action_type='DELETE',
        record_id=str(user_id),
        old_data=old_data,
        new_data=None
    )
    
    # Perform deletion
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    cursor.close()
    
    flash('User deleted successfully', 'success')
    return redirect('/users')

@app.route('/updateUser', methods=['POST'])
def update_user():
    user_id = request.form['edit_user_id']
    username = request.form['edit_username']
    first_name = request.form['edit_first_name']
    middle_name = request.form['edit_middle_name']
    last_name = request.form['edit_last_name']
    email = request.form['edit_email']
    role = request.form['edit_role']
    department = request.form.get('edit_department')
    status = int(request.form.get('edit_status', 1))
    name = f"{first_name} {middle_name} {last_name}".strip()
    last_update = session['username']
    timestamp = datetime.now()

    # Remove department for certain roles
    if role in ['admin', 'user']:
        department = None

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    #Get old data
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)) #change table and field names
    old_data = cursor.fetchone() 

    if not old_data:
        # Handle error: record not found
        return "User not found", 404 #change message
    
    #Get new data 
    new_data = old_data.copy()
    new_data['user_id'] = user_id  #change ALL field names (should be similar to the table)
    new_data['username'] = username
    new_data['first_name'] = first_name
    new_data['middle_name'] = middle_name
    new_data['last_name'] = last_name
    new_data['email'] = email
    new_data['role'] = role
    new_data['department'] = department
    new_data['status'] = status
    new_data['name'] = name
    new_data['last_update'] = last_update
    new_data['timestamp'] = timestamp
    
    try:
        cursor.execute("""
            UPDATE users 
            SET username=%s, first_name=%s, middle_name=%s, last_name=%s, name=%s, email=%s, role=%s, department=%s, status=%s, last_update=%s, timestamp=%s
            WHERE user_id=%s
        """, (username, first_name, middle_name, last_name, name, email, role, department, status, last_update, timestamp, user_id))
        mysql.connection.commit()
        
        #Save logs
        log_audit_event(
            actor_id=session['username'],
            timestamp=timestamp,
            table_name='users',  #change table name
            action_type='UPDATE', 
            record_id=str(user_id), #change field name
            old_data=old_data, 
            new_data=new_data 
        )

        flash("✅ User updated successfully!", "success")
    except Exception as e:
        print("❌ Update error:", e)
        flash("❌ Failed to update user.", "danger")
    finally:
        cursor.close()

    return redirect('/users')

@app.route('/bill/<int:booking_id>')
def view_bill(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch requests
    cursor.execute("""
        SELECT 
            r.*, 
            s.name AS service_name,
            f.name AS item_name
        FROM requests r
        LEFT JOIN hotel_services s ON r.service_id = s.service_id
        LEFT JOIN food_items f ON r.item_id = f.item_id
        WHERE r.booking_id = %s
    """, (booking_id,))
    requests = cursor.fetchall()

    # Aggregate by service/item
    grouped_requests = {}
    for r in requests:
        name = r.get('service_name') or r.get('item_name') or 'N/A'
        if name not in grouped_requests:
            grouped_requests[name] = {
                'quantity': 0,
                'unit_cost': float(r.get('unitCost', r.get('unit_cost', 0))),
                'total_cost': 0
            }
        grouped_requests[name]['quantity'] += int(r.get('quantity', 1))
        grouped_requests[name]['total_cost'] += float(r.get('totalCost', r.get('total_cost', 0)))

    requests_grouped_list = [
        {
            'service_name': name,
            'quantity': data['quantity'],
            'unit_cost': data['unit_cost'],
            'total_cost': data['total_cost']
        } 
        for name, data in grouped_requests.items()
    ]

    # Total bill
    total_bill = sum(r['total_cost'] for r in requests_grouped_list)

    # Fetch payments
    cursor.execute("""
        SELECT *
        FROM payment
        WHERE booking_id = %s
    """, (booking_id,))
    payments = cursor.fetchall()

    # Payment summary
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_payment,
               IFNULL(MAX(status), 'Pending') AS payment_status
        FROM payment
        WHERE booking_id = %s
    """, (booking_id,))
    payment_summary = cursor.fetchone()
    total_payment = float(payment_summary['total_payment'])  # now in pesos
    payment_status = payment_summary['payment_status']

    balance = round(max(total_bill - total_payment, 0), 2)
    has_requests = total_bill > 0


    cursor.close()

    return render_template(
        'bill.html',
        requests=requests_grouped_list,
        total_bill=total_bill,
        booking_id=booking_id,
        payments=payments,
        total_payment=total_payment,
        balance=balance,
        payment_status=payment_status,
        has_requests=has_requests
    )

@app.route('/pay', methods=['POST'])
def pay():
    booking_id = request.form.get('booking_id')
    amount = int(request.form.get('amount', 0))  # sent in centavos
    amount_pesos = amount / 100  # convert to pesos

    HEADERS = {
        "Authorization": "Basic " + base64.b64encode(f"{PAYMONGO_SECRET_KEY}:".encode()).decode(),
        "Content-Type": "application/json"
    }

    # Step 1: Create payment intent
    intent_payload = {
        "data": {
            "attributes": {
                "amount": amount,
                "currency": "PHP",
                "description": f"Booking #{booking_id} Payment",
                "payment_method_allowed": ["card", "gcash", "grab_pay"],
                "payment_method_options": {"card": {"request_three_d_secure": "any"}}
            }
        }
    }
    intent_resp = requests.post("https://api.paymongo.com/v1/payment_intents", headers=HEADERS, json=intent_payload)
    intent_data = intent_resp.json()
    if "data" not in intent_data:
        return f"<h3>❌ Error creating payment intent.</h3><pre>{json.dumps(intent_data, indent=2)}</pre>"

    # Save a pending payment in pesos
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO payment (booking_id, amount, payment_date, payment_method, status) 
        VALUES (%s, %s, NOW(), %s, %s)
    """, (booking_id, amount_pesos, 'PayMongo', 'Paid'))  # amount now in pesos
    mysql.connection.commit()
    cursor.close()

    # Step 2: Create checkout link
    intent_id = intent_data["data"]["id"]
    checkout_payload = {
        "data": {
            "attributes": {
                "payment_intent": intent_id,
                "billing": {"name": "ezStay Guest"},
                "description": f"Booking #{booking_id} Payment",
                "amount": amount,
                "currency": "PHP",
                "success_url": url_for('success', booking_id=booking_id, _external=True),
                "cancel_url": url_for('failed', _external=True),
                "remarks": "ezStay payment link"
            }
        }
    }

    checkout_resp = requests.post("https://api.paymongo.com/v1/links", headers=HEADERS, json=checkout_payload)
    checkout_data = checkout_resp.json()
    if "data" not in checkout_data:
        return f"<h3>❌ Error creating checkout link.</h3><pre>{json.dumps(checkout_data, indent=2)}</pre>"

    checkout_url = checkout_data["data"]["attributes"]["checkout_url"]
    return jsonify({"checkout_url": checkout_url})

@app.route('/success')
def success():
    booking_id = request.args.get('booking_id')

    if not booking_id:
        return "<h2>✅ Payment successful!</h2>"

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Find the latest pending payment for this booking
    cursor.execute("""
        UPDATE payment
        SET status = 'Paid', payment_date = NOW()
        WHERE booking_id = %s AND status = 'Pending'
        ORDER BY payment_id DESC LIMIT 1
    """, (booking_id,))

    # Check total paid and compare with total bill
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_paid
        FROM payment
        WHERE booking_id = %s AND status = 'Paid'
    """, (booking_id,))
    total_paid = cursor.fetchone()['total_paid']

    cursor.execute("""
        SELECT COALESCE(SUM(totalCost), 0) AS total_bill
        FROM requests
        WHERE booking_id = %s
    """, (booking_id,))
    total_bill = cursor.fetchone()['total_bill']

    if total_paid >= total_bill:
        cursor.execute("UPDATE bookings SET status = 'Paid' WHERE booking_id = %s", (booking_id,))

    mysql.connection.commit()
    cursor.close()

    return f"""
    <html>
      <head>
        <title>Payment Success</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      </head>
      <body class='text-center p-5'>
        <h2>✅ Payment successful for Booking #{booking_id}!</h2>
        <a href='/bookings' class='btn btn-primary mt-3'>Back to Bookings</a>
      </body>
    </html>
    """

@app.route('/failed')
def failed():
    return """
    <html>
      <head>
        <title>Payment Failed</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      </head>
      <body class='text-center p-5'>
        <h2>❌ Payment was cancelled or failed. Please try again.</h2>
        <a href='/bookings' class='btn btn-secondary mt-3'>Back to Bookings</a>
      </body>
    </html>
    """

@app.route('/webhook/paymongo', methods=['POST'])
def paymongo_webhook():
    event = request.json
    event_type = event.get('type')
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Payment intent succeeded
    if event_type == "payment_intent.paid":
        # You can match by booking_id if included in description or metadata
        description = event['data']['attributes'].get('description', '')
        # Assuming description = "Booking #123 Payment"
        booking_id = description.split("#")[1].split()[0]

        # Update the latest pending payment for this booking
        cursor.execute("""
            UPDATE payment 
            SET status = 'Paid', payment_date = NOW() 
            WHERE booking_id = %s AND status = 'Pending'
            ORDER BY payment_id DESC LIMIT 1
        """, (booking_id,))

        # Update booking status if fully paid
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_paid
            FROM payment
            WHERE booking_id = %s AND status = 'Paid'
        """, (booking_id,))
        total_paid = cursor.fetchone()['total_paid']

        cursor.execute("""
            SELECT COALESCE(SUM(totalCost), 0) AS total_bill
            FROM requests
            WHERE booking_id = %s
        """, (booking_id,))
        total_bill = cursor.fetchone()['total_bill']

        if total_paid >= total_bill:
            cursor.execute("UPDATE bookings SET status = 'Paid' WHERE booking_id = %s", (booking_id,))

        mysql.connection.commit()

    # Payment failed
    elif event_type == "payment_intent.failed":
        description = event['data']['attributes'].get('description', '')
        booking_id = description.split("#")[1].split()[0]

        cursor.execute("""
            UPDATE payment 
            SET status = 'Failed' 
            WHERE booking_id = %s AND status = 'Pending'
            ORDER BY payment_id DESC LIMIT 1
        """, (booking_id,))
        mysql.connection.commit()

    cursor.close()
    return jsonify({"status": "success"}), 200

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    # Prevent accessing OTP page if there is no active OTP session
    if "otp" not in session or "otp_expiry" not in session:
        flash("No OTP session found. Please log in again.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        # Concatenate all six OTP fields
        entered_otp = "".join([
            request.form.get(f"otp_{i}", "") for i in range(1, 7)
        ])

        if len(entered_otp) != 6 or not entered_otp.isdigit():
            flash("Invalid OTP format. Please enter the 6-digit code.", "danger")
            return redirect(url_for("verify_otp"))

        saved_otp = str(session.get("otp", ""))
        expiry = session.get("otp_expiry")

        if not saved_otp or not expiry:
            flash("Session expired or no OTP found. Please request a new code.", "danger")
            if session.get("reset_email"):
                return redirect(url_for("forgot_password"))
            return redirect(url_for("login"))

        try:
            expiry_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        except Exception:
            expiry_dt = None

        if expiry_dt and datetime.now() > expiry_dt:
            session.pop("otp", None)
            session.pop("otp_expiry", None)
            flash("OTP has expired. Please request a new one.", "danger")
            if session.get("reset_email"):
                return redirect(url_for("forgot_password"))
            return redirect(url_for("login"))

        # OTP validated
        if entered_otp == saved_otp:
            # Always clear OTP data after validation
            session.pop("otp", None)
            session.pop("otp_expiry", None)

            # Handle login verification
            pending = session.pop("pending_user", None)
            if pending and "username" in pending and "role" in pending:
                session["loggedin"] = True
                session["username"] = pending["username"]
                session["role"] = pending["role"]
                session["department"] = pending.get("department")
                flash(f"Welcome back, {pending['username']}!", "success")
                return redirect(url_for("dashboard"))

            # Handle password reset verification
            if session.get("reset_email"):
                flash("OTP verified. You may now reset your password.", "success")
                return redirect(url_for("reset_password"))

            # Default fallback for unexpected flow
            flash("OTP verified, but no action found. Please log in again.", "info")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP. Please try again.", "danger")
            return redirect(url_for("verify_otp"))

    return render_template("verify_otp.html")

@app.route('/forceassigntask', methods=['POST'])
def forceassigntask():
    request_id = request.form.get("assignTask_request_id")
    staff_id_value = request.form.get("assignTask_staff_id")

    # debug log incoming form
    print("DEBUG /forceassigntask form:", dict(request.form))

    if not request_id or not staff_id_value:
        flash("Missing request or staff ID", "danger")
        return redirect(url_for("show_requests"))

    # try to cast to int, if fails show message and return
    try:
        staff_candidate_id = int(staff_id_value)
    except (ValueError, TypeError):
        flash("Invalid staff id selected.", "danger")
        return redirect(url_for("show_requests"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        #get old staff id
        cursor.execute("SELECT staff_id FROM requests WHERE request_id = %s", (request_id,))
        old_staff_id = cursor.fetchone()
        
        # 1) Check if that id exists in staff table
        cursor.execute("SELECT * FROM staff WHERE staff_id = %s", (staff_candidate_id,))
        staff_row = cursor.fetchone()

        # 2) If not in staff, check users table (user-as-staff)
        if not staff_row:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (staff_candidate_id,))
            user_row = cursor.fetchone()

            if user_row:
                # create a staff row from user row (adapt fields as needed)
                # keep phone empty if not available
                first_name = user_row.get('first_name') or user_row.get('username') or ''
                last_name = user_row.get('last_name') or ''
                role = user_row.get('role') or 'staff'
                email = user_row.get('email') or ''
                phone = user_row.get('phone') or ''

                cursor.execute("""
                    INSERT INTO staff (first_name, last_name, role, email, phone, last_update, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (first_name, last_name, role, email, phone, session.get('username'), datetime.now()))
                mysql.connection.commit()

                # get the newly created staff_id
                cursor.execute("SELECT LAST_INSERT_ID() AS staff_id")
                new_row = cursor.fetchone()
                if not new_row:
                    flash("Failed to create staff record from user.", "danger")
                    cursor.close()
                    return redirect(url_for("show_requests"))

                staff_candidate_id = new_row['staff_id']
            else:
                flash("Selected person not found in staff or users table.", "danger")
                cursor.close()
                return redirect(url_for("show_requests"))

        # 3) Update request with valid staff_id
        cursor.execute("""
            UPDATE requests
            SET staff_id = %s
            WHERE request_id = %s
        """, (staff_candidate_id, request_id))
        mysql.connection.commit()
        
                # Optional: log audit for reassignment
        log_audit_event(
            actor_id=session.get('username'),
            timestamp=datetime.now(),
            table_name='requests',
            action_type='UPDATE (Assign Staff to Request)',
            record_id=request_id,
            old_data=old_staff_id,
            new_data={'staff_id': staff_candidate_id}
        )

        
        flash("Staff assigned successfully", "success")
    except Exception as e:
        mysql.connection.rollback()
        print("ERROR /forceassigntask:", e)
        flash("Failed to assign staff, see server logs.", "danger")
    finally:
        cursor.close()

    return redirect(url_for("show_requests"))

def _resolve_target_role(cursor, request_id):
    """
    Determine which department this request belongs to and return the corresponding staff role.
    Rules:
      - Service Request: Role = "<service.category> - Staff"
      - Food Request: Role = "Food/Dining - Staff"
    """
    cursor.execute("""
        SELECT r.service_id, r.item_id,
               hs.category AS service_category,
               fi.category AS food_category
        FROM requests r
        LEFT JOIN hotel_services hs ON r.service_id = hs.service_id
        LEFT JOIN food_items fi ON r.item_id = fi.item_id
        WHERE r.request_id = %s
    """, (request_id,))
    
    row = cursor.fetchone()
    if not row:
        return None

    if row['service_id']:
        dept = row['service_category'] or ''
        target_role = f"{dept} - Staff"
    else:
        target_role = "Food/Dining - Staff"

    return target_role

def _pick_least_loaded_staff(cursor, target_role):
    
    #Choose the staff with the fewest *active* requests (status != 'completed') for the role.
    #Ties are broken by lowest staff_id.
    
    cursor.execute("""
        SELECT s.staff_id,
                COALESCE(SUM(CASE WHEN lower(r.status) <> 'completed' THEN 1 ELSE 0 END), 0) AS load_now
        FROM staff s
        LEFT JOIN requests r ON r.staff_id = s.staff_id
        WHERE s.role = %s
        GROUP BY s.staff_id
        ORDER BY load_now ASC, s.staff_id ASC
        LIMIT 1
    """, (target_role,))
    return cursor.fetchone()

@app.route('/assigntask', methods=['POST'])
def assigntask():
    req_id = request.form.get('assignTask_request_id')
    if not req_id:
        flash("No request id.", "danger")
        return redirect('/requests')
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cur.execute("SELECT staff_id, status FROM requests WHERE request_id = %s", (req_id,))
    req_row = cur.fetchone()
    if not req_row:
        cur.close()
        flash("Request not found.", "danger")
        return redirect('/requests')
    
    # Optional: store old staff for audit
    old_staff_id = req_row['staff_id']

    target_role = _resolve_target_role(cur, req_id)
    if not target_role:
        cur.close()
        flash("Could not resolve request category.", "danger")
        return redirect('/requests')
    
    staff = _pick_least_loaded_staff(cur, target_role)
    
    # Fallback: If no Staff found, try the Manager of the same department
    if not staff and " - Staff" in target_role:
        mgr_role = target_role.replace(" - Staff", " - Manager")
        staff = _pick_least_loaded_staff(cur, mgr_role)
        
    if not staff:
        cur.close()
        flash(f"No available staff for role '{target_role}'.", "warning")
        return redirect('/requests')
    
    cur.execute("""
        UPDATE requests
        SET staff_id = %s,
            status = CASE WHEN status = 'pending' THEN 'pending' ELSE status END
        WHERE request_id = %s
    """, (staff['staff_id'], req_id))
    mysql.connection.commit()
    
    # Optional: log audit for reassignment
    log_audit_event(
        actor_id=session.get('username'),
        timestamp=datetime.now(),
        table_name='requests',
        action_type='UPDATE (Assign Staff to Request)',
        record_id=req_id,
        old_data={'staff_id': old_staff_id},
        new_data={'staff_id': staff['staff_id']}
    )
    
    cur.close()
    flash(f"Request assigned successfully.", "success")
    return redirect('/requests')

def log_audit_event(actor_id, timestamp, table_name, action_type, record_id, old_data=None, new_data=None):
    """Inserts a manual audit log entry into the MySQL audit_log table."""
    try:
        read_status = 0
        old_value_json = json.dumps(old_data, default=str) if old_data else None
        new_value_json = json.dumps(new_data, default=str) if new_data else None

        cursor = mysql.connection.cursor()
        cursor.execute(
            """INSERT INTO audit_log 
               (username, timestamp, table_name, action_type, record_id, old_value, new_value, read_status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (actor_id, timestamp, table_name, action_type, record_id, old_value_json, new_value_json, read_status)
        )

        mysql.connection.commit()
        cursor.close()
    except Exception as e:
        # Log but do not crash the app
        print(f"FATAL AUDIT FAILURE: {e}")
        
                
@app.route('/getBooking/<int:checkin_id>')
def getBooking(checkin_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            c.checkin_id,
            c.booking_id,
            c.room_number,
            b.actual_check_in,
            g.first_name,
            g.last_name
        FROM check_ins c
        JOIN bookings b ON b.booking_id = c.booking_id
        JOIN guest g ON g.guest_id = c.guest_id
        WHERE c.checkin_id = %s
    """, (checkin_id,))

    booking = cursor.fetchone()
    cursor.close()

    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    return jsonify(booking)        

@app.route('/getBookingByRef/<string:random_booking_ref>')
def getBookingByRef(checkin_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            c.checkin_id,
            c.booking_id,
            c.room_number,
            b.actual_check_in,
            g.first_name,
            g.last_name
        FROM check_ins c
        JOIN bookings b ON b.booking_id = c.booking_id
        JOIN guest g ON g.guest_id = c.guest_id
        WHERE b.random_booking_ref = %s
    """, (random_booking_ref,))

    booking = cursor.fetchone()
    cursor.close()

    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    return jsonify(booking)        

        
@app.route('/completedRequest', methods=['POST'])
def completedRequest():
    request_id = request.form.get('completed_request_id')
    completion_time = request.form.get('completion_time')

    if not request_id or not completion_time:
        flash("Missing request ID or completion time", "danger")
        return redirect(url_for('show_requests'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        UPDATE requests
        SET status = 'completed',
            completion_time = %s
        WHERE request_id = %s
    """, (completion_time, request_id))
    mysql.connection.commit()
    
    # Optional: log audit for reassignment
    log_audit_event(
        actor_id=session.get('username'),
        timestamp=datetime.now(),
        table_name='requests',
        action_type='UPDATE (Set Completion Date)',
        record_id=request_id,
        old_data={},
        new_data={'Completion Date': completion_time}
    )
    
    cursor.close()

    flash("Request marked as completed successfully", "success")
    return redirect(url_for('show_requests'))

@app.route('/index')
def index():
    # This function renders the HTML file you provided
    return render_template('index.html') 
# ------------------------------


@app.route('/feedback')
def feedback():
    # This function renders the HTML file you provided
    return render_template('feedback.html', show_thank_modal=False) 
# ------------------------------


@app.route('/addFeedback', methods=['POST'])
def add_feedback():
    # Get values from form
    rating           = request.form.get('rating')          # 1–5
    comment         = request.form.get('comment')
    guest_name       = request.form.get('guest_name')
    service_category = request.form.get('service_category')
    created_at        = datetime.now()
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("""
            INSERT INTO feedback
                (rating, comment, guest_name, service_category, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (rating, comment, guest_name, 
              service_category, created_at))

        new_feedback_id = cursor.lastrowid
        mysql.connection.commit()

        if new_feedback_id:
            new_data_for_log = {
                'rating': rating,
                'comment': comment,
                'guest_name': guest_name,
                'service_category': service_category,
                'created_at': created_at
            }
            log_audit_event(
                actor_id='',
                timestamp=created_at,
                table_name='feedback',
                action_type='INSERT',
                record_id=str(new_feedback_id),
                old_data=None,
                new_data=new_data_for_log
            )

    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash('Error saving feedback. Please try again.', 'danger')
        print("MySQL error:", e)

    finally:
        cursor.close()

    if success:
        # show modal, then redirect to index via JS
        return render_template('feedback.html', show_thank_modal=True)
    else:
        return redirect(url_for('feedback_form'))

#Feedback List
@app.route('/feedbacklist')
def view_feedbacklist():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Connect to the database
    
    cursor.execute("""
    SELECT log_id, timestamp,
           CONCAT(username, ' ', action_type, ' record ', record_id, ' in ', table_name) AS message,
           read_status
    FROM audit_log
    WHERE read_status = 0
    ORDER BY timestamp DESC
    LIMIT 5
""")
    notifications = cursor.fetchall()

    # inside your dashboard route (or wherever you render template)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # unread count for badge
    cur.execute("SELECT COUNT(*) AS count FROM audit_log WHERE read_status = 0")
    unread_count = cur.fetchone()['count']

    cur.close()

    cursor.execute("""
                   SELECT * FROM feedback ORDER BY feedback_id DESC
                   """)
    feedbacks = cursor.fetchall() #After executing sql, fetch results
    return render_template('feedbacklist.html', feedbacks=feedbacks, notifications=notifications,
        unread_count=unread_count) #pass the contents of logs to auditlogs.html

            
if __name__ == '__main__':
    app.run(debug=True)