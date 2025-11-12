

# Variables for Anyscale Add-on Resources for GCP Compute Engine

variable "google_project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "google_region" {
  description = "The Google Cloud region"
  type        = string
}

variable "anyscale_cloud_id" {
  description = "Anyscale Cloud ID"
  type        = string
}

variable "common_prefix" {
  description = "A common prefix to use for all resources"
  type        = string
}

variable "vpc_name" {
  description = "Name of the VPC to create"
  type        = string
  default     = "anyscale-compute-engine-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet to create"
  type        = string
  default     = "anyscale-subnet"
}

variable "subnet_cidr" {
  description = "CIDR range for the subnet"
  type        = string
  default     = "10.0.0.0/20"
}

variable "bucket_name" {
  description = "(Optional) GCS bucket name. If left null, will default to common_prefix-bucket-{random}"
  type        = string
  default     = null
}

variable "enable_filestore" {
  description = "Whether to create a Filestore instance for shared storage"
  type        = bool
  default     = true
}

variable "filestore_capacity_gb" {
  description = "The capacity of the Filestore instance in GB. Must be at least 1024 GB"
  type        = number
  default     = 1024
}

variable "filestore_tier" {
  description = "The tier of the filestore to create. Supported values: STANDARD, PREMIUM, BASIC_HDD, BASIC_SSD, HIGH_SCALE_SSD, ENTERPRISE, ZONAL, REGIONAL"
  type        = string
  default     = "STANDARD"
}

variable "labels" {
  description = "A map of labels to apply to all resources that accept labels"
  type        = map(string)
  default     = {
    environment = "development"
    project     = "anyscale-gcp-compute"
  }
}

# Workload Identity / AWS Authentication Variables
# AWS account ID is Anyscale's official production account used for all customer integrations
locals {
  aws_account_id = "525325868955"
}

variable "aws_role_name" {
  description = "The AWS IAM role name for workload identity federation (specific to your organization, provided by Anyscale support)"
  type        = string
}

variable "service_account_name_prefix" {
  description = "Prefix for the service account name"
  type        = string
  default     = "anyscale-nodes"
}

variable "workload_identity_pool_prefix" {
  description = "Prefix for the workload identity pool name"
  type        = string
  default     = "anyscale-pool"
}

variable "filestore_zone" {
  description = "The zone suffix for filestore location (e.g., 'a' for us-west2-a)"
  type        = string
  default     = "a"
}

 