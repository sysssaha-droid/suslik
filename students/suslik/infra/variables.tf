variable "aws_region" {
  description = "AWS region where the EC2 instance is created."
  type        = string
  default     = "eu-central-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "aws_region must look like eu-central-1."
  }
}

variable "project_name" {
  description = "Prefix used for all resource names and tags."
  type        = string
  default     = "ecotrack"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.project_name))
    error_message = "project_name must be 2-21 lowercase letters, digits or dashes."
  }
}

variable "instance_type" {
  description = "EC2 instance type. t3.micro is enough for this app and fits the free tier."
  type        = string
  default     = "t3.micro"
}

variable "ssh_public_key" {
  description = "OpenSSH public key registered on the instance for the ec2-user deploy account."
  type        = string

  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) ", trimspace(var.ssh_public_key)))
    error_message = "Provide an OpenSSH public key, for example: ssh-ed25519 AAAA... user@host."
  }
}

variable "ssh_cidr" {
  description = "CIDR allowed to connect over SSH. Restrict it to your IP or to GitHub Actions runners."
  type        = string
  default     = "0.0.0.0/0"

  validation {
    condition     = can(cidrhost(var.ssh_cidr, 0))
    error_message = "ssh_cidr must be a valid CIDR block, for example 203.0.113.10/32."
  }
}

variable "app_port" {
  description = "Public TCP port of the EcoTrack HTTP API."
  type        = number
  default     = 8000

  validation {
    condition     = var.app_port >= 1 && var.app_port <= 65535
    error_message = "app_port must be between 1 and 65535."
  }
}

variable "root_volume_size" {
  description = "Size of the encrypted gp3 root volume in GiB."
  type        = number
  default     = 8

  validation {
    condition     = var.root_volume_size >= 8
    error_message = "root_volume_size must be at least 8 GiB."
  }
}
