#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# NOTE: SLURM argument/value pairs should be passed with whitespaces in between and not equal signs.

DEFAULT_SLURM_ARGS = {"--mail-user": "saeidnp@cs.ubc.ca",
                      "--mail-type": "ALL",
                      "--mem": "4G", 
                      "--time": "12:00:00"}
SBATCH_COMMAND = "sbatch"
# Paths
ROOT_DIR = Path(__file__).parent.absolute()
BATCH_JOB_FILES_DIR = ROOT_DIR / "batch_job_files"
SUBMIT_JOB_SCRIPT = BATCH_JOB_FILES_DIR / "_run_python.sh"
REPORTS_DIR = BATCH_JOB_FILES_DIR / "reports"

# Arguments:
# --script: used to change the default worker script. The scripts should be placed under BATCH_JOB_FILES_DIR directory r.g. <BATCH_JOB_FILES_DIR>/_run.sh
# --array-tag: (only useful for array jobs) if given, uses the provided value as the python script argument name to pass SLURM_ARRAY_TASK_ID
# Useful SLURM options (and SLURM option aliases):
# --cores <N>: specifies the number of CPU cores needed
# --gpu <N>: specifies the number of GPUs needed
# -w <node_name>: specifies a node name
# --array <first_idx>-<last_idx>: submits an array job with indices in [first_idx, last_idx]

def default_slurm_args():
    """ Identifies the cluster (PLAI/CC) and create the default parameters (DEFAULT_SLURM_ARGS)
        accordingly based on the json file at batch_job_files/default.json

    Raises:
        Exception: If there is no SLURM environment
        Exception: If the SLURM cluster machines are not recognized (neither of UBC or ComputeCanada-cedar)
    
    Returns:
        dict: a dictionary containing default SLURM arguments
    """
    DEFAULT_SLURM_ARGS = {}
    # Read the json config file
    config_file_path = str(BATCH_JOB_FILES_DIR / "default.json")
    with open(config_file_path) as json_file:
        json_data = json.load(json_file)
    # Set the cluster-independent default parameters
    if "__all__" in json_data:
        d = json_data["__all__"]
        if "--mail-user" in d:
            assert d["--mail-user"] is not None and len(d["--mail-user"]) > 0,\
                f"The email address is not set in {config_file_path}"
        for k,v in d.items():
            DEFAULT_SLURM_ARGS[k] = v
    # Figure out which cluster we are on
    retcode, slurm_nodes = subprocess.getstatusoutput("sinfo -h -o %N")
    cluster = None
    if retcode == 0:
        if "plai[" in slurm_nodes:        
            # Default configuration for PLAI mahcines
            cluster = "PLAI"
        elif "cdr[" in slurm_nodes:
            # Default configuration for cedar machines
            cluster = "CC"
        else:
            raise Exception("Unexpected SLURM nodes. Make sure you are on either of borg (UBC) or cedar (ComputeCanada)")
    else:
        raise Exception("No SLURM environment found (sinfo failed). Make sure you are on either of borg (UBC) or cedar (ComputeCanada)")
    # Add the cluster-specific parameters to the default parameters
    for k,v in json_data[cluster].items():
        DEFAULT_SLURM_ARGS[k] = v
    return DEFAULT_SLURM_ARGS

def resolve_slurm_aliases(slurm_args, slurm_flags):
    if "--cores" in slurm_args:
        assert "--ntasks-per-node" not in slurm_args, "Both --cores and --ntasks-per-node were found in SLURM arguments."
        slurm_args["--ntasks-per-node"] = slurm_args.pop("--cores")
    if "--gpu" in slurm_args:
        assert "--gres" not in slurm_args, "Both --gpu and --gres were found in SLURM arguments."
        for flag in slurm_flags:
            assert not flag.startswith("--gres"), "Both --gpu and --gres were found in SLURM arguments."
        slurm_flags.append(f"--gres=gpu:{slurm_args.pop('--gpu')}")
    if "--script" in slurm_args:
        global SUBMIT_JOB_SCRIPT
        SUBMIT_JOB_SCRIPT = BATCH_JOB_FILES_DIR / slurm_args.pop("--script")
    return slurm_args, slurm_flags


