# Arista ContainerLab Helper

## Disclaimer!
I'll start by saying that I am not a developer, nor do I resemble anything close to a developer.
The code you will find in this repository is most likely offensive to developers everywhere and for that I apologise.

# Exec Summary
This 'code' is designed to help you deploy, destroy and inspect topologies in ContainerLab.
Features include:
- Deploy 2 different Arista based topologies
- Automatic provisioning into CloudVision if required
- Destroy any running lab and perform either a full clean-up or leave the files intact for next time
- Inspect all running labs
- Generating 

# Requirements
Obviously ContainerLab is required in order for this to work, if you haven't already done this you should head over to the ContainerLab site and follow [this](https://containerlab.dev/install/) guide.

You will also need a cEOS image which can be downloaded from the [Arista website.](https://www.arista.com/en/support/software-download)
Once downloaded you will need to import that image into ContainerLab, to do this you need to use the `docker import *ceos_filename* *image_name*` command, e.g. `docker import cEOS-lab-4.29.0F.tar ceos:4.29.0F`.
This command imports the container image that you downloaded and saves it into the docker image repository using the *image_name* you have given it.
You need to follow the correct image naming standard of ceos:#.##.##.

**Please Note:** Its best to avoid CEOS images prior to *CEOS-4.28.0F* as they might not boot depending on the runtime environment. More info on this limitation can be found [here](https://containerlab.dev/manual/kinds/ceos/#known-issues-or-limitations)

Next up would be a functioning version of Python (This was written in version 3.10.6 but I'm fairly certain it will run on most version 3+). 
You should also be installing [python-pip](https://pypi.org/project/pip/) as you will be using that to install the external modules required.

I have utilised three external python modules in this script:
- [cvPrac](https://github.com/aristanetworks/cvprac) - Which is a RESTful API client for Cloudvision® Portal (CVP) which can be used for building applications that work with Arista CVP
- [requests](https://pypi.org/project/requests/) - The python HTTP library
- [docker](https://pypi.org/project/docker/) - A python library for the Docker Engine API


Once you have installed ContainerLab, Python and Python-pip. You can go ahead and either clone the repository or download the zip and extract it into a folder of your choosing.
I've created a clab-helper folder within the containerlab directory which is found in your user directory.

You will then want to run `sudo pip install -r requirements.txt` which will install the three external modules listed above.

# Usage
ContainerLab requires elevated privileges so you will need to run the script with sudo.
`sudo Python3 clab-helper.py` should get you started.

Assuming everything has gone well you will be presented with a menu giving you the option to Deploy, Destroy, Inspect or Quit.
From here everything is pretty self explanatory.


# Topologies


