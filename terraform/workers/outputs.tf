output "worker_inventory" {
  description = "Mapping of worker host names to their IP addresses"
  value = {
    for idx, ip in [for w in harvester_virtualmachine.worker : w.network_interface[0].ip_address] :
    "worker${idx + 1}" => { ansible_host = ip }
  }
}
