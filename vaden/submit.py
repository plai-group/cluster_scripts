#!/usr/bin/env python
from job_submitter import submit
from pathlib import Path

# can use relative or absolute paths, but *must* be put in
# ./ml_project_skeleton_template/experiments/experiment_name/submit.py. This strictly enforces a new directory (+ submission script) per experiment.
project_path = Path(".").cwd()

# works on both cedar and local cluster
job_options = {
    "gpu": True,
    "hrs": 48,
    "cpu": 1,
    "mem": "12400M",
    "partition": 'plai', # local cluster only
    "env": 'ml3', # virtual env to use
    "account":"rrg-kevinlb" # cedar user
}

# Will grid search over all permutations. The
gridsearch_gp = {
    "learning_task": ['continuous_vae'],
    "dataset": ['mnist'],
    "S": [10, 50],
    "test_frequency":1000,
    "loss":['tvo'],
    "schedule": ['gp_bandit'],
    "K": [10, 15],
    "epochs":[10000],
    "seed":[2,3,4,5,6]
}

# Submit single job. The keys of the dictionary are required to correspond to sacred command lin arguments.
single_job = {
    "learning_task": ['continuous_vae'],
    "dataset": ['mnist'],
    "S": [10,],
    "test_frequency":1000,
    "loss":['tvo'],
    "schedule": ['log'],
    "K": [10],
    "epochs":[10000],
    "seed":[2]
}


submit([gridsearch_gp, single_job], #all entries in the dictionary will be gridsearched over. Can pass in a list of dicts or the dict directly.
       "neurips_camera_ready", # name for slurm job
       project_path,
       script_name='main.py', # must be saved in ./ml_project_skeleton_template/main.py
       file_storage_observer=True,  # save locally using sacred. Set False to save to wandb instead
       **job_options)
