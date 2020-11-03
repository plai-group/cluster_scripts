# Job submission script instructions
## Quick start
- First, set your default SLURM arguments in [batch_job_files/default.json](batch_job_files/default.json) (__most importantly, your email address__)
- Make sure the [submit_job.py](submit_job.py) is executable. It can be made executable by `chmod +x submit_job.py`.

### Submitting a generic job
- Run the following
    ```
    ./submit_job.py --script _run.sh -J <job_name> --time <time_limit> --mem <mem_limit> -- <WORKER_CMD>
    ```
    where `<WORKER_CMD>` is the command to be run by the worker.
- Example:
    ```
    ./submit_job.py --script _run.sh -J wandb_sweep --time 2:00:00 --mem 2G -- hostname
    ```
    it submits a job with the specified name, time limit and memory limit which runs the exact command `hostname` which prints the worker machine's name.

### Submitting a Python job
- Place the python environment activation command in the [ENV file](ENV) e.g. `source ~/.virtualenvs/venv/bin/activate`.
- Run the following
    ```
    ./submit_job.py -J <job_name> --time <time_limit> --mem <mem_limit> -- <PYTHON_ARGS>
    ```
    where `<PYTHON_ARGS>` are the arguments (including file name) to python.
- Example: The following submits a job called "test" with 2 hours time and 2GB memory limit which runs `python main.py with lr=0.1 batch_size=128`
    ```
    ./submit_job.py -J test --time 2:00:00 --mem 2G -- main.py with lr=0.1 batch_size=128
    ```

__NOTE__: The job outputs (both stdout and stderr) are logged in [batch_job_files/reports](batch_job_files/reports) with the naming format of `results-<job_id>-<job_name>.out` for non-array jobs and `results-<job_id>_<array_index>-<job_name>.out` for array jobs/

## How it works (in more details)
This is the job submission command format
```
./submit_job.py <JOB_SUBMISSION_ARGS> <SLURM_ARGS> -- <WORKER_ARGS>
```
It automatically detects the cluster you're on, sets the default arguments for that cluster (currently PLAI and cedar clusters are supported) and submits a SLURM job with `<SLURM_ARGS>` configuration. The submitted job will run one of the scripts in [batch_job_files](batch_job_files/) (we call that "worker script") and `<WORKER_ARGS>` are carried over to this worker script.
- `<JOB_SUBMISSION_ARGS>` are the arguments to the job submission script itself ([submit_job.py](submit_job.py)). Here is the list of supported arguments:
    - `--script <path>`: specifies the worker script. default: [_run_python.sh](batch_job_files/_run_python.sh)
    - `--array-tag`: (useful for array jobs) populates the environemnt variable `SLURM_ARRAY_TAG` and passes it to the worker script. It is useful for submitting array jobs the job array id (`SLURM_ARRAY_TASK_ID`) should be passed to the user script as an argument. See [batch_job_files/_run_python.sh](batch_job_files/_run_python.sh) for an example use.
- `<SLURM_ARGS>` are SLURM arguments. These commands are directly passed to the `sbatch` command (see [here](https://slurm.schedmd.com/sbatch.html) for the list of sbatch arguments). Additionally, This script supports the following config aliases:
    - `--cores <N>` (alias for `--ntasks-per-node`): specifies the number of CPU cores needed.
    - `--gpu <N>` (alias for `--gres=gpu:<N>`): specifies the number of GPUs needed.

    Here is a list of frequently used SLURM arguments:
    - `-J <job_name>`: specifies the job's name.
    - `--time <time_limit>`: specifies the job's time limit.
    - `--mem <mem_limit>`: specifies the job's memory limit.
    - `-w <node_name>`: specifies the node name to submit the job to.
    - `--array <first_idx>-<last_idx>`: submits an array job with indices in [first_idx, last_idx].
- `<WORKER_ARGS>` are the arguments to the user script. These arguments will be directly passed to the worker script (see .sh files in [batch_job_files/](batch_job_files/)) in an environment variable called `SCRIPT_ARGS`.
