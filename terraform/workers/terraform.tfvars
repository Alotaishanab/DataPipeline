provider_endpoint  = "" # FILL THIS HERE 
provider_token     = "" # FILL THIS HERE  
provider_namespace = "" # FILL THIS HERE 
network_name    = "" # FILL THIS HERE 
username           = "Fill THIS HERE"   

id_rsa_pub       = "../keys/id_rsa.pub"
marker_pub  = "../keys/lecturer_key.pub"

image_name      = "image-bp52g" 
image_namespace = "harvester-public" 

# Worker VM Specs
worker_count     = 4         # Four workers as per specification
worker_cpu       = 4
worker_memory    = "32Gi"
worker_disk_size = "50Gi"
worker_extra_disk_size = "200Gi"


# Instance Tags for Worker VMs (updated with NodeManager UI)
worker_vm_tags = {
  # Existing Node Exporter monitoring
  "condenser_ingress_node_hostname"       = "ucabbaav2-nodeexporter"
  "condenser_ingress_node_port"           = "9100"

  # Newly added NodeManager Web UI (for YARN container logs)
  "condenser_ingress_nodemanager_hostname" = "ucabbaav2-nodemanager"
  "condenser_ingress_nodemanager_port"     = "8042"

  # Required flags for exposure
  "condenser_ingress_isAllowed"           = "true"
  "condenser_ingress_isEnabled"           = "true"
}
