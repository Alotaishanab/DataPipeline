output "mgmt_vm_ip" {
  description = "The IP address of the management (host) VM"
  value       = harvester_virtualmachine.mgmt.network_interface[0].ip_address
}