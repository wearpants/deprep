#!/bin/bash
ROOT=$(dirname ${0})
${ROOT}/deprep.py requirements.txt overrides.txt extras.txt manual.txt license-report.csv


