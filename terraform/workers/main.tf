locals {
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")
  worker_vm_tags_full = {
    for key, suffix in var.worker_vm_tags :
    key => contains(["datapipeline_ingress_node_hostname"], key)
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
  # Use an absolute path so that it always writes to the intended user's home
  filename             = "/home/almalinux/.ssh/ansible_v2"
  file_permission      = "0600"
  directory_permission = "0700"
}

# Fix ownership of the generated key so that the key is owned by the 'almalinux' user.
resource "null_resource" "chown_ansible_v2" {
  depends_on = [local_file.ansible_v2_private]
  provisioner "local-exec" {
    command = "chown almalinux:almalinux /home/almalinux/.ssh/ansible_v2"
  }
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

