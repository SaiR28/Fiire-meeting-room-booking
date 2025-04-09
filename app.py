from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper functions
def get_available_dates():
    today = datetime.now().date()
    return [today + timedelta(days=i) for i in range(7) if (today + timedelta(days=i)).weekday() != 6]

def get_time_slots():
    return [f"{hour}:00-{hour+1}:00" for hour in range(9, 17)]

def get_booked_slots(date):
    bookings = Booking.query.filter_by(date=date).all()
    return [booking.time_slot for booking in bookings]

# Routes
@app.route('/')
def index():
    available_dates = get_available_dates()
    time_slots = get_time_slots()

    available_time_slots_per_date = {}
    for date in available_dates:
        booked_slots = get_booked_slots(date)
        available_slots = [slot for slot in time_slots if slot not in booked_slots]
        available_time_slots_per_date[date.strftime('%Y-%m-%d')] = available_slots

    return render_template('index.html', dates=available_dates, available_time_slots_per_date=available_time_slots_per_date)

@app.route('/book', methods=['POST'])
def book():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    company = request.form.get('company')
    date_str = request.form.get('date')
    time_slot = request.form.get('time_slot')

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format')
        return redirect(url_for('index'))

    if date not in get_available_dates():
        flash('Selected date is not available')
        return redirect(url_for('index'))

    if time_slot not in get_time_slots():
        flash('Invalid time slot')
        return redirect(url_for('index'))

    if time_slot in get_booked_slots(date):
        flash('This slot is already booked')
        return redirect(url_for('index'))

    user = User.query.filter_by(email=email).first()
    if user:
        daily_bookings = Booking.query.filter_by(user_id=user.id, date=date).count()
        if daily_bookings >= 2:
            flash('You cannot book more than 2 slots on the same day')
            return redirect(url_for('index'))
    else:
        user = User(name=name, email=email, phone=phone, company=company)
        db.session.add(user)
        db.session.commit()

    booking = Booking(date=date, time_slot=time_slot, user_id=user.id)
    db.session.add(booking)
    db.session.commit()

    flash('Booking successful!')
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    dates = get_available_dates()
    bookings_by_date = {}

    for date in dates:
        bookings = Booking.query.filter_by(date=date).all()
        bookings_with_user = []
        for booking in bookings:
            user = db.session.get(User, booking.user_id)
            bookings_with_user.append({
                'id': booking.id,
                'time_slot': booking.time_slot,
                'user_name': user.name,
                'user_email': user.email,
                'user_phone': user.phone,
                'user_company': user.company
            })
        bookings_by_date[date.strftime('%Y-%m-%d')] = bookings_with_user

    return render_template('admin_dashboard.html', bookings_by_date=bookings_by_date, dates=dates)

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('instance/bookings.db'):
        init_db()
    app.run(debug=True)
