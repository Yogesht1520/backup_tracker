from flask_sqlalchemy import SQLAlchemy

# Create a single shared SQLAlchemy instance
db = SQLAlchemy()

class BackupJob(db.Model):
    __tablename__ = 'backup_jobs'
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='PENDING')
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    logs = db.Column(db.Text)
