username           = "ucabbaa@ucl.ac.uk"
id_rsa_pub         = "../keys/id_rsa.pub"
marker_pub         = "../keys/lecturer_key.pub"
image_name         = "image-bp52g"
image_namespace    = "harvester-public"
network_name       = "ucabbaa-comp0235-ns/ds4eng"
provider_namespace = "ucabbaa-comp0235-ns"
provider_endpoint  = "https://rancher.condenser.arc.ucl.ac.uk/k8s/clusters/c-m-bv9x5ngh"
provider_token     = "kubeconfig-u-fhgdi4zayztbpvr:dwrdmsvv68wbnq7vp7sb25bgl9qgmk466dghxvwb7ns756g8ggcn9b"
mgmt_cpu           = 2
mgmt_memory        = "4Gi"
mgmt_disk_size     = "10Gi"
mgmt_vm_tags = {
  "condenser_ingress_prometheus_hostname"   = "ucabbaa-prometheus"
  "condenser_ingress_prometheus_port"         = "9090"
  "condenser_ingress_grafana_hostname"        = "ucabbaa-grafana"
  "condenser_ingress_grafana_port"            = "3000"
  "condenser_ingress_nodeexporter_hostname"   = "ucabbaa-nodeexporter"
  "condenser_ingress_nodeexporter_port"       = "9100"
  "condenser_ingress_hadoop_hostname"         = "ucabbaa-hadoop"
  "condenser_ingress_hadoop_port"             = "9870"
  "condenser_ingress_yarn_hostname"           = "ucabbaa-yarn"
  "condenser_ingress_yarn_port"               = "8088"
  "condenser_ingress_nodemanager_hostname"    = "ucabbaa-nodemanager-host"
  "condenser_ingress_nodemanager_port"        = "8042"
  "condenser_ingress_webserver_hostname"      = "ucabbaa-webserver"
  "condenser_ingress_isAllowed"               = "true"
  "condenser_ingress_isEnabled"               = "true"
}



