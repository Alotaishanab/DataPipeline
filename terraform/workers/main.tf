locals {
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")
  worker_vm_tags_full = {
    for key, suffix in var.worker_vm_tags :
    key => contains([
      "datapipeline_ingress_node_hostname"
    ], key)
      ? "${local.sanitized_username}${suffix}"
      : suffix
  }
}

resource "random_id" "secret" {
  byte_length = 4
}

resource "tls_private_key" "ansible_v2" {
  algorithm = "ED25519"
}

resource "local_file" "ansible_v2_private" {
  content              = tls_private_key.ansible_v2.private_key_openssh
  filename             = pathexpand("~/.ssh/ansible_v2")
  file_permission      = "0600"
  directory_permission = "0700"
}

data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

resource "harvester_virtualmachine" "worker" {
  count                = var.worker_count
  name                 = "${local.sanitized_username}-worker-${count.index + 1}-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description     = "Worker Node"
  cpu             = var.worker_cpu
  memory          = var.worker_memory
  efi             = true
  secure_boot     = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.sanitized_username}-worker-${count.index + 1}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"
  tags            = local.worker_vm_tags_full

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = var.worker_disk_size
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
        public_key_1 = file(var.id_rsa_pub),
        public_key_2 = file(var.marker_pub),
        public_key_3 = tls_private_key.ansible_v2.public_key_openssh
      }
    )
  }
  timeouts {
    create = "5m"
  }
}

resource "null_resource" "generate_inventory" {
  # Ensure that all worker VMs are created first.
  depends_on = [harvester_virtualmachine.worker]

  provisioner "local-exec" {
    # Run the generate_inventory.py script.
    # The script uses the state file from the workers directory and writes
    # the static inventory file to /home/almalinux/DataPipeline/ansible/inventory/inventory.json.
    command = "python3 ${path.module}/../scripts/generate_inventory.py"
  }
}
