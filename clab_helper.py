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
    try:
        output = (
            subprocess.check_output(["docker", "--version"]).decode("utf-8").strip()
        )
        dockerInstalled = True
        return dockerInstalled
    except subprocess.CalledProcessError:
        dockerInstalled = False
        return dockerInstalled


def clab_check():
    try:
        output = subprocess.check_output(["clab", "version", "|", "grep", "version"])
        clabInstalled = True
        return clabInstalled
    except subprocess.CalledProcessError:
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


### DEPLOY LAB FUNCTIONS ###


def deployment_type_menu():
    os.system("clear")
    if not os.path.exists("./inventory"):
        os.makedirs("./inventory")

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

    info = Info()

    print("What type of lab are you deploying?")
    for i, lab in enumerate(labs):
        print(f"{i+1}. {lab.labType}")

    choice = input("Enter your choice: ")
    try:
        choice = int(choice)
        lab = labs[choice - 1]

        if not os.path.exists(lab.configDir):
            os.makedirs(lab.configDir)

    except (ValueError, IndexError):
        print("Invalid choice. Try again.")
        deployment_type_menu()
    deploy_lab(lab, info)


def cvp_required(info):
    os.system("clear")
    choice = prompt_yes_no("Is Cloudvision Required? (yes/no): ")
    info.cvpRequired = choice


def cvp_provision_required(info):
    os.system("clear")
    choice = prompt_yes_no(
        "Would you like to automatically provision devices into Cloudvision? (yes/no): "
    )
    info.cvpProvision = choice


def get_cvp_info(info):
    os.system("clear")
    info.cvpIp = input("CVP IP Address: ")
    validIp = validate_ip_address(info.cvpIp)
    if not validIp:
        os.system("clear")
        print("Invalid IP Address")
        input("Press any key to try again...")
        get_cvp_info(info)
    info.cvpIpList = [info.cvpIp]
    info.cvpServer = "https://" + info.cvpIp + "/cvpservice"
    info.cvpUsername = input("CVP Username: ")
    info.cvpPassword = getpass.getpass("CVP Password: ")
    info.headers = {"accept": "application/json", "Content-Type": "application/json"}
    cvp_connect_check(info)
    if info.cvpConnected == False:
        os.system("clear")
        print("Could not connected to CVP Instance")
        input("Press any key to try again...")
        get_cvp_info(info)


def get_switch_info(info):
    os.system("clear")
    info.swUsername = input("Set Switch Username: ")
    info.swPassword = getpass.getpass("Set Switch Password: ")


def get_IP_info(info):
    os.system("clear")
    print(
        "Note: The generated configuration files assume a /24 management network, if a different subnet mask is required changes can be made to the /base_config/leaf.cfg and spine.cfg files"
    )
    info.managementRange = input("Management IP Range (i.e 192.168.0.0): ")
    validIp = validate_ip_address(info.managementRange)
    if not validIp:
        os.system("clear")
        print("Invalid IP Address")
        input("Press any key try again...")
        get_IP_info(info)
    splitOctets = ".".join(info.managementRange.split(".")[:3])
    info.spineIp = (
        input(
            f"First management IP for Spines [Press enter for default ({splitOctets}.101)]: "
        )
        or splitOctets + ".101"
    )
    info.leafIp = (
        input(
            f"First management IP for Leafs [Press enter for default ({splitOctets}.111)]: "
        )
        or splitOctets + ".111"
    )
    info.gatewayIp = (
        input(
            f"Gateway IP Address for Management Range [Press enter for default ({splitOctets}.1)]: "
        )
        or splitOctets + ".1"
    )
    confirm_ip_info(info)


def confirm_ip_info(info):
    os.system("clear")
    print("IP Information")
    print("Management IP Range: " + info.managementRange)
    print("First Spine IP Address: " + info.spineIp)
    print("First Leaf IP Address: " + info.leafIp)
    print("Management Network Gateway: " + info.gatewayIp)
    choice = prompt_yes_no("Is this IP information correct? (yes/no): ")
    info.infoCorrect = choice


def select_ceos_image(info):
    os.system("clear")
    dockerClient = docker.from_env()
    dockerImages = dockerClient.images.list()
    imageDicts = []
    for image in dockerImages:
        for tag in image.tags:
            if tag.startswith("ceos"):
                imageDict = {"tags": [tag]}
                imageDicts.append(imageDict)
                break
    jsonStr = json.dumps(imageDicts)
    jsonData = json.loads(jsonStr)
    print("Available CEOS Images:")
    for i, item in enumerate(jsonData):
        imageTags = item["tags"]
        print(f"{i + 1}. {', '.join(imageTags)}")

    choice = input("Select an Image for use: ")
    while not choice.isdigit() or int(choice) < 1 or int(choice) > len(jsonData):
        choice = input(
            "Invalid choice. Please enter the number of the image you want to use: "
        )
    selectedImage = jsonData[int(choice) - 1]
    imageTags = selectedImage["tags"]
    info.strippedCEOSImage = ", ".join([tag.strip("[").strip("]") for tag in imageTags])


def select_host_image(info):
    os.system("clear")
    dockerClient = docker.from_env()
    availableImages = ["ubuntu", "centos", "alpine"]
    print("Available images: ")
    for index, image in enumerate(availableImages):
        print(f"{index + 1}. {image}")
    imageIndex = int(input("Enter the index of the image you want to use: "))
    selectedImage = availableImages[imageIndex - 1]
    try:
        dockerClient.images.get(selectedImage)
    except docker.errors.ImageNotFound:
        os.system("clear")
        print(f"{selectedImage} doesn't exist, downloading...")
        dockerClient.images.pull(selectedImage)
    info.strippedHostImage = selectedImage + ":latest"


def update_mgmt_ip(lab, info):
    template_file = Path("./base_config") / (lab.labName + ".yml")
    output_file = Path("./inventory") / (lab.labName + ".yml")
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

    with open(template_file, "r") as f:
        content = f.read()

    for placeholder, ip in ips.items():
        content = content.replace("{" + placeholder + "}", ip)

    with open(output_file, "w") as f:
        f.write(content)


def generate_spine_config(lab, info):
    startNumber = 1
    for i in range(1, lab.noSpines + 1):
        startSpines = str(startNumber)
        if startNumber > 1:
            octets = info.spineIp.split(".")
            last_octet = int(octets[-1]) + 1
            octets[-1] = str(last_octet)
            info.spineIp = ".".join(octets)
        template_filename = "./base_config/spine.cfg"
        output_file = lab.configDir + "ceos-spine-" + str(startSpines) + ".cfg"
        with open(template_filename, "r") as file:
            content = file.read()
        if info.cvpRequired == True:
            content = content.replace("{USERNAME}", info.cvpUsername)
            content = content.replace("{PASSWORD}", info.cvpPassword)
            content = content.replace("{CVPIP}", info.cvpIp)
        if info.cvpRequired == False:
            content = content.replace("{USERNAME}", info.swUsername)
            content = content.replace("{PASSWORD}", info.swPassword)
            content = content.replace("-cvaddr={CVPIP}:9910", "")
        content = content.replace("{NUMBER}", startSpines)
        content = content.replace("{SPINEIP}", info.spineIp)
        content = content.replace("{GATEWAYIP}", info.gatewayIp)
        with open(output_file, "w") as file:
            file.write(content)
        startNumber += 1


def generate_leaf_config(lab, info):
    startNumber = 1
    for i in range(1, lab.noLeafs + 1):
        startLeafs = str(startNumber)
        if startNumber > 1:
            octets = info.leafIp.split(".")
            last_octet = int(octets[-1]) + 1
            octets[-1] = str(last_octet)
            info.leafIp = ".".join(octets)

        template_filename = "./base_config/leaf.cfg"
        output_file = lab.configDir + "ceos-leaf-" + str(startLeafs) + ".cfg"
        with open(template_filename, "r") as file:
            content = file.read()

        if info.cvpRequired == True:
            content = content.replace("{USERNAME}", info.cvpUsername)
            content = content.replace("{PASSWORD}", info.cvpPassword)
            content = content.replace("{CVPIP}", info.cvpIp)
        if info.cvpRequired == False:
            content = content.replace("{USERNAME}", info.swUsername)
            content = content.replace("{PASSWORD}", info.swPassword)
            content = content.replace("-cvaddr={CVPIP}:9910", "")
        content = content.replace("{NUMBER}", startLeafs)
        content = content.replace("{LEAFIP}", info.leafIp)
        content = content.replace("{GATEWAYIP}", info.gatewayIp)

        with open(output_file, "w") as file:
            file.write(content)

        startNumber += 1


def deploy_lab(lab, info):
    cvp_required(info)
    if info.cvpRequired == True:
        cvp_provision_required(info)
        get_cvp_info(info)
    elif info.cvpRequired == False:
        get_switch_info(info)
    get_IP_info(info)
    select_ceos_image(info)
    if lab.hostReq == True:
        select_host_image(info)
    update_mgmt_ip(lab, info)
    generate_spine_config(lab, info)
    generate_leaf_config(lab, info)
    os.system("clear")
    print("Generating Switch Configurations")
    time.sleep(10)
    os.system("clear")
    print("Deploying Lab Now... Please wait for lab information display")
    subResult = subprocess_run(lab.deploy_command)
    os.system("clear")
    os.system("clear")
    if info.cvpProvision == True:
        print("Provisioning Devices into CVP")
        os.system("clear")
        print("Creating Lab Container")
        cvp_create_container(lab, info)
        os.system("clear")
        cvp_execute_tasks(info)
        print("Executing Remaining tasks in CVP")
        os.system("clear")
        print(subResult.stdout.decode())
        print("Lab has been deployed and is ready for use")
        input("Press any key to return to the Main Menu")
        main()
    else:
        print(subResult.stdout.decode())
        print("Lab has been deployed and is ready for use")
        input("Press any key to return to the Main Menu")
        main()


### CVP SPECIFIC FUNCTIONS ###


def cvp_connect_check(info):
    cvpClient = CvpClient()
    try:
        cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)
        info.cvpConnected = True
    except CvpLoginError as e:
        info.cvpConnected = False


def cvp_create_container(lab, info):
    cvpClient = CvpClient()
    cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword, 120, 120)
    newContainer = cvpClient.api.get_container_by_name("Tenant")
    containerName = lab.labName
    try:
        print(f"Creating Container {containerName}\n")
        cvpClient.api.add_container(
            containerName, newContainer["name"], newContainer["key"]
        )
    except Exception as e:
        if "jsonData already exists in jsonDatabase" in str(e):
            print("Container already exists, continuing...")
    parentContainer = cvpClient.api.get_container_by_name("Undefined")
    mgmtIpListFile = lab.labDir + "topology-data.json"
    ipList = []
    with open(mgmtIpListFile) as f:
        jsonData = json.load(f)
    for name, node in jsonData["nodes"].items():
        ipList.append(node["mgmt-ipv4-address"])
    cvpList = []
    for devIp in ipList:
        cvpDict = {
            "device_ip": devIp,
            "parent_name": parentContainer["name"],
            "parent_key": parentContainer["key"],
        }
        cvpList.append(cvpDict)
    print("Adding Devices to CVP Inventory")
    cvpClient.api.add_devices_to_inventory(cvpList)
    deviceList = []
    deviceNames = cvpClient.api.get_devices_in_container("Undefined")
    for v in deviceNames:
        cvpDict = {"deviceName": v["fqdn"]}
        deviceList.append(cvpDict)
    print("Moving devices to " + lab.labName + " container")
    for device in deviceList:
        device = cvpClient.api.get_device_by_name(device["deviceName"])
        container = cvpClient.api.get_container_by_name(containerName)
        move = cvpClient.api.move_device_to_container("python", device, container)


def cvp_execute_tasks(info):
    cvpClient = CvpClient()
    cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)
    print("Executing Tasks in CVP")
    tasks = cvpClient.api.get_tasks_by_status("Pending")
    for task in tasks:
        taskId = task["workOrderId"]
        result = cvpClient.api.execute_task(taskId)


def cvp_decomm(info):
    cvpClient = CvpClient()
    cvpClient.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)
    deviceList = cvpClient.api.get_inventory()
    cvpClient.api.get_devices_in_container(info.selectedDelete)
    for v in deviceList:
        cvpDevice = v["serialNumber"]
        cvpRequest = str(uuid.uuid4())
        cvpClient.api.device_decommissioning(cvpDevice, cvpRequest)


def cvp_delete_container(info):
    cvp_client = CvpClient()
    cvp_client.connect(info.cvpIpList, info.cvpUsername, info.cvpPassword)
    devices = []
    for device in cvp_client.api.get_devices_in_container(info.selectedDelete):
        devices.append({"deviceName": device["fqdn"]})
    while True:
        os.system("clear")
        print(
            "Waiting for devices to be decommissioned (This can take up to 5 minutes)"
        )
        devices = []
        for device in cvp_client.api.get_devices_in_container(info.selectedDelete):
            devices.append({"deviceName": device["fqdn"]})
        if not devices:
            break
        time.sleep(20)
    container = cvp_client.api.get_container_by_name(info.selectedDelete)
    cvp_client.api.delete_container(
        container["name"], container["key"], "Tenant", "root"
    )


### DELETE LAB FUNCTIONS ###


def destroy_lab(info):
    destroy_lab_info(info)
    delete_lab_files(info)
    decommission_required(info)
    if info.decommDevice == True:
        get_cvp_info(info)
        os.system("clear")
        print("Decommissioning Devices from CVP")
        cvp_decomm(info)
        cvp_delete_container(info)
    destroy_lab_commands(info)


def destroy_lab_info(info):
    os.system("clear")
    inspect_command = "clab inspect --all --format json | jq -r '.containers | unique_by(.labPath)' > lab_info"
    subResult = subprocess_run(inspect_command)
    labInfoFile = "lab_info"
    if os.path.getsize(labInfoFile) == 0:
        print("There are no labs running at this time")
        input("Press any key to return to the main menu")
    else:
        print("The following labs are running")
        with open(labInfoFile) as f:
            labjsonData = json.load(f)
        for index, v in enumerate(labjsonData):
            print(f"{index + 1}. {v['lab_name']}")
        while True:
            try:
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
    os.system("clear")
    info.deleteChoice = labjsonData[labChoice - 1]["labPath"]
    info.selectedDelete = labjsonData[labChoice - 1]["lab_name"]
    info.deletePath = "./configs/" + info.selectedDelete


def delete_lab_files(info):
    os.system("clear")
    choice = prompt_yes_no(
        "Would you like to delete all lab files for the selected topology? (yes/no): "
    )
    info.deleteFiles = choice


def decommission_required(info):
    os.system("clear")
    choice = prompt_yes_no(
        "Would you like to decommission devices in cloudvision? (yes/no): "
    )
    info.decommDevice = choice


def destroy_lab_commands(info):
    if info.deleteFiles == True:
        destroy_command = f"sudo clab destroy -t {info.deleteChoice} --cleanup"
        for confFile in os.scandir(info.deletePath):
            if confFile.is_file():
                os.remove(confFile)
    elif info.deleteFiles == False:
        destroy_command = f"sudo clab destroy -t {info.deleteChoice}"
    subResult = subprocess_run(destroy_command)
    os.remove("lab_info")
    os.remove("./inventory/" + info.selectedDelete + ".yml")
    os.remove("./inventory/." + info.selectedDelete + ".yml.bak")
    os.system("clear")
    if info.deleteFiles == True:
        print(f"Lab {info.selectedDelete} and all associated files have been deleted")
        input("Press any key to return to main menu")
        main()
    else:
        print(
            f"Lab {info.selectedDelete} has been destroyed however all lab and configuration files can be found in the clab-{info.selectedDelete} folder"
        )
        input("Press any key to return to main menu")
        main()


### INSPECT RUNNING LABS ###


def check_status():
    os.system("clear")
    inspect_command = "clab inspect --all"
    subResult = subprocess_run(inspect_command)
    statusOutput = subResult.stdout.decode()
    if not statusOutput:
        print("There are no Labs running right now")
        input("Press any key to return to main menu")
        main()
    else:
        print(statusOutput)
        input("Press any key to return to main menu")
        main()


### EXIT SCRIPT ###


def terminate_script():
    os.system("clear")
    sys.exit()


### SHARED FUNCTIONS ###


def prompt_yes_no(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response == "y" or response == "yes":
            return True
        elif response == "n" or response == "no":
            return False
        else:
            print('Invalid response. Please enter "yes" or "no".')


def validate_ip_address(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def increment_ip(ip, increment):
    octets = ip.split(".")
    octets[3] = str(int(octets[3]) + increment)
    return ".".join(octets)


def subprocess_run(command):
    subResult = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return subResult


def main_menu():
    print("Welcome to the ContainerLab helper")
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
