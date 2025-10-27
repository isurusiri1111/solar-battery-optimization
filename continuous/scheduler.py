from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.tasks = {}
        logger.info("Task scheduler initialized")
    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")
    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
