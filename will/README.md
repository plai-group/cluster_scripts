# Will's cluster scripts

These scripts are very minimal compared to the others in this repository. I have one copy of these scripts for each project I work on, since things like the Python environment are hardcoded. Some features I like about them: the job submission script [saves a permanent record of every job I submit (commands used, job ID, etc)](#history.txt), and this script is simple enough that you can just quickly write a few lines of Python to create any list of jobs to be submitted.

There are two scripts in here: `start_jobs.py`, is the one which you call to submit jobs and which internally calls `sbatch ... job.sh`. Then `job.sh` contains the code that is executed on the cluster. The same `job.sh` file can be used to run different commands since it runs `exec $COMMAND`, executing any command passed in with the environment variable `COMMAND`. This environment variable is set before submitting each job in `start_jobs.py`.

## Setting up

### Set $SCRATCH environment variable
In my `~/.bashrc` file I have the line `export SCRATCH="/ubc/cs/research/plai-scratch/wsgh"`, which sets an environment variable to point to my directory in plai-scratch. `start_jobs.py` is configured to save logs inside a subdirectory of this (`$SCRATCH/slurm-outputs`), using this environment variable, and so for this to work I recommend adding a similar line in your `~/.bashrc`. Once you have added it to your `~/.bashrc` and run `source ~/.bashrc`, you will then need to make the subdirectory by running `mkdir $SCRATCH/slurm-outputs`.

### Set up wandb project/username
Some of our codebases which log to [wandb.ai/](wandb.ai/) use the environment variables `WANDB_ENTITY` and `WANDB_PROJECT` internally to find where to log to. These are hardcoded inside `job.sh`, so modify these to your own wandb username/teamname and desired project name.

### Set up Python environment and current directory
There is a line in `job.sh` to activate a Python environment. Edit this line to whatever command you use to start your Python environment. Similarly, the line after that goes to whichever directory my codebase for the project lives in. Edit this as well.

### Running on clusters other than the PLAI cluster
These scripts as given are for the PLAI cluster, to be submitted on borg, since the `sbatch` command inside `start_jobs.py` is given `-p plai` as an argument. You should change this to `-p ubcml-rti` to run on the UBC ML cluster, and to something like `--account=rrg-kevinlb` for Compute Canada. 

## Submitting a job (or jobs)
Inside `start_jobs.py`, the `commands` list defines which jobs will be started. It is a list of tuples. Each tuple describes a single job to start. You will want to change the first item in each tuple, the job name (which will show whenever you call `squeue -u $USER` to check on your running jobs). The second item is the number of GPUs that the job will use, currently set to 1. The third item in each tuple is the number of hours that the job should run for. The fourth item is the command itself that should be run, e.g. `python train.py ...` . Modify all of these to whatever parameters you desire.

I like defining this list of commands inside a Python script since it makes it trivially each to run searches lists of parameters by e.g. using a list comprehension:
```
commands = [
    ('example-job-name', 1, 3, f"python train.py --seed {seed}"),
    for seed in range(10)
]
```
or by naively listing them, or in any other way.

Once your commands are set up, just run `python start_jobs.py`. Output will be printed to the terminal for each command submitted and should look something like:
```
wsgh@borg:will$ python3 start_jobs.py 
sbatch -p plai --export=all --ntasks=1 -t 3:0:0 --mem=12000 --cpus-per-task 5 --gres=gpu:1 -J example-job-name --output="/ubc/cs/research/plai-scratch/wsgh/slurm-outputs/%j.out" --error="/ubc/cs/research/plai-scratch/wsgh/slurm-outputs/%j.err" job.sh
python -V
Submitted batch job 1077919
```

## Output from your job

### history.txt
All of the output printed to the terminal when you run `python start_jobs.py` is also appended to `history.txt` in this folder, giving a permanent record of all the jobs/commands you've ever submitted, with their training commands, sbatch commands, and job IDs

### .out and .err files
Your job will also save a `{job_id}.out` and `{job_id}.err` file inside `$SCRATCH/slurm-outputs` if everything is configured correctly. If you want to find these files for a particular job you submitted but don't know it's job id, check in `history.txt`, which will contain the job id.
