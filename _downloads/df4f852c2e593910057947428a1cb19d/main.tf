# ---------------------------------------------------------------------------------------------------------------------
# Anyscale Add-on Resources for GCP Compute Engine
# This creates only the Anyscale-specific resources for use with existing GCP infrastructure
# ---------------------------------------------------------------------------------------------------------------------



provider "google" {
  project = var.google_project_id
  region  = var.google_region
}

# Generate a random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Data source to get current project information
data "google_project" "current" {
  project_id = var.google_project_id
}

locals {
  full_labels = merge(tomap({
    anyscale-cloud-id = var.anyscale_cloud_id,
    }),
    var.labels
  )
}

# Create GCS bucket for Anyscale logs and shared resources
module "anyscale_cloudstorage" {
  source = "anyscale/anyscale-cloudfoundation-modules/google//modules/google-anyscale-cloudstorage"

  module_enabled = true
  
  bucket_iam_members = [
    "serviceAccount:${google_service_account.compute_nodes.email}"
  ]

  anyscale_bucket_name = var.bucket_name != null ? var.bucket_name : "${var.common_prefix}-bucket-${random_id.suffix.hex}"
  bucket_force_destroy = false
  anyscale_project_id  = var.google_project_id
  
  labels = local.full_labels
}

# Create Filestore instance for shared storage (optional)
module "anyscale_filestore" {
  count  = var.enable_filestore ? 1 : 0
  source = "anyscale/anyscale-cloudfoundation-modules/google//modules/google-anyscale-filestore"

  module_enabled = true
  
  filestore_vpc_name = google_compute_network.anyscale_vpc.name
  filestore_tier     = var.filestore_tier
  filestore_location = "${var.google_region}-${var.filestore_zone}"
  
  anyscale_project_id = var.google_project_id
  labels              = local.full_labels
}

# Create workload identity pool for Anyscale authentication
resource "google_iam_workload_identity_pool" "anyscale_pool" {
  workload_identity_pool_id = "${var.workload_identity_pool_prefix}-${random_id.suffix.hex}"
  display_name              = "Anyscale Workload Identity Pool"
  description               = "Identity pool for Anyscale authentication"
  project                   = var.google_project_id
}

# Create workload identity pool provider for AWS
resource "google_iam_workload_identity_pool_provider" "anyscale_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.anyscale_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "anyscale-provider"
  display_name                       = "Anyscale Provider"
  description                        = "AWS identity pool provider for Anyscale"
  
  attribute_mapping = {
    "google.subject"           = "assertion.arn"
    "attribute.aws_account_id" = "assertion.account"
  }
  
  attribute_condition = "assertion.arn.startsWith('arn:aws:sts::${local.aws_account_id}:assumed-role/${var.aws_role_name}')"
  
  aws {
    account_id = local.aws_account_id
  }
}

# Create service account for Anyscale compute nodes
resource "google_service_account" "compute_nodes" {
  account_id   = "${var.service_account_name_prefix}-${random_id.suffix.hex}"
  display_name = "Service Account for Anyscale Compute Engine nodes"
  project      = var.google_project_id
}

# Grant Service Account User role to the service account for itself
resource "google_service_account_iam_member" "compute_nodes_self_user" {
  service_account_id = google_service_account.compute_nodes.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.compute_nodes.email}"
}

# Grant necessary roles to the service account
resource "google_project_iam_member" "compute_nodes_roles" {
  for_each = toset([
    "roles/storage.admin",                  # Access to GCS buckets
    "roles/file.editor",                    # Access to Filestore
    "roles/iam.serviceAccountTokenCreator", # Generate presigned URL for Google Cloud Storage
    "roles/logging.logWriter",              # Write logs
    "roles/monitoring.metricWriter",        # Write metrics
    "roles/monitoring.viewer",              # Read metrics
    "roles/compute.instanceAdmin.v1",       # Manage compute instances
    "roles/artifactregistry.reader"         # Pull container images
  ])

  project = var.google_project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.compute_nodes.email}"
}

# Bind the workload identity pool to the service account
# Note: This requires iam.serviceAccounts.setIamPolicy permission
# If you get a permission error, ask your GCP admin to grant you the "Service Account Admin" role
resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.compute_nodes.name
  role               = "roles/iam.workloadIdentityUser"
  
  members = [
    "principalSet://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.workload_identity_pool_prefix}-${random_id.suffix.hex}/attribute.aws_account_id/${local.aws_account_id}"
  ]
}

# ----------------
# Network Firewall Policy (Anyscale Standard)
# ----------------
resource "google_compute_network_firewall_policy" "anyscale_firewall_policy" {
  project = var.google_project_id
  name    = "anyscale-firewall-policy-${random_id.suffix.hex}"
  description = "Anyscale firewall policy for compute engine deployment"
}

resource "google_compute_network_firewall_policy_association" "anyscale_firewall_policy" {
  project = var.google_project_id
  name              = "anyscale-vpc-association"
  attachment_target = google_compute_network.anyscale_vpc.id
  firewall_policy   = google_compute_network_firewall_policy.anyscale_firewall_policy.name
}
# Internal traffic rule
resource "google_compute_network_firewall_policy_rule" "ingress_with_self" {
  project = var.google_project_id
  
  description     = "Internal Ingress Rule"
  direction       = "INGRESS"
  action          = "allow"
  enable_logging  = false
  firewall_policy = google_compute_network_firewall_policy.anyscale_firewall_policy.name
  priority        = 100

  match {
    src_ip_ranges = [google_compute_subnetwork.anyscale_subnet.ip_cidr_range]
    layer4_configs {
      ip_protocol = "tcp"
    }
    layer4_configs {
      ip_protocol = "udp"
    }
    layer4_configs {
      ip_protocol = "icmp"
    }
  }
}

# SSH access rule
resource "google_compute_network_firewall_policy_rule" "ssh_access" {
  project = var.google_project_id
  
  description     = "SSH Access Rule"
  direction       = "INGRESS"
  action          = "allow"
  enable_logging  = false
  firewall_policy = google_compute_network_firewall_policy.anyscale_firewall_policy.name
  priority        = 200

  match {
    src_ip_ranges = ["0.0.0.0/0"]
    layer4_configs {
      ip_protocol = "tcp"
      ports       = ["22"]
    }
  }
}

 