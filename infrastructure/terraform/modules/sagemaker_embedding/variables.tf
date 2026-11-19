variable "name_prefix" { type = string }
variable "aws_region" { type = string }
variable "sagemaker_image_uri" {
  type    = string
  default = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:1.13.1-transformers4.26.0-cpu-py39-ubuntu20.04"
}
variable "embedding_model_name" {
  type    = string
  default = "sentence-transformers/all-MiniLM-L6-v2"
}
variable "memory_size_mb" {
  type    = number
  default = 3072
}
variable "max_concurrency" {
  type    = number
  default = 2
}
variable "tags" {
  type    = map(string)
  default = {}
}