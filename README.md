clone the repo
https://github.com/Alotaishanab/DataPipeline.git

cd DataPipeline
cd terraform 
.env input your 
token and username 
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