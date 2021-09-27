# Job submission script instructions
## Quick start
- First, set your default SLURM arguments in [default.json](default.json) (__most importantly, your email address__)
- Make sure the [submit_job.py](submit_job.py) is executable. It can be made executable by `chmod +x submit_job.py`.
- __Setting it up as a bash function__: You can add the following code to your bashrc or zshrc file. It defines makes this submissions script accessible in your terminal!
    ```
    submit_job(){
        <PATH_TO_submit_job.py> $*
    }
    ```
    where `<PATH_TO_submit_job.py>` should be replaced with the absolute path to the `submit_job.py` file. Then, you can replace all the `./submit_job.py` in the following sections with `submit_job`.

### Submitting a generic job

- Run the following
    ```
    ./submit_job.py -J <job_name> --time <time_limit> --mem <mem_limit> -- <WORKER_CMD>
    ```
    where `<WORKER_CMD>` is the command to be run by the worker.

- Example:
    ```
    ./submit_job.py -J wandb_sweep --time 2:00:00 --mem 2G -- hostname
    ```
    it submits a job with the specified name, time limit and memory limit which runs the exact command `hostname` which prints the worker machine's name.

- __NOTE__: the job submission script ([_run.sh](_run.sh)) runs `source ENV` in the working directory if the file `ENV` exists. It gives the ability to prepare environments for example, setting environment variables or activating a Python virtual environment. A simple example of the contents of an `ENV` file is `source ~/.virtualenvs/venv/bin/activate`.

- The job outputs (both stdout and stderr) are logged in a directory called `batch_job_reports` in the working directoy (this directory will be created if it does not exist). Each output file has the naming format of `results-<job_id>-<job_name>.out` for non-array jobs and `results-<job_id>_<array_index>-<job_name>.out` for array jobs.
- __NOTE__: If you use the custom `zshrc` file provided in this repository, it defines a custom function `submit_job` that calls `submit_job.py` under the hood. Therefore, it won't be required to type in the full file path anymore.

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
