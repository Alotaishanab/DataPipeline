#!/bin/bash
set -e

echo "Running setup phase..."
ansible-playbook ansible/playbooks/setup_phase.yml
echo "Setup phase completed."

echo "Running master pipeline..."
ansible-playbook ansible/playbooks/master_pipeline.yml
echo "Master pipeline completed."
