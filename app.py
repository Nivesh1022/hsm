from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import os
from werkzeug.security import generate_password_hash, check_password_hash

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'app123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_management.sqlite3'
    app.config['CHART_FOLDER'] = os.path.join('static', 'charts')
    os.makedirs(app.config['CHART_FOLDER'], exist_ok=True)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PASSWORD_HASH'] = 'app123'
    db.init_app(app)
    return app

db = SQLAlchemy()

class Admin(db.Model):
    username = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    admin_email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    doctors = db.relationship('Doctor', backref='department', lazy=True)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    availability = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    blacklisted = db.Column(db.Boolean, default=False)
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(30))
    password = db.Column(db.String(255), nullable=False)
    blacklisted = db.Column(db.Boolean, default=False)
    appointments = db.relationship('Appointment', backref='patient', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(30), default='Booked')
    treatment = db.relationship("Treatment", backref="appointment", uselist=False)

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(10), nullable=True)
    end_time = db.Column(db.String(10), nullable=True)

def create_admin():
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(username='admin', name='Admin', admin_email='admin@hospital.com', password=generate_password_hash('admin123'))
        db.session.add(admin)
        db.session.commit()

app = create_app()

with app.app_context():
    db.create_all()
    create_admin()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        email_or_name = request.form['email_or_name']
        password = request.form['password']

        if role == "admin":
            admin = Admin.query.filter_by(admin_email=email_or_name).first()
            if admin and check_password_hash(admin.password, password):
                session['admin_username'] = admin.username
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid Admin credentials")

        elif role == "doctor":
            doctor = Doctor.query.filter_by(name=email_or_name).first()
            if doctor and check_password_hash(doctor.password, password):
                session['doctor_id'] = doctor.id
                return redirect(url_for('doctor_dashboard'))
            else:
                flash("Invalid Doctor credentials")

        elif role == "patient":
            patient = Patient.query.filter_by(email=email_or_name).first()
            if patient and check_password_hash(patient.password, password):
                session['patient_id'] = patient.id
                return redirect(url_for('patient_dashboard'))
            else:
                flash("Invalid Patient credentials")

    return render_template("home.html")

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_username' not in session:
        return redirect(url_for('home'))

    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()

    doctors = Doctor.query.all()
    patients = Patient.query.all()
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()

    return render_template('admin_dashboard.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           doctors=doctors,
                           patients=patients,
                           appointments=appointments,
                           results=[])

