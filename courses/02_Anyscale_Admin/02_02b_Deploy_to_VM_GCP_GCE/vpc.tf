# Create VPC
resource "google_compute_network" "anyscale_vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
}

# Create subnet
resource "google_compute_subnetwork" "anyscale_subnet" {
  name          = var.subnet_name
  ip_cidr_range = var.subnet_cidr
  region        = var.google_region
  network       = google_compute_network.anyscale_vpc.id
}

# Note: Firewall rules are now managed by network firewall policies in main.tf
# This provides better integration with Anyscale's security requirements
