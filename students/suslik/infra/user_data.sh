#!/bin/bash
# cloud-init bootstrap for the EcoTrack server.
# Installs Docker and prepares the deploy directory. The application
# container itself is started by the GitHub Actions deploy job.
set -euxo pipefail

# Docker is the only runtime dependency on the host.
dnf install -y docker
systemctl enable --now docker

# The deploy user must be able to talk to the Docker daemon.
usermod -aG docker ec2-user

# Helper directory used by the deployment pipeline.
install -d -o ec2-user -g ec2-user /opt/ecotrack
