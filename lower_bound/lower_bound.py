# lower_bound/lower_bound.py

import heapq
from typing import List

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Import the shared Job definition
from branch_and_bound.job import Job
from branch_and_bound.job_generator import JobGenerator

def compute_lb_knapsack(jobs: List[Job]):
    n = len(jobs)
    H = max(job.d for job in jobs)       # orizzonte massimo
    # dp[c] = massimo numero di job on‐time usabili con cap. c
    dp = [0] * (H + 1)
    for job in jobs:
        w = job.p
        # itero a ritroso per evitare riuso multiplo
        for c in range(H, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + 1)
    K_star = max(dp)
    return n - K_star

def compute_lb(jobs: List[Job]) -> int:
    """
    Compute the lower bound for 1|r_j|∑U_j via preemptive EDF.
    Returns the minimum number of tardy jobs.
    """
    # 1) Sort jobs by release time
    jobs_by_release = sorted(jobs, key=lambda job: job.r)
    
    # 2) Prepare a min-heap for active jobs (keyed by due date)
    #    Each entry: [due_date, remaining_time, job_id]
    active_heap = []
    
    # 3) Initialize time 't' and index into release list
    t = jobs_by_release[0].r if jobs_by_release else 0
    idx = 0
    tardy_count = 0
    
    # 4) Main simulation loop
    while idx < len(jobs_by_release) or active_heap:
        # 4a) Release new jobs
        while idx < len(jobs_by_release) and jobs_by_release[idx].r <= t:
            job = jobs_by_release[idx]
            heapq.heappush(active_heap, [job.d, job.p, job.id])
            idx += 1
        
        # 4b) If no active job, jump to next release
        if not active_heap:
            t = jobs_by_release[idx].r
            continue
        
        # 4c) Pop the job with earliest due date
        due_date, rem_time, job_id = heapq.heappop(active_heap)
        
        # 4d) Determine next event (completion or next release)
        next_release = jobs_by_release[idx].r if idx < len(jobs_by_release) else float('inf')
        run_time = min(rem_time, next_release - t)
        
        # 4e) Advance time and update remaining
        t += run_time
        rem_time -= run_time
        
        # 4f) Check completion
        if rem_time == 0:
            if t > due_date:
                tardy_count += 1
        else:
            # Reinsert with updated remaining time
            heapq.heappush(active_heap, [due_date, rem_time, job_id])
    
    return tardy_count