@app.route('/unblacklist_doctor/<int:doctor_id>')
def unblacklist_doctor(doctor_id):
    if 'admin_username' not in session:
        return redirect(url_for('home'))

    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.blacklisted = False
    db.session.commit()

    flash("Doctor un-blacklisted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/unblacklist_patient/<int:patient_id>')
def unblacklist_patient(patient_id):
    if 'admin_username' not in session:
        return redirect(url_for('home'))

    patient = Patient.query.get_or_404(patient_id)
    patient.blacklisted = False
    db.session.commit()

    flash("Patient un-blacklisted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_search')
def admin_search():
    if 'admin_username' not in session:
        return redirect(url_for('home'))

    query = request.args.get('query', '')
    results = []

    if query:
        doctors = Doctor.query.filter(Doctor.name.ilike(f"%{query}%")).all()
        patients = Patient.query.filter(Patient.name.ilike(f"%{query}%")).all()
        results = [f"Doctor: {d.name} ({d.specialization})" for d in doctors]
        results += [f"Patient: {p.name} ({p.email})" for p in patients]

    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    doctors = Doctor.query.all()
    appointments = Appointment.query.all()

    return render_template("admin_dashboard.html",
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           doctors=doctors,
                           appointments=appointments,
                           results=results)

@app.route('/blacklist_doctor/<int:doctor_id>')
def blacklist_doctor(doctor_id):
    if 'admin_username' not in session:
        return redirect(url_for('home'))

    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.blacklisted = True
    db.session.commit()

    flash("Doctor blacklisted!", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)

    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.specialization = request.form['specialization']
        doctor.availability = request.form['availability']
        db.session.commit()
        flash("Doctor updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_doctor.html', doctor=doctor)

@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    if 'admin_username' not in session:
        return redirect('/login')

    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted!", "danger")
    return redirect('/admin_dashboard')

@app.route('/delete_appointment/<int:id>')
def delete_appointment(id):
    if 'admin_username' not in session:
        return redirect('/login')

    appt = Appointment.query.get_or_404(id)
    db.session.delete(appt)
    db.session.commit()

    flash("Appointment deleted!", "danger")
    return redirect('/admin_dashboard')

@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    if 'admin_username' not in session:
        return redirect('/login')

    doc = Doctor.query.get_or_404(id)
    db.session.delete(doc)
    db.session.commit()

    flash("Doctor deleted!", "danger")
    return redirect('/admin_dashboard')

@app.route('/blacklist_patient/<int:patient_id>')
def blacklist_patient(patient_id):
    if 'admin_username' not in session:
        return redirect(url_for('home'))

    patient = Patient.query.get_or_404(patient_id)
    patient.blacklisted = True
    db.session.commit()

    flash("Patient blacklisted!", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/register')
def register():
    return render_template("register.html")

@app.route('/register_patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        existing = Patient.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered!", "danger")
            return redirect(url_for('register_patient'))

        hashed_pass = generate_password_hash(password)

        new_patient = Patient(name=name, email=email, phone=phone, password=hashed_pass)
        db.session.add(new_patient)
        db.session.commit()

        flash("Patient Registered Successfully! Please login.", "success")
        return redirect(url_for('home'))

    return render_template("register_patient.html")

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'patient_id' not in session:
        return redirect('/login')

    patient = Patient.query.get(session['patient_id'])
    today = datetime.today()
    next_week = today + timedelta(days=7)

    upcoming = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date >= today.date()
    ).all()

    past = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date < today.date()
    ).all()

    specializations = [d.specialization for d in Doctor.query.distinct(Doctor.specialization).all()]
    doctors = Doctor.query.all()

    return render_template("patient_dashboard.html",
                           patient=patient,
                           upcoming=upcoming,
                           past=past,
                           specializations=specializations,
                           doctors=doctors)

@app.route("/doctor_suggestions/<spec>")
def doctor_suggestions(spec):
    doctors = Doctor.query.filter_by(specialization=spec).all()
    names = [d.name for d in doctors]
    return jsonify(names)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'patient_id' not in session:
        return redirect(url_for('login'))

    patient = Patient.query.get(session['patient_id'])
    patient.name = request.form['name']
    patient.email = request.form['email']
    patient.phone = request.form['phone']
    db.session.commit()

    flash("Profile updated!", "success")
    return redirect(url_for('patient_dashboard'))

@app.route('/search_doctor', methods=['GET', 'POST'])
def search_doctor():
    specializations = db.session.query(Doctor.specialization).distinct().all()
    specializations = [s[0] for s in specializations]

    doctors = None

    if request.method == 'POST':
        specialization = request.form['specialization']
        location = request.form.get('location')

        query = Doctor.query.filter_by(specialization=specialization)

        if location and location.strip() != "":
            query = query.filter(Doctor.location.ilike(f"%{location}%"))

        doctors = query.all()

    return render_template("search_doctor.html",
                           specializations=specializations,
                           doctors=doctors)

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'patient_id' not in session:
        return redirect(url_for('login'))

    doctor_id = request.form['doctor_id']
    date_str = request.form['date']
    time_str = request.form['time']

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    time_obj = datetime.strptime(time_str, "%H:%M").time()

    new_app = Appointment(
        patient_id=session['patient_id'],
        doctor_id=doctor_id,
        date=date_obj,
        time=time_obj,
        status="Booked"
    )

    db.session.add(new_app)
    db.session.commit()

    flash("Appointment booked successfully!", "success")
    return redirect(url_for('patient_dashboard'))

@app.route('/reschedule/<int:appointment_id>', methods=['POST'])
def reschedule(appointment_id):
    appt = Appointment.query.get(appointment_id)

    new_date = request.form['date']
    new_time = request.form['time']

    appt.date = new_date
    appt.time = new_time

    db.session.commit()

    flash("Appointment rescheduled!", "info")
    return redirect(url_for('patient_dashboard'))

@app.route('/cancel/<int:appointment_id>')
def cancel(appointment_id):
    appt = Appointment.query.get(appointment_id)
    appt.status = "Cancelled"
    db.session.commit()

    flash("Appointment cancelled.", "warning")
    return redirect(url_for('patient_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/register_doctor', methods=['GET', 'POST'])
def register_doctor():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        availability = request.form['availability']
        password = request.form['password']

        hashed_pass = generate_password_hash(password)

        new_doc = Doctor(name=name, specialization=specialization, availability=availability, password=hashed_pass)
        db.session.add(new_doc)
        db.session.commit()

        flash("Doctor Registered Successfully!", "success")
        return redirect(url_for('home'))

    return render_template("register_doctor.html")

@app.route("/doctor_dashboard")
def doctor_dashboard():
    if "doctor_id" not in session:
        return redirect("/login")

    doctor_id = session["doctor_id"]
    doctor = Doctor.query.get(doctor_id)

    today = date.today()
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date >= today
    ).order_by(Appointment.date.asc(), Appointment.time.asc()).all()

    availability = Availability.query.filter_by(doctor_id=doctor_id).all()

    assigned_patients = Patient.query.join(Appointment, Appointment.patient_id == Patient.id).filter(
        Appointment.doctor_id == doctor_id).distinct().all()

    patients = Patient.query.all()
    patient_list = [{"id": p.id, "name": p.name, "email": p.email, "phone": p.phone} for p in patients]

    return render_template("doctor_dashboard.html",
                           doctor=doctor,
                           upcoming_appointments=upcoming_appointments,
                           availability=availability,
                           assigned_patients=assigned_patients,
                           patient_list=patient_list)

@app.route("/update_appointment_status/<int:appt_id>", methods=["POST"])
def update_appointment_status(appt_id):
    if "doctor_id" not in session:
        return redirect("/login")

    new_status = request.form.get("status")
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = new_status
    db.session.commit()
    flash(f"Appointment marked {new_status}", "info")
    return redirect("/doctor_dashboard")

@app.route('/update_availability', methods=['POST'])
def update_availability():
    if 'doctor_id' not in session:
        return redirect('/login')

    doctor_id = session['doctor_id']
    Availability.query.filter_by(doctor_id=doctor_id).delete()

    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for day in week_days:
        start = request.form.get(f"{day}_from")
        end = request.form.get(f"{day}_to")

        if start and end:
            new_avail = Availability(
                doctor_id=doctor_id,
                day=day,
                start_time=start,
                end_time=end
            )
            db.session.add(new_avail)

    db.session.commit()
    return redirect('/doctor_dashboard')

@app.route("/add_treatment", methods=["POST"])
def add_treatment():
    if "doctor_id" not in session:
        return redirect("/login")

    doctor_id = session["doctor_id"]
    patient_id = request.form.get("patient_id")

    appt = Appointment.query.filter_by(patient_id=patient_id, doctor_id=doctor_id).order_by(
        Appointment.date.desc(), Appointment.time.desc()).first()

    if not appt:
        flash("No appointment found for this patient with you.", "warning")
        return redirect("/doctor_dashboard")

    diagnosis = request.form.get("diagnosis")
    prescription = request.form.get("prescription")
    notes = request.form.get("treatment")

    treat = Treatment(
        appointment_id=appt.id,
        diagnosis=diagnosis,
        prescription=prescription,
        notes=notes
    )

    appt.status = "Completed"
    db.session.add(treat)
    db.session.commit()
    flash("Treatment saved and appointment marked Completed.", "success")
    return redirect("/doctor_dashboard")

@app.route('/update_treatment', methods=['POST'])
def update_treatment():
    if 'doctor_id' not in session:
        return redirect('/login')

    patient_id = request.form.get("patient_id")
    diagnosis = request.form.get("diagnosis")
    treatment = request.form.get("treatment")
    prescription = request.form.get("prescription")

    patient = Patient.query.get(patient_id)
    patient.diagnosis = diagnosis
    patient.treatment = treatment
    patient.prescription = prescription

    db.session.commit()

    return redirect('/doctor_dashboard')

@app.route('/complete_appointment/<int:appointment_id>', methods=['POST'])
def complete_appointment(appointment_id):
    if 'doctor_id' not in session:
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)

    diagnosis = request.form['diagnosis']
    prescription = request.form['prescription']
    notes = request.form['notes']

    appointment.status = "Completed"

    treatment = Treatment(
        appointment_id=appointment.id,
        diagnosis=diagnosis,
        prescription=prescription,
        notes=notes
    )

    db.session.add(treatment)
    db.session.commit()

    flash("Appointment completed successfully!", "success")
    return redirect(url_for('doctor_dashboard'))

@app.route("/add_availability", methods=["POST"])
def add_availability():
    if "doctor_id" not in session:
        return redirect("/login")

    doctor_id = session["doctor_id"]
    day = request.form.get("day")
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    if not (day and start_time and end_time):
        flash("Please provide day, start and end time.", "warning")
        return redirect("/doctor_dashboard")

    new_slot = Availability(
        doctor_id=doctor_id,
        day=day,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(new_slot)
    db.session.commit()
    flash("Availability slot added.", "success")
    return redirect("/doctor_dashboard")

@app.route("/cancel_appointment/<int:appointment_id>")
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = "Cancelled"
    db.session.commit()
    return redirect("/doctor_dashboard")

@app.route('/patient_history/<int:patient_id>')
def patient_history(patient_id):
    if 'doctor_id' not in session:
        return redirect(url_for('login'))

    patient = Patient.query.get_or_404(patient_id)
    history = Appointment.query.filter_by(patient_id=patient.id,status="Completed" ).all()

    return render_template("patient_history.html",patient=patient, history=history)

if __name__ == '__main__':
    app.run(debug=True)
