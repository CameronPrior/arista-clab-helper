import getpass
import sys
import os
import subprocess
import time
import requests
import json
from datetime import datetime
from cvprac.cvp_client import CvpClient, CvpLoginError
import ssl
import ipaddress
from pathlib import Path
import requests.packages
import uuid
import docker

ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()


def docker_check():
    # Attempt to run the `docker --version` command and verify that docker is installed
    try:
        output = (
            subprocess.check_output(["docker", "--version"]).decode("utf-8").strip()
        )
        # If the command executes successfully, set `dockerInstalled` to `True` and return it
        dockerInstalled = True
        return dockerInstalled
    # If the command raises a `CalledProcessError`, set `dockerInstalled` to `False` and return it
    except (OSError, subprocess.CalledProcessError):
        dockerInstalled = False
        return dockerInstalled


def clab_check():
    # Attempt to run the `clab version | grep version` command and verify that ContainerLab is installed
    try:
        output = subprocess.check_output(["clab", "version", "|", "grep", "version"])
        # If the command executes successfully, set `clabInstalled` to `True` and return it
        clabInstalled = True
        return clabInstalled
    # If the command raises a `CalledProcessError`, set `clabInstalled` to `False` and return it
    except (OSError, subprocess.CalledProcessError):
        clabInstalled = False
        return clabInstalled


class Lab:
    def __init__(
        self,
        labName,
        noSpines,
        noLeafs,
        configDir,
        labDir,
        deploy_command,
        hostReq,
        labType,
    ):
        self.labName = labName
        self.noSpines = noSpines
        self.noLeafs = noLeafs
        self.configDir = configDir
        self.labDir = labDir
        self.deploy_command = deploy_command
        self.hostReq = hostReq
        self.labType = labType


class Info:
    def __init__(self):
        self.cvpRequired = False
        self.cvpProvision = False
        self.cvpIp = ""
        self.cvpIpList = []
        self.cvpServer = ""
        self.cvpUsername = ""
        self.cvpPassword = ""
        self.headers = ""
        self.swUsername = ""
        self.swPassword = ""
        self.spineIp = ""
        self.leafIp = ""
        self.gatewayIp = ""
        self.managementRange = ""
        self.infoCorrect = False
        self.strippedCEOSImage = ""
        self.strippedHostImage = ""
        self.deleteChoice = ""
        self.deletePath = ""
        self.selectedDelete = ""
        self.deleteFiles = False
        self.decommDevice = False
        self.cvpConnected = False


####################################
####    Deploy Lab Functions    ####
####################################


def deployment_type_menu():
    # Clear the console screen
    os.system("clear")

    # Create the inventory directory if it doesn't exist
    if not os.path.exists("./inventory"):
        os.makedirs("./inventory")

    # Define the list of labs with their configurations
    labs = [
        Lab(
            labName="Arista-SDC-LS-MLAG",
            noSpines=2,
            noLeafs=4,
            configDir="./configs/Arista-SDC-LS-MLAG/",
            labDir="./clab-Arista-SDC-LS-MLAG/",
            deploy_command="clab deploy -t ./inventory/Arista-SDC-LS-MLAG.yml",
            hostReq=False,
            labType="Single DC - Leaf Spine",
        ),
        Lab(
            labName="Arista-DDC-LS-MLAG",
            noSpines=4,
            noLeafs=12,
            configDir="./configs/Arista-DDC-LS-MLAG/",
            labDir="./clab-Arista-DDC-LS-MLAG/",
            deploy_command="clab deploy -t ./inventory/Arista-DDC-LS-MLAG.yml",
            hostReq=False,
            labType="Dual DC - Leaf Spine",
        ),
        Lab(
            labName="Arista-SDC-LS-MLAG-HOSTS",
            noSpines=2,
            noLeafs=4,
            configDir="./configs/Arista-SDC-LS-MLAG-HOSTS/",
            labDir="./clab-Arista-SDC-LS-MLAG-HOSTS/",
            deploy_command="clab deploy -t ./inventory/Arista-SDC-LS-MLAG-HOSTS.yml",
            hostReq=True,
            labType="Single DC - Leaf Spine with Hosts",
        ),
        Lab(
            labName="Arista-DDC-LS-MLAG-HOSTS",
            noSpines=4,
            noLeafs=12,
            configDir="./configs/Arista-DDC-LS-MLAG-HOSTS/",
            labDir="./clab-Arista-DDC-LS-MLAG-HOSTS/",
            deploy_command="clab deploy -t ./inventory/Arista-DDC-LS-MLAG-HOSTS.yml",
            hostReq=True,
            labType="Dual DC - Leaf Spine with Hosts",
        ),
    ]
    # Define an Info object to hold information about the lab
    info = Info()

    # Display the list of labs and ask the user to choose one
    print("What type of lab are you deploying?")
    for i, lab in enumerate(labs):
        print(f"{i+1}. {lab.labType}")

    choice = input("Enter your choice: ")

    try:
        # Convert the user's choice to an integer and select the corresponding lab
        choice = int(choice)
        lab = labs[choice - 1]

        # Create the configuration directory if it doesn't exist
        if not os.path.exists(lab.configDir):
            os.makedirs(lab.configDir)

    except (ValueError, IndexError):
        # If the user enters an invalid choice, display an error message and ask them to choose again
        print("Invalid choice. Try again.")
        deployment_type_menu()

    # Deploy the selected lab
    deploy_lab(lab, info)


