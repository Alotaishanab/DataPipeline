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
  # Prometheus + Grafana + NodeExporter
  "condenser_ingress_prometheus_hostname"     = "ucabbaa-prometheus"
  "condenser_ingress_prometheus_port"         = "9090"
  "condenser_ingress_grafana_hostname"        = "ucabbaa-grafana"
  "condenser_ingress_grafana_port"            = "3000"
  "condenser_ingress_nodeexporter_hostname"   = "ucabbaa-nodeexporter"
  "condenser_ingress_nodeexporter_port"       = "9100"

  # Webserver + Celery Flower
  "condenser_ingress_webserver_hostname"      = "ucabbaa-webserver"
  "condenser_ingress_flower_hostname"         = "ucabbaa-flower"
  "condenser_ingress_flower_port"             = "5555"

  # MinIO (S3 Endpoint)
  "condenser_ingress_os_hostname"             = "ucabbaa-s3"
  "condenser_ingress_os_port"                 = "9000"
  "condenser_ingress_os_protocol"             = "https"
  "condenser_ingress_os_nginx_proxy-body-size"= "100000m"

  # MinIO Console
  "condenser_ingress_cons_hostname"           = "ucabbaa-cons"
  "condenser_ingress_cons_port"               = "9001"
  "condenser_ingress_cons_protocol"           = "https"
  "condenser_ingress_cons_nginx_proxy-body-size" = "100000m"

  # Global Ingress Control
  "condenser_ingress_isAllowed"               = "true"
  "condenser_ingress_isEnabled"               = "true"
}



