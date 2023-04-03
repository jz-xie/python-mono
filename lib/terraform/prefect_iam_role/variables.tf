variable "aws_region" {
  description = "AWS Region to be used that was defined in AWS CLI configuration"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name of your project/product/application"
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

variable "job_iam_policies" {
  description = "ARNs of the policies required by the job"
  type        = list(string)
}

variable "additional_assume_role_policy_statements" {
  description = "Additional assume role policy statements"
  # type = object({
  # Version = string, Statement = list(map) })
  # default     = ""
}

variable "prefect_storage_access_policy_name" {
  description = "Policy to access prefect S3 storage"
  type = string
}