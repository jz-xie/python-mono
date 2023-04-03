terraform {
  #   backend "s3" {
  #     bucket = "sample-bucket"
  #     key    = "sample-prefix"
  #     region = "us-east-1"
  #   }
}

provider "aws" {
  region = "us-east-1"
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.this.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.this.token
}

module "irsa" {
  source = "./irsa"

  eks_cluster_id        = data.aws_eks_cluster.this.id
  eks_oidc_provider_arn = data.aws_iam_openid_connect_provider.this.arn

  create_kubernetes_namespace = false
  kubernetes_namespace        = "prefect"
  kubernetes_service_account  = var.project

  irsa_iam_role_name = var.project
  irsa_iam_policies = concat(
    [data.aws_iam_policy.prefect_storage_staging_access.arn],
    var.job_iam_policies
  )
  additional_assume_role_policy_statements = var.additional_assume_role_policy_statements
}
