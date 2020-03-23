#!/bin/bash
poetry export -f requirements.txt --dev --without-hashes >requirements.txt

