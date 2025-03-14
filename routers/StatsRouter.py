import app.internal.settings as settings
from fastapi import APIRouter
import os
from app.internal.stats import StatsManager
import app.internal.settings as settings

StatsRouter = APIRouter()
stats_manager = StatsManager(os.path.join(settings.STATS_PATH, settings.STATS_FILENAME))



@StatsRouter.get("/actfast/stats", tags=["Stats & Misc"])
@stats_manager.track_stats("Get_ACTFast_Stats")
async def get_stats():
    """
    ACTFast uses a custom stats manager to track execution times and hit counts. This endpoint returns the current stats.
    Note that these stats do not persist across updates or restarts of the container.
    No point in adding persistant storage just for this data.

    :return:
    """


    return stats_manager.get_stats()