def cvp_required(info):
    # clear the console screen
    os.system("clear")

    print("----------------------------------------")
    print("CVP Requirements")
    print("----------------------------------------")
    print(" ")

    # prompt user for input
    choice = user_selection("Is Cloudvision Required? (yes/no): ")

    # set the cvpRequired attribute of the Info object based on user input
    info.cvpRequired = choice


def cvp_provision_required(info):
    # prompt user for input
    choice = user_selection(
        "Would you like to automatically provision devices into Cloudvision? (yes/no): "
    )

    # set the cvpProvision attribute of the Info object based on user input
    info.cvpProvision = choice


def get_cvp_info(info):
    # clear the console screen
    os.system("clear")

    print("----------------------------------------")
    print("CVP Host Information")
    print("----------------------------------------")
    print(" ")

    # prompt user for CVP IP address
    info.cvpIp = input("CVP IP Address: ")

    # validate the IP address entered by the user
    validIp = validate_ip_address(info.cvpIp)

    # if the IP address is invalid, print an error message and prompt the user again
    if not validIp:
        os.system("clear")
        print("----------------------------------------")
        print("Configuration Error")
        print("----------------------------------------")
        print("")
        print("The IP address entered is not valid.")
        input("Press any key to try again...")
        get_cvp_info(info)

    # store the CVP IP address in a list as cvPrac requires the host IP in list format
    info.cvpIpList = [info.cvpIp]

    # Build the URL for cvPrac to use when making API calls
    info.cvpServer = "https://" + info.cvpIp + "/cvpservice"

    # prompt user for CVP username and password
    info.cvpUsername = input("CVP Username: ")
    info.cvpPassword = getpass.getpass("CVP Password: ")

    # set headers for HTTP requests to CVP API
    info.headers = {"accept": "application/json", "Content-Type": "application/json"}

    # check connectivity to the CVP instance using the provided credentials
    cvp_connect_check(info)

    # if connectivity to the CVP instance fails, print an error message and prompt the user again
    if info.cvpConnected == False:
        os.system("clear")
        print("----------------------------------------")
        print("CVP Connection Error")
        print("----------------------------------------")
        print(" ")
        print("Could not connect to CVP Instance. Potential reasons for this are:")
        print(f" - Host IP is incorrect. IP Entered: {info.cvpIp}")
        print(f" - CVP Username is incorrect. Username Entered: {info.cvpUsername}")
        print(" - CVP Password is incorrect")
        print(" - CVP Server us unreachable")
        input("Press any key to try again...")
        get_cvp_info(info)


def get_switch_info(info):
    # if CVP is not required, obtain switch credential information for use
    os.system("clear")
    print("----------------------------------------")
    print("Switch Credential Information")
    print("----------------------------------------")
    print(" ")
    info.swUsername = input("Set Switch Username: ")
    info.swPassword = getpass.getpass("Set Switch Password: ")


