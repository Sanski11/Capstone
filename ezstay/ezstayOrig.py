from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime

app = Flask(__name__)

#SQL Server connection string
#app.config['SQLALCHEMY_DATABASE_URI'] = (
 #  'mssql+pyodbc://LAPTOP-8RDEM6JD\MSSQLSERVER01/ezStay'
  #  '?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
#)
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#MySQL connection string
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/hotelsystem/ezstay'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Initialize SQLAlchemy
db = SQLAlchemy(app)

#Room model
class Room(db.Model):
    __tablename__ = 'room'
    room_id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String)
    room_type = db.Column(db.String)
    room_status = db.Column(db.String)

#Staff model
class Staff(db.Model):
    __tablename__ = 'staff'
    staff_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    role = db.Column(db.String)
    email = db.Column(db.String)
    phone = db.Column(db.String)
 
 #Guest model   
class Guest(db.Model):
    __tablename__ = 'guest'
    guest_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    middle_name = db.Column(db.String)
    last_name = db.Column(db.String)
    email = db.Column(db.String)
    phone = db.Column(db.String)
    
#Services model
class Services(db.Model):
    __tablename__ = 'services'
    service_id = db.Column(db.Integer, primary_key=True)
    service_type = db.Column(db.String)
    item = db.Column(db.String)
    amount = db.Column(db.Numeric)

#RoomGuest model
class RoomGuest(db.Model):
    __tablename__ = 'roomguest'
    roomGuest_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('Room.room_id'))
    guest_id = db.Column(db.Integer, db.ForeignKey('Guest.guest_id'))
    checkin_date = db.Column(db.DateTime)
    checkout_date = db.Column(db.DateTime)
    
# Requests model
class Requests(db.Model):
    __tablename__ = 'requests'
    request_id = db.Column(db.Integer, primary_key=True)
    roomGuest_id = db.Column(db.Integer, db.ForeignKey('RoomGuest.roomGuest_id'))
    service_id = db.Column(db.Integer, db.ForeignKey('Services.service_id'))
    quantity = db.Column(db.Integer)
    unitCost = db.Column(db.Numeric)
    totalCost = db.Column(db.Numeric)
    status = db.Column(db.String)
    request_time = db.Column(db.DateTime)


#Guest list for demo purposes
guest_list = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/guests')
def show_guest():
    query = request.args.get('search', '')

    if query:
        guests = Guest.query.filter(
            Guest.first_name.ilike(f"%{query}%") |
            Guest.middle_name.ilike(f"%{query}%") |
            Guest.last_name.ilike(f"%{query}%") |
            Guest.email.ilike(f"%{query}%") |
            Guest.phone.ilike(f"%{query}%")
        ).all()
    else:
        guests = Guest.query.all()

    return render_template('guests.html', guests=guests)

@app.route('/delete/<int:index>')
def delete_guest(index):
    if 0 <= index < len(guest_list):
        guest_list.pop(index)
    return redirect('/guests')

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def editGuest(index):
    if index >= len(guest_list):
        return redirect('/guests')
    if request.method == 'POST':
        guest_list[index]['name'] = request.form['name']
        guest_list[index]['email'] = request.form['email']
        return redirect('/guests')
    guest = guest_list[index]
    return render_template('editGuest.html', guest=guest, index=index)


@app.route('/requests')
def view_requests():
    search = request.args.get('search', '')

    if search:
        results = Requests.query.filter(
            or_(
                Requests.request_id.like(f"%{search}%"),
                Requests.roomGuest_id.like(f"%{search}%"),
                Requests.service_id.like(f"%{search}%"),
                Requests.quantity.like(f"%{search}%"),
                Requests.unitCost.like(f"%{search}%"),
                Requests.totalCost.like(f"%{search}%"),
                Requests.status.ilike(f"%{search}%"),
                Requests.request_time.cast(db.String).like(f"%{search}%")
            )
        ).all()
    else:
        results = Requests.query.all()

    return render_template('requests.html', requests=results)

