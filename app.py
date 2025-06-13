from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from ezstay import db, Room

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = "mssql+pyodbc://localhost/ezStay?driver=ODBC+Driver+17+for+SQL+Server"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # Initialize the database with the app

# ROUTES

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/rooms')
def rooms():
    query = request.args.get('search', '')
    if query:
        all_rooms = Room.query.filter(
            Room.room_number.ilike(f"%{query}%") |
            Room.room_type.ilike(f"%{query}%") |
            Room.room_status.ilike(f"%{query}%")
        ).all()
    else:
        all_rooms = Room.query.all()
    return render_template("rooms.html", rooms=all_rooms)

@app.route('/addRoom', methods=['POST'])
def addRoom():
    room_number = request.form['room_number']
    room_type = request.form['room_type']
    room_status = request.form['room_status']

    new_room = Room(room_number=room_number, room_type=room_type, room_status=room_status)
    db.session.add(new_room)
    db.session.commit()

    return redirect('/rooms')

@app.route('/editRoom/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.room_number = request.form['room_number']
        room.room_type = request.form['room_type']
        room.room_status = request.form['room_status']
        db.session.commit()
        return redirect('/rooms')
    return render_template('editRooms.html', room=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)