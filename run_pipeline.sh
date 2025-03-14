#!/bin/bash
set -e

# Change directory to the ansible folder to ensure ansible.cfg is used
cd ansible

echo "Running setup phase..."
ansible-playbook playbooks/setup_phase.yml
echo "Setup phase completed."

echo "Running master pipeline..."
ansible-playbook playbooks/master_pipeline.yml
echo "Master pipeline completed."
