output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.anyscale_vpc.vpc_id
}

output "subnet_ids" {
  description = "List of subnet IDs"
  value       = concat(module.anyscale_vpc.private_subnet_ids, module.anyscale_vpc.public_subnet_ids)
}

output "s3_bucket_id" {
  description = "The ID of the S3 bucket"
  value       = module.anyscale_s3.s3_bucket_id
}

output "instance_profile_arn" {
  description = "The ARN of the instance profile"
  value       = module.anyscale_iam_roles.iam_cluster_node_instance_profile_role_arn
}

output "anyscale_registration_command" {
  description = "The Anyscale registration command"
  value       = local.anyscale_register_command
}

output "efs_id" {
  description = "The ID of the EFS file system"
  value       = module.anyscale_efs.efs_id
}

output "security_group_id" {
  description = "The ID of the security group"
  value       = module.anyscale_security_group.security_group_id
} 