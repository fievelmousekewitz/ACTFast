import os
from decimal import Decimal
from datetime import datetime
from pytz import timezone
import pandas as pd
import pickle
import json
import time as t
from app.internal.utils import InsightUtils
from app.internal import settings
import time
import logging
from app.internal.stats import StatsManager
import app.internal.settings as settings

stats_manager = StatsManager(os.path.join(settings.STATS_PATH, settings.STATS_FILENAME))
logger = logging.getLogger(__name__)

labor_data_file = os.path.join(settings.DATA_PATH, 'labordata.pkl')
emps_not_clocked_file = os.path.join(settings.DATA_PATH, 'empsnotclocked.pkl')


@stats_manager.track_stats("Process_Live_Labor")
def process_live_labor():
    # for testing purposes, we're going to just pickle the json data to a file and retrieve it.
    starttime = time.time()

    # get the data
    data = labormagic()

    # pickle the data
    # TODO: Add a check to see if the data is the same as the last data, if it is, don't pickle it.
    # TODO: Add a check to make sure we dont cross paths with another instance here.


    resulttime = time.time() - starttime

    #data_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # DATEFIX: Convert to US/Pacific timezone
    data_datetime = datetime.now().astimezone(timezone('US/Pacific')).strftime('%Y-%m-%d %H:%M:%S')

    if data is None:
        # create a dummy with timestamp and executiontime
        data = dict()
        data['timestamp'] = data_datetime
        data['executiontime'] = resulttime
        with open(labor_data_file, 'wb') as f:
            pickle.dump(data, f)

        return "No Data Found."

    # add the data_datetime and resulttime to the data dict.
    data['timestamp'] = data_datetime
    data['executiontime'] = resulttime

    with open(labor_data_file, 'wb') as f:
        pickle.dump(data, f)

    return "Data Processed."



def retrieve_pickles():
    # check if there's pickled data first.
    try:
        with open(labor_data_file, 'rb') as f:
            data = pickle.load(f)
        return data
    except:
        return None



def GetShiftData():
    """
    Get all active employee shift data.
    :return: pandas shift data
    """

    query = """
        SELECT
            EmpBasic.Empid,
            EmpBasic.Name,
            EmpBasic.FirstName,
            EmpBasic.LastName,
            EmpBasic.JCDept,
            JCShift.Shift,
            JCShift.StartTime,
            JCShift.EndTime,
            JCShift.LunchStart,
            JCShift.LunchEnd,
            ShiftBrk.BreakStart,
            ShiftBrk.BreakEnd
        FROM Erp.Empbasic
            INNER JOIN Erp.JCShift ON Empbasic.Shift = JCShift.Shift
            LEFT OUTER JOIN Erp.Shiftbrk ON JCShift.Shift = ShiftBrk.Shift
        WHERE EmpBasic.EmpStatus = 'A'
    """
    shiftdata = InsightUtils.QueryWrapper(query, longCache=True)
    shiftdata = pd.DataFrame(shiftdata)
    return shiftdata




