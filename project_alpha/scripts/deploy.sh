#!/bin/bash
#
# A simple script to deploy Project Alpha to a staging environment.
#

set -e

echo "--- Starting Project Alpha Deployment ---"

# Step 1: Run tests
echo "Running unit tests..."
python -m unittest discover tests
echo "Tests passed."

# Step 2: Package the application
echo "Packaging application..."
# (In a real scenario, this would create a zip or tarball)
sleep 1 # Simulate work
echo "Packaging complete."

# Step 3: Deploy to server (simulation)
# In a real script, this would use scp or rsync.
# We require an SSH key stored in the DEPLOY_KEY env var.
if [ -z "$DEPLOY_KEY" ]; then
  echo "Error: DEPLOY_KEY environment variable is not set."
  exit 1
fi

echo "Deploying to staging server..."
echo "Using key from DEPLOY_KEY variable."
sleep 1 # Simulate network activity
echo "Deployment successful!"

echo "--- Deployment Finished ---"
