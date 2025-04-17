clone the repo
https://github.com/Alotaishanab/DataPipeline.git

cd DataPipeline
cd terraform 
.env input your 
token and username 


#### Add Required Variables

Insert the following variables with your specific values:

```hcl
provider_token       = "YOUR_PROVIDER_TOKEN"
provider_namespace   = "YOUR_PROVIDER_NAMESPACE"
username             = "YOUR_USERNAME"
network_name         = "YOUR_NETWORK_NAME"
```

then cd into terraform/host
run terraform apply -auto approve

## 1. SSH into the Host Node

Use your marker’s private key or the `ansible_ed25519` key generated on the VM you are using to SSH into the host node:

```bash
ssh -i ~/.ssh/ansible_ed25519 almalinux@<HOST_IP_ADDRESS>
```

**Note:** Replace `<HOST_IP_ADDRESS>` with the actual IP address of your host node.

#### Using the Proxy Jump (-J) Option

If you're accessing the host node through the condenser-proxy, use the `-J` option as shown:

```bash
ssh -i ~/.ssh/ansible_ed25519 -J condenser-proxy almalinux@<HOST_IP_ADDRESS>
```

cd DataPipeline
and run 
./run_pipeline.sh 

and the whole pipeline will run and assemble itself 

you can visit your 





to run ansible test 

cd DataPipeline
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook   -i ansible/inventory/inventory.json   --ssh-common-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'   tests/ansible/test_playbooks.yml


to run frontend tests
cd DataPipeline/frontend/react-ui
run npm test


to run backend tests
cd DataPipeline
export PYTHONPATH=$PWD/backend
pytest backend/tests/



## Accessing Monitoring Services

After deployment, you can access the monitoring services using the following URLs. Replace `<USERNAME>` with your specific username:

- **Prometheus:** https://<USERNAME>-prometheus.comp0235.condenser.arc.ucl.ac.uk/
- **Grafana:** https://<USERNAME>-grafana.comp0235.condenser.arc.ucl.ac.uk/
- **Node Exporter:** https://<USERNAME>-nodeexporter.comp0235.condenser.arc.ucl.ac.uk/
- **Web Server:** https://<USERNAME>-webserver.comp0235.condenser.arc.ucl.ac.uk/

## Grafana Credentials

- **Username:** admin  
- **Password:** admin  

**Security Note:** It is highly recommended to change the default Grafana credentials after the initial setup to secure your monitoring dashboards.