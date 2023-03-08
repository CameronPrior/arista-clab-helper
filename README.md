# Arista ContainerLab Helper

## Disclaimer!
I'll start by saying that I am not a developer, nor do I resemble anything close to a developer.
The code you will find in this repository is most likely offensive to developers everywhere and for that I apologise.

# Exec Summary
This 'code' is designed to help you deploy, destroy and inspect topologies in ContainerLab.
Features include:
- Deploy 2 different Arista based topologies (with or without attached Hosts)
- Automatic provisioning into CloudVision (CVP) if required
- Destroy any running lab and perform either a full clean-up or leave the files intact for next time
- Inspect all running labs

# Requirements
In order for clab-helper to work, it requires the following:
 - [Docker](https://docker.com)
 - [ContainerLab](https://containerlab.dev/)
 - [Python 3.10.0+](https://www.python.org/)
 - [Python-pip](https://pypi.org/project/pip/)
 - A supported cEOS image (cEOS-4.28.0F and above)
 

Docker installation guides can be found [here](https://docs.docker.com/engine/install/)

ContainerLab installation guides can be found [here](https://containerlab.dev/install/)

Python installation guides can be found [here](https://wiki.python.org/moin/BeginnersGuide/Download)

Python-pip installation guide can be found [here](https://pip.pypa.io/en/stable/installation/)
**Note:** I reccommend using the `get-pip.py` script to install pip

cEOS images can be downloaded from the [Arista website.](https://www.arista.com/en/support/software-download)

# cEOS Install Instructions
Once a supported cEOS images has been downloaded use the `docker import {CEOS FILENAME} {IMAGE NAME}` command, e.g. `docker import cEOS-lab-4.29.0F.tar ceos:4.29.0F`.
This command imports the container image that you downloaded and saves it into the docker image repository using the *image_name* you have given it.
You need to follow the correct image naming standard of ceos:#.##.##(.#)

# clab_helper Install Instructions
Once everything has been installed, clone the repository using `git clone https://github.com/CameronPrior/arista-clab-helper.git` into a directory of your choosing.
After the repo has been cloned, navigate into the directory and run `sudo pip install -r requirements.txt` to install the python modules required. 

## Python Modules Used
I have utilised three external python modules in this script:
- [cvPrac](https://github.com/aristanetworks/cvprac) - Which is a RESTful API client for Cloudvision® Portal (CVP) which can be used for building applications that work with Arista CVP
- [requests](https://pypi.org/project/requests/) - The python HTTP library
- [docker](https://pypi.org/project/docker/) - A python library for the Docker Engine API

# clab_helper Usage
ContainerLab requires elevated privileges so you will need to run the script with sudo.
`sudo Python3 clab-helper.py` should get you started.

The script will ask you what type of lab you would like to deploy, then it will gather various information for said lab.
If you select to deploy a lab with Hosts attached, it will ask what image you would like to use for the hosts.
If this image does not exist, it will use docker to download the image.


# Topologies
The following topologies are included:

### Single Data Center with MLAG
![SDC-MLAG](https://user-images.githubusercontent.com/680877/222593712-17c56723-d3e8-4902-a2a1-673cda7629b0.png)

### Single Data Center with MLAG and Attached Hosts
![SDC-MLAG-HOSTS](https://user-images.githubusercontent.com/680877/222593900-6bdf43f1-1579-436a-b966-a2e9227a379e.png)

### Dual Data Center with MLAG
![DDC-MLAG](https://user-images.githubusercontent.com/680877/222652486-0c9a11cf-65d3-409b-b79d-709262638057.png)

### Dual Data Center with MLAG and Attached Hosts
![DDC-MLAG-HOSTS](https://user-images.githubusercontent.com/680877/222652533-d089356c-ed29-49d0-a8d8-740d444ade47.png)

**Please Note:** You will around 32Gb of RAM to run the Dual DC Topologies as each container uses around 1.6Gb


# CloudVision Setup
In order to use CVP with ContainerLab, the CVP host needs a static route configured back to the management range you have configured.
When configuring CVP, I used the same interface for both the Cluster Interface and the Device Interface.
After CVP is up and running, add a static route using the `ip route add {MANAGEMENT RANGE} via {DOCKER HOST IP} dev eth0` command.

### CloudVision Setup Diagram
![CVP Config](https://user-images.githubusercontent.com/680877/222660607-a5fa8d7a-d500-43aa-9400-3a24ed21c60d.png)

