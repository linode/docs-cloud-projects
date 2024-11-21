# Kafka One-Click CLUSTER
![kafka-cluster.png](images/kafka-cluster-04.png)

Apache Kafka is a robust, scalable, and high-performance system for managing real-time data streams. Its versatile architecture and feature set make it an essential component for modern data infrastructure, supporting a wide range of applications from log aggregation to real-time analytics and more. Whether you are building data pipelines, event-driven architectures, or stream processing applications, Kafka provides a reliable foundation for your data needs.

The manual deployment of Kafka is using Kafka's native consensus protocol, [KRaft](https://kafka.apache.org/documentation/#kraft). There are a few things to highligh from our deployment:

- While the provisioning, the cluster will be configured with mTLS for authentication. This means that inter-broker communication as well as client authentication is established via certificate identity
- The minimum cluster size is 3. At all times, 3 controllers are configured in the cluster for fault-tolerance.
- Clients that connect to the cluster will need their own valid certificate. All certificates are create with a self-signed Certicate Authority (CA). Client keystores and truststore are found on the first Kafka node in `/etc/kafka/ssl/keystore` and `/etc/kafka/ssl/truststore`
- The CA key and certificate pair are on the first Kafka node in `/etc/kafka/ssl/ca`

## Distributions

- Ubuntu 24.04 LTS

## Sotware Included

| Software  | Version   | Description   |
| :---      | :----     | :---          |
| Apache Kafka    | 3.8.0    | Scalable, high-performance, fault-tolerant streaming processing application  |
| KRaft | | Kafka native consensus protocol |
| UFW      | 0.36.1    | Uncomplicated Firewall |
| Fail2ban   | 0.11.2    | Bruteforce protection utility |

## Installation

Create a virtual environment to isolate dependencies from other packages on your system.

```
python3 -m venv env
source env/bin/activate
pip install -U pip
```

Install Ansible collections and required Python packages.

```
pip install -r requirements.txt
ansible-galaxy collection install -r collections.yml
```

## Setup

All secrets are encrypted with Ansible vault for best practices. To run the next commands you will need to export `VAULT_PASSWORD` so that secrets can be encrypted. Let's go ahead and export:

```command
export VAULT_PASSWORD=MyVaultPassword
```

Please replace `MyVaultPassword` with your own. 

Encrypt your Linode root password and valid APIv4 token with ansible-vault. Replace the value of @R34llyStr0ngP455w0rd! with your own strong password and `LINODE_TOKEN` with your own access token.

```
ansible-vault encrypt_string '@R34llyStr0ngP455w0rd!' --name 'root_password'
ansible-vault encrypt_string '@R34llyStr0ngP455w0rd!' --name 'sudo_password'
ansible-vault encrypt_string 'LINODE_TOKEN' --name 'api_token'
ansible-vault encrypt_string '@R34llyStr0ngP455w0rd!' --name 'truststore_password'
ansible-vault encrypt_string '@R34llyStr0ngP455w0rd!' --name 'keystore_password'
ansible-vault encrypt_string '@R34llyStr0ngP455w0rd!' --name 'ca_password'
```

Copy the generated outputs to the group_vars/kafka/secret_vars file.

```
root_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38306438386334663834633634363930343233373066353234616363356534653033346232333538
          3163313031373138383965383739356339663831613061660a666332636564356236656331323361
          61383134663166613462363633646330678356561386230383332313564643135343538383161383236
          6432396332643232620a393630633132336134613039666336326337376566383531393464303864
          34306435376534653961653739653232383262613336383837343962633565356546
sudo_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38306438386334663834633634363930343233373066353234616363356534653033346232333538
          3163313031373138383965383739356339663831613061660a666332636564356236656331323361
          61383134663166613462363633646330356561386230383332313564643135343538383161383236
          6432396332643232620a393630633sdf32336134613039666336326337376566383531393464303864
          34306435376534653961653739653232383262613336383837343962633565356546
api_token: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38306438386334663834633634363930343233373066353234616363356534653033346232333538
          3163313031373138383965383739356339663831613061660a666332636564356236656331323361
          6138313466316661346236363364567330356561386230383332313564643135343538383161383236
          6432396332643232620a393630633132336134613039666336326337376566383531393464303864
          34306435376534653961653739653232383262613336383837343962633565356546
truststore_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38306438386334663834633634363930343233373066353234616363356534653033346232333538
          3163313031373138383965383739356339663831613061660a666332636564356236656331323361
          6138313466316661346236363364567330356561386230383332313564643135343538383161383236
          6432396332643232620a393630633132336134613039666336326337376566383531393464303864
          34306435376534653961653739653232383262613336383837343962633565356546
keystore_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38306438386334663834633634363930343233373066353234616363356534653033346232333538
          3163313031373138383965383739356339663831613061660a666332636564356236656331323361
          6138313466316661346236363364567330356561386230383332313564643135343538383161383236
          6432396332643232620a393630633132336134613039666336326337376566383531393464303864
          34306435376534653961653739653232383262613336383837343962633565356546
ca_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38306438386334663834633634363930343233373066353234616363356534653033346232333538
          3163313031373138383965383739356339663831613061660a666332636564356236656331323361
          6138313466316661346236363364567330356561386230383332313564643135343538383161383236
          6432396332643232620a393630633132336134613039666336326337376566383531393464303864
          34306435376534653961653739653232383262613336383837343962633565356546                              
```

