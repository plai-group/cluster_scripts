#!/bin/bash

echo ${ROOT_DIR}
cd ${ROOT_DIR}

source "ENV"

echo '# hostname = '`hostname`

if [ ! -z $SLURM_ARRAY_TAG ]
then
    python $SCRIPT_ARGS
else
    python $SCRIPT_ARGS ${SLURM_ARRAY_TAG} ${SLURM_ARRAY_TASK_ID}
fi