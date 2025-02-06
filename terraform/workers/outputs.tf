output "worker_vm_ips" {
  description = "List of worker VM IP addresses"
  value = [for w in harvester_virtualmachine.worker : w.network_interface[0].ip_address]
}
