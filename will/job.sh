#!/bin/bash

# some of our codebases use these environment variables to set up wandb logging, so
# customize these lines or remove them as needed
export WANDB_ENTITY="wsgharvey"
export WANDB_PROJECT="example-project"

# activate python environment
conda activate my-python-environment

# go to the directory of whatever codebase you're using
cd $SCRATCH/example-directory/

# run the command passed through by the "COMMAND" environment variable
exec $COMMAND
