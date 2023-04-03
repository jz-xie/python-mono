output "IAM_Role_ARN" {
  value = module.irsa.irsa_iam_role_arn
}

output "service_account" {
  value = module.irsa.service_account
}

output "service_account_namespace" {
  value = module.irsa.namespace
}
