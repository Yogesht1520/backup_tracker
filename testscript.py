from app import db, BackupJob, app

with app.app_context():
    new_job = BackupJob(job_name='new_backup')
    db.session.add(new_job)
    db.session.commit()

    jobs = BackupJob.query.all()
    print(jobs)

