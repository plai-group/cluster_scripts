#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import re

VERBOSE = True if "SUBMIT_JOB_VERBOSE" in os.environ else False

# NOTE: SLURM argument/value pairs should be passed with whitespaces in between and not equal signs.

DEFAULT_SLURM_ARGS = {"--mail-user": "saeidnp@cs.ubc.ca",
                      "--mail-type": "ALL",
                      "--mem": "4G", 
                      "--time": "12:00:00"}
SBATCH_COMMAND = "sbatch"
# Paths
EXP_DIR = Path(os.getcwd())
ROOT_DIR = Path(__file__).parent.absolute()
SUBMIT_JOB_SCRIPT = ROOT_DIR / "_run.sh"
REPORTS_DIR = EXP_DIR / "batch_job_reports"

# Arguments:
# --script: used to change the default worker script. The scripts should be placed under ROOT_DIR directory r.g. <ROOT_DIR>/_run_python.sh
# --array-tag: (only useful for array jobs) if given, uses the provided value as the python script argument name to pass SLURM_ARRAY_TASK_ID
# Useful SLURM options (and SLURM option aliases):
# --cores <N>: specifies the number of CPU cores needed
# --gpu <N>: specifies the number of GPUs needed
# -w <node_name>: specifies a node name
# --array <first_idx>-<last_idx>: submits an array job with indices in [first_idx, last_idx]

def jobid_from_stdout(stdout, stderr):
    prefix = "Submitted batch job "
    msg = re.findall(prefix + r"[0-9]+", stdout)
    assert len(msg) == 1, "Unexpected stdout from the sbatch command:\nSTDOUT:\n{}\n{}\nSTDERR:\n{}".format(stdout, '-' * 10, stderr)
    msg = msg[0]
    jobid = msg[len(prefix):]
    return jobid

def default_slurm_args():
    """ Identifies the cluster (PLAI/CC) and create the default parameters (DEFAULT_SLURM_ARGS)
        accordingly based on the json file at <ROOT_DIR>/default.json

    Raises:
        Exception: If there is no SLURM environment
        Exception: If the SLURM cluster machines are not recognized (neither of UBC or ComputeCanada-cedar)
    
    Returns:
        dict: a dictionary containing default SLURM arguments
    """
    DEFAULT_SLURM_ARGS = {}
    # Read the json config file
    config_file_path = str(ROOT_DIR / "default.json")
    with open(config_file_path) as json_file:
        json_data = json.load(json_file)
    # Set the cluster-independent default parameters
    if "__all__" in json_data:
        d = json_data["__all__"]
        if "--mail-user" in d:
            assert d["--mail-user"] is not None and len(d["--mail-user"]) > 0,\
                "The email address is not set in {}".format(config_file_path)
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
    return DEFAULT_SLURM_ARGS, cluster

def resolve_slurm_aliases(slurm_args, slurm_flags):
    if "--cores" in slurm_args:
        assert "--cpus-per-task" not in slurm_args, "Both --cores and --cpus-per-task were found in SLURM arguments."
        slurm_args["--cpus-per-task"] = slurm_args.pop("--cores")
    if "--gpu" in slurm_args:
        assert "--gres" not in slurm_args, "Both --gpu and --gres were found in SLURM arguments."
        for flag in slurm_flags:
            assert not flag.startswith("--gres"), "Both --gpu and --gres were found in SLURM arguments."
        slurm_flags.append("--gres=gpu:{}".format(slurm_args.pop('--gpu')))
    if "--script" in slurm_args:
        global SUBMIT_JOB_SCRIPT
        SUBMIT_JOB_SCRIPT = ROOT_DIR / slurm_args.pop("--script")
    return slurm_args, slurm_flags


