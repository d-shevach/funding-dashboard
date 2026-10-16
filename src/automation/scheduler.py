"""Task scheduler for automated operations"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from src.automation.tasks import (
    PriceUpdateTask,
    ExchangeRateUpdateTask,
    PortfolioSnapshotTask,
    ReportGenerationTask
)
from src.automation.daily_email import send_daily_report
from src.automation.returns import IntradayUpdateTask, ensure_return_columns
from src.automation.monthly_returns import update_benchmarks
from src.automation.backup import backup_database
from src.logger import get_logger

logger = get_logger("automation.scheduler")

TIMEZONE = "Asia/Jerusalem"


class AutomationScheduler:
    """Manages scheduled automated tasks"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._jobs_added = False

    def start(self):
        """Start the scheduler"""
        if self._jobs_added:
            logger.warning("Scheduler already started")
            return

        ensure_return_columns()
        self._add_jobs()
        self.scheduler.start()
        logger.info("Automation scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Automation scheduler stopped")

    def _add_jobs(self):
        """Add all scheduled jobs"""

        # NYSE closes 16:00 ET, which is 23:00 in Tel Aviv year-round
        self.scheduler.add_job(
            self._run_task_with_logging,
            CronTrigger(hour=23, minute=5, day_of_week="mon-fri", timezone=TIMEZONE),
            args=["Price Update", PriceUpdateTask.execute],
            id="price_update",
            name="Daily Price Update",
            replace_existing=True
        )
        logger.info("Added job: Daily Price Update (23:05 weekdays, Tel Aviv)")

        # US market 16:30-23:00 Tel Aviv
        self.scheduler.add_job(
            self._run_task_with_logging,
            CronTrigger(hour="16-22", minute="*/15", day_of_week="mon-fri", timezone=TIMEZONE),
            args=["Intraday Update", IntradayUpdateTask.execute],
            id="intraday_update",
            name="Intraday Update",
            replace_existing=True
        )
        logger.info("Added job: Intraday Update (every 15 min, 16:00-22:45 weekdays, Tel Aviv)")

        self.scheduler.add_job(
            self._run_task_with_logging,
            CronTrigger(hour=23, minute=30, day_of_week="mon-fri", timezone=TIMEZONE),
            args=["Benchmark Update", update_benchmarks],
            id="benchmark_update",
            name="Benchmark Update",
            replace_existing=True
        )
        logger.info("Added job: Benchmark Update (23:30 weekdays, Tel Aviv)")

        self.scheduler.add_job(
            self._run_task_with_logging,
            CronTrigger(hour=2, minute=0, timezone=TIMEZONE),
            args=["Database Backup", backup_database],
            id="database_backup",
            name="Database Backup",
            replace_existing=True
        )
        logger.info("Added job: Database Backup (02:00 daily, Tel Aviv)")

        self.scheduler.add_job(
            self._run_task_with_logging,
            CronTrigger(hour=23, minute=20, day_of_week="mon-fri", timezone=TIMEZONE),
            args=["Daily Email Report", send_daily_report],
            id="daily_email_report",
            name="Daily Email Report",
            replace_existing=True
        )
        logger.info("Added job: Daily Email Report (23:20 weekdays, Tel Aviv)")

        # Update exchange rates every 6 hours
        self.scheduler.add_job(
            self._run_task_with_logging,
            IntervalTrigger(hours=6),
            args=["Exchange Rate Update", ExchangeRateUpdateTask.execute],
            id="exchange_rate_update",
            name="Exchange Rate Update",
            replace_existing=True
        )
        logger.info("Added job: Exchange Rate Update (every 6 hours)")

        # Portfolio snapshot at midnight daily
        self.scheduler.add_job(
            self._run_task_with_logging,
            CronTrigger(hour=0, minute=5, timezone=TIMEZONE),
            args=["Portfolio Snapshot", PortfolioSnapshotTask.execute],
            id="portfolio_snapshot",
            name="Daily Portfolio Snapshot",
            replace_existing=True
        )
        logger.info("Added job: Daily Portfolio Snapshot (00:05)")

        self._jobs_added = True

    @staticmethod
    def _run_task_with_logging(task_name: str, task_func):
        """Run a task with logging"""
        try:
            logger.info(f"Starting task: {task_name}")
            result = task_func()

            if result and isinstance(result, dict):
                if result.get("errors"):
                    logger.warning(f"{task_name} completed with errors: {result['errors']}")
                else:
                    logger.info(f"{task_name} completed successfully: {result}")
            else:
                logger.info(f"{task_name} completed")

        except Exception as e:
            logger.error(f"Error in task {task_name}: {e}")

    def get_jobs(self) -> list:
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
            return False
