variable "aws_region" {
  description = "The AWS region in which all resources will be created."
  type        = string
  default     = "us-west-2"
}

variable "anyscale_cloud_name" {
  description = "The name of the Anyscale cloud."
  type        = string
  default     = "anyscale-cloud-ec2-private-example"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "172.24.0.0/16"
}

variable "customer_ingress_cidr_ranges" {
  description = <<-EOT
    The IPv4 CIDR block that is allowed to access the clusters.
    This provides the ability to lock down the stack to just the public IPs of a corporate network.
    This is added to the security group and allows port 443 (https) access.
    ex: `52.1.1.23/32,10.1.0.0/16`
  EOT
  type        = list(string)
  default     = ["52.1.1.23/32", "10.1.0.0/16"]
}

variable "role_permissions_boundary_arn" {
  description = "Permissions boundary ARN to use for IAM role."
  type        = string
  default     = null
}

variable "anyscale_default_trusted_role_arns" {
  description = "ARNs of AWS entities who can assume these roles. Allow Anyscale's AWS account (525325868955) to assume this role in your AWS account"
  type        = list(string)
  default     = ["arn:aws:iam::525325868955:root"]
}

variable "tags" {
  description = "A map of tags to all resources that accept tags."
  type        = map(string)
  default     = {
    Environment = "development"
    Project     = "anyscale-ec2-new"
  }
} 
