username           = ""
id_rsa_pub         = "../keys/id_rsa.pub"
marker_pub         = "../keys/lecturer_key.pub"
image_name         = "image-bp52g"
image_namespace    = "harvester-public"
network_name       = "" # FILL THIS HERE 
provider_namespace = "" # FILL THIS HERE 
provider_endpoint  = "" # FILL THIS HERE 
provider_token     = "" # FILL THIS HERE 
mgmt_cpu           = 2
mgmt_memory        = "4Gi"
mgmt_disk_size     = "10Gi"
mgmt_vm_tags = {
  # ── Prometheus / Grafana / Node‑Exporter ───────────────────────────
  "condenser_ingress_prometheus_hostname"     = "ucabbaav2-prometheus"
  "condenser_ingress_prometheus_port"         = "9090"
  "condenser_ingress_grafana_hostname"        = "ucabbaav2-grafana"
  "condenser_ingress_grafana_port"            = "3000"
  "condenser_ingress_nodeexporter_hostname"   = "ucabbaav2-nodeexporter"
  "condenser_ingress_nodeexporter_port"       = "9100"

  # ── Web‑server ingress ─────────────────────────────────────────────
  "condenser_ingress_webserver_hostname"      = "ucabbaav2-webserver"
  "condenser_ingress_webserver_port"                = "80"
  "condenser_ingress_webserver_protocol"            = "http"
  "condenser_ingress_webserver_nginx_proxy-body-size" = "2048m"

  # ── Global ingress flags ───────────────────────────────────────────
  "condenser_ingress_isAllowed"               = "true"
  "condenser_ingress_isEnabled"               = "true"
}




