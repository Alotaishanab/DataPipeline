#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------
# 1) Ansible tests
# ----------------------------------------
echo "==> Running Ansible tests…"
ANSIBLE_CONFIG=ansible/ansible.cfg \
  ansible-playbook \
    -i ansible/inventory/inventory.json \
    --ssh-common-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' \
    ansible/tests/test_playbooks.yml

# ----------------------------------------
# 2) Backend tests
# ----------------------------------------
echo "==> Running backend (pytest) tests…"
export PYTHONPATH="$(pwd)/backend"
pytest backend/tests/

# ----------------------------------------
# 3) Frontend tests
# ----------------------------------------
echo "==> Running React frontend tests…"
pushd frontend/react-ui >/dev/null
# CI=true ensures it exits after running, and --watchAll=false turns off watch mode
CI=true npm test -- --watchAll=false
popd >/dev/null

echo "✅ All tests passed!"
