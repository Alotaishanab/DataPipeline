provider_endpoint  = "https://rancher.condenser.arc.ucl.ac.uk/k8s/clusters/c-m-bv9x5ngh"
provider_token     = "kubeconfig-u-fhgdi4zayztbpvr:dwrdmsvv68wbnq7vp7sb25bgl9qgmk466dghxvwb7ns756g8ggcn9b"
provider_namespace = "ucabbaa-comp0235-ns"
username           = "ucabbaa@ucl.ac.uk"

id_rsa_pub         = "../keys/id_rsa.pub"
marker_pub         = "../keys/lecturer_key.pub"

image_name         = "image-bp52g"
image_namespace    = "harvester-public"
network_name       = "ucabbaa-comp0235-ns/ds4eng"

worker_count       = 4
worker_cpu         = 4
worker_memory      = "32Gi"
worker_disk_size   = "50Gi"
worker_extra_disk_size = "200Gi"

worker_vm_tags = {
  # Note: nodemanager hostname will be overridden per worker dynamically
  "condenser_ingress_node_hostname"       = "ucabbaa-nodeexporter"
  "condenser_ingress_node_port"           = "9100"
  "condenser_ingress_nodemanager_hostname" = "ucabbaa-nodemanager"  # overridden in main.tf
  "condenser_ingress_nodemanager_port"     = "8042"
  "condenser_ingress_isAllowed"           = "true"
  "condenser_ingress_isEnabled"           = "true"
}
