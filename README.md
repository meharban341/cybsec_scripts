# cybsec_scripts
## Automated ELK Stack Deployment

The files in this repository were used to configure the network depicted below.

![TODO: Update the path with the name of your diagram](Images/diagram.png)

These files have been tested and used to generate a live ELK deployment on Azure. They can be used to either recreate the entire deployment pictured above. Alternatively, select portions of the roles file may be used to install only certain pieces of it, such as Filebeat.

  

This document contains the following details:
- Description of the Topology
- Access Policies
- ELK Configuration
  - Beats in Use
  - Machines Being Monitored
- How to Use the Ansible Build


### Description of the Topology

The main purpose of this network is to expose a load-balanced and monitored instance of DVWA, the D*mn Vulnerable Web Application.

Load balancing ensures that the application will be highly availability, in addition to restricting traffic to the network.


Integrating an ELK server allows users to easily monitor the vulnerable VMs for changes to the file and system metrics.


The configuration details of each machine may be found below.
_Note: Use the [Markdown Table Generator](http://www.tablesgenerator.com/markdown_tables) to add/remove values from the table_.

| Name     | Function | IP Address | Operating System |
|----------|----------|------------|------------------|
| Jump Box | Gateway  | 10.0.0.4   | Linux            |
| Web-1    | Webserver| 10.0.0.5   | Linux            |
| Web-2    | Webserver| 10.0.0.6   | Linux            |
| Web-3    | Webserver| 10.0.0.8   | Linux            |
| ELK      |Monitoring| 10.1.0.4   | Linux            |

### Access Policies

The machines on the internal network are not exposed to the public Internet. 

Only the jumpbox machine can accept connections from the Internet. Access to the machine is only allowed through the public IP's of whitelisted workstations
- 172.116.233.158

Machines within the network can only be accessed internally in the system by one another. Web 1,2 and 3 can send traffic to the elk server..


A summary of the access policies in place can be found in the table below.

| Name     | Publicly Accessible | Allowed IP Addresses |
|----------|---------------------|----------------------|
| Jump Box | Yes                 | 172.116.233.158      |
| ELK      | No                  | 10.0.0.1-254         |
| Web-1    | No                  | 10.0.0.1-254         |
| Web-2    | No                  | 10.0.0.1-254         |
| Web-3    | No                  | 10.0.0.1-254          |
### Elk Configuration

Ansible was used to automate configuration of the ELK machine. No configuration was performed manually, which is advantageous because
using automated configuration allows for a more accessible environment and allows developers and programmers of multiple skill levels to deploy configurations. It also frees up time which would be spent  configuring ELK and can now be devoted to other more important tasks.

The playbook implements the following tasks:
Install docker.io
Installs pip3 for python
Install the docker python module
Use sysctl module to increase memory usage
Downloads and launches a docker elk container.

The following screenshot displays the result of running `docker ps` after successfully configuring the ELK instance.

![TODO: Update the path with the name of your screenshot of docker ps output](Images/docker_ps_output.png)

### Target Machines & Beats
This ELK server is configured to monitor the following machines:
Web-1 [10.0.0.5]
Web-2 [10.0.0.6]
Web-3 [10.0.0.8]
We have installed the following Beats on these machines:
Filebeat
Metricbeat

These Beats allow us to collect the following information from each machine:
Filebeat records if there has been any changes to the filesystem and reports it back to the server, which allows the user to monitor suspcious activity through the kibana page. Metricbeat collects data on how the system metrics change such as if too much CPU or RAM is being usec. This allows user to monitor the kibana page and detect things such as high resource usage or if someone is attempting to ssh or escalate sudo priveleges. 

### Using the Playbook
In order to use the playbook, you will need to have an Ansible control node already configured. Assuming you have such a control node provisioned: 

SSH into the control node and follow the steps below:
- Copy the  file to /etc/ansible.
- update the hosts files to include the IP's of your elk server [10.1.0.4] and the webservers [10.0.05-6] [10.0.0.8] under their respective columns
- Run the playbook, and navigate to http://13.82.212.3:5601/app/kibana to check that the installation worked as expected.



_As a **Bonus**, provide the specific commands the user will need to run to download the playbook, update the files, etc._