# Job submission script instructions

These scripts are highly opinionated, meaning they enforce a strict directory structure and are only set up to work with my [machine learning project skeleton](https://github.com/vmasrani/ml_project_skeleton). That said they should be easy to modify for your own use.

## If you want to use my project template

Submissions happen entirely though python. See `submit.py` for an example. User imports specifies a dictionary of job options and a dictionary of hyperparameters, and calls `submit()` from `job_submitter.py`. A few comments:

- Rather than copying `static.py` and `job_submitter.py` into every new project, create a hidden directory in home (i.e. `~/.python`) and set your `PYTHONPATH` in your bashrc via:

  `export PYTHONPATH=~/.python:$PYTHONPATH`

then you can use `import job_submitter` in all your projects. Super handy to prevent the case where you have K copies of job_submitter.py and you've tweaked one of them but can't remember which.

- `submit.py` strictly enforces a few things (see comments within `submit.py` for more info). If you use my project skeleton, all requirements should be met. Just make sure to make a new directory for each experiment, and call `submit.py` within `modified_ml_project_skeleton/experiments/my_experiment_name/submit.py`.  Strict enforcement of directory structure is to ensure the output from each experiment is self contained.


## If you want to modify the scripts for your own project

The logic of `job_submitter.py` is broken into a few components, each of which should be easily modifiable for your own purposes:
1. Validate directory structure.
   - `verify_dirs()` checks the required path exists, and loads global parameters to avoid passing paths around everywhere. Also creates a unique timestamped results directory within the experiments folder.
2. Process hyperparameters
   - This expects a dictionary (or a list of dictionaries) in the format
        ```python
        my_hypers = {
            "lr":[0.001, 0.0001, ...],
            "seed":[1, 2, ...],
            "other_hyper": ['cat']
        }
        ```
        and will return a list of strings in of the form
        ```python
        my_hypers_strings = [
            "'lr=0.001' 'seed=1' 'other_hyper=cat'",
            "'lr=0.001' 'seed=2' 'other_hyper=cat'",
            "'lr=0.0001' 'seed=1' 'other_hyper=cat'",
            "'lr=0.0001' 'seed=2' 'other_hyper=cat'",
            ...
        ]
        ```
        note the extra single-quotes within the string. This is tailored for sacred's command line interface. **Modify line 157 for a different string format.**
  3. Iterate through each hyperparameter string and ask the user if they want to submit the job. The purpose of this is that the first submission will invariably fail for some reason or another. Submit a test job, wait to see that it runs correctly, then submit the rest.
  4. When a user submits a job, two command line string are made in `make_commands()`. The first turns the hyperparameter string into a sacred-specific python command, which looks something like
       ```python
        python_command = "python main.py with 'lr=0.001' 'seed=1' 'other_hyper=cat' "
        ```
        **Modify line 209 for a different python command**. The second produces the slurm command itself and shouldn't need to be modified.
  5. Finally, in `make_bash_script()`, a bash script `submit.sh` is made and saved using a prewritten template in `static.py` and the previously made python command.  **Modify make_bash_script() and static.py for different slurm configurations**. Line 79 actually calls the bash command. `submit.sh` is rewritten each time to prevent a buildup of submit.sh files, but if just want to make them then submit them yourself for debugging purposes, use the `manual_mode=True` flag.
