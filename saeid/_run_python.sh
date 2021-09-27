#!/bin/bash

echo ${EXP_DIR}
cd ${EXP_DIR}

if [ -f "ENV" ]; then
    source ENV
fi

if [ -z $ARRAY_TAG ]
then
    python $SCRIPT_ARGS
else
    python $SCRIPT_ARGS ${ARRAY_TAG} ${SLURM_ARRAY_TASK_ID}
fi
