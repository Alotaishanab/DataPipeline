#!/usr/bin/env python3
import os
import json
import subprocess
import sys
import socket

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

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        sys.exit(f"Error obtaining local mgmt IP: {e}")

def generate_static_inventory(outputs, mgmt_ip):
    worker_inventory = outputs.get("worker_inventory", {}).get("value", {})
    if not worker_inventory:
        sys.exit("Error: No worker_inventory found in Terraform outputs.")

    inventory = {
        "all": {
            "children": {
                "worker_inventory": {
                    "hosts": worker_inventory
                },
                "mgmt": {
                    "hosts": {
                        "localhost": {
                            "ansible_connection": "local"
                        }
                    }
                }
            }
        }
    }

    return inventory

if __name__ == "__main__":
    outputs = get_terraform_outputs()
    mgmt_ip = get_local_ip()  # Still fetched, in case you want to log or use elsewhere
    inv = generate_static_inventory(outputs, mgmt_ip)
    inventory_file = "/home/almalinux/DataPipeline/ansible/inventory/inventory.json"
    os.makedirs(os.path.dirname(inventory_file), exist_ok=True)
    with open(inventory_file, "w") as f:
        json.dump(inv, f, indent=2)
    print(f"Inventory written to {inventory_file}")