def GetLaborDtlData(date=None, oprseq=None, empdata=False):
    """
    Get labor data for a given date and oprseq.
    :param date: labor date, default to None/Today
    :param oprseq: operation seq.
    :param empdata: if true, return the shift data as well. else just labor data. I know this is weird.
    :return: if empdata=False: labor totals; if empdata=True: [labor totals, shift data]
    """


    df_empbreak = GetShiftData() # this is cached for 1 hr

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    # make sure date is a date.
    try:
        if not isinstance(date, datetime):
            date = datetime.strptime(date, '%Y-%m-%d')
    except:
        logger.error(f'Invalid date: {date}')

    # DATEFIX: Convert date to US/Pacific timezone
    date = date.astimezone(timezone('US/Pacific')).strftime('%Y-%m-%d')

    # TODO: this gets all labor data, should we filter by oprseq? would be 'wrong' if emp worked on mult oprs.
    query = f"""
        SELECT EmployeeNum, JobNum, OprSeq, ClockInDate, ClockInTime, ClockOutTime, ActiveTrans FROM erp.LaborDtl 
        WHERE ClockInDate = \'{date}\'
    """

    df_sql = InsightUtils.QueryWrapper(query)
    df_sql = pd.DataFrame(df_sql)


    # Move data to pandas and filter for oprseq
    #deptdata = df_sql[df_sql['OprSeq'] == oprseq].sort_values(by=['JobNum', 'EmployeeNum'])
    # TODO: OPRSEQ CHANGE MARK

    # instead, get all oprseqs
    deptdata = df_sql.sort_values(by=['JobNum', 'EmployeeNum'])


    # Remove zero value clockintimes, these are adjustments. NEVERMIND. We need to keep these, only groupwork sets clockout to 24 on activetrans.
    # deptdata = deptdata[deptdata['ClockInTime'] != 0]

    # if there's a 24 in ClockOutTime, replace it with the current time, these are active labor transactions.
    #curtime = datetime.now().time()

    # DATEFIX: Convert to US/Pacific timezone
    curtime = datetime.now().astimezone(timezone('US/Pacific')).time()


    nowdectime = curtime.hour + curtime.minute / 60 + curtime.second / 3600
    deptdata.loc[deptdata['ClockOutTime'] == 24, 'ClockOutTime'] = nowdectime
    deptdata.loc[deptdata['ClockOutTime'] == 0, 'ClockOutTime'] = nowdectime

    #print(f'NowDecTime: {nowdectime}')

    # if there's no data....
    if deptdata.empty:
        return None, None

    # This has to be after we remove 0s. Used to set the beginning of the time range.
    minTime = frmt(deptdata['ClockInTime'].min())
    maxTime = frmt(deptdata['ClockOutTime'].max()) # Used to set the end of the time range.


    #print(f'Min Time: {minTime} Max Time: {maxTime}')
    # Create Pandas time range using 5 minute intervals
    timeRange = pd.date_range(start=minTime, end=maxTime, freq='5min').time

    # Fill with job data
    index = pd.MultiIndex.from_product([deptdata['JobNum'].unique(), deptdata['EmployeeNum'].unique()], names=['JobNum', 'Emp'])
    df = pd.DataFrame(index=index, columns=timeRange)

    for index, row in deptdata.iterrows():
        job = row['JobNum']
        emp = row['EmployeeNum']
        start = row['ClockInTime']  # start of labordtl record
        end = row['ClockOutTime']  # end of labordtl record
        start_s = frmt(start)
        end_s = frmt(end)
        # convert start_s & end_s to timestamp fmt
        start_s = datetime.strptime(start_s, "%H:%M:%S").time()
        end_s = datetime.strptime(end_s, "%H:%M:%S").time()

        #
        # this is very expensive processing. There's probably a better way to do this.
        # TODO: Optimize time slicing for labor data.
        #

        # Pandas says I need to defragment this dataframe. I'm not sure why, but I'm doing it.
        df = df.copy()
        x = 0

        # By end of day, this is 120 (190?)~
        for time in timeRange:
            x += 1
            if time >= start_s and time <= end_s:
                dectime = time.hour + time.minute / 60 + time.second / 3600
                if isEmpOnBreak(df_empbreak, emp, dectime):
                    df.at[(job, emp), time] = 0
                else:
                    df.at[(job, emp), time] = 1
            else:
                df.at[(job, emp), time] = 0
            # if time col has 0s for all emps, drop the col to avoid div/0 errors.
            # This just means there's no active labor. Could probably trim these earlier.

            if df[time].sum() == 0:
               df.drop(columns=[time], inplace=True)


    df.fillna(0.0, inplace=True)  # Seems redundant, but needed.

    # with pd.option_context('display.max_rows', None):
    #    display(df)

    # Apply Job Counts

    jobCounts = df.groupby('Emp').sum()

    # df to csv
    #df.to_csv('kitlabordtl.csv')
    #jobCounts.to_csv('kitjobcounts.csv')

    df = df.div(jobCounts, axis=0) # dividing the labor for emps by the number of jobs they're working on.
    df.fillna(0.0, inplace=True)

    # remove labor for emps that have ended labor on the job, as epicor does that already and we can grab it from joboper.
    for index, row in df.iterrows():
        # check if the emp is active on the job. if not remove the row.
        if not isEmpActiveOnJob(df_sql, index[0], index[1]):
            df.drop(index, inplace=True)

    # df is our raw data, lets get grouped by jobnum....

    dftotals = df.groupby(level='JobNum').sum().sum(axis=1)

    dftotals = dftotals.reset_index()
    dftotals.columns = ['JobNum', 'Total']

    # this just prevents us from having to grab this data twice. lazy.
    if empdata:
        return dftotals, df_empbreak
    else:
        return dftotals


# Helper time func
def frmt(tm):
    """
    Convert a decimal time to a string time
    :param tm: decimal time
    :return: string time
    """
    hours, _min = divmod(tm, 1)
    minutes, _sec = divmod(_min * 60, 1)
    seconds, _msec = divmod(_sec * 60, 1)
    dt = datetime(1900, 1, 1, int(hours), int(minutes), int(seconds))
    return dt.strftime('%H:%M:%S')