The first thing that we need to do is update the Linode instance parameters located in `group_vars/kafka/vars`. The following values need to be updated with your own values:

```
ssh_keys:
  - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJQalZuAjeiWaPek5kJZxP4rTxuKlWgtSDFsdEGddf user1@desktop.local
  - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCg2ANZcgWWFGh0vakgX1/xw== user2@desktop.local

instance_prefix: kafka
type: g6-dedicated-2
region: us-southeast
image: linode/ubuntu22.04
group:
linode_tags:

cluster_size: 3
client_count: 2
sudo_username: admin

#tls
country_name: US
state_or_province_name: Pennsylvania
locality_name: Philadelphia
organization_name: Akamai Technologies
email_address: webmaster@example.com
ca_common_name: Kafka RootCA
```

## Usage

Run `provision.yml` to stand up the compute instances and write your Ansible inventory to the hosts file. The playbook will complete when ssh becomes available on all instances.

```
ansible-playbook -vvv provision.yml"
```

Once that's complete you will see the following output:

```
PLAY RECAP ************************************************************************************************************************************************************************************************************************************************************
localhost                  : ok=6    changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Next run the `site.yml` playbook with against the inventory file. This playbook will configure and install all required dependancies in for cluster.

```
ansible-playbook -vvv -i hosts site.yml
```

When the playbook is finished, you should see a similar output:

```
PLAY RECAP ************************************************************************************************************************************************************************************************************************************************************
192.0.2.21                 : ok=25   changed=24   unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
198.51.100.17              : ok=25   changed=24   unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
203.0.113.24               : ok=49   changed=46   unreachable=0    failed=0    skipped=3    rescued=0    ignored=0
```

## Producing and Consuming Data

### Install Python Dependancy

Now that you have a Kafka cluster up an running on your account we can produce and consume messages from the brokers. First, we will need to install the following system package:

```command
pip install confluent_kafka
```

### Obtain Client Certificate

In order to send data to the Kafka broker, you must obtain three certificate files (ca-cert, client1.crt, and client1.key) stored on the first Kafka server in your cluster, kafka1. 
These certificate files must also be located in the same working directory as the `produce.py` and `consume.py` scripts used to produce and consume testing data, respectively. 
These scripts are located in the `/scripts` directory of the **manual-kafka-cluster** folder that was cloned from the docs-cloud-projects repository.

In your local virtual environment, navigate to the scripts folder within manual-kafka-cluster:

`cd scripts`

Confirm the contents of the directory:

`ls`

You should see both the `produce.py` and `consume.py` scripts, along with the `getcerts.sh` script used to obtain the necessary certificate files from the kafka1 server:

```
consume.py  getcerts.sh produce.py
```

To obtain the certificate files, run the `getcerts.sh` script. Replace `IP_ADDRESS` with the IP address of your first Kafka node, kafka1.

`bash getcerts.sh IP_ADDRESS`

Output:
```
[info] fetching /etc/kafka/ssl/cert/client1.crt from 192.0.2.21..
[info] fetching /etc/kafka/ssl/key/client1.key from 192.0.2.21..
[info] fetching /etc/kafka/ssl/ca/ca-crt from 192.0.2.21..
```
Confirm successful download of the certificate files, ca-cert, client1.crt, and client1.key:

`ls`

```
ca-crt      client1.crt client1.key consume.py  getcerts.sh produce.py
```

### Produce Messages

Before we can send any data to the Kafka broker you will need to download both `produce.py` and `consume.py` scripts located in the `/script` directory of this repo.

- [produce.py](https://github.com/linode/docs-cloud-projects/blob/main/apps/manual-kafka-cluster/scripts/produce.py)
- [consume.py](https://github.com/linode/docs-cloud-projects/blob/main/apps/manual-kafka-cluster/scripts/consume.py)

Make sure that you update your local `/etc/hosts` file to point to the Kafka servers. For example:

```
192.0.2.21 kafka1
198.51.100.175 kafka2
203.0.113.24 kafka3
```

The `produce.py` script connects to one of the three Kafka broker nodes to send sample message data over port 9092. This is the default port Kafka brokers use to communicate with clients that produce and consume data.

While in the `scripts` directory, run the `produce.py` script to send message data to the broker node:

```
python3 produce.py
```

OUTPUT:
```
Message delivered to test [0] at offset 0
Message delivered to test [0] at offset 1
Message delivered to test [0] at offset 2
```
***NOTE:***

Make sure that `produce.py` and `consume.py` are in the same directory where the certicates are present. The script will look for the neccessary files granted that they are in the current working directory.

### Consume Messages

Similar to the produce.py script, the `consume.py` script is provided to test the consumption of message data. The `consume.py` script connects to one of the available Kafka nodes to consume the messages that were produced by the `produce.py` script.

While in the same working directory, `scripts`, run the `consume.py` script to receive the sample data:

```
python3 consume.py
```

OUTPUT:
```
Received event: {'event_id': 0, 'timestamp': 1727888292, 'message': 'Event number 0'}
Received event: {'event_id': 1, 'timestamp': 1727888292, 'message': 'Event number 1'}
Received event: {'event_id': 2, 'timestamp': 1727888292, 'message': 'Event number 2'}
```