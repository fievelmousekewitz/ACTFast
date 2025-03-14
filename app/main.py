import os
from datetime import datetime
from fastapi import FastAPI, Query, Response
from app.internal import settings, laborMagic
import app.internal.logging
# Scheduler
import app.internal.ACTFastScheduler as ACTFastScheduler
scheduler = ACTFastScheduler.scheduler  # Scheduler must be created before the routers are imported.
scheduler.add_job(
    laborMagic.process_live_labor,
    "interval",
    seconds=settings.LABOR_REFRESH_INTERVAL,
    id="labor_magic",
    max_instances=1)

# /Scheduler
from app.internal.stats import StatsManager


app.internal.logging.logger.info("Scheduler started.")
settings.VERSION = "0.1.8"
stats_manager = StatsManager(os.path.join(settings.STATS_PATH, settings.STATS_FILENAME))


# TODO: Run the scheduled job on startup to populate the cache.
# TODO: Add script to compare current data and query existing deployed api to make sure they are the same.
# TODO: Execute/Update endpoint should exit and run job in background, instead of hanging the user.
# TODO: https://www.uvicorn.org/deployment/ - generate ssl keys for uvicorn to use.
# TODO: Expand csv export so users can link their excel to the api.
# http://actfast:8080/Epicor/Labor/ActiveLaborEfficiency?OprSeq=440



# Create the FastAPI instance
ACTFast = FastAPI(
    title="ACTFast API",
    description="""
    Custom built API for ACTI. Used to do complex data retrieval and evaluation tasks for ACTI.
    
    This API also runs a scheduler to update large datasets on a regular basis, and serve the cached data to clients.
    
    An example of this is the "Live Labor Efficiency" endpoint, which retrieves data from the Epicor database, and calculates the efficiency of the labor. This is an expensive operation that can take ~1m to complete. 
    ACTFast runs this job once per 5 minutes and stores the data. Clients can then query the data without having to wait for the calculation to complete. 
    
    Currently primarily used for Insight/ShopScreens.\n""",

    version=settings.VERSION,
    contact={
        "name": "Jeff Johnson",
        "url": "https://insight.ddc.local",
        "email": "jeff.johnson@acti.aero}"}
)


# Tags for the API
tags_metadata = [
    {
        "name": "Retrieval",
        "description": "Data Retrieval Endpoints"
    },
    {
        "name": "Execution",
        "description": "Use these with care. They can have a significant impact on the system."
    },
    {
        "name": "Configuration",
        "description": "Configuration Endpoints"

    },
    {
        "name": "Stats & Misc",
        "description": "Stats and miscellaneous endpoints"
    }

]

from app.routers import LaborRouter, StatsRouter, MiscRouter
ACTFast.include_router(LaborRouter.LaborRouter)
ACTFast.include_router(MiscRouter.MiscRouter)
ACTFast.include_router(StatsRouter.StatsRouter)

