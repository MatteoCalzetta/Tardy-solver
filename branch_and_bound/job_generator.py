import random

class Job:
    def __init__(self, job_id, r, p, d):
        self.id = job_id
        self.r = r         # release time
        self.p = p         # processing time
        self.d = d         # due date

    def __repr__(self):
        return f"J{self.id}(r={self.r}, p={self.p}, d={self.d})"

class JobGenerator:
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)

    def generate(self, n_jobs, r_range=(0, 100), p_range=(1, 5), tight_due_dates=True):
        jobs = []
        for i in range(1, n_jobs + 1):
            r = random.randint(*r_range)
            p = random.randint(*p_range)
            if tight_due_dates:
                # Scadenze moderate: un po' più di slack ma non troppo
                slack = random.randint(1, max(3, p))  # slack proporzionale al processing time
                d = r + p + slack
            else:
                # Scadenze larghe
                d = r + p + random.randint(5, 15)
            jobs.append(Job(i, r, p, d))
        return jobs
