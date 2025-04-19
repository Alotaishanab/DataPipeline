# DataPipeline: Scalable Bioinformatics Processing Pipeline

A distributed computational pipeline for protein sequence analysis using ESM2-T6-8M language models. Implements infrastructure-as-code and parallel processing for efficient large-scale biological data analysis.

GitHub Repository: https://github.com/Alotaishanab/DataPipeline.git

## Table of Contents
1. Setup Instructions
2. SSH Access
3. Testing
4. Monitoring
5. Project Structure
6. Development Roadmap

---

## SETUP INSTRUCTIONS

### Requirements
- Terraform v1.0 or later
- Existing SSH key pair at ~/.ssh/ansible_ed25519
- Valid UCL Condenser cluster credentials

### Deployment Process

1. Get the source code:
git clone https://github.com/Alotaishanab/DataPipeline.git
cd DataPipeline/terraform

2. Configure host node:
cd host/
nano terraform.tfvars

Required parameters:
network_name       = "FILL THIS"
provider_namespace = "FILL THIS"
provider_endpoint  = "FILL THIS"
provider_token     = "FILL THIS"
username           = "FILL THIS"

3. Initialize host environment:
terraform apply -auto-approve
ssh -i ~/.ssh/ansible_ed25519 almalinux@<HOST_VM_IP>

4. Set up worker nodes:
cd DataPipeline/terraform/workers/
nano terraform.tfvars
Fill the same variables as in the host node

5. Optional: Enable test mode (skips full dataset):
cd DataPipeline/ansible/scripts/controller.py
Set: ONLY_USER_MODE = True

6. Start the pipeline:
cd DataPipeline
./run_pipeline.sh

---

## SSH ACCESS INSTRUCTIONS

Standard connection:
ssh -i ~/.ssh/ansible_ed25519 almalinux@<HOST_VM_IP>

Through Condenser proxy:
ssh -i ~/.ssh/ansible_ed25519 -J condenser-proxy almalinux@<HOST_VM_IP>

---

## TESTING PROCEDURE

Run validation suite:
cd tests
./run_tests.sh

Verifications performed:
- API functionality checks
- Sequence file handling
- Task queue validation
- Interface components

---

## MONITORING ACCESS

Default configuration uses ucabbaav2 (modify in terraform.tfvars)
All endpoints are set to ucabbaav2 by default

Monitoring Endpoints:
Prometheus:    https://[username]-prometheus.comp0235.condenser.arc.ucl.ac.uk
Grafana:       https://[username]-grafana.comp0235.condenser.arc.ucl.ac.uk
Node Exporter: https://[username]-nodeexporter.comp0235.condenser.arc.ucl.ac.uk
Web Interface: https://[username]-webserver.comp0235.condenser.arc.ucl.ac.uk

Initial Grafana access:
User: admin
Pass: admin
(Change immediately after initial setup)

---

## PROJECT STRUCTURE

DataPipeline/
├── ansible/              # Deployment automation
├── backend/              # Core processing logic
├── frontend/             # Visualization interface
├── terraform/            # Infrastructure definitions
│   ├── host/             # Control plane
│   └── workers/          # Processing nodes
├── benchmark_results/    # Performance data
└── tests/                # Quality verification

---

## DEVELOPMENT PLANS

### Feature Pipeline
- Container deployment support
- Kubernetes integration
- Cloud storage compatibility
- Multi-user access controls
- Workflow system integration

