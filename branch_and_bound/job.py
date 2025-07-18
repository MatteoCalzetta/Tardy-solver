class Job:
    def __init__(self, job_id, r, p, d):
        self.id = job_id
        self.r = r         # release time
        self.p = p         # processing time
        self.d = d         # due date

    def __repr__(self):
        return f"J{self.id}(r={self.r}, p={self.p}, d={self.d})"
