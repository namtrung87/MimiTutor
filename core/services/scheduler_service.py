import logging
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from core.agents.scheduler_agent import scheduler_node
from core.state import AgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def start(self):
        if not self.is_running:
            # Job 1: Hourly optimization check
            self.scheduler.add_job(
                self.run_optimization_job, 
                'interval', 
                hours=1, 
                id='hourly_opt',
                next_run_time=datetime.datetime.now()
            )
            
            # Job 2: Morning Plan (7:00 AM)
            self.scheduler.add_job(
                self.run_morning_plan, 
                'cron', 
                hour=7, 
                minute=0, 
                id='morning_plan'
            )

            # Job 3: Commute Monitor (Check for bus ride starts)
            self.scheduler.add_job(
                self.check_commute_status,
                'interval',
                minutes=15,
                id='commute_monitor'
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("SchedulerService started.")

    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("SchedulerService stopped.")

    def run_optimization_job(self):
        logger.info("Running scheduled optimization job...")
        # In a real app, this would trigger a flow via the Supervisor or Universal Agent
        # Mocking an AgentState for the node
        state: AgentState = {
            "messages": ["System: Triggered scheduled optimization."],
            "user_id": "trungnguyen",
            "session_id": "auto-sched",
            "retry_count": 0,
            "is_valid": True,
            "parallel_outputs": {},
            "handoff_target": None
        }
        try:
            result = scheduler_node(state)
            logger.info("Optimization job completed.")
            # Here we would send a notification via Telegram if significant changes found
        except Exception as e:
            logger.error(f"Error in optimization job: {e}")

    def run_morning_plan(self):
        logger.info("Generating morning plan...")
        # Similar to run_optimization_job but with a specific 'morning' prompt context
        pass

    def check_commute_status(self):
        """Logic to detect and trigger commute mode."""
        now = datetime.datetime.now()
        # Mocking bus schedule: 6:30-8:30 AM and 4:30-6:30 PM
        is_commute_time = (6, 30) <= (now.hour, now.minute) <= (8, 30) or \
                          (16, 30) <= (now.hour, now.minute) <= (18, 30)
        
        if is_commute_time:
            logger.info("📍 Commute Time detected. Preparing background tasks...")
            # Trigger background research or recovery checks via the graph
            # This is where 'Passive Recovery' logic lives.

if __name__ == "__main__":
    service = SchedulerService()
    service.start()
    try:
        # Keep the main thread alive
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        service.stop()
