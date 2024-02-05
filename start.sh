#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]
then
  set -a # automatically export all variables
  source .env
  set +a # stop automatically exporting variables
fi

flask run