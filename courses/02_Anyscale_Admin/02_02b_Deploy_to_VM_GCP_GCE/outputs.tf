# Outputs from the Anyscale add-on resources

locals {
  registration_command_parts = compact([
    "anyscale cloud register",
    "--name <anyscale_cloud_name>",
    "--provider gcp",
    "--region ${var.google_region}",
    "--compute-stack vm",
    "--anyscale-operator-iam-identity ${google_service_account.compute_nodes.email}",
    "--cloud-storage-bucket-name ${module.anyscale_cloudstorage.cloudstorage_bucket_name}",
    "--project-id ${var.google_project_id}",
    "--vpc-name ${google_compute_network.anyscale_vpc.name}",
    "--subnet-names ${google_compute_subnetwork.anyscale_subnet.name}",
    "--anyscale-service-account-email ${google_service_account.compute_nodes.email}",
    "--instance-service-account-email ${google_service_account.compute_nodes.email}",
    "--provider-name projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.workload_identity_pool_prefix}-${random_id.suffix.hex}/providers/anyscale-provider",
    "--firewall-policy-names ${google_compute_network_firewall_policy.anyscale_firewall_policy.name}",
    length(module.anyscale_filestore) > 0 ? "--file-storage-id ${module.anyscale_filestore[0].anyscale_filestore_name}" : "",
    length(module.anyscale_filestore) > 0 ? "--filestore-location ${module.anyscale_filestore[0].anyscale_filestore_location}" : ""
  ])
}

output "gcs_bucket_name" {
  description = "The name of the GCS bucket"
  value       = module.anyscale_cloudstorage.cloudstorage_bucket_name
}

output "compute_nodes_service_account_email" {
  description = "The email of the Compute Engine nodes service account"
  value       = google_service_account.compute_nodes.email
}

output "filestore_instance_name" {
  description = "The name of the Filestore instance"
  value       = length(module.anyscale_filestore) > 0 ? module.anyscale_filestore[0].anyscale_filestore_name : null
}

# Note: filestore IP address output not available in this module version

output "filestore_location" {
  description = "The location of the Filestore instance"
  value       = length(module.anyscale_filestore) > 0 ? module.anyscale_filestore[0].anyscale_filestore_location : null
}

output "anyscale_registration_command" {
  description = "The Anyscale registration command to register this infrastructure with Anyscale"
  value       = join(" \\\n    ", local.registration_command_parts)
}

output "firewall_policy_name" {
  description = "The name of the network firewall policy created"
  value       = google_compute_network_firewall_policy.anyscale_firewall_policy.name
}

output "workload_identity_pool_provider" {
  description = "The workload identity pool provider for AWS authentication"
  value       = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.workload_identity_pool_prefix}-${random_id.suffix.hex}/providers/anyscale-provider"
}

 