variable "username" {
  description = "User's email address"
  type        = string
}

variable "id_rsa_pub" {
  description = "Path to your id_rsa public key file"
  type        = string
}

variable "marker_pub" {
  description = "Path to your marker public key file"
  type        = string
}

variable "image_name" {
  description = "Name of the Harvester image"
  type        = string
}

variable "image_namespace" {
  description = "Namespace of the Harvester image"
  type        = string
}

variable "network_name" {
  description = "Name of the network to attach the VMs"
  type        = string
}

variable "provider_namespace" {
  description = "Namespace for the Harvester provider"
  type        = string
}

variable "provider_endpoint" {
  description = "Harvester provider endpoint"
  type        = string
}

variable "provider_token" {
  description = "Harvester provider token"
  type        = string
  sensitive   = true
}

variable "worker_count" {
  description = "Number of worker VMs"
  type        = number
}

variable "worker_cpu" {
  description = "Number of CPUs for worker VMs"
  type        = number
}

variable "worker_memory" {
  description = "Memory for worker VMs"
  type        = string
}

variable "worker_disk_size" {
  description = "Disk size for worker VMs"
  type        = string
}

variable "worker_vm_tags" {
  description = "Tags for the worker VMs"
  type        = map(string)
}
