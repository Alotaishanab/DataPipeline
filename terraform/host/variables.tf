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
  description = "Name of the network to attach the VM"
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

variable "mgmt_cpu" {
  description = "Number of CPUs for the management VM"
  type        = number
}

variable "mgmt_memory" {
  description = "Memory for the management VM"
  type        = string
}

variable "mgmt_disk_size" {
  description = "Disk size for the management VM"
  type        = string
}

variable "mgmt_vm_tags" {
  description = "Tags for the management VM"
  type        = map(string)
}
