import logging

def setup_logger():
    logging.basicConfig(filename='backup_tracker.log',
                        level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s')
    return logging.getLogger()
