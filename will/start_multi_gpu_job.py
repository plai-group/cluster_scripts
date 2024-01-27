import os
from subprocess import run, PIPE
from time import sleep
import itertools as it



hostname = run('hostname', stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True).stdout.strip()
print(hostname)
job_script, queue = {
    'submit-ml': ('job.sh', 'ubcml-rti'),
    'borg': ('job.sh', 'plai'),
}[hostname.split('.')[0]]
print(f"Submitting to", (job_script, queue,))


def submit(command, jobname, n_gpus, n_hours):
    
    # set some environment variables - these will be passed though and accessible to the script we submit
    # (job.sh) inside the submitted job
    # COMMAND is what we use to pass through the Python command that will be run inside the job
    os.environ['COMMAND'] = command
    os.environ['GPUS'] = str(n_gpus)

    # compile an 'sbatch' command to use to start the job
    # there are some hard-coded values in here like the memory allocation (12GB per GPU) and the number of
    # CPUs (5 pe GPU). I think these are usually reasonable values but you may wish to change them.
    #
    # outputs (.out and .err) files will be saved inside '$SCRATCH/slurm-outputs/'. You need to set the
    # SCRATCH environment variable to point to a directory for this to work. I do so with the line
    # 'export SCRATCH="/ubc/cs/research/plai-scratch/wsgh"' in ~/.bashrc
    output_dir = os.path.join(os.environ['SCRATCH'], 'slurm-outputs')
    sbatch_command = f"sbatch --export=all --ntasks=1 -t {n_hours}:0:0 --mem={12000*max(1, n_gpus)} --cpus-per-task {5*max(1, n_gpus)} --gres=gpu:{n_gpus} -J {jobname} --output=\"{output_dir}/%j.out\" --error=\"{output_dir}/%j.err\" job.sh"

    # exectute sbatch_command and store the output in 'result'
    result = run(sbatch_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    
    # put together a message with the original command, Python command, and any output
    msg = sbatch_command + '\n' + str(command) + '\n' + str(result.stdout) + '\n' + str(result.stderr) + '\n'
    
    # print the message and then save it in our 'history.txt' file
    print(msg)
    with open('history.txt', 'a') as f:
        f.write(msg)

    # pause in between submitting jobs - o.w. scheduler might crash if too many jobs are submitted at once
    sleep(1)


# fill the below list with jobs to be submitted in form (name, n_gpus, n_hours, command to run)
# command to run should be e.g. a python calling your script - "python -V" is a dummy command
# which should just print out the Python version
commands = [
    ('example-job-name', 1, 3, "python -V"),
]

if __name__ == '__main__':
    for name, n_gpus, n_hours, command in commands:
        submit(command, jobname=name, n_gpus=n_gpus, n_hours=n_hours)
