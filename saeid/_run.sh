#!/bin/bash

echo ${EXP_DIR}
cd ${EXP_DIR}

if [ -f "ENV" ]; then
    source ENV
fi

eval $SCRIPT_ARGS
