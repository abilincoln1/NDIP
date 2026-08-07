"""
NDIP Phase D.3 — Scheduler V2
File: scheduler_v2.py  (replaces / supplements existing scheduler at /app/scheduler_v2.py)

Integrates Phase D.3 jobs into the existing scheduler infrastructure.
Uses the `schedule` library (already in the scheduler container).

Hourly (every 60 min from startup):
  - nlp_extraction_job
  - duplicate_detection_job
  - verification_queue_job
  - notification_retry_job

Nightly (02:00 UTC):
  - impact_score_rebuild_job
  - leaderboard_rebuild_job
  - chapter_summaries_job
  - cleanup_job

All jobs are wrapped in try/except so a failing job never crashes the
scheduler loop. Job outcomes are written to scheduler_job_log.

To integrate into the existing scheduler entrypoint, add at the bottom:
    from scheduler_v2 import register_d3_jobs
    register_d3_jobs()
Or run this file directly for standalone D3 scheduling.
"""
import logging
import os
import sys
import time

# Add /app to path so app.* imports resolve
sys.path.insert(0, "/app")

import schedule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ndip.scheduler_v2")


def _safe_run(job_fn):
    """Wrap a job function in error handling so scheduler loop survives failures."""
    def wrapper():
        logger.info("Starting job: %s", job_fn.__name__)
        try:
            result = job_fn()
            logger.info("Completed job: %s — %s", job_fn.__name__, result)
        except Exception as e:
            logger.error("Job failed: %s — %s", job_fn.__name__, e, exc_info=True)
    wrapper.__name__ = job_fn.__name__
    return wrapper


def register_d3_jobs():
    """Register all D3 jobs with the schedule library."""
    try:
        from app.scheduler.d3_jobs import (
            nlp_extraction_job,
            duplicate_detection_job,
            verification_queue_job,
            notification_retry_job,
            impact_score_rebuild_job,
            leaderboard_rebuild_job,
            chapter_summaries_job,
            cleanup_job,
        )
    except ImportError as e:
        logger.error("Could not import D3 jobs: %s", e)
        return

    # Hourly jobs
    schedule.every(60).minutes.do(_safe_run(nlp_extraction_job))
    schedule.every(60).minutes.do(_safe_run(duplicate_detection_job))
    schedule.every(60).minutes.do(_safe_run(verification_queue_job))
    schedule.every(60).minutes.do(_safe_run(notification_retry_job))

    # Nightly jobs at 02:00 UTC
    schedule.every().day.at("02:00").do(_safe_run(impact_score_rebuild_job))
    schedule.every().day.at("02:15").do(_safe_run(leaderboard_rebuild_job))
    schedule.every().day.at("02:30").do(_safe_run(chapter_summaries_job))
    schedule.every().day.at("02:45").do(_safe_run(cleanup_job))

    logger.info("D3 jobs registered: 4 hourly + 4 nightly")


def run_once_now():
    """Run all D3 jobs immediately — used for initial validation."""
    try:
        from app.scheduler.d3_jobs import run_all_hourly, run_all_nightly
        logger.info("Running all D3 hourly jobs now...")
        hourly_results = run_all_hourly()
        logger.info("Hourly results: %s", hourly_results)
        logger.info("Running all D3 nightly jobs now...")
        nightly_results = run_all_nightly()
        logger.info("Nightly results: %s", nightly_results)
    except Exception as e:
        logger.error("run_once_now failed: %s", e, exc_info=True)


if __name__ == "__main__":
    logger.info("NDIP Scheduler V2 starting...")
    register_d3_jobs()

    if "--run-now" in sys.argv:
        run_once_now()

    logger.info("Entering scheduler loop...")
    while True:
        schedule.run_pending()
        time.sleep(30)
