def is_on_time_schedulable(job_list):
    # Earliest Deadline First semplificato
    sorted_jobs = sorted(job_list, key=lambda j: j.d)
    t = 0
    for job in sorted_jobs:
        t = max(t, job.r) + job.p
        if t > job.d:
            return False
    return True

def select_job(node, jobs):
    decided = node.T.union(node.S)
    for job in jobs:
        if job.id not in decided:
            return job.id
    return None
