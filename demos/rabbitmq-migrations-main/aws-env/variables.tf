variable "aws_region" {
  default = "us-west-1"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance"
  default = "ami-0da424eb883458071"
}

variable "instance_name" {
  description = "EC2 instance name"
  default = "FlaskAppSNS"
}

variable "aws_access_key" {}

variable "aws_secret_key" {}