def get_IP_info(info):
    # Clear the terminal screen
    os.system("clear")
    print("----------------------------------------")
    print("Management IP Information")
    print("----------------------------------------")
    # Print a note to the user about subnet mask assumptions
    print(
        "Note: The generated configuration files assume a /24 management network, if a different subnet mask is required changes will need to be made to the ./base_config/leaf.cfg and spine.cfg files"
    )
    print("")
    # Prompt the user for the management IP range and validate it
    info.managementRange = input(
        "Management IP Range without CIDR notation (i.e 192.168.0.0): "
    )
    validIp = validate_ip_address(info.managementRange)
    # If the IP is invalid, notify the user and ask for input again
    if not validIp:
        os.system("clear")
        print("----------------------------------------")
        print("Configuration Error")
        print("----------------------------------------")
        print("")
        print("The IP address range entered is not valid")
        input("Press any key try again...")
        get_IP_info(info)

    # Get the first management IP for spines, adding a default option
    splitOctets = ".".join(info.managementRange.split(".")[:3])
    info.spineIp = (
        input(
            f"First management IP for Spines [Press enter for default ({splitOctets}.101)]: "
        )
        or splitOctets + ".101"
    )

    # Get the first management IP for leafs, adding a default option
    info.leafIp = (
        input(
            f"First management IP for Leafs [Press enter for default ({splitOctets}.111)]: "
        )
        or splitOctets + ".111"
    )

    # Get the gateway IP address for the management network, adding a default option assuming .1 is the default gateway
    info.gatewayIp = (
        input(
            f"Gateway IP Address for Management Range [Press enter for default ({splitOctets}.1)]: "
        )
        or splitOctets + ".1"
    )

    # Confirm the IP information with the user
    confirm_ip_info(info)


def confirm_ip_info(info):
    # Clear the terminal screen
    os.system("clear")

    # Print the IP address information for the user to confirm
    print("----------------------------------------")
    print("Confirm IP Address Information")
    print("----------------------------------------")
    print("")
    print("Management IP Range: " + info.managementRange)
    print("First Spine IP Address: " + info.spineIp)
    print("First Leaf IP Address: " + info.leafIp)
    print("Management Network Gateway: " + info.gatewayIp)
    print("")

    # Get user input to confirm the information is correct
    choice = user_selection("Is this IP information correct? (yes/no): ")

    # Set a flag in the info object to indicate whether the information is correct
    info.infoCorrect = choice


def select_ceos_image(info):
    # Clear the terminal screen
    os.system("clear")

    # Connect to the Docker API
    dockerClient = docker.from_env()

    # Get a list of all Docker images
    dockerImages = dockerClient.images.list()

    # Create an empty list to hold image dictionaries
    imageDicts = []

    # Loop through all Docker images and add any with a tag starting with "ceos" to the list
    for image in dockerImages:
        for tag in image.tags:
            if tag.startswith("ceos"):
                imageDict = {"tags": [tag]}
                imageDicts.append(imageDict)
                break

    # Convert the list of image dictionaries to a JSON string and then back to a list of dictionaries
    jsonStr = json.dumps(imageDicts)
    jsonData = json.loads(jsonStr)

    # Display a list of available CEOS images to the user
    print("----------------------------------------")
    print("CEOS Image Selection")
    print("----------------------------------------")
    print("")
    for i, item in enumerate(jsonData):
        imageTags = item["tags"]
        print(f"{i + 1}. {', '.join(imageTags)}")

    # Prompt the user to select an imag
    print("")
    choice = input("Select an Image for use: ")

    # Validate the user's input
    while not choice.isdigit() or int(choice) < 1 or int(choice) > len(jsonData):
        choice = input(
            "Invalid choice. Please enter the number of the image you want to use: "
        )

    # Get the selected image and its tags
    selectedImage = jsonData[int(choice) - 1]
    imageTags = selectedImage["tags"]

    # Strip square brackets and whitespace from the image tags and store the result in the info object
    info.strippedCEOSImage = ", ".join([tag.strip("[").strip("]") for tag in imageTags])


def select_host_image(info):
    # Clear the terminal screen
    os.system("clear")

    # Connect to the Docker API
    dockerClient = docker.from_env()

    # Define a list of available images and display them to the user
    availableImages = ["ubuntu", "centos", "alpine"]
    print("----------------------------------------")
    print("Host Image Selection")
    print("----------------------------------------")
    print("Note: The selected image will be downloaded if it does not already exist")
    print("")
    print("Available images: ")
    for index, image in enumerate(availableImages):
        print(f"{index + 1}. {image}")

    # Prompt the user to select an image
    imageIndex = int(input("Select an Image for use: "))

    # Get the selected image and check if it exists locally
    selectedImage = availableImages[imageIndex - 1]
    try:
        dockerClient.images.get(selectedImage)
    except docker.errors.ImageNotFound:
        # If the image doesn't exist locally, download it from the Docker Hub registry
        os.system("clear")
        print("----------------------------------------")
        print("Downloading Host Image")
        print("----------------------------------------")
        print(f"{selectedImage} doesn't exist, downloading...")
        dockerClient.images.pull(selectedImage)

    # Strip whitespace from the image name and append ":latest" to it, then store the result in the info object
    info.strippedHostImage = selectedImage + ":latest"


