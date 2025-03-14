import os
from app.internal import utils

VERSION = "0.0.0"

# get app path
BASE_PATH = utils.get_project_root()

DATA_PATH = os.path.join(BASE_PATH, "data")
STATS_PATH = DATA_PATH
STATS_FILENAME = "api_stats.json"



LABOR_REFRESH_INTERVAL = 5 * 60  # 5 minutes

EPICORSQL_SERVER = '<DBSERVER>'
EPICORSQL_USER = '<DBUSER>
EPICORSQL_PW = '<PASSWORD>'
EPICORSQL_DB = '<DBNAME>'

# Translate DeptCodes to OprSeq
DEPT_TRANSLATE = {
    175: ['COR'],
    200: ['KIT'],
    220: ['LU'],
    300: ['A/C'],
    440: ['TRIM'],
    450: ['Honda AS'],
    460: ['ASMBY'],
    520: ['PAINT', 'PPREP', 'FINISHING'],
}