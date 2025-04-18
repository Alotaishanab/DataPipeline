# DataPipeline: Scalable Bioinformatics Processing Pipeline

This project provides a modular and scalable distributed pipeline for biological sequence analysis using the ESM2-T6-8M model. The system leverages infrastructure-as-code principles, distributed task scheduling, and shared storage to automate and streamline large-scale processing of protein sequences.

## 🌐 Repository
Access the full implementation and source code:
👉 **[GitHub Repository](https://github.com/Alotaishanab/DataPipeline.git)**

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Alotaishanab/DataPipeline.git
cd DataPipeline/terraform
```

### 2. Configure the `.env` File
Create a `.env` file with the following variables filled in:

```hcl
provider_token       = "YOUR_PROVIDER_TOKEN"
provider_namespace   = "YOUR_PROVIDER_NAMESPACE"
username             = "YOUR_USERNAME"
network_name         = "YOUR_NETWORK_NAME"
```

### 3. Deploy Infrastructure
Navigate to the host configuration directory and apply Terraform:
```bash
cd terraform/host
terraform apply -auto-approve
```

---

## 🔐 SSH Access Instructions

### SSH into the Management Node
```bash
ssh -i ~/.ssh/ansible_ed25519 almalinux@<IP_ADDRESS>
```

### Or using Proxy Jump
```bash
ssh -i ~/.ssh/ansible_ed25519 -J condenser-proxy almalinux@<IP_ADDRESS>
```

---

## 🚀 Running the Full Pipeline

Once logged into the management node:
```bash
cd DataPipeline
./run_pipeline.sh
```

---

## ✅ Running All Tests
**Please note run the tests after running ./run_pipeline.sh and setting up the pipeline **
```bash
cd DataPipeline/tests
./run_tests.sh
```

---

## 📈 Accessing Monitoring Services

Replace `<USERNAME>` with your actual username:

- **Prometheus:** https://<USERNAME>-prometheus.comp0235.condenser.arc.ucl.ac.uk/
- **Grafana:** https://<USERNAME>-grafana.comp0235.condenser.arc.ucl.ac.uk/
- **Node Exporter:** https://<USERNAME>-nodeexporter.comp0235.condenser.arc.ucl.ac.uk/
- **Web Server:** https://<USERNAME>-webserver.comp0235.condenser.arc.ucl.ac.uk/

### Grafana Login
- **Username:** `admin`
- **Password:** `admin`  
> ⚠️ You should change these credentials after first login!

---

## 📂 Directory Structure

```text
alotaishanab-datapipeline/
├── README.md
├── run_pipeline.sh
├── ansible/
│   ├── playbooks/
│   ├── roles/
│   ├── scripts/
│   └── tests/
├── backend/
│   ├── flask_server.py
│   ├── split_uploaded_fasta.py
│   └── tests/
├── benchmark_results/
├── docs/
├── frontend/
│   └── react-ui/
│       ├── public/
│       ├── src/
│       └── tests/
├── terraform/
│   ├── host/
│   ├── workers/
│   ├── scripts/
│   └── keys/
└── tests/
    └── run_tests.sh
```

Each component is modular, with clear separation between infrastructure, orchestration, backend logic, and UI.

---

## 🔮 Future Improvements

- Containerization using Docker
- Kubernetes-based orchestration
- S3-compatible object storage
- User authentication and multi-user dashboards
- Workflow engines like Airflow or Nextflow
