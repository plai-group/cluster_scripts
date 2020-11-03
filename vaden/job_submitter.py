#!/usr/bin/env python
import os
from string import Template
import time
import datetime
import pandas as pd
from pprint import pprint
from pathlib import Path
import sys
import itertools
from itertools import chain
import static
import socket
import subprocess

# Global Arguments
COMPUTE_CANADA_HOSTS = ['cedar{}.cedar.computecanada.ca'.format(i) for i in range(10)]
UBC_SLURM_HOSTS = ['borg.cs.ubc.ca']

hostname = socket.gethostname()

# find host and scheduler
if hostname in COMPUTE_CANADA_HOSTS:
    HOST      = static.CC
elif hostname in UBC_SLURM_HOSTS:
    HOST      = static.UBC
else:
    raise ValueError("Scheduler not detected")

# Paths
PROJECT_DIR    = ""
EXPERIMENT_DIR = ""
SRC_PATH       = ""
DATA_DIR       = ""
RESULTS_DIR    = ""

SLEEP_TIME = 0.05

REQUIRED_OPTIONS = set(["gpu", "hrs", "cpu", "mem", "partition", "env"])

########################
# Main submission loop #
########################

def submit(hyper_params,
           experiment_name,
           experiment_dir,
           manual_mode=False,
           file_storage_observer=False,
           script_name="main.py",
           prune_successful='',
           **kwargs):

    # Validate arguments
    verify_dirs(experiment_dir, experiment_name, script_name)

    # Display info
    hypers = process_hyperparameters(hyper_params, prune_successful)

    assert REQUIRED_OPTIONS.issubset(set(kwargs.keys())), f"{REQUIRED_OPTIONS} must be specified"

    print("------Scheduler Options------")
    pprint(kwargs)
    print("-----------(SLURM)-----------")

    print("Saving results in: {}".format(RESULTS_DIR))
    print("------Sweeping over------")
    pprint(hyper_params)
    print("-------({} runs)-------".format(len(hypers)))

    ask = True
    flag = 'y'
    for idx, hyper_string in enumerate(hypers):
        if ask:
            flag = input("Submit ({}/{}): {}? (y/n/all/exit) ".format(idx + 1, len(hypers), hyper_string))
        if flag in ['yes', 'all', 'y', 'a']:
            scheduler_command, python_command, job_dir = make_commands(hyper_string, experiment_name, idx, file_storage_observer)
            make_bash_script(python_command, static.SUBMISSION_FILE_NAME, job_dir, **kwargs)
            output = subprocess.check_output(scheduler_command,  stderr=subprocess.STDOUT, shell=True)
            print("Submitting ({}/{}): {}".format(idx + 1, len(hypers), output.strip().decode()))
        if flag in ['all', 'a']:
            ask = False
            time.sleep(SLEEP_TIME)

        if flag in ['exit', 'e']:
            sys.exit()


########################
# ---- path management -
########################

# Strictly enforce directory structure
def verify_dirs(experiment_dir, experiment_name, script_name):
    project_dir    = Path(experiment_dir).parents[1]
    src_path       = Path(project_dir) / script_name
    data_dir       = Path(project_dir) / 'data'

    assert project_dir.is_dir(), "{} does not exist".format(project_dir)
    assert data_dir.is_dir(), "{} does not exist".format(data_dir)
    assert src_path.is_file(), "{} does not exist".format(src_path)

    now = datetime.datetime.now()

    # make global
    global PROJECT_DIR
    global EXPERIMENT_DIR
    global SRC_PATH
    global RESULTS_DIR

    PROJECT_DIR = project_dir
    EXPERIMENT_DIR = experiment_dir
    SRC_PATH = f"{script_name}"
    RESULTS_DIR = f'results/{experiment_name}/{now.strftime("%Y_%m_%d_%H:%M:%S")}'


#################################
# ------- hyperparameters -------
#################################

def process_hyperparameters(hyper_params, prune_successful=''):
    df = None
    if prune_successful:
        flag = input(f"Prune submits based on {prune_successful}?")
        if flag in ['yes', 'all', 'y', 'a']:
            df = pd.read_csv(prune_successful, index_col=0)
    if isinstance(hyper_params, dict):
        return make_hyper_string_from_dict(hyper_params, df)
    elif isinstance(hyper_params, list):
        return list(itertools.chain.from_iterable([make_hyper_string_from_dict(d, df) for d in hyper_params]))
    else:
        raise ValueError("hyper_params must be either a single dictionary or a list of dictionaries")


def verify_header(header, df):
    if df is None:
        return True
    else:
        tokens = [df[df[k] == v].shape[0] != 0 for k, v in header]
    return all(tokens)

# returns strings of form: name1=value1 name2=value2 name3=value3...
def make_hyper_string_from_dict(hyper_dict, df):
    # Check all values are iterable lists
    def type_check(value):
        if isinstance(value, (list, range)):
            return list(value)
        else:
            return [value]

    hyper_dict = {key: type_check(value) for key, value in hyper_dict.items()}

    commands = []
    for args in itertools.product(*hyper_dict.values()):
        header = list(zip(hyper_dict.keys(), args))
        if verify_header(header, df):
            command = "".join(["'{}={}' ".format(k, v) for k, v in header])
            commands.append(command[:-1])
        else:
            print(f"skipping: {header}")

    return commands


def make_bash_script(python_command, file_name, job_dir, **kwargs):
    myfile = static.SLURM_TEMPLATE
    myfile = add_slurm_option(myfile, f"#SBATCH --mem={kwargs['mem']}")
    myfile = add_slurm_option(myfile, f"#SBATCH --time=00-{kwargs['hrs']}:00")
    myfile = add_slurm_option(myfile, f"#SBATCH --cpus-per-task={kwargs['cpu']}")
    myfile = add_slurm_option(myfile, f"#SBATCH --output=%x-%j.out")

    if kwargs['gpu']:
        myfile = add_slurm_option(myfile, f"#SBATCH --gres=gpu:1")

    if "nodelist" in kwargs:
        myfile = add_slurm_option(myfile, "#SBATCH --nodelist=" + ",".join(kwargs['nodelist']))

    if "exclude" in kwargs:
        myfile = add_slurm_option(myfile, "#SBATCH --exclude=" + ",".join(kwargs['exclude']))

    if HOST == static.UBC:
        myfile = add_slurm_option(myfile, f"#SBATCH --partition={kwargs['partition']}")
        python_init = f"source /ubc/cs/research/fwood/vadmas/miniconda3/bin/activate {kwargs['env']}"
    else:
        myfile = add_slurm_option(myfile, f"#SBATCH --account={kwargs['account']}")
        python_init = Template(static.CC_PYTHON_INIT_TOKEN).safe_substitute(pip_install=static.CC_PIP_INSTALLS[kwargs['env']])

    myfile = Template(myfile).safe_substitute(
        init= python_init,
        python_command=python_command,
        home_dir=PROJECT_DIR,
        job_dir=job_dir
    )

    with open(file_name, 'w') as rsh:
        rsh.write(myfile)


def add_slurm_option(myfile, option):
    return myfile.replace("\n\n",f"\n\n{option}\n", 1) # set maxreplace = 1 to only replace first occurance

def make_commands(hyper_string, experiment_name, job_idx, file_storage_observer):
    job_dir = Path(EXPERIMENT_DIR) / Path(RESULTS_DIR) / f"job_{job_idx}"
    job_dir.mkdir(exist_ok=False, parents=True)

    artifact_dir = job_dir / 'artifacts'
    artifact_dir.mkdir(exist_ok=False, parents=True)

    python_command = f"python $HOME_DIR/{SRC_PATH} with home_dir=$HOME_DIR artifact_dir=$JOB_DIR/artifacts {hyper_string} -p --name {experiment_name}"

    if file_storage_observer or (HOST == static.CC):
        python_command = f"{python_command} -F $JOB_DIR/file_storage_observer"

    args_file_name = job_dir / "args.txt"
    res_name = job_dir / 'results.res'
    err_name = job_dir / 'error.err'

    with open(args_file_name, 'w') as rsh:
        rsh.write(hyper_string.replace("' '", "'\n'"))

    scheduler_command = f"sbatch -o {res_name} -e {err_name} -J {experiment_name} --export=ALL {static.SUBMISSION_FILE_NAME}"

    return scheduler_command, python_command, job_dir

