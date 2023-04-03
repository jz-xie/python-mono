variable "aws_region" {
  description = "AWS Region to be used that was defined in AWS CLI configuration"
  type        = string
  default     = "us-east-1"
}

variable "app" {
  description = "Name of application"
  type        = string
}


variable "environment" {
  description = "Workspace environment: staging or production"
  type        = string
}

variable "cluster_name" {
  description = "EKS Cluster name"
  type        = string
}

variable "aws_rds_engine_name" {
  description = "AWS RDS engine name"
  type        = string
}

variable "aws_rds_engine_version" {
  description = "AWS RDS engine version"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "Security groups for the RDS instance"
  type        = list(string)
}

variable "db_subnet_group_name" {
  description = "Subnet group name for the RDS instance"
  type        = string
}


variable "instances" {
  description = "Instances argument for RDS cluster"
  type        = map(map(any))
  default = {
    one = {}
  }
}

variable "rds_master_passwored" {
  description = "Master password for the RDS cluster"
  type        = string
  sensitive   = true
}

variable "publicly_accessible" {
  description = "Whether the RDS is publicly accessible"
  type        = bool
  default     = false
}
