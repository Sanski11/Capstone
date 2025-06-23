from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
#app.config['MYSQL_PASSWORD'] = 'Kitty_909'
app.config['MYSQL_PASSWORD'] = 'Kitty_909'
app.config['MYSQL_DB'] = 'staff_portal'

mysql = MySQL(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        if user:
            if user['status'] != 'Active':
                return render_template('login.html', error="Your account is not yet approved.")
            session['username'] = user['username']
            session['role'] = user['role']
            # Redirect admin to dashboard, others as needed
            if user['role'] == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('dashboard'))  # Or another page for non-admins
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        if user:
            cursor.execute('UPDATE users SET password = %s WHERE username = %s', (new_password, username))
            mysql.connection.commit()
            return redirect(url_for('login'))
        else:
            return render_template('forgot_password.html', error="Username not found")
    
    return render_template('forgot_password.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        department = request.form['department']
        # If admin, set status to Active, else For approval
        status = 'Active' if role == 'admin' else 'For approval'

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role, email, department, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (username, password, role, email, department, status)
            )
            mysql.connection.commit()
            if role == 'admin':
                session['username'] = username
                session['role'] = role
                return redirect(url_for('dashboard'))
            return redirect(url_for('login'))
        except MySQLdb.IntegrityError:
            return render_template('signup.html', error="Username or email already exists")
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Housekeeping: Count of housekeeping services requested
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Housekeeping'
        """)
        housekeeping = cursor.fetchone()['count']

        # Food: Dining services
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Dining'
        """)
        food = cursor.fetchone()['count']

        # Laundry services
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Laundry'
        """)
        laundry = cursor.fetchone()['count']

        # Spa / Massage services
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM Requests r 
            JOIN Services s ON r.service_id = s.service_id 
            WHERE s.service_type = 'Massage'
        """)
        spa = cursor.fetchone()['count']

        # Pie chart data
        cursor.execute("""
            SELECT service_type, COUNT(*) AS count
            FROM services s
            JOIN requests r ON s.service_id = r.service_id
            GROUP BY service_type
        """)
        service_data = cursor.fetchall()

        # Bar chart data (requests vs completed by staff)
        cursor.execute("""
            SELECT s.first_name AS staff, 
                   COUNT(r.request_id) AS requests,
                   SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) AS completed
            FROM requests r
            JOIN staff s ON r.staff_id = s.staff_id
            GROUP BY s.first_name
        """)
        staff_data = cursor.fetchall()

        return render_template(
            'dashboard.html',
            user=session['username'],
            stats={
                "housekeeping": housekeeping,
                "food": food,
                "laundry": laundry,
                "spa": spa
            },
            service_data=service_data,
            staff_data=staff_data
        )
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'username' in session and 'role' in session:
        return render_template('profile.html', user=session['username'], role=session['role'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/staff')
def staff():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Staff")
    staffs = cursor.fetchall()
    cursor.close()
    return render_template('staff.html', staffs=staffs)

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

    # GET method - show the edit form
    cursor.execute("SELECT * FROM Guest WHERE guest_id = %s", (guest_id,))
    guest = cursor.fetchone()
    cursor.close()

    if not guest:
        # Instead of redirecting, render the template with guest=None or show an error
        return render_template('editGuest.html', guest=None, error="Guest not found")
    return render_template('editGuest.html', guest=guest)

@app.route('/requests')
def show_requests():
    query = request.args.get('search', '')
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch all staff for the dropdown
    cursor.execute("SELECT * FROM staff")
    staff_list = cursor.fetchall()

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
    return render_template('requests.html', requests=requests, staff_list=staff_list, current_time=current_time)

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

@app.route('/updateStatus', methods=['POST'])
def updateStatus():
    request_id = request.form['updateStatus_request_id']
    status = request.form['updateStatus_status']
    completionTime = datetime.strptime(request.form['updateStatus_completionTime'], '%Y-%m-%dT%H:%M')

    cursor = mysql.connection.cursor()
    sql = "UPDATE requests SET status = %s, completionTime = %s WHERE request_id = %s"
    cursor.execute(sql, (status, completionTime, request_id))
    mysql.connection.commit()
    cursor.close()

    return redirect('/requests')

@app.route('/rooms')
def view_rooms():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Room")
    rooms = cursor.fetchall()
    return render_template('rooms.html', rooms=rooms)
  
@app.route('/services')
def view_services():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Services")
    services = cursor.fetchall()
    return render_template('services.html', services=services)
 
@app.route('/guests')
def view_guests():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Guest")
    guests = cursor.fetchall()
    return render_template('guests.html', guests=guests)

@app.route('/roomGuest')
def show_roomGuest():
    query = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if query:
        search_pattern = f"%{query}%"
        sql = """
            SELECT * FROM bookings 
            WHERE 
                CAST(booking_id AS CHAR) LIKE %s OR
                CAST(room_id AS CHAR) LIKE %s OR
                CAST(guest_id AS CHAR) LIKE %s OR
                CAST(exp_check_in AS CHAR) LIKE %s OR
                CAST(exp_check_out AS CHAR) LIKE %s OR
                CAST(actual_check_in AS CHAR) LIKE %s OR
                CAST(actual_check_out AS CHAR) LIKE %s
        """
        cursor.execute(sql, (search_pattern,) * 7)
    else:
        cursor.execute("SELECT * FROM bookings WHERE status = 'Confirmed'")

    bookings = cursor.fetchall()
    cursor.close()
    return render_template('roomGuest.html', bookings=bookings)

@app.route('/addRoom', methods=['POST'])
def add_rooms():
    roomNumber = request.form['room_number']
    roomType = request.form['room_type']
    roomStatus = request.form['room_status']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO room (room_number, room_type, room_status) VALUES (%s, %s, %s)",
        (roomNumber, roomType, roomStatus)
    )
    mysql.connection.commit()
    cursor.close()
    return redirect('/rooms')

@app.route('/updateRoom', methods=['POST'])
def updateRoom():
    room_id = int(request.form['edit_room_id'])
    room_number = request.form['edit_room_number']
    room_type = request.form['edit_room_type']
    room_status = request.form['edit_room_status']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        """
        UPDATE room
        SET room_number = %s, room_type = %s, room_status = %s
        WHERE room_id = %s
        """,
        (room_number, room_type, room_status, room_id)
    )
    mysql.connection.commit()
    cursor.close()
    return redirect('/rooms')

