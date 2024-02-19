#!/bin/bash

# Load environment variables from .env file
if [ -f prod.env ]
then
  set -a # automatically export all variables
  source prod.env
  set +a # stop automatically exporting variables
fi

flask run