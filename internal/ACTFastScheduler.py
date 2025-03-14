from apscheduler.schedulers.background import BackgroundScheduler



class ACTFastScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def add_job(self, func, trigger, **kwargs):
        self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id):
        self.scheduler.remove_job(job_id)

    def get_jobs(self):
        return self.scheduler.get_jobs()

    def get_job(self, job_id):
        return self.scheduler.get_job(job_id)

    def pause_job(self, job_id):
        self.scheduler.pause_job(job_id)

    def resume_job(self, job_id):
        self.scheduler.resume_job(job_id)

    def shutdown(self):
        self.scheduler.shutdown()


scheduler = ACTFastScheduler()