@app.route('/deleteRoom/<int:room_id>', methods=['GET'])
def deleteRoom(room_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM room WHERE room_id = %s", (room_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/rooms')

@app.route('/addGuests', methods=['POST'])
def add_guests():
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        INSERT INTO Guest (first_name, middle_name, last_name, email, phone)
        VALUES (%s, %s, %s, %s, %s)
    """, (first_name, middle_name, last_name, email, phone))
    mysql.connection.commit()
    cursor.close()

    return redirect('/guests')


@app.route('/updateGuests', methods=['POST'])
def updateGuests():
    guest_id = int(request.form['edit_guest_id'])
    first_name = request.form['edit_first_name']
    middle_name = request.form['edit_middle_name']
    last_name = request.form['edit_last_name']
    email = request.form['edit_email']
    phone = request.form['edit_phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        UPDATE Guest 
        SET first_name = %s, middle_name = %s, last_name = %s, email = %s, phone = %s 
        WHERE guest_id = %s
    """, (first_name, middle_name, last_name, email, phone, guest_id))
    mysql.connection.commit()
    cursor.close()

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
    request_id = request.form['edit_request_id']
    booking_id = request.form['edit_booking_id']
    service_id = request.form['edit_service_id']
    quantity = int(request.form['edit_quantity'])
    unitCost = float(request.form['edit_unitCost'])
    totalCost = quantity * unitCost

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        UPDATE requests
        SET booking_id=%s, service_id=%s, quantity=%s, unitCost=%s, totalCost=%s
        WHERE request_id=%s
    """, (booking_id, service_id, quantity, unitCost, totalCost, request_id))
    mysql.connection.commit()
    cursor.close()
    return redirect('/requests')

@app.route('/updateRequestStatus', methods=['POST'])
def update_request_status():
    request_id = request.form['edit_request_id']
    status = request.form['edit_status']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "UPDATE Requests SET status = %s WHERE request_id = %s",
        (status, request_id)
    )
    mysql.connection.commit()
    cursor.close()
    return redirect('/requests')

@app.route('/deleteRequest/<int:request_id>', methods=['GET'])
def deleteRequest(request_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Delete assignments first
    cursor.execute("DELETE FROM StaffAssignments WHERE request_id = %s", (request_id,))
    # Then delete the request
    cursor.execute("DELETE FROM Requests WHERE request_id = %s", (request_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/requests')

@app.route('/addService', methods=['POST'])
def add_service():
    service_type = request.form['service_type']
    item = request.form['item']
    amount = float(request.form['amount'])

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO Services (service_type, item, amount) VALUES (%s, %s, %s)",
        (service_type, item, amount)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect('/services')

@app.route('/addStaff', methods=['POST'])
def add_staff():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    role = request.form['role']
    email = request.form['email']
    phone = request.form['phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO Staff (first_name, last_name, role, email, phone) VALUES (%s, %s, %s, %s, %s)",
        (first_name, last_name, role, email, phone)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect('/staff')

@app.route('/updateStaff', methods=['POST'])
def updateStaff():
    staff_id = int(request.form['edit_staff_id'])
    first_name = request.form['edit_first_name']
    last_name = request.form['edit_last_name']
    role = request.form['edit_role']
    email = request.form['edit_email']
    phone = request.form['edit_phone']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
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


@app.route('/deleteStaff/<int:staff_id>', methods=['GET'])
def deleteStaff(staff_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM Staff WHERE staff_id = %s", (staff_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/staff')

@app.route('/updateServices', methods=['POST'])
def updateServices():
    service_id = int(request.form['edit_service_id'])
    service_type = request.form['edit_service_type']
    item = request.form['edit_item']
    amount = float(request.form['edit_amount'])

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        """
        UPDATE Services 
        SET service_type = %s, item = %s, amount = %s 
        WHERE service_id = %s
        """,
        (service_type, item, amount, service_id)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect('/services')

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

@app.route('/deleteGuest/<int:guest_id>', methods=['GET'])
def deleteGuest(guest_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM Guest WHERE guest_id = %s", (guest_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/guests')


# ROUTE FOR BOOKINGS
@app.route('/bookings')
def view_bookings():
    search = request.args.get('search', '')
    selected_type = request.args.get('room_type', '')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get all guests
    cursor.execute("SELECT * FROM guest")
    guests = cursor.fetchall()

    # Get rooms (with optional room type filter)
    if selected_type:
        cursor.execute("SELECT * FROM room WHERE room_type = %s", (selected_type,))
    else:
        cursor.execute("SELECT * FROM room")
    rooms = cursor.fetchall()

    # Get bookings with guest name and room number using JOIN
    if search:
        like = f"%{search}%"
        query = """
            SELECT 
                b.*, 
                g.first_name AS guest_first_name,
                g.last_name AS guest_last_name,
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
        cursor.execute(query, (like,) * 10)
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
    
    bookings = cursor.fetchall()
    cursor.close()

    return render_template('bookings.html', bookings=bookings, guests=guests, rooms=rooms, selected_type=selected_type)