def isEmpActiveOnJob(df, jobnum, empnum):
    # df is the dataframe of labor data
    #just check the jobnum and empnum in df to see if the ActiveTrans = 1 for that job.

    if len(df[(df['JobNum'] == jobnum) & (df['EmployeeNum'] == empnum) & (df['ActiveTrans'] == 1)]):
        return True
    else:
        return False


def isEmpOnBreak(shiftdata, empnum, chktime):
    """
    Check if the employee is on break at the given time.
    :param shiftdata: dataframe of shiftdata
    :param empnum: employee number
    :param chktime: The time in decimal to check if the employee is on break
    :return: true or false
    """
    for index, row in shiftdata[shiftdata['Empid'] == empnum].iterrows():
        # Check Lunch
        if row['LunchStart'] is not None and row['LunchEnd'] is not None:
            if row['LunchStart'] <= chktime <= row['LunchEnd']:
                return True
        # Check Shift Break
        if row['BreakStart'] is not None and row['BreakEnd'] is not None:
            if row['BreakStart'] <= chktime <= row['BreakEnd']:
                return True
    return False




def labormagic(oprseq=220):
    # Convert oprseq to int, or return 0 if it's not a number.
    # Lord almighty, this is a hack. Fix it later.
    # TODO: OprSeq param isn't being used for anything, it is legacy from the old system. This function and it's children
    #       all ignore the param now.

    dept_translate = settings.DEPT_TRANSLATE

    try:
        oprseq = int(oprseq)
    except:
        logger.error(f'Invalid oprseq: {oprseq}')
        oprseq = 0
    depts = []
    totals_data, empdata = GetLaborDtlData(oprseq=oprseq, empdata=True)  # defaults to today's date

    # get the depts for this oprseq
    empdepts = dept_translate[oprseq]
    empdepts = [f"'{str(dept)}'" for dept in empdepts]

    deptwhere = '(' + ', '.join(empdepts) + ')'

    # check if any emps are not clocked in.
    query = f"""
        select 
         laborhed.employeenum,
         empbasic.FirstName,
         empbasic.LastName,
         empbasic.jcdept,
         count(labordtl.labordtlseq) as Laborcount

        from erp.laborhed
         left outer join erp.labordtl on labordtl.laborhedseq = laborhed.laborhedseq
         inner join erp.empbasic on laborhed.EmployeeNum = empbasic.empid

         where
         laborhed.activetrans = 1 --and empbasic.jcdept in {deptwhere}
          group by laborhed.employeenum, empbasic.FirstName, empbasic.LastName, empbasic.jcdept
         having count(labordtl.labordtlseq) = 0
    """
    empsnotclocked = InsightUtils.QueryWrapper(query)

    # Build the empsnotclocked list with F. LastName and depttranslate column

    for item in empsnotclocked:
        # get the oprseq from the jcdept
        for dept in dept_translate:
            if dept_translate[dept][0] == item['jcdept']:
                item['OprSeq'] = dept
                break
        item['Name'] = item['FirstName'] + ' ' + item['LastName'][0] + '.'

    # if there's no emps working, return empty list.
    # pickle the emps_notclocked data for later use.

    with open(emps_not_clocked_file, 'wb') as f:
        pickle.dump(empsnotclocked, f)

    if totals_data is None:
        return None

    # get all active labor data for oprseq
    query = f"""
    SELECT DISTINCT
	LaborDtl.OprSeq,
	LaborDtl.JobNum,
	Jobhead.PartNum,
	JobOper.EstProdHours as Standard,
	JobOper.ActProdHours
FROM Erp.LaborDtl 
	INNER JOIN Erp.JobHead ON LaborDtl.Company = JobHead.Company AND LaborDtl.JobNum = JobHead.JobNum
	INNER JOIN Erp.JobOper ON LaborDtl.JobNum = JobOper.JobNum AND LaborDtl.OprSeq = JobOper.OprSeq
WHERE LaborDtl.ActiveTrans = 1 --AND LaborDtl.OprSeq = {oprseq}
    """

    # QUERY FOR ACTIVE LABOR DATA
    active_labor = InsightUtils.QueryWrapper(query)
    #active_labor = pickledata(active_labor, 'active_labor.pkl')

    # convert to pandas dataframe
    active_labor = pd.DataFrame(active_labor)

    # get emps for oprseq and what they're working on.
    query = f"""
    SELECT EmployeeNum, Jobnum
    FROM Erp.LaborDtl WHERE ActiveTrans = 1 -- AND OprSeq = {oprseq}
    """

    # QUERY FOR EMPLOYEES WORKING ON JOBNUMS, to get ACTIVE transactions.
    emps = InsightUtils.QueryWrapper(query)

    # pickle the data for later use. if flagged to do so.
    #emps = pickledata(emps, 'emps.pkl')

    # If nobody's working
    if len(emps) == 0:
        return None
        #return render(request, 'effeciency.html',
         #             {"active_labor": [], "oprseq": oprseq, "depts": depts, "empsnotclocked": empsnotclocked})

    # convert to pandas dataframe
    emps = pd.DataFrame(emps)

    # For each jobnum in active_labor, append the totals_data for that jobnum to the active_labor dataframe.
    for index, row in active_labor.iterrows():
        jobnum = row['JobNum']
        # calc this job labor
        labor = totals_data[totals_data['JobNum'] == jobnum]['Total'].sum()
        labor = labor * 5 / 60  # mins worked total

        # get Standard and Actual
        std = row['Standard']
        prevhrs = row['ActProdHours']

        # convert everything to dec
        std = Decimal(std)
        prevhrs = Decimal(prevhrs)
        labor = Decimal(labor)

        # calc eff
        eff = 0
        if std > 0:
            # print(f'{jobnum} - Std: {std} - Prv: {prevhrs} - Act: {labor}')
            eff = (prevhrs + labor) / std

        # round everything to 2 decimal places
        std = round(std, 2)
        prevhrs = round(prevhrs, 2)
        labor = round(labor, 2)
        eff = round(eff, 2)

        active_labor.at[index, 'PrevHrs'] = prevhrs
        active_labor.at[index, 'Standard'] = std
        active_labor.at[index, 'Efficiency'] = eff

        active_labor.at[index, 'ActiveLabor'] = labor  # totals_data[totals_data['JobNum'] == jobnum]['Total'].sum()

    # drop actprodhours column now.
    # active_labor.drop(columns=['ActProdHours'], inplace=True)

    # ReOrder columns: OprSeq, JobNum, PartNum, Standard, PrevHrs, ActiveLabor, Efficiency
    active_labor = active_labor[['OprSeq', 'JobNum', 'PartNum', 'Standard', 'PrevHrs', 'ActiveLabor', 'Efficiency']]

    # under each jobnum, list the employees working on it.
    # for each jobnum in active_labor, get the emps working on it.

    for index, row in active_labor.iterrows():
        jobnum = row['JobNum']
        empsworking = emps[emps['Jobnum'] == jobnum]['EmployeeNum'].unique()
        # print("EMPS WORKING")
        # print(empsworking)

        # translate empsworking to names using empdata["Firstname"] and empdata["LastName"], but trim lastname to 1 char.
        for i, emp in enumerate(empsworking):
            emp = empdata[empdata['Empid'] == emp]
            # empsworking[i] = emp['FirstName'].values[0] + '' + emp['LastName'].values[0][0]
            empsworking[i] = emp['FirstName'].values[0][0] + '. ' + emp['LastName'].values[0]

        #        empsworking = [empdata[empdata['Empid'] == emp]['FirstName'].values[0] + ' ' + empdata[empdata['Empid'] == emp]['LastName'].values[0][0] for emp in empsworking]

        empsworking = ' - '.join(empsworking)
        active_labor.at[index, 'Emps'] = empsworking

    # order by partnum, jobnum for consistency.
    active_labor = active_labor.sort_values(by=['PartNum', 'JobNum'])

    active_labor = active_labor.to_dict(orient='records')

    # convert dec values to float for json
    for record in active_labor:
        record['Standard'] = float(record['Standard'])
        record['PrevHrs'] = float(record['PrevHrs'])
        record['ActiveLabor'] = float(record['ActiveLabor'])
        record['Efficiency'] = float(record['Efficiency'])


    # build the return object
    data = dict()
    data['active_labor'] = active_labor
    data['empsnotclocked'] = empsnotclocked

    # pickle empsnotclocked for retrieval later.
    with open(emps_not_clocked_file, 'wb') as f:
        pickle.dump(empsnotclocked, f)

    return data


def get_emps_not_clocked():
    try:
        with open(emps_not_clocked_file, 'rb') as f:
            data = pickle.load(f)
        return data
    except:
        return None