@app.route('/rooms')
def rooms():
    query = request.args.get('search', '')

    if query:
        rooms = Room.query.filter(
            Room.room_number.ilike(f"%{query}%") |
            Room.room_type.ilike(f"%{query}%") |
            Room.room_status.ilike(f"%{query}%")
        ).all()
    else:
        rooms = Room.query.all()

    return render_template('rooms.html', rooms=rooms)
    
    
@app.route('/services')
def services():
    query = request.args.get('search', '')

    if query:
        services = Services.query.filter(
            Services.service_type.ilike(f"%{query}%") |
            Services.item.ilike(f"%{query}%")
        ).all()
    else:
        services = Services.query.all()

    return render_template('services.html', services=services)
    
@app.route('/checkin')
def checkin():
    return render_template('checkin.html')

@app.route('/staff')
def show_staff():
    query = request.args.get('search', '')

    if query:
        staffs = Staff.query.filter(
            Staff.first_name.ilike(f"%{query}%") |
            Staff.last_name.ilike(f"%{query}%") |
            Staff.role.ilike(f"%{query}%") |
            Staff.email.ilike(f"%{query}%") |
            Staff.phone.ilike(f"%{query}%")
        ).all()
    else:
        staffs = Staff.query.all()

    return render_template('staff.html', staffs=staffs)

from sqlalchemy import cast, String

@app.route('/roomGuest')
def show_roomGuest():
    query = request.args.get('search', '')

    if query:
        roomGuests = RoomGuest.query.filter(
            cast(RoomGuest.room_id, String).ilike(f"%{query}%") |
            cast(RoomGuest.guest_id, String).ilike(f"%{query}%") |
            cast(RoomGuest.checkin_date, String).like(f"%{query}%") |
            cast(RoomGuest.checkout_date, String).like(f"%{query}%")
        ).all()
    else:
        roomGuests = RoomGuest.query.all()

    return render_template('roomGuest.html', roomGuests=roomGuests)

@app.route('/addRoom', methods=['POST'])
def add_rooms():
    roomNumber = request.form['room_number']
    roomType = request.form['room_type']
    roomStatus = request.form['room_status']
    new_room = Room(room_number=roomNumber, room_type=roomType, room_status=roomStatus)
    db.session.add(new_room)
    db.session.commit()
    return redirect('/rooms')

@app.route('/updateRoom', methods=['POST'])
def updateRoom():
    room_id = int(request.form['edit_room_id'])
    room = Room.query.get(room_id)

    room.room_number = request.form['edit_room_number']
    room.room_type = request.form['edit_room_type']
    room.room_status = request.form['edit_room_status']

    db.session.commit()
    return redirect('/rooms')

@app.route('/deleteRoom/<int:room_id>', methods=['GET'])
def deleteRoom(room_id):
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    return redirect('/rooms')

@app.route('/addGuests', methods=['POST'])
def add_guests():
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']

    new_guest = Guest(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        email=email,
        phone=phone
    )
    db.session.add(new_guest)
    db.session.commit()
    return redirect('/guests')

@app.route('/updateGuests', methods=['POST'])
def updateGuests():
    guest_id = int(request.form['edit_guest_id'])
    guest = Guest.query.get(guest_id)

    guest.first_name = request.form['edit_first_name']
    guest.middle_name = request.form['edit_middle_name']
    guest.last_name = request.form['edit_last_name']
    guest.email = request.form['edit_email']
    guest.phone = request.form['edit_phone']

    db.session.commit()
    return redirect('/guests')

@app.route('/addRequest', methods=['POST'])
def add_request():
    roomGuest_id = request.form['roomGuest_id']
    service_id = request.form['service_id']
    quantity = int(request.form['quantity'])
    unitCost = float(request.form['unitCost'])
    status = request.form['status']
    request_time = datetime.strptime(request.form['request_time'], '%Y-%m-%dT%H:%M')

    totalCost = quantity * unitCost

    new_request = Requests(
        roomGuest_id=roomGuest_id,
        service_id=service_id,
        quantity=quantity,
        unitCost=unitCost,
        totalCost=totalCost,
        status=status,
        request_time=request_time
    )

    db.session.add(new_request)
    db.session.commit()
    return redirect('/requests')