def arglist2dicts(arg_list):
    args = {}
    flags = []
    i = 0
    while i < len(arg_list):
        cur_arg = arg_list[i]
        assert cur_arg.startswith('-'), "Argument should start with - or -- ({})".format(cur_arg)
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
    print("Current Time: {}".format(current_time))
    # Assertions
    assert SUBMIT_JOB_SCRIPT.exists(), "Missing SLURM run sctipt at {}.".format(SUBMIT_JOB_SCRIPT)
    # Parse arguments
    script_path = sys.argv[0]
    (slurm_args, slurm_flags), script_args = parse_arguments(sys.argv[1:])
    # Add default arguments (if not already set by the user in command-line)
    DEFAULT_SLURM_ARGS, cluster_name = default_slurm_args()
    for k,v in DEFAULT_SLURM_ARGS.items():
        if k not in slurm_args:
            slurm_args[k] = v
    # Check SLURM arguments and make sure the required ones are existing
    if "--job-name" not in slurm_args and "-J" not in slurm_args:
        raise Exception("Experiment name not provided. Use -J or --job-name to provide one.")
    # Take out the job submission arguments no for slurm ([--array-tag])
    SLURM_ARRAY_TAG = None
    if "--array-tag" in slurm_args:
        SLURM_ARRAY_TAG = slurm_args.pop("--array-tag")
    # Provide log file paths to slurm (if not already set by the user in command-line)
    if "--output" not in slurm_args and "-o" not in slurm_args:
        if "--array" in slurm_args or "-a" in slurm_args:
            slurm_args["--output"] = REPORTS_DIR / "results-%A_%a-%x.out"
        else:
            slurm_args["--output"] = REPORTS_DIR / "results-%j-%x.out"
        if not REPORTS_DIR.exists():
            REPORTS_DIR.mkdir(exist_ok=True)
    # Get all arguments in string format
    script_args_str = ' '.join(script_args)
    slurm_args_str = ' '.join("{} {}".format(k, v) for (k,v) in slurm_args.items())
    slurm_args_str = slurm_args_str + ' ' + ' '.join(slurm_flags)
    slurm_args_str = slurm_args_str + ' --export=ALL'
    # Set and export environment variables to be used later by the SLURM run script.
    os.putenv("SCRIPT_ARGS", script_args_str)
    os.putenv("EXP_DIR", str(EXP_DIR))
    if SLURM_ARRAY_TAG is not None:
        os.putenv("SLURM_ARRAY_TAG", SLURM_ARRAY_TAG)
    # Print
    def get_header_f(header, width, dashes_width):
        """Returns the given header in pretty printing format (something like "#---- {header} ----").
            In case the header is None, returns a string of the format "#------" with its length
            matching the header
        Args:
            header: The header string itself
            width: The width of the header (will pad the header if shorter than this argument)
            dashes_width: The additional width around the (padded) header
        """
        if header is None:
            return "#" + "-"*(header_dashes_width * 2 + header_width + 1)
        ldashes = max(0, (width - len(header)) // 2) # Number of padding dashes on the left of the header
        rdashes = max(0, (width - len(header) + 1) // 2) # Number of padding dashes on the right of the header
        assert len(header) + ldashes + rdashes == width
        return "#{} {} {}".format("-" * (header_dashes_width - 1 + ldashes),
               header,
               "-" * (rdashes + header_dashes_width))
    def get_output_line(k, v=None):
        if v is None:
            return "# {}".format(k)
        return "# {:20}: {}".format(k, v)
    header_width = 30
    header_dashes_width = 15
    get_header = lambda x: get_header_f(x, header_width, header_dashes_width)
    ## Print SLRUM arguments
    print(get_header("SLURM arguments ({})".format(cluster_name)))
    job_name = slurm_args['job-name'] if 'job-name' in slurm_args else slurm_args['-J']
    print(get_output_line("Job name", job_name))
    for k, v in slurm_args.items():
        if k == "-J" or k == "--job-name":
            continue
        print(get_output_line(k.lstrip('-'), v))
    ## Print SLURM flags
    for k in slurm_flags:
        print(get_output_line(k.lstrip('-'), "(flag)"))
    ## Print script arguments
    print(get_header("Script arguments"))
    print(get_output_line(script_args_str))

    # Submit the job
    cmd = " ".join([SBATCH_COMMAND, slurm_args_str, str(SUBMIT_JOB_SCRIPT)])
    if VERBOSE:
        print(cmd)

    proc = subprocess.Popen(cmd,
                            stderr=subprocess.PIPE, 
                            stdout = subprocess.PIPE,
                            universal_newlines=True,
                            shell=True)
    stdout = proc.stdout.read()
    stderr = proc.stderr.read()
    proc.communicate()
    returncode = proc.returncode
    proc.stdout.close()
    proc.stderr.close()
    if VERBOSE:
        print(stdout)
        print(stderr)
    # Extract and print the job id
    jobid = jobid_from_stdout(stdout, stderr)
    print(get_header("Job submission"))
    print(get_output_line("Job ID", jobid))
    print(get_header(None))
