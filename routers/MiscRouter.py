import os
from datetime import datetime, timedelta
from fastapi import APIRouter
from fastapi import Query, Response, HTTPException
from app.internal import settings
from app.internal.ACTFastScheduler import scheduler
from app.internal.stats import StatsManager
import app.internal.logging

MiscRouter = APIRouter()

stats_manager = StatsManager(os.path.join(settings.STATS_PATH, settings.STATS_FILENAME))




@MiscRouter.get("/", tags=["Stats & Misc"])
async def get_version():
    return {"message": f"ACTFast API.",
            "version": settings.VERSION,
            }


@MiscRouter.get("/datatest", tags=["Stats & Misc"], responses={
    200: {
        "description": "This example can return data in JSON or CSV format. I plan on using this someday to connect this api to excel.",
        "content": {
            "application/json": {},
            "text/csv": {}
        },
    }
})
def get_sample_mixed_data(format: str = Query(default="json", enum=["json", "csv"])):
    import pandas as pd
    data =[
    {"name": "Jeff", "test": 1},
    {"name": "Steve", "test": 2},
    {"name": "Bob", "test": 3}]

    df = pd.DataFrame(data)

    if format == "csv":
        return Response(content=df.to_csv(index=False), media_type="text/csv")
    else:
        # Default to JSON
        return Response(content=df.to_json(orient="records"), media_type="application/json")




# check the status of the scheduler
@MiscRouter.get("/scheduler/status", tags=["Stats & Misc"])
async def get_scheduler_status():
    """
    Get the status of the scheduler jobs.

    (OK/ERROR) status is based on the 'process_live_labor' job. If the job is NOT scheduled to run, or the next runtime is not within the next 5 minutes, the status will be "ERROR".

    :return: List of jobs and their next run time.
    """
    scheduler_info = []
    labor_magic_status = "ERROR"

    try:
        for job in scheduler.get_jobs():
            scheduler_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.replace(tzinfo=None),
            })

        # This job is why we built the API, so it should be around a while.
        for job in scheduler_info:
            if job["name"] == "process_live_labor":
                if job["next_run_time"] is not None:
                    # If the next run time is within the next 5 minutes, we're good.
                    if job["next_run_time"] <= datetime.now() + timedelta(seconds=settings.LABOR_REFRESH_INTERVAL):
                        labor_magic_status = "OK"
                break
    except Exception as e:
        app.internal.logging.logger.error(f"Error getting scheduler status: {e}")
        scheduler_info = []

    return {
        "status": labor_magic_status,
        "jobs": scheduler_info
    }


@MiscRouter.get("/Config/Settings", tags=["Configuration"])
@stats_manager.track_stats("Get_Settings")
async def get_settings():
    """
    Get the current settings for the API.
    :return:
    """

    return {
        "refresh_interval": settings.LABOR_REFRESH_INTERVAL,
        "dept_translate": settings.DEPT_TRANSLATE
    }


@MiscRouter.get("/health", tags=["Stats & Misc"])
async def health_check():
    """
    Simple health check endpoint for docker.
    :return:
    """
    try:
        for job in scheduler.get_jobs():
            if job.name == "process_live_labor":
                return {"status": "OK"}
        raise HTTPException(status_code=500, detail="Live Labor Job Not Running.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduler erorr: {e}")









# Execution times for labor magic calls. This is heavy, so I'm keeping track.
exec_times = {
    "Last_Exec_Time": 0.0,
    "Max_Exec_Time": 0.0,
    "Min_Exect_Time": 0.0
}