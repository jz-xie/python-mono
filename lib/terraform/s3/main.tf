resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  tags = merge(
    var.additional_tags,
    var.required_tags
  )
}

resource "aws_s3_bucket_public_access_block" "this" {
  count  = var.block_all_public_acccess ? 1 : 0
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "allow_access_from_another_account" {
  count  = var.bucket_policy != null ? 1 : 0
  bucket = aws_s3_bucket.this.id
  policy = var.bucket_policy.json
}