def update_mgmt_ip(lab, info):
    # get the path of the template and output files
    template_file = Path("./base_config") / (lab.labName + ".yml")
    output_file = Path("./inventory") / (lab.labName + ".yml")

    # define the IPs dictionary based on the lab name
    if lab.labName == "Arista-SDC-LS-MLAG":
        ips = {
            "MGMTRANGE": info.managementRange,
            "SPINE1IP": info.spineIp,
            "SPINE2IP": increment_ip(info.spineIp, 1),
            "LEAF1IP": info.leafIp,
            "LEAF2IP": increment_ip(info.leafIp, 1),
            "LEAF3IP": increment_ip(info.leafIp, 2),
            "LEAF4IP": increment_ip(info.leafIp, 3),
            "CEOSIMAGE": info.strippedCEOSImage,
        }
    elif lab.labName == "Arista-DDC-LS-MLAG":
        ips = {
            "MGMTRANGE": info.managementRange,
            "SPINE1IP": info.spineIp,
            "SPINE2IP": increment_ip(info.spineIp, 1),
            "SPINE3IP": increment_ip(info.spineIp, 2),
            "SPINE4IP": increment_ip(info.spineIp, 3),
            "LEAF1IP": info.leafIp,
            "LEAF2IP": increment_ip(info.leafIp, 1),
            "LEAF3IP": increment_ip(info.leafIp, 2),
            "LEAF4IP": increment_ip(info.leafIp, 3),
            "LEAF5IP": increment_ip(info.leafIp, 4),
            "LEAF6IP": increment_ip(info.leafIp, 5),
            "LEAF7IP": increment_ip(info.leafIp, 6),
            "LEAF8IP": increment_ip(info.leafIp, 7),
            "LEAF9IP": increment_ip(info.leafIp, 8),
            "LEAF10IP": increment_ip(info.leafIp, 9),
            "LEAF11IP": increment_ip(info.leafIp, 10),
            "LEAF12IP": increment_ip(info.leafIp, 12),
            "CEOSIMAGE": info.strippedCEOSImage,
        }
    elif lab.labName == "Arista-SDC-LS-MLAG-HOSTS":
        ips = {
            "MGMTRANGE": info.managementRange,
            "SPINE1IP": info.spineIp,
            "SPINE2IP": increment_ip(info.spineIp, 1),
            "LEAF1IP": info.leafIp,
            "LEAF2IP": increment_ip(info.leafIp, 1),
            "LEAF3IP": increment_ip(info.leafIp, 2),
            "LEAF4IP": increment_ip(info.leafIp, 3),
            "CEOSIMAGE": info.strippedCEOSImage,
            "HOSTIMAGE": info.strippedHostImage,
        }
    elif lab.labName == "Arista-DDC-LS-MLAG-HOSTS":
        ips = {
            "MGMTRANGE": info.managementRange,
            "SPINE1IP": info.spineIp,
            "SPINE2IP": increment_ip(info.spineIp, 1),
            "SPINE3IP": increment_ip(info.spineIp, 2),
            "SPINE4IP": increment_ip(info.spineIp, 3),
            "LEAF1IP": info.leafIp,
            "LEAF2IP": increment_ip(info.leafIp, 1),
            "LEAF3IP": increment_ip(info.leafIp, 2),
            "LEAF4IP": increment_ip(info.leafIp, 3),
            "LEAF5IP": increment_ip(info.leafIp, 4),
            "LEAF6IP": increment_ip(info.leafIp, 5),
            "LEAF7IP": increment_ip(info.leafIp, 6),
            "LEAF8IP": increment_ip(info.leafIp, 7),
            "LEAF9IP": increment_ip(info.leafIp, 8),
            "LEAF10IP": increment_ip(info.leafIp, 9),
            "LEAF11IP": increment_ip(info.leafIp, 10),
            "LEAF12IP": increment_ip(info.leafIp, 12),
            "CEOSIMAGE": info.strippedCEOSImage,
            "HOSTIMAGE": info.strippedHostImage,
        }

    # Open the template file in read mode and read its contents
    with open(template_file, "r") as f:
        content = f.read()

    # Replace each placeholder in the template file with the corresponding variable value
    for placeholder, ip in ips.items():
        content = content.replace("{" + placeholder + "}", ip)

    # Open the output file in write mode and write the modified template contents to it
    with open(output_file, "w") as f:
        f.write(content)


def generate_spine_config(lab, info):
    # Initialize the starting number for the spines
    startNumber = 1

    # Loop through the spines
    for i in range(1, lab.noSpines + 1):
        # Convert the starting spine number to a string
        startSpines = str(startNumber)

        # If this is not the first spine, increment the last octet of the spine IP address
        if startNumber > 1:
            octets = info.spineIp.split(".")
            last_octet = int(octets[-1]) + 1
            octets[-1] = str(last_octet)
            info.spineIp = ".".join(octets)

        # Set the filename for the spine configuration template and the output file
        template_filename = "./base_config/spine.cfg"
        output_file = lab.configDir + "ceos-spine-" + str(startSpines) + ".cfg"

        # Open the spine configuration template file and read its contents
        with open(template_filename, "r") as file:
            content = file.read()

        # If CVP integration is required, replace the appropriate placeholders in the template with the CVP information
        if info.cvpRequired == True:
            content = content.replace("{USERNAME}", info.cvpUsername)
            content = content.replace("{PASSWORD}", info.cvpPassword)
            content = content.replace("{CVPIP}", info.cvpIp)

        # If CVP integration is not required, replace the appropriate placeholders in the template with the switch information
        if info.cvpRequired == False:
            content = content.replace("{USERNAME}", info.swUsername)
            content = content.replace("{PASSWORD}", info.swPassword)
            content = content.replace("-cvaddr={CVPIP}:9910", "")

        # Replace the remaining placeholders in the template with the appropriate information
        content = content.replace("{NUMBER}", startSpines)
        content = content.replace("{SPINEIP}", info.spineIp)
        content = content.replace("{GATEWAYIP}", info.gatewayIp)

        # Write the modified spine configuration to the output file
        with open(output_file, "w") as file:
            file.write(content)

        # Increment the starting number for the spines
        startNumber += 1


def generate_leaf_config(lab, info):
    # Initialize the starting number for the leafs
    startNumber = 1

    # Loop through the spines
    for i in range(1, lab.noLeafs + 1):
        # Convert the starting leaf number to a string
        startLeafs = str(startNumber)

        # If this is not the first leaf, increment the last octet of the leaf IP address
        if startNumber > 1:
            octets = info.leafIp.split(".")
            last_octet = int(octets[-1]) + 1
            octets[-1] = str(last_octet)
            info.leafIp = ".".join(octets)

        # Set the filename for the leaf configuration template and the output file
        template_filename = "./base_config/leaf.cfg"
        output_file = lab.configDir + "ceos-leaf-" + str(startLeafs) + ".cfg"

        # Open the leaf configuration template file and read its contents
        with open(template_filename, "r") as file:
            content = file.read()

        # If CVP integration is required, replace the appropriate placeholders in the template with the CVP information
        if info.cvpRequired == True:
            content = content.replace("{USERNAME}", info.cvpUsername)
            content = content.replace("{PASSWORD}", info.cvpPassword)
            content = content.replace("{CVPIP}", info.cvpIp)

        # If CVP integration is not required, replace the appropriate placeholders in the template with the switch information
        if info.cvpRequired == False:
            content = content.replace("{USERNAME}", info.swUsername)
            content = content.replace("{PASSWORD}", info.swPassword)
            content = content.replace("-cvaddr={CVPIP}:9910", "")

        # Replace the remaining placeholders in the template with the appropriate information
        content = content.replace("{NUMBER}", startLeafs)
        content = content.replace("{LEAFIP}", info.leafIp)
        content = content.replace("{GATEWAYIP}", info.gatewayIp)

        # Write the modified leaf configuration to the output file
        with open(output_file, "w") as file:
            file.write(content)

        # Increment the starting number for the leafs
        startNumber += 1


def deploy_lab(lab, info):
    # Check if CVP is required
    cvp_required(info)

    # Get CVP information if required
    if info.cvpRequired == True:
        cvp_provision_required(info)
        get_cvp_info(info)

    # Get switch authentication information if CVP is not required
    elif info.cvpRequired == False:
        get_switch_info(info)

    # Get Management IP range information
    get_IP_info(info)

    # Get ceos image for use
    select_ceos_image(info)

    # Get host image if user has selected lab with hosts attached
    if lab.hostReq == True:
        select_host_image(info)

    # Update the tags for replacement in the configuration templates
    update_mgmt_ip(lab, info)

    # Generate spine configuration files
    generate_spine_config(lab, info)

    # Generate leaf configuration files
    generate_leaf_config(lab, info)

    # Clear the screen and show deployment progress
    os.system("clear")
    print("----------------------------------------")
    print("Deployment Status")
    print("----------------------------------------")
    print("")
    print("Generating Switch Configurations")
    time.sleep(10)
    print("Done.")
    print("")
    print("Deploying selected ContainerLab topology")

    # run the deployment command
    subResult = subprocess_run(lab.deploy_command)
    print("Done.")
    os.system("clear")

    # If CVP is required, clear the screen and show progress for CVP provisioning
    if info.cvpProvision == True:
        print("----------------------------------------")
        print("Deployment Status")
        print("----------------------------------------")
        print("")
        print("Creating Lab Container for Devices")
        time.sleep(3)
        print("Done.")
        print("")
        print("Provisioning Devices into CVP")
        cvp_create_container(lab, info)
        print("Done.")
        print("")
        print("Moving Devices into Lab Container")
        cvp_execute_tasks(info)
        print("Done")
        os.system("clear")
        print("----------------------------------------")
        print("Deployment Information")
        print("----------------------------------------")
        print("")

        # Show deployment success message and wait for user input
        print(subResult.stdout.decode())
        print("Lab has been deployed and is ready for use")
        input("Press any key to return to the Main Menu")
        main()
    else:
        print("----------------------------------------")
        print("Deployment Information")
        print("----------------------------------------")
        print("")
        # Show deployment success message and wait for user input
        print(subResult.stdout.decode())
        print("Lab has been deployed and is ready for use")
        input("Press any key to return to the Main Menu")
        main()


#############################
####    CVP Functions    ####
#############################


def cvp_connect_check(info):
    # Create a CvpClient object
    cvpClient = CvpClient()

    try:
        # Try to connect to CVP using the provided credentials
        cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)
        # Set the info object's cvpConnected attribute to True if connection is successful
        info.cvpConnected = True
    except CvpLoginError as e:
        # If there's a login error, set the info object's cvpConnected attribute to False
        info.cvpConnected = False


def cvp_create_container(lab, info):
    # Create CvpClient object and connect to CVP
    cvpClient = CvpClient()
    cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword, 120, 120)

    # Get reference to 'Tenant' container in CVP
    newContainer = cvpClient.api.get_container_by_name("Tenant")

    # Set the name of the new container to be created
    containerName = lab.labName

    try:
        # Attempt to create new container in CVP
        print(f"Creating Container {containerName}\n")
        cvpClient.api.add_container(
            containerName, newContainer["name"], newContainer["key"]
        )
    except Exception as e:
        # If container already exists, continue execution
        if "jsonData already exists in jsonDatabase" in str(e):
            print("Container already exists, continuing...")

    # Get reference to 'Undefined' container in CVP
    parentContainer = cvpClient.api.get_container_by_name("Undefined")

    # Read management IP list from file
    mgmtIpListFile = lab.labDir + "topology-data.json"
    ipList = []
    with open(mgmtIpListFile) as f:
        jsonData = json.load(f)
    for name, node in jsonData["nodes"].items():
        ipList.append(node["mgmt-ipv4-address"])

    # Create list of dictionaries containing device IP, and parent container information
    cvpList = []
    for devIp in ipList:
        cvpDict = {
            "device_ip": devIp,
            "parent_name": parentContainer["name"],
            "parent_key": parentContainer["key"],
        }
        cvpList.append(cvpDict)

    # Add devices to CVP inventory
    cvpClient.api.add_devices_to_inventory(cvpList)

    # Get list of devices in 'Undefined' container
    deviceList = []
    deviceNames = cvpClient.api.get_devices_in_container("Undefined")

    # Move devices to new container
    for v in deviceNames:
        cvpDict = {"deviceName": v["fqdn"]}
        deviceList.append(cvpDict)
    for device in deviceList:
        device = cvpClient.api.get_device_by_name(device["deviceName"])
        container = cvpClient.api.get_container_by_name(containerName)
        move = cvpClient.api.move_device_to_container("python", device, container)


def cvp_execute_tasks(info):
    # Create a CvpClient object
    cvpClient = CvpClient()

    # Connect to CVP using the provided IP address, username and password
    cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)

    # Retrieve all tasks that are in "Pending" status
    tasks = cvpClient.api.get_tasks_by_status("Pending")

    # Execute each task using its workOrderId
    for task in tasks:
        taskId = task["workOrderId"]
        result = cvpClient.api.execute_task(taskId)


def cvp_decomm(info):
    # Create a new CvpClient object
    cvpClient = CvpClient()

    # Connect to CVP using the provided IP address, username and password
    cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)

    # Get the list of devices in the selected container
    deviceList = cvpClient.api.get_inventory()
    cvpClient.api.get_devices_in_container(info.selectedDelete)

    # Loop through each device in the list
    for v in deviceList:
        # Get the serial number of the device
        cvpDevice = v["serialNumber"]
        # Generate a unique request ID for the decommissioning request
        cvpRequest = str(uuid.uuid4())
        # Send a device decommissioning request to CVP for the current device
        cvpClient.api.device_decommissioning(cvpDevice, cvpRequest)


def cvp_delete_container(info):
    # Create a CvpClient object
    cvp_client = CvpClient()

    # Connect to CVP using the provided IP address, username and password
    cvp_client.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)

    # Get the devices in the container to be deleted and store their names in a list
    devices = []
    for device in cvp_client.api.get_devices_in_container(info.selectedDelete):
        devices.append({"deviceName": device["fqdn"]})

    # Wait for devices to be decommissioned before deleting the container
    while True:
        # Check if all devices have been decommissioned by getting their names again
        devices = []
        for device in cvp_client.api.get_devices_in_container(info.selectedDelete):
            devices.append({"deviceName": device["fqdn"]})
        if not devices:
            break
        time.sleep(20)

    # Get the container to be deleted and its name and key
    container = cvp_client.api.get_container_by_name(info.selectedDelete)

    # Delete the container
    cvp_client.api.delete_container(
        container["name"], container["key"], "Tenant", "root"
    )


####################################
####    Delete Lab Functions    ####
####################################


def destroy_lab(info):
    # Clear the screen and build menu
    os.system("clear")
    print("----------------------------------------")
    print("Lab Deletion Information")
    print("----------------------------------------")
    print("")
    # Obtain Lab information for Deletion
    destroy_lab_info(info)

    # Check if user would like to delete all lab files
    delete_lab_files(info)

    # Check if user would like to decommission devices from CVP
    decommission_required(info)

    # If decommission is required, get CVP host information
    if info.decommDevice == True:
        get_cvp_info(info)
        os.system("clear")
        # Decommission devices from CVP
        cvp_decomm(info)
        # Delete empty container in CVP
        cvp_delete_container(info)

    # Remove remaining Lab files
    destroy_lab_commands(info)


def destroy_lab_info(info):
    # Get running labs and store information in lab_info file
    inspect_command = "clab inspect --all --format json | jq -r '.containers | unique_by(.labPath)' > lab_info"
    subResult = subprocess_run(inspect_command)

    # Check if the file has any content. If not, inform the user that no labs are runing and return to the main menu.
    labInfoFile = "lab_info"
    if os.path.getsize(labInfoFile) == 0:
        print("There are no labs running at this time")
        input("Press any key to return to the main menu...")
        main()
    else:
        # Read the lab information from the file and display it to the user
        print("The following labs are running")
        with open(labInfoFile) as f:
            labjsonData = json.load(f)
        for index, v in enumerate(labjsonData):
            print(f"{index + 1}. {v['lab_name']}")

        # Prompt the user to select a lab to destroy and validate the input
        while True:
            try:
                print("")
                labChoice = int(input("Select the Lab you wish to Destroy: "))
                if labChoice < 1 or labChoice > len(labjsonData):
                    print(
                        "Invalid choice. Please enter a number between 1 and",
                        len(labjsonData),
                    )

                else:
                    break
            except ValueError:
                print("Invalid input. Please enter a number.")

    # Set the selected lab's information to the "info" object
    info.deleteChoice = labjsonData[labChoice - 1]["labPath"]
    info.selectedDelete = labjsonData[labChoice - 1]["lab_name"]
    info.deletePath = "./configs/" + info.selectedDelete


def delete_lab_files(info):
    # Clear the screen and display a header
    os.system("clear")
    print("----------------------------------------")
    print("Lab Deletion Options")
    print("----------------------------------------")
    print("")

    # Prompt the user to confirm if they want to delete all lab files for the selected topology
    choice = user_selection(
        "Would you like to delete all lab files for the selected topology? (yes/no): "
    )

    # Set the "info" object's "deleteFiles" attribute to the user's choice
    info.deleteFiles = choice


def decommission_required(info):
    # Prompt the user to confirm if they want to decommission devices from CVP
    choice = user_selection(
        "Would you like to decommission devices in Cloudvision? (yes/no): "
    )
    # Set the "info" object's "decommDevice" attribute to the user's choice
    info.decommDevice = choice


def destroy_lab_commands(info):
    # Set the destroy command to include the "cleanup" flag if the user has selected to delete
    os.system("clear")
    print("----------------------------------------")
    print("Lab Deletion Status")
    print("----------------------------------------")
    print("")
    if info.deleteFiles == True:
        print(f"Destroying {info.deleteChoice} and cleaning up related files")
        destroy_command = f"sudo clab destroy -t {info.deleteChoice} --cleanup"
        # Remove all lab configuration files
        for confFile in os.scandir(info.deletePath):
            if confFile.is_file():
                os.remove(confFile)
        time.sleep(3)
        print("Done.")
        print("")
    elif info.deleteFiles == False:
        print(f"Destroying {info.deleteChoice}")
        destroy_command = f"sudo clab destroy -t {info.deleteChoice}"
        time.sleep(3)
        print("Done.")
        print("")

    # Run the destroy command and remove the lab_info file
    subResult = subprocess_run(destroy_command)

    # Remove the inventory files for the destroyed lab
    print(f"Deleting inventory files")
    os.remove("lab_info")
    os.remove("./inventory/" + info.selectedDelete + ".yml")
    os.remove("./inventory/." + info.selectedDelete + ".yml.bak")
    time.sleep(2)
    print("Done")

    # Clear the screen and display a message to the user
    os.system("clear")
    if info.deleteFiles == True:
        os.system("clear")
        print("----------------------------------------")
        print("Lab Deleted")
        print("----------------------------------------")
        print("")
        print(f"Lab {info.selectedDelete} and all associated files have been deleted")
        input("Press any key to return to main menu...")
        main()
    else:
        os.system("clear")
        print("----------------------------------------")
        print("Lab Deleted")
        print("----------------------------------------")
        print("")
        print(
            f"Lab {info.selectedDelete} has been destroyed however all lab and configuration files can be found in the clab-{info.selectedDelete} folder"
        )
        input("Press any key to return to main menu...")
        main()


#####################################
####    Inspect Lab Functions    ####
#####################################


def check_status():
    os.system("clear")
    print("----------------------------------------")
    print("Running Lab Information")
    print("----------------------------------------")
    print("")
    # Run the "clab inspect" command to get information about all running labs
    inspect_command = "clab inspect --all"
    subResult = subprocess_run(inspect_command)
    statusOutput = subResult.stdout.decode()
    # Check if any labs are currently running
    if not statusOutput:
        print("There are no Labs running right now")
    else:
        # Display information about the running labs
        print(statusOutput)
    # Prompt the user to return to the main menu
    input("Press any key to return to main menu...")
    main()


#########################################
####    Terminate Script Function    ####
#########################################


def terminate_script():
    sys.exit()


################################
####    Shared Functions    ####
################################


# Function to obtain a Yes or No response from the user
def user_selection(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response == "y" or response == "yes":
            return True
        elif response == "n" or response == "no":
            return False
        else:
            print('Invalid response. Please enter "yes" or "no".')


# Function to validate IP address using the ipaddress module
def validate_ip_address(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


# Function to increment the 4th octect in management IP range for Spine/Leaf configurations
def increment_ip(ip, increment):
    octets = ip.split(".")
    octets[3] = str(int(octets[3]) + increment)
    return ".".join(octets)


# Function to run commands on the underlying os
def subprocess_run(command):
    subResult = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return subResult


def main_menu():
    print("----------------------------------------")
    print("ContainerLab Helper")
    print("----------------------------------------")
    print("")
    print("1. Deploy Lab")
    print("2. Destroy Lab")
    print("3. Check Running Lab Status")
    print("4. Quit")


def main():
    os.system("clear")
    if os.getuid() == 0:
        info = Info()
        dockerInstalled = docker_check()
        if dockerInstalled == False:
            print(
                "Docker is not currently installed, please install Docker first before running this script"
            )
            terminate_script()
        clabInstalled = clab_check()
        if clabInstalled == False:
            print(
                "ContainerLab is not currently installed, please install ContainerLab first before running this script"
            )
            terminate_script()
        main_menu()
        choice = input("Enter your choice: ")
        if choice == "1":
            deployment_type_menu()
        elif choice == "2":
            destroy_lab(info)
        elif choice == "3":
            check_status()
        elif choice == "4":
            terminate_script()
        else:
            print("Invalid choice. Try again.")
            main()
    else:
        print(
            "Container lab needs superuser privileges to run, Please restart with either 'sudo' or as root"
        )


if __name__ == "__main__":
    main()
