import logging
import os
import pickle
import time
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.internal import settings
from app.internal import laborMagic
from app.internal.stats import StatsManager

LaborRouter = APIRouter()

stats_manager = StatsManager(os.path.join(settings.STATS_PATH, settings.STATS_FILENAME))

from pydantic import BaseModel, Field
from typing import List, Optional


class EmployeeNotClocked(BaseModel):
    employeenum: str = Field(description="The employee's number")
    FirstName: str = Field(description="First name of the employee")
    LastName: str = Field(description="Last name of the employee")
    jcdept: str = Field(description="Department code")
    Laborcount: int = Field(default=0, description="Count of labor entries")
    #OprSeq: int = Field(description="Operation sequence number")
    Name: str = Field(description="Formatted name of the employee")

class LaborData(BaseModel):
    OprSeq: int = Field(description="Operation sequence number")
    JobNum: str = Field(description="Job number")
    PartNum: str = Field(description="Part number")
    Standard: float = Field(description="Standard number of hours expected")
    PrevHrs: float = Field(default=0, description="Previous hours worked")
    ActiveLabor: float = Field(description="Hours of active labor")
    Efficiency: float = Field(description="Efficiency rating")
    Emps: str = Field(description="Employee names involved")

class ActiveLaborData(BaseModel):
    active_labor: List[LaborData] = Field(default=[], description="List of active labor entries")
    empsnotclocked: List[EmployeeNotClocked] = Field(default_factory=list, description="List of employees who are not clocked")
    oprseq: int = Field(description="Operation sequence")
    timestamp: datetime = Field(description="Timestamp of the data retrieval")
    executiontime: float = Field(description="Time taken for the scheduled task to run (NOT this query)")



ActiveLaborEfficiency200Response = {
        "description": "Successfully retrieved labor data",
        "content": {
            "application/json": {
                "example": {
                    "active_labor": [
                        {
                            "OprSeq": 220,
                            "JobNum": "12345",
                            "PartNum": "149A7132-927A",
                            "Standard": 8,
                            "PrevHrs": 0,
                            "ActiveLabor": 5.92,
                            "Efficiency": 0.74,
                            "Emps": "John D. - Aaron O."
                        }
                    ],
                    "empsnotclocked": [
                        {
                            "employeenum": "1234",
                            "FirstName": "John",
                            "LastName": "Doe",
                            "jcdept": "Layup",
                            "Laborcount": 0,
                            "OprSeq": 520,
                            "Name": "John D."
                        }
                    ],
                    "oprseq": 220,
                    "timestamp": "2024-05-06T09:17:44",
                    "executiontime": 21.79
                }
            }
        }
    }


EmpsNotClocked200Response = {
    "description": "Successfully retrieved employees not clocked in",
    "content": {
        "application/json": {
            "example": [
                {
                    "employeenum": "1234",
                    "FirstName": "John",
                    "LastName": "Doe",
                    "jcdept": "Layup",
                    "Laborcount": 0,
                    #"OprSeq": 520,
                    "Name": "John D."
                }
            ]
        }
    }
}



async def update_exec_times(exec_times):
    """
    Update the execution times for the labor magic calls.
    :return:
    """
    # pickle the exectimes to disk so we can keep track of them.
    with open('exec_times.pkl', 'wb') as f:
        pickle.dump(exec_times, f)


async def load_exec_times():
    """
    Load the execution times from disk.
    :return:
    """
    try:
        with open('exec_times.pkl', 'rb') as f:
            exec_times = pickle.load(f)
    except:
        exec_times = {
            "Last_Exec_Time": 0.0,
            "Max_Exec_Time": 0.0,
            "Min_Exect_Time": 0.0
        }
    return exec_times





@LaborRouter.get("/Epicor/Labor/ActiveLaborEfficiency", tags=["Retrieval"],
                 response_model=ActiveLaborData,
                 responses={200: ActiveLaborEfficiency200Response})
@stats_manager.track_stats("Get_Labor_Efficiency")
async def Get_Labor_Efficiency(OprSeq: int = Query(default=220, description="The operation sequence to query, i.e. 220, 300, 440, 520, etc",)):
    """
    Get the active labor efficiency data for a specific oprseq.
    :param oprseq: Operation Sequence i.e. 220, 300, 440, etc.
    :return:
    """

    oprseq = int(OprSeq)
    data = laborMagic.retrieve_pickles()

    try:
        if data is None or 'active_labor' not in data:
            active_labor = []
            empsnotclocked = []
            timestamp = None
            executiontime = None
            return {"active_labor": active_labor,
                    "empsnotclocked": empsnotclocked,
                    "oprseq": oprseq,
                    "timestamp": timestamp,
                    "executiontime": executiontime}
    except:
        logging.error("DATA ERROR")
        active_labor = []
        empsnotclocked = []
        timestamp = None
        executiontime = None
        return {"active_labor": active_labor,
                "empsnotclocked": empsnotclocked,
                "oprseq": oprseq,
                "timestamp": timestamp,
                "executiontime": executiontime}

    active_labor = data['active_labor']

    empsnotclocked = data['empsnotclocked']

    filtered_emps = [item for item in empsnotclocked if item.get('OprSeq') == oprseq]
    filtered_data = [item for item in active_labor if item.get('OprSeq') == oprseq]

    # TODO: Add condition to get all oprseqs, might be useful in the future.

    timestamp = data['timestamp']
    executiontime = data['executiontime']

    return {"active_labor": filtered_data,
            "empsnotclocked": filtered_emps,
            "oprseq": oprseq,
            "timestamp": timestamp,
            "executiontime": executiontime}


@LaborRouter.get("/Epicor/Labor/EmployeesNotClockedIntoJobs", tags=["Retrieval"],
                 response_model=List[EmployeeNotClocked],
                 responses={200: EmpsNotClocked200Response})
@stats_manager.track_stats("Get_Emps_Not_Clocked")
async def emps_not_clocked(oprseq: Optional[int] = Query(default=None, description="Operation sequence to filter by")):
    """
    Get the employees that are not clocked in, optionally filter by OprSeq.
    Note that OprSeq is translated to JCDEPT via settings.DEPT_TRANSLATE. Which cna be retrieved via /Config/Settings

    :return: List of employees not clocked in.
    """

    if oprseq is not None:
        data = laborMagic.get_emps_not_clocked()

        # translate the department codes to department names
        for item in data:
            dept = item.get('jcdept')
            for key, value in settings.DEPT_TRANSLATE.items():
                if dept in value:
                    item['OprSeq'] = key
                    break
        data = [item for item in data if item.get('OprSeq') == oprseq]

        return data
    else:
        data = laborMagic.get_emps_not_clocked()

    return data


@LaborRouter.get("/Epicor/Labor/EmployeeMaster", tags=["Retrieval"])
@stats_manager.track_stats("Get_Emp_Master")
async def emp_master():
    """
    Get all employee & shift data.
    :return:
    """
    #data = laborMagic.retrieve_pickles()
    #emp_master = data['emp_master']
    #return emp_master
    return None


@LaborRouter.get("/Epicor/Labor/ForceActiveLaborUpdate", tags=["Execution"])
async def Exec_Force_Update():
    """
    Force update the labor data. This data normally updates on the interval set in settings.py, but this can be used to force an update.
    :return: None
    """
    starttime = time.time()
    totaltime = time.time() - starttime

    msg = laborMagic.process_live_labor()

    return {"message": "Forced Labor Update", "executiontime": totaltime, "status": msg}


@LaborRouter.get("/Epicor/Labor/ExecutionTimes", tags=["Retrieval"])
async def Get_Exec_Times():
    """
    DEPRECATED Get the execution times for the last operation, and min/max values.
    :return:
    """

    exec_times = await load_exec_times()
    return exec_times


