
import pymssql
import time
import cachetools
from app.internal import settings

UtilCache = cachetools.TTLCache(maxsize=100, ttl=300)
LongCache = cachetools.TTLCache(maxsize=100, ttl=3600)


from pathlib import Path
def get_project_root() -> Path:
    return Path(__file__).parent.parent

class InsightUtils:
    @staticmethod
    def QueryWrapper(query, name='', cacheOn=False, longCache=False):
        """
        Wrapper for querying Epicor SQL Server
        :param query: query string
        :param name: name the query for logging
        :param cacheOn: regular cache, default ttl 300s
        :param longCache: long cache, default ttl 3600s (1hr)
        :return: data
        """

        @cachetools.cached(LongCache)
        def longcachefetch(fquery, name):
            """
            Fetch data from Epicor SQL Server, using cache
            :return:
            """
            conn = pymssql.connect(
                settings.EPICORSQL_SERVER,
                user=settings.EPICORSQL_USER,
                password=settings.EPICORSQL_PW,
                database=settings.EPICORSQL_DB
            )
            cursor = conn.cursor(as_dict=True)
            cursor.execute(fquery)
            data = cursor.fetchall()
            return data

        @cachetools.cached(UtilCache)
        def cachefetch(fquery, name):
            """
            Fetch data from Epicor SQL Server, using cache
            :return:
            """
            conn = pymssql.connect(
                settings.EPICORSQL_SERVER,
                user=settings.EPICORSQL_USER,
                password=settings.EPICORSQL_PW,
                database=settings.EPICORSQL_DB
            )
            cursor = conn.cursor(as_dict=True)
            cursor.execute(fquery)
            data = cursor.fetchall()
            return data

        def fetch(fquery, name):
            conn = pymssql.connect(
                settings.EPICORSQL_SERVER,
                user=settings.EPICORSQL_USER,
                password=settings.EPICORSQL_PW,
                database=settings.EPICORSQL_DB
            )
            cursor = conn.cursor(as_dict=True)
            cursor.execute(fquery)
            data = cursor.fetchall()
            return data

        if cacheOn:
            data = cachefetch(query,name)
        elif longCache:
            data = longcachefetch(query,name)
        else:
            data = fetch(query,name)

        return data


