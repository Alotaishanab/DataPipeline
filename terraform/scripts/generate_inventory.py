#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

def run(command):
    return subprocess.run(command, capture_output=True, text=True)

def get_terraform_outputs():
    """
    Fetch all Terraform outputs in JSON format.
    """
    tf = run(["terraform", "output", "-json"])
    if tf.returncode != 0:
        print("Error: Could not run 'terraform output -json'. Please ensure Terraform is initialized.", file=sys.stderr)
        sys.exit(1)
    try:
        outputs = json.loads(tf.stdout)
    except json.JSONDecodeError:
        print("Error: Could not parse Terraform outputs as JSON.", file=sys.stderr)
        sys.exit(1)
    return outputs

def generate_inventory(outputs):
    """
    Generate Ansible inventory from Terraform outputs.
    Note: Storage outputs are omitted in this configuration.
    """
    mgmt_list = outputs.get("mgmt_vm_ips", {}).get("value", [])
    worker_list = outputs.get("worker_vm_ips", {}).get("value", [])
    
    if not mgmt_list:
        print("Error: No mgmt_vm_ips found in Terraform outputs.", file=sys.stderr)
        sys.exit(1)
    if not worker_list:
        print("Error: No worker_vm_ips found in Terraform outputs.", file=sys.stderr)
        sys.exit(1)
    
    inventory = {
        "all": {
            "children": {
                "mgmtnode": {},
                "workers": {}
            }
        },
        "mgmtnode": {
            "hosts": {
                "host": {"ansible_host": mgmt_list[0]}
            }
        },
        "workers": {
            "hosts": {f"worker{i+1}": {"ansible_host": ip} for i, ip in enumerate(worker_list)}
        }
    }
    return inventory

def main():
    outputs = get_terraform_outputs()
    inventory = generate_inventory(outputs)
    
    # Updated path: Go three levels up from this file (scripts -> terraform -> DataPipeline)
    inventory_file_path = Path(__file__).resolve().parent.parent.parent / "ansible/inventories/inventory.json"
    inventory_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(inventory_file_path, "w") as f:
        json.dump(inventory, f, indent=4)
    
    print(f"Inventory saved to {inventory_file_path}")
    print(json.dumps(inventory, indent=4))

if __name__ == "__main__":
    main()