from datetime import datetime

@app.route('/updateRequest', methods=['POST'])
def updateRequest():
    request_id = int(request.form['edit_request_id'])
    req = Requests.query.get(request_id)

    req.roomGuest_id = request.form['edit_roomGuest_id']
    req.service_id = request.form['edit_service_id']
    req.quantity = request.form['edit_quantity']
    req.unitCost = request.form['edit_unitCost']
    req.totalCost = request.form['edit_totalCost']
    req.status = request.form['edit_status']
    
    # Convert datetime-local input format to Python datetime
    raw_time = request.form['edit_request_time']
    req.request_time = datetime.strptime(raw_time, "%Y-%m-%dT%H:%M")

    db.session.commit()
    return redirect('/requests')


@app.route('/deleteRequest/<int:request_id>', methods=['GET'])
def deleteRequest(request_id):
    request = Requests.query.get_or_404(request_id)
    db.session.delete(request)
    db.session.commit()
    return redirect('/requests')

@app.route('/addService', methods=['POST'])
def add_service():
    service_type = request.form['service_type']
    item = request.form['item']
    amount = request.form['amount']

    new_service = Services(service_type=service_type, item=item, amount=amount)
    db.session.add(new_service)
    db.session.commit()

    return redirect('/services')

@app.route('/addStaff', methods=['POST'])
def add_staff():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    role = request.form['role']
    email = request.form['email']
    phone = request.form['phone']

    new_staff = Staff(
        first_name=first_name,
        last_name=last_name,
        role=role,
        email=email,
        phone=phone
    )
    db.session.add(new_staff)
    db.session.commit()
    return redirect('/staff')

@app.route('/updateStaff', methods=['POST'])
def updateStaff():
    staff_id = int(request.form['edit_staff_id'])
    staff = Staff.query.get(staff_id)

    #service.service_id = request.form['edit_service_id']
    staff.first_name = request.form['edit_first_name']
    staff.last_name = request.form['edit_last_name']
    staff.role = request.form['edit_role']
    staff.email = request.form['edit_email']
    staff.phone = request.form['edit_phone']

    db.session.commit()
    return redirect('/staff')


@app.route('/deleteStaff/<int:staff_id>', methods=['GET'])
def deleteStaff(staff_id):
    staff = Staff.query.get_or_404(staff_id)
    db.session.delete(staff)
    db.session.commit()
    return redirect('/staff')

@app.route('/updateServices', methods=['POST'])
def updateServices():
    service_id = int(request.form['edit_service_id'])
    service = Services.query.get(service_id)

    #service.service_id = request.form['edit_service_id']
    service.service_type = request.form['edit_service_type']
    service.item = request.form['edit_item']
    service.amount = request.form['edit_amount']

    db.session.commit()
    return redirect('/services')

@app.route('/deleteServices/<int:service_id>', methods=['GET'])
def deleteServices(service_id):
    service = Services.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    return redirect('/services')

@app.route('/addRoomGuest', methods=['POST'])
def add_room_guest():
    room_id = request.form['room_id']
    guest_id = request.form['guest_id']
    checkin_date = request.form['checkin_date']
    checkout_date = request.form['checkout_date']

    new_roomguest = RoomGuest(
        room_id=room_id,
        guest_id=guest_id,
        checkin_date=checkin_date,
        checkout_date=checkout_date
    )
    db.session.add(new_roomguest)
    db.session.commit()
    return redirect('/roomGuest')

@app.route('/deleteGuest/<int:guest_id>', methods=['GET'])
def deleteGuest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    db.session.delete(guest)
    db.session.commit()
    return redirect('/guests')

if __name__ == '__main__':
    app.run(debug=True)