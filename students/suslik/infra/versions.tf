terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Partial backend configuration. Bucket, key and region are supplied by CI:
  #   terraform init -backend-config="bucket=..." -backend-config="key=..." ...
  # See the README for the one-time state bucket setup.
  backend "s3" {}
}
