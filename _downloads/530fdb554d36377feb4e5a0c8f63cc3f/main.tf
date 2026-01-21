locals {
  public_subnets  = ["172.24.101.0/24", "172.24.102.0/24"]
  private_subnets = ["172.24.20.0/24", "172.24.21.0/24"]
  
  tags = merge(var.tags, {
    "managed-by" = "terraform",
    "deployment" = "anyscale-ec2-new-vpc"
  })
}

# Create a new VPC
module "anyscale_vpc" {
  source = "github.com/anyscale/terraform-aws-anyscale-cloudfoundation-modules//modules/aws-anyscale-vpc"

  anyscale_vpc_name = "anyscale-ec2-vpc"
  cidr_block        = var.vpc_cidr

  public_subnets  = local.public_subnets
  private_subnets = local.private_subnets

  tags = local.tags
}

# Create S3 bucket first (IAM depends on this)
module "anyscale_s3" {
  source = "github.com/anyscale/terraform-aws-anyscale-cloudfoundation-modules//modules/aws-anyscale-s3"
  
  module_enabled = true
  tags = var.tags
  anyscale_bucket_name = "anyscale-ec2-new-${var.aws_region}"
}

# Create custom security group (following EKS example pattern)
module "anyscale_security_group" {
  source = "github.com/anyscale/terraform-aws-anyscale-cloudfoundation-modules//modules/aws-anyscale-securitygroups"

  vpc_id = module.anyscale_vpc.vpc_id
  security_group_name = "anyscale-ec2-sg-new"
  security_group_description = "Anyscale EC2 Security Group (New VPC)"

  # HTTPS access from customer CIDR ranges (no SSH)
  ingress_from_cidr_map = [
    {
      rule        = "https-443-tcp"
      cidr_blocks = join(",", var.customer_ingress_cidr_ranges)
      description = "Allow HTTPS from customer CIDR ranges"
    }
  ]

  # Allow all traffic within the VPC for internal communication
  ingress_with_self = [
    {
      rule = "all-all"
      description = "Allow all traffic from within the VPC"
    }
  ]

  tags = local.tags
}

# Create IAM roles (depends on S3 bucket)
module "anyscale_iam_roles" {
  source = "github.com/anyscale/terraform-aws-anyscale-cloudfoundation-modules//modules/aws-anyscale-iam"

  anyscale_access_role_name = "anyscale-ec2-role-new"
  anyscale_access_role_path = "/"
  anyscale_access_role_description = "Anyscale EC2 IAM Role (New VPC)"
  role_permissions_boundary_arn = var.role_permissions_boundary_arn
  anyscale_default_trusted_role_arns = var.anyscale_default_trusted_role_arns
  
  # Pass S3 bucket ARN to IAM module
  anyscale_s3_bucket_arn = module.anyscale_s3.s3_bucket_arn
  
  depends_on = [module.anyscale_s3]
}

# Create EFS (following EKS example pattern)
module "anyscale_efs" {
  source = "github.com/anyscale/terraform-aws-anyscale-cloudfoundation-modules//modules/aws-anyscale-efs"

  module_enabled = true

  anyscale_efs_name          = "anyscale-ec2-efs-new"
  mount_targets_subnet_count = length(local.private_subnets)
  mount_targets_subnets      = module.anyscale_vpc.private_subnet_ids

  associated_security_group_ids = [module.anyscale_security_group.security_group_id]

  tags = local.tags
  
  depends_on = [module.anyscale_security_group]
}

# Generate the Anyscale registration command
locals {
  anyscale_register_command = <<EOT
anyscale cloud register --provider aws \
  --name ${var.anyscale_cloud_name} \
  --region ${var.aws_region} \
  --vpc-id ${module.anyscale_vpc.vpc_id} \
  --subnet-ids ${join(",", concat(module.anyscale_vpc.private_subnet_ids, module.anyscale_vpc.public_subnet_ids))} \
  --s3-bucket-id ${module.anyscale_s3.s3_bucket_id} \
  --anyscale-iam-role-id ${module.anyscale_iam_roles.iam_anyscale_access_role_arn} \
  --instance-iam-role-id ${module.anyscale_iam_roles.iam_cluster_node_role_arn} \
  --security-group-ids ${module.anyscale_security_group.security_group_id} \
  --efs-id ${module.anyscale_efs.efs_id}
EOT
} 