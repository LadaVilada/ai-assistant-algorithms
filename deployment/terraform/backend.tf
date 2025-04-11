terraform {
  backend "s3" {
    bucket = "my-tf-state-bucket"
    key    = "state/recipe-assistant.tfstate"
    region = "us-east-1"
  }
}