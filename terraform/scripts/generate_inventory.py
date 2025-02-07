#!/usr/bin/env python3
import json
import subprocess
import sys

def get_terraform_outputs():
    try:
        # Use the full path to terraform so that it is found
        result = subprocess.run(
            ["/usr/local/bin/terraform", "output", "-json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        sys.exit(f"Error obtaining Terraform outputs: {e}")

def generate_inventory(outputs):
    inventory = {"_meta": {"hostvars": {}}}
    # Read the mapping from Terraform output (make sure your Terraform config outputs worker_inventory)
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
    inventory_file = "/home/almalinux/DataPipeline/ansible/inventory/inventory.json"  # adjust as needed
    with open(inventory_file, "w") as f:
        json.dump(inv, f, indent=2)
    print(f"Inventory written to {inventory_file}")
