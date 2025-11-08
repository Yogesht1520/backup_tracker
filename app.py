from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from datetime import datetime
import random, logging, os
from anomaly_detector.anomaly_model import detect_anomalies
from database import db, BackupJob
from flask_socketio import SocketIO, emit
from urllib.parse import quote_plus
import smtplib
from email.message import EmailMessage
from vault_manager import encrypt_and_store, list_vault_files, decrypt_file
from flask import send_file
import os
from flask import request, send_file, jsonify
from cryptography.fernet import Fernet
import hashlib
import psutil



os.chdir(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(BASE_DIR, "vault")
DECRYPT_DIR = os.path.join(BASE_DIR, "restored")

os.makedirs(VAULT_DIR, exist_ok=True)
os.makedirs(DECRYPT_DIR, exist_ok=True)

# Ensure same vault key is used
KEY_PATH = os.path.join(BASE_DIR, "vault_key.key")
if os.path.exists(KEY_PATH):
    with open(KEY_PATH, "rb") as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)

fernet = Fernet(key)

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
"""
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
"""
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
    
    cpu_value = psutil.cpu_percent(interval=1)
    if cpu_value > 80:  # threshold for anomaly
        socketio.emit('anomaly_alert', {'cpu': cpu_value, 'message': 'Anomaly detected'})

""" 
    if stats["failed"] > 0:
        send_alert_email(stats["failed"])
"""  

with app.app_context():
    scheduler.add_job(id='Update Jobs', func=update_jobs, trigger='interval', seconds=30)
    scheduler.init_app(app)
    scheduler.start()


def compute_sha256(filepath):
    """Compute SHA-256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


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
    
@app.route('/vault/upload', methods=['POST'])
def vault_upload():
    """Encrypt and store uploaded file"""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    filename = file.filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    encrypted_filename = f"{filename}_{timestamp}.enc"
    file_path = os.path.join(VAULT_DIR, encrypted_filename)

    # Encrypt
    data = file.read()
    encrypted_data = fernet.encrypt(data)
    with open(file_path, "wb") as f:
        f.write(encrypted_data)

    hash_value = compute_sha256(file_path)
    hash_path = file_path + ".hash"
    with open(hash_path, "w") as h:
        h.write(hash_value)
    
    # Notify via Socket.IO (optional)
    socketio.emit('vault_update', {"message": f"{filename} encrypted successfully"})

    return jsonify({"message": "File encrypted and stored", "filename": encrypted_filename})


@app.route('/vault/list', methods=['GET'])
def vault_list():
    """List encrypted files in the vault"""
    files = []
    for file in os.listdir(VAULT_DIR):
        path = os.path.join(VAULT_DIR, file)
        size_kb = os.path.getsize(path) / 1024
        last_modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        files.append({
            "name": file,
            "size_kb": round(size_kb, 2),
            "modified": last_modified
        })
    return jsonify(files)

@app.route('/vault/verify/<filename>', methods=['GET'])
def vault_verify(filename):
    """Verify integrity of encrypted file using its hash"""
    file_path = os.path.join(VAULT_DIR, filename)
    hash_path = file_path + ".hash"

    if not os.path.exists(file_path):
        return jsonify({"error": "Encrypted file not found"}), 404
    if not os.path.exists(hash_path):
        return jsonify({"error": "Hash file missing"}), 404

    stored_hash = open(hash_path).read().strip()
    current_hash = compute_sha256(file_path)

    if stored_hash == current_hash:
        return jsonify({"verified": True, "message": "✅ Integrity check passed"})
    else:
        return jsonify({"verified": False, "message": "⚠️ File integrity compromised!"})

    with open(file_path, "rb") as f:
        decrypted_data = fernet.decrypt(f.read())
    restore_path = os.path.join(DECRYPT_DIR, filename.replace(".enc", ""))
    with open(restore_path, "wb") as f:
        f.write(decrypted_data)

    return send_file(restore_path, as_attachment=True)


@app.route('/vault/restore/<filename>', methods=['GET'])
def vault_restore(filename):
    """Decrypt and send back the original file"""
    file_path = os.path.join(VAULT_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "Encrypted file not found."}), 404

    try:
        with open(file_path, "rb") as enc_file:
            encrypted_data = enc_file.read()
        decrypted_data = fernet.decrypt(encrypted_data)

        # Create restored output file
        original_name = filename.replace(".enc", "")
        restore_path = os.path.join(DECRYPT_DIR, original_name)

        with open(restore_path, "wb") as f:
            f.write(decrypted_data)

        return send_file(
            restore_path,
            as_attachment=True,
            download_name=original_name
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/anomalies', methods=['GET'])
def api_anomalies():
    """Return recent metrics and anomaly flags"""
    import pandas as pd
    from anomaly_detector.anomaly_model import detect_anomalies

    csv_path = os.path.join(os.path.dirname(__file__), "anomaly_detector", "sample_metrics.csv")
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return jsonify({"error": "No metrics data found"}), 404

    try:
        df = detect_anomalies()  # This returns DataFrame with 'anomaly' and 'anomaly_label'
        df = df.tail(50)         # send last 50 records for charting

        records = df.to_dict(orient='records')
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@socketio.on('metrics_update')
def handle_metrics(data):
    socketio.emit('metrics_update', data)

@socketio.on('anomaly_alert')
def handle_anomaly(data):
    socketio.emit('anomaly_alert', data)




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use socketio.run() instead of app.run() for proper asynchronous support
    # Eventlet is automatically used if installed.
    # Set 'debug=True' for development mode.
    socketio.run(app, host='127.0.0.1', port=5050, debug=True)
