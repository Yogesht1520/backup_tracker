from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from datetime import datetime
import random, logging, os
from database import db, BackupJob
from flask_socketio import SocketIO, emit
from urllib.parse import quote_plus
import smtplib
from email.message import EmailMessage

# ---------- Flask Setup ----------
app = Flask(__name__)
password = quote_plus("Be/1229/2019-20")
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://root:{password}@localhost/backup_tracker"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

socketio = SocketIO(app, cors_allowed_origins="*")

# ---------- Logging Setup ----------
def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    logger = logging.getLogger("BackupTracker")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler('logs/backup_tracker.log')
    fh.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(fh)
    return logger

logger = setup_logger()
logger.info(" Flask app started")

# ---------- Scheduler ----------
scheduler = APScheduler()

def send_alert_email(failed_count):
    msg = EmailMessage()
    msg.set_content(f"{failed_count} backup job(s) failed!")
    msg['Subject'] = 'Backup Tracker Alert'
    msg['From'] = 'yogesht1520@gmail.com'
    msg['To'] = 'yt6399941@gmail.com'
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.starttls()
        s.login('yogesht1520@gmail.com', 'nbyrpwtwyliswsjf')
        s.send_message(msg)

def update_jobs():
    with app.app_context():
        jobs = BackupJob.query.filter_by(status='PENDING').all()
        for job in jobs:
            job.status = random.choice(['SUCCESS', 'FAILED'])
            job.logs = f"Job {job.job_name} completed with status {job.status}"
        db.session.commit()
        
        stats = {
        "total": BackupJob.query.count(),
        "success": BackupJob.query.filter_by(status='SUCCESS').count(),
        "failed": BackupJob.query.filter_by(status='FAILED').count(),
        "pending": BackupJob.query.filter_by(status='PENDING').count()
    }
    socketio.emit('job_update', stats)
    
    if stats["failed"] > 0:
        send_alert_email(stats["failed"])
        

with app.app_context():
    scheduler.add_job(id='Update Jobs', func=update_jobs, trigger='interval', seconds=30)
    scheduler.init_app(app)
    scheduler.start()

# ---------- Routes ----------
@app.route('/')
def home():
    return "Flask Backup Tracker Running"

@app.route('/dashboard')
def dashboard():
    jobs = BackupJob.query.order_by(BackupJob.timestamp.desc()).all()
    return render_template('dashboard.html', jobs=jobs)

@app.route('/create_job', methods=['POST'])
def create_job():
    data = request.json
    new_job = BackupJob(job_name=data['job_name'])
    db.session.add(new_job)
    db.session.commit()
    return jsonify({"message": "Job created", "job_id": new_job.id})

@app.route('/jobs', methods=['GET'])
def get_jobs():
    jobs = BackupJob.query.all()
    return jsonify([
        {"id": j.id, "name": j.job_name, "status": j.status, "timestamp": str(j.timestamp)} 
        for j in jobs
    ])
    
@app.route('/api/jobs')
def api_jobs():
    jobs = BackupJob.query.order_by(BackupJob.timestamp.asc()).all()
    return jsonify([
        {
            "id": j.id,
            "name": j.job_name,
            "status": j.status,
            "timestamp": j.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for j in jobs
    ])
    
@app.route('/api/stats')
def api_stats():
    total = BackupJob.query.count()
    success = BackupJob.query.filter_by(status='SUCCESS').count()
    failed = BackupJob.query.filter_by(status='FAILED').count()
    pending = BackupJob.query.filter_by(status='PENDING').count()

    success_rate = round((success / total) * 100, 2) if total > 0 else 0
    fail_rate = round((failed / total) * 100, 2) if total > 0 else 0

    return jsonify({
        "total": total,
        "success": success,
        "failed": failed,
        "pending": pending,
        "success_rate": success_rate,
        "fail_rate": fail_rate
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use socketio.run() instead of app.run() for proper asynchronous support
    # Eventlet is automatically used if installed.
    # Set 'debug=True' for development mode.
    socketio.run(app, host='127.0.0.1', port=5050, debug=True)