@app.route('/addBooking', methods=['POST'])
def add_booking():
    guest_id = request.form['guest_id']
    room_type = request.form['room_type']
    room_id = request.form['room_id']
    exp_check_in = request.form['exp_check_in']
    exp_check_out = request.form['exp_check_out']
    status = request.form['status']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        INSERT INTO Bookings (guest_id, room_type, room_id, exp_check_in, exp_check_out, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (guest_id, room_type, room_id, exp_check_in, exp_check_out, status))
    mysql.connection.commit()
    cursor.close()
    return redirect('/bookings')

@app.route('/updateBooking', methods=['POST'])
def updateBooking():
    booking_id = int(request.form['edit_booking_id'])
    guest_id = request.form['edit_guest_id']
    room_type = request.form['edit_room_type']
    room_id = request.form['edit_room_id']
    exp_check_in = request.form['exp_check_in']
    exp_check_out = request.form['exp_check_out']
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

@app.route('/deleteBooking/<int:booking_id>', methods=['GET'])
def deleteBooking(booking_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM Bookings WHERE booking_id = %s", (booking_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/bookings')

# gina - ROUTE FOR CHECKIN/OUT

@app.route('/checkin', methods=['POST'])
def checkin():
    booking_id = request.form['booking_id']
    actual_check_in = request.form['actual_check_in']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Update booking table
    cursor.execute("""
        UPDATE Bookings
        SET actual_check_in = %s
        WHERE booking_id = %s
    """, (actual_check_in, booking_id))

    # Get room_id and update room status
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
    # Update booking
    cursor.execute("""
        UPDATE Bookings
        SET actual_check_out = %s
        WHERE booking_id = %s
    """, (actual_check_out, booking_id))

    # Get room_id and update status to Vacant
    cursor.execute("SELECT room_id FROM Bookings WHERE booking_id = %s", (booking_id,))
    room = cursor.fetchone()
    if room:
        cursor.execute("UPDATE Room SET room_status = 'Vacant' WHERE room_id = %s", (room['room_id'],))
    else:
        return "Room not found", 404

    mysql.connection.commit()
    cursor.close()
    return redirect('/roomGuest')

@app.route('/addPayment/<int:booking_id>', methods=['GET', 'POST'])
def add_payment(booking_id):
    if request.method == 'POST':
        amount = request.form['amount']
        payment_date = request.form['payment_date']
        payment_method = request.form['payment_method']
        status = request.form['status']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "INSERT INTO Payment (booking_id, amount, payment_date, payment_method, status) VALUES (%s, %s, %s, %s, %s)",
            (booking_id, amount, payment_date, payment_method, status)
        )
        mysql.connection.commit()
        cursor.close()
        return redirect('/payments')
    return render_template('add_payment.html', booking_id=booking_id)

@app.route('/bill/<int:guest_id>')
def view_bill(guest_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Get all requests for this guest (via RoomGuest)
    cursor.execute("""
        SELECT r.*, s.item, s.amount
        FROM Requests r
        JOIN bookings b ON r.booking_id = b.booking_id
        JOIN Services s ON r.service_id = s.service_id
        WHERE b.booking_id = %s
    """, (guest_id,))
    requests = cursor.fetchall()
    total_bill = sum(r['totalCost'] for r in requests)
    cursor.close()
    return render_template('bill.html', requests=requests, total_bill=total_bill, guest_id=guest_id)

@app.route('/users')
def view_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template('users.html', users=users)

@app.route('/addUser', methods=['POST'])
def add_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    email = request.form['email']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s)",
        (username, password, role, email)
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

@app.route('/approveUser/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("UPDATE users SET status = 'Active' WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/users')

# Example: restrict to admin only
@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)