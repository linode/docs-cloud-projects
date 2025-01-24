output "flask_app_public_ip" {
  value = aws_instance.flask_app.public_ip
}