def arglist2dicts(arg_list):
    args = {}
    flags = []
    i = 0
    while i < len(arg_list):
        cur_arg = arg_list[i]
        assert cur_arg.startswith('-'), f"Argument should start with - or -- ({cur_arg})"
        if i+1 >= len(arg_list) or arg_list[i+1].startswith('-'):
            # It's a flag
            flags.append(cur_arg)
            i += 1
        else:
            # It's an argument which requires a value
            args[cur_arg] = arg_list[i+1]
            i += 2
    return args, flags


def parse_arguments(all_args):
    split_idx = all_args.index("--") if "--" in all_args else len(all_args)
    script_args = all_args[split_idx+1:]
    slurm_args = all_args[:split_idx]

    return resolve_slurm_aliases(*arglist2dicts(slurm_args)), script_args


if __name__ == "__main__":
    # Print current time
    now = datetime.now()
    current_time = now.strftime("%Y/%m/%d %H:%M:%S")
    print(f"Current Time: {current_time}")
    # Assertions
    assert SUBMIT_JOB_SCRIPT.exists(), f"Missing SLURM run sctipt at {SUBMIT_JOB_SCRIPT}."
    # Parse arguments
    script_path = sys.argv[0]
    (slurm_args, slurm_flags), script_args = parse_arguments(sys.argv[1:])
    # Add default arguments (if not already set by the user in command-line)
    DEFAULT_SLURM_ARGS = default_slurm_args()
    for k,v in DEFAULT_SLURM_ARGS.items():
        if k not in slurm_args:
            slurm_args[k] = v
    # Check SLURM arguments and make sure the required ones are existing
    if "--job-name" not in slurm_args and "-J" not in slurm_args:
        raise Exception("Experiment name not provided. Use -J or --job-name to provide one.")
    # Take out the job submission arguments no for slurm ([--array-tag])
    ARRAY_TAG = None
    if "--array-tag" in slurm_args:
        ARRAY_TAG = slurm_args.pop(ARRAY_TAG)
    # Provide log file paths to slurm (if not already set by the user in command-line)
    if "--output" not in slurm_args and "-o" not in slurm_args:
        if "--array" in slurm_args or "-a" in slurm_args:
            slurm_args["--output"] = REPORTS_DIR / "results-%A_%a-%x.out"
        else:
            slurm_args["--output"] = REPORTS_DIR / "results-%j-%x.out"
        if not REPORTS_DIR.exists():
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    # Get all arguments in string format
    script_args_str = ' '.join(script_args)
    slurm_args_str = ' '.join(f"{k} {v}" for (k,v) in slurm_args.items())
    slurm_args_str = slurm_args_str + ' ' + ' '.join(slurm_flags)
    slurm_args_str = slurm_args_str + ' --export=ALL'
    # Set and export environment variables to be used later by the SLURM run script.
    os.putenv("SCRIPT_ARGS", script_args_str)
    os.putenv("ROOT_DIR", str(ROOT_DIR))
    if ARRAY_TAG is not None:
        os.putenv("ARRAY_TAG", ARRAY_TAG)
    # Print
    print(f"submitting job: {slurm_args['job-name'] if 'job-nanme' in slurm_args else slurm_args['-J']}")
    print(f"\t {SBATCH_COMMAND} {slurm_args_str} {str(SUBMIT_JOB_SCRIPT)}")
    print(f"\t script arguments: {script_args_str}")
    # Submit the job
    cmd = " ".join([SBATCH_COMMAND, slurm_args_str, str(SUBMIT_JOB_SCRIPT)])
    subprocess.call(cmd, shell=True)
    print("--------------------------------------------------\n")