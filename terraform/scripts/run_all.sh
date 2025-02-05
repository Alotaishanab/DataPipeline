#!/bin/bash
set -e

# --- Functions ---

install_terraform() {
    if ! command -v terraform &> /dev/null; then
        echo "Terraform not found. Installing Terraform..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            TERRAFORM_VERSION="1.10.1"
            wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
            unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip
            sudo mv terraform /usr/local/bin/
            rm -f terraform_${TERRAFORM_VERSION}_linux_amd64.zip
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            TERRAFORM_VERSION="1.10.1"
            brew tap hashicorp/tap
            brew install hashicorp/tap/terraform
        else
            echo "Unsupported OS. Please install Terraform manually."
            exit 1
        fi
    else
        echo "Terraform is already installed."
    fi
}

install_packages() {
    echo "Installing required packages..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -y
            sudo apt-get install -y wget unzip git python3
        elif command -v yum &> /dev/null; then
            sudo yum update -y
            sudo yum install -y epel-release
            sudo yum install -y wget unzip git python3
        else
            echo "Unsupported Linux package manager. Please install wget, unzip, git, and python3 manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install wget unzip git python3
        if ! command -v jq &> /dev/null; then
            echo "jq not found. Installing jq..."
            brew install jq
        fi
    else
        echo "Unsupported OS. Please install wget, unzip, git, and python3 manually."
        exit 1
    fi
}

generate_placeholder_files() {
    CONDENSER_CERT_FILE=~/.ssh/id_arc_rsa.signed
    CONDENSER_IDENTITY_FILE=~/.ssh/id_rsa

    if [ ! -f "$CONDENSER_CERT_FILE" ]; then
        echo "Generating placeholder for CertificateFile at $CONDENSER_CERT_FILE..."
        touch "$CONDENSER_CERT_FILE"
        echo "# Placeholder for CertificateFile. Please add your CertificateFile here." > "$CONDENSER_CERT_FILE"
        chmod 600 "$CONDENSER_CERT_FILE"
        echo "Please edit $CONDENSER_CERT_FILE and add your CertificateFile."
    fi

    if [ ! -f "$CONDENSER_IDENTITY_FILE" ]; then
        echo "Generating placeholder for IdentityFile at $CONDENSER_IDENTITY_FILE..."
        touch "$CONDENSER_IDENTITY_FILE"
        echo "# Placeholder for IdentityFile. Please add your IdentityFile here." > "$CONDENSER_IDENTITY_FILE"
        chmod 600 "$CONDENSER_IDENTITY_FILE"
        echo "Please edit $CONDENSER_IDENTITY_FILE and add your IdentityFile."
    fi
}

update_known_hosts() {
    echo "Updating known_hosts with the jump host key..."
    ssh-keyscan -H ssh.condenser.arc.ucl.ac.uk >> ~/.ssh/known_hosts 2>/dev/null
    echo "Jump host key added to ~/.ssh/known_hosts"
}

run_terraform() {
    echo "Initializing Terraform..."
    terraform init
    echo "Applying Terraform configuration..."
    terraform apply -auto-approve
}

get_ssh_config() {
    echo "Fetching SSH configuration from Terraform output..."
    SSH_CONFIG=$(terraform output -raw ssh_config)
}

print_ssh_instructions() {
    echo ""
    echo "=============================================="
    echo "         SSH Access Instructions              "
    echo "=============================================="
    echo ""
    echo "You can SSH into your VMs using the following commands:"
    echo ""
    echo "$SSH_CONFIG" | awk '/^Host / {host=$2} /^    HostName / {print "ssh -i ~/.ssh/ansible_ed25519" (ENVIRON["ON_CONDENSER"] == "true" ? "" : " -J condenser-proxy") " almalinux@"$2" # "host}'
    echo ""
    echo "=============================================="
    echo "Ensure that your SSH keys are correctly set up."
    echo "=============================================="
}

# --- Main script execution ---

install_packages
install_terraform
generate_placeholder_files

# Change directory to the Terraform directory (parent of the current scripts directory)
echo "Changing directory to the Terraform directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")"
echo "Terraform directory resolved to: $TERRAFORM_DIR"
cd "$TERRAFORM_DIR" || { echo "Failed to change directory to $TERRAFORM_DIR"; exit 1; }

echo "Current directory: $(pwd)"
echo "Listing Terraform directory contents:"
ls -la

# Run Terraform to provision VMs
run_terraform

# Retrieve and display SSH config from Terraform outputs
get_ssh_config
print_ssh_instructions

echo "Provisioning and setup complete."
echo "You can now SSH into the Host VM using the instructions above."

# Update known_hosts to pre-populate jump host key.
update_known_hosts

echo "Done."
