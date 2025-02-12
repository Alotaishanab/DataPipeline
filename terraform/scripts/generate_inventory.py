#!/usr/bin/env python3
import os
import json
import subprocess
import sys

def get_terraform_outputs():
    try:
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

def generate_static_inventory(outputs):
    # Expect Terraform to output "worker_inventory" as a mapping of host names to host variables.
    worker_inventory = outputs.get("worker_inventory", {}).get("value", {})
    if not worker_inventory:
        sys.exit("Error: No worker_inventory found in Terraform outputs.")
    
    # Build an inventory that contains only the worker hosts.
    inventory = {
        "all": {
            "children": {
                "worker_inventory": {
                    "hosts": worker_inventory
                }
            }
        }
    }
    return inventory

if __name__ == "__main__":
    outputs = get_terraform_outputs()
    inv = generate_static_inventory(outputs)
    inventory_file = "/home/almalinux/DataPipeline/ansible/inventory/inventory.json"
    os.makedirs(os.path.dirname(inventory_file), exist_ok=True)
    with open(inventory_file, "w") as f:
        json.dump(inv, f, indent=2)
    print(f"Inventory written to {inventory_file}")
