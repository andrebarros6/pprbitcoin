"""
Scheduler service for automatic data updates
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import asyncio
import logging

from services.bitcoin_updater import BitcoinUpdater
from services.ppr_scraper import PPRScraperManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataUpdateScheduler:
    """
    Scheduler for automatic data updates
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.bitcoin_updater = BitcoinUpdater()
        self.ppr_scraper_manager = PPRScraperManager()

    async def update_bitcoin_price(self):
        """
        Update Bitcoin price (runs daily)
        """
        try:
            logger.info("🔄 Starting Bitcoin price update...")
            result = await self.bitcoin_updater.update_latest()

            if result['success']:
                logger.info(f"✅ Bitcoin updated: {result['price']} EUR")
            else:
                logger.error(f"❌ Bitcoin update failed: {result['error']}")

        except Exception as e:
            logger.error(f"❌ Error updating Bitcoin: {e}")

    async def update_ppr_quotas(self):
        """
        Update PPR quota values (runs daily)
        """
        try:
            logger.info("🔄 Starting PPR quotas update...")
            result = await self.ppr_scraper_manager.scrape_all()

            logger.info(f"✅ PPR update complete: {result['success']} success, {result['failed']} failed")

            if result['errors']:
                for error in result['errors']:
                    logger.error(f"   ✗ {error['ppr']}: {error['error']}")

        except Exception as e:
            logger.error(f"❌ Error updating PPRs: {e}")

    async def weekly_backup_check(self):
        """
        Weekly health check and logging (runs Sunday 2am)
        """
        try:
            logger.info("🔍 Running weekly health check...")

            from database import SessionLocal
            from models.bitcoin import BitcoinHistoricalData
            from models.ppr import PPR

            db = SessionLocal()
            try:
                btc_count = db.query(BitcoinHistoricalData).count()
                ppr_count = db.query(PPR).count()

                logger.info(f"   📊 Bitcoin records: {btc_count}")
                logger.info(f"   📊 PPR funds: {ppr_count}")
                logger.info("✅ Health check complete")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Health check error: {e}")

    def start(self):
        """
        Start the scheduler with all jobs
        """
        logger.info("🚀 Starting data update scheduler...")

        # Daily Bitcoin update at 09:00 UTC
        self.scheduler.add_job(
            self.update_bitcoin_price,
            CronTrigger(hour=9, minute=0),
            id='bitcoin_daily_update',
            name='Update Bitcoin Price',
            replace_existing=True
        )

        # Daily PPR update at 18:00 UTC (after market close)
        self.scheduler.add_job(
            self.update_ppr_quotas,
            CronTrigger(hour=18, minute=0),
            id='ppr_daily_update',
            name='Update PPR Quotas',
            replace_existing=True
        )

        # Weekly health check on Sunday at 02:00 UTC
        self.scheduler.add_job(
            self.weekly_backup_check,
            CronTrigger(day_of_week='sun', hour=2, minute=0),
            id='weekly_health_check',
            name='Weekly Health Check',
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        logger.info("✅ Scheduler started successfully")

        # Log scheduled jobs
        self.print_jobs()

    def stop(self):
        """
        Stop the scheduler
        """
        logger.info("🛑 Stopping scheduler...")
        self.scheduler.shutdown()
        logger.info("✅ Scheduler stopped")

    def print_jobs(self):
        """
        Print all scheduled jobs
        """
        logger.info("\n📅 Scheduled Jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"   • {job.name} - Next run: {job.next_run_time}")

    async def run_now(self, job_name: str):
        """
        Run a specific job immediately (for testing)

        Args:
            job_name: Name of job to run ('bitcoin', 'ppr', or 'health')
        """
        if job_name == 'bitcoin':
            await self.update_bitcoin_price()
        elif job_name == 'ppr':
            await self.update_ppr_quotas()
        elif job_name == 'health':
            await self.weekly_backup_check()
        else:
            logger.error(f"Unknown job: {job_name}")


# Global scheduler instance
scheduler = DataUpdateScheduler()


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "start":
            # Start scheduler and keep running
            scheduler.start()
            try:
                asyncio.get_event_loop().run_forever()
            except (KeyboardInterrupt, SystemExit):
                scheduler.stop()

        elif command == "test":
            # Test run all jobs once
            async def test_all():
                await scheduler.update_bitcoin_price()
                await scheduler.update_ppr_quotas()
                await scheduler.weekly_backup_check()

            asyncio.run(test_all())

        elif command == "bitcoin":
            # Test Bitcoin update
            asyncio.run(scheduler.update_bitcoin_price())

        elif command == "ppr":
            # Test PPR update
            asyncio.run(scheduler.update_ppr_quotas())

        else:
            print("Usage:")
            print("  python scheduler.py start    # Start scheduler daemon")
            print("  python scheduler.py test     # Test all jobs once")
            print("  python scheduler.py bitcoin  # Test Bitcoin update")
            print("  python scheduler.py ppr      # Test PPR update")
    else:
        print("Usage:")
        print("  python scheduler.py start    # Start scheduler daemon")
        print("  python scheduler.py test     # Test all jobs once")
        print("  python scheduler.py bitcoin  # Test Bitcoin update")
        print("  python scheduler.py ppr      # Test PPR update")