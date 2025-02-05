locals {
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")
  mgmt_vm_tags_full  = {
    for key, suffix in var.mgmt_vm_tags :
    key => contains([
      "datapipeline_ingress_prometheus_hostname",
      "datapipeline_ingress_grafana_hostname",
      "datapipeline_ingress_nodeexporter_hostname",
      "datapipeline_ingress_webserver_hostname"
    ], key)
      ? "${local.sanitized_username}${suffix}"
      : suffix
  }
}

resource "random_id" "secret" {
  byte_length = 4
}

# Generate a key pair for the host internal purpose (optional)
resource "tls_private_key" "ansible_v1" {
  algorithm = "ED25519"
}

# Optionally, store the private key locally (this remains on your local machine, not injected)
resource "local_file" "ansible_v1_private" {
  content              = tls_private_key.ansible_v1.private_key_openssh
  filename             = pathexpand("~/.ssh/ansible_v1")
  file_permission      = "0600"
  directory_permission = "0700"
}

data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

resource "harvester_virtualmachine" "mgmt" {
  name                 = "${local.sanitized_username}-mgmt-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description     = "Management Node"
  cpu             = var.mgmt_cpu
  memory          = var.mgmt_memory
  efi             = true
  secure_boot     = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.sanitized_username}-mgmt-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"
  tags            = local.mgmt_vm_tags_full

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = var.mgmt_disk_size
    bus         = "virtio"
    boot_order  = 1
    image       = data.harvester_image.img.id
    auto_delete = true
  }

  cloudinit {
    type      = "noCloud"
    user_data = templatefile(
      "${path.module}/templates/cloud-config.yaml",
      {
        public_key_1     = file(var.id_rsa_pub),
        public_key_2     = file(var.marker_pub),
        public_key_3 = tls_private_key.ansible_v1.public_key_openssh
      }
    )
  }
  timeouts {
    create = "5m"
  }
}
