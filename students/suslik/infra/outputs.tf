output "public_ip" {
  description = "Elastic IP of the application server."
  value       = aws_eip.app.public_ip
}

output "instance_id" {
  description = "EC2 instance identifier."
  value       = aws_instance.app.id
}

output "app_url" {
  description = "Public URL of the EcoTrack dashboard."
  value       = "http://${aws_eip.app.public_ip}:${var.app_port}"
}

output "ssh_command" {
  description = "Example SSH command (replace the key path with your own)."
  value       = "ssh -i ./ec2_key ec2-user@${aws_eip.app.public_ip}"
}
