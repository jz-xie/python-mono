data "aws_eks_cluster" "this" {
  name = var.cluster_name
}

data "aws_iam_openid_connect_provider" "this" {
  url = data.aws_eks_cluster.this.identity[0].oidc[0].issuer
}

data "aws_eks_cluster_auth" "this" {
  name = var.cluster_name
}

data "aws_iam_policy" "prefect_storage_staging_access" {
  name = var.prefect_storage_access_policy_name
}

