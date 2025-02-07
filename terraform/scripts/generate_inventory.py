#!/usr/bin/env python3
import os
import json
import subprocess
import sys

def get_terraform_outputs():
    try:
        # Use the full path to terraform and set cwd so that the correct state file is used.
        result = subprocess.run(
            ["/usr/local/bin/terraform", "output", "-json"],
            capture_output=True,
            text=True,
            check=True,
            cwd="/home/almalinux/DataPipeline/terraform/workers"
        )
        return json.loads(result.stdout)
    except Exception as e:
        sys.exit(f"Error obtaining Terraform outputs: {e}")

def generate_inventory(outputs):
    inventory = {"_meta": {"hostvars": {}}}
    # Look for the Terraform output named "worker_inventory"
    worker_inventory = outputs.get("worker_inventory", {}).get("value", {})
    if not worker_inventory:
        sys.exit("Error: No worker_inventory found in Terraform outputs.")
    inventory["worker_inventory"] = {"hosts": []}
    for host, vars in worker_inventory.items():
        inventory["worker_inventory"]["hosts"].append(host)
        inventory["_meta"]["hostvars"][host] = vars
    # Also add localhost (if needed)
    inventory["localhost"] = {"hosts": ["localhost"]}
    inventory["_meta"]["hostvars"]["localhost"] = {"ansible_connection": "local"}
    return inventory

if __name__ == "__main__":
    outputs = get_terraform_outputs()
    inv = generate_inventory(outputs)
    inventory_file = "/home/almalinux/DataPipeline/ansible/inventory/inventory.json"
    # Ensure the directory exists
    os.makedirs(os.path.dirname(inventory_file), exist_ok=True)
    with open(inventory_file, "w") as f:
        json.dump(inv, f, indent=2)
    print(f"Inventory written to {inventory_file}")
