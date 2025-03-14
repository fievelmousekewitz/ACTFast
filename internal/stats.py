import os
import time
from datetime import datetime
import inspect
import json

from fastapi import APIRouter
from functools import wraps





class StatsManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.stats = self.load_stats()
        self.start_date = datetime.now()

    def get_stats(self):
        self.stats = self.load_stats()
        # round all the stats to 3 decimal places
        for endpoint in self.stats:
            self.stats[endpoint]['min_time'] = round(self.stats[endpoint]['min_time'], 3)
            self.stats[endpoint]['max_time'] = round(self.stats[endpoint]['max_time'], 3)
            self.stats[endpoint]['last_time'] = round(self.stats[endpoint]['last_time'], 3)

        return {
            'start_date': self.start_date,
            'stats': self.stats
        }

    def reset_stats(self):
        self.stats = {}
        self.save_stats()

    def get_start_date(self):
        return self.start_date

    def load_stats(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                return json.load(f)
        return {}

    def save_stats(self):
        # if the file doesn't exist, create it
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                f.write('{}')
        with open(self.filepath, 'w') as f:
            json.dump(self.stats, f)


    def track_stats(self, endpoint_name):
        def decorator(func):
            if inspect.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    response = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.update_stats(endpoint_name, execution_time)
                    return response
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    response = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.update_stats(endpoint_name, execution_time)
                    return response
                return sync_wrapper
        return decorator

    def update_stats(self, endpoint_name, execution_time):
        self.stats = self.load_stats()
        if endpoint_name not in self.stats:
            self.stats[endpoint_name] = {
                'count': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'last_time': None
            }
        self.stats[endpoint_name]['count'] += 1
        self.stats[endpoint_name]['last_time'] = execution_time
        self.stats[endpoint_name]['min_time'] = min(self.stats[endpoint_name]['min_time'], execution_time)
        self.stats[endpoint_name]['max_time'] = max(self.stats[endpoint_name]['max_time'], execution_time)
        self.save_stats()





