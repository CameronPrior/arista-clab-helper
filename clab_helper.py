import getpass
import sys
import os
import subprocess
import time
import requests
import json
from datetime import datetime
from cvprac.cvp_client import CvpClient
import ssl
import ipaddress
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context
import requests.packages

requests.packages.urllib3.disable_warnings()
import uuid
import docker


def main_menu():
    print("Welcome to the ContainerLab helper")
    print("1. Deploy Lab")
    print("2. Destroy Lab")
    print("3. Check Running Lab Status")
    print("4. Quit")


def deployment_type_menu():
    global noSpines, noLeafs, configDir, labDir, labName, deploy_command
    os.system("clear")
    if not os.path.exists("./inventory"):
        os.makedirs("./inventory")
    print("What type of lab are you deploying?")
    print("1. Single DC - Leaf Spine")
    print("2. Dual DC - Leaf Spine")
    choice = input("Enter your choice: ")
    if choice == "1":
        noSpines = 2
        noLeafs = 4
        configDir = "./configs/Arista-SDC-LS-MLAG/"
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        labDir = "./clab-Arista-SDC-LS-MLAG/"
        deploy_command = "clab deploy -t ./inventory/Arista-SDC-LS-MLAG.yml"
        labName = "Arista-SDC-LS-MLAG"
        deploy_lab()
    elif choice == "2":
        noSpines = 4
        noLeafs = 12
        configDir = "./configs/Arista-DDC-LS-MLAG/"
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        labDir = "./clab-Arista-DDC-LS-MLAG/"
        deploy_command = "clab deploy -t ./inventory/Arista-DDC-LS-MLAG.yml"
        labName = "Arista-DDC-LS-MLAG"
        deploy_lab()
    else:
        print("Invalid choice. Try again.")
        deployment_type_menu()


def cvp_required():
    global cvpRequired
    os.system("clear")
    print("Is Cloudvision Required:")
    print("1. Yes")
    print("2. No")
    choice = input("Enter your choice: ")
    if choice == "1":
        cvpRequired = True
    elif choice == "2":
        cvpRequired = False
    else:
        print("Invalid choice. Try again.")
        cvp_required()


def cvp_provision_required():
    global cvpProvision
    os.system("clear")
    print("Would you like to automatically provision devices into Cloudvision: ")
    print("1. Yes")
    print("2. No")
    choice = input("Enter your choice: ")
    if choice == "1":
        cvpProvision = True
    elif choice == "2":
        cvpProvision = False
    else:
        print("Invalid choice. Try again.")
        cvp_provision_required()


def get_cvp_info():
    global cvpIp, cvpIpList, cvpServer, cvpUsername, cvpPassword, headers
    os.system("clear")
    cvpIp = input("CVP IP Address: ")
    cvpIpList = [cvpIp]
    cvpServer = "https://" + cvpIp + "/cvpservice"
    cvpUsername = input("CVP Username: ")
    cvpPassword = getpass.getpass("CVP Password: ")
    headers = {"accept": "application/json", "Content-Type": "application/json"}


def get_switch_info():
    global swUsername, swPassword
    os.system("clear")
    swUsername = input("Set Switch Username: ")
    swPassword = getpass.getpass("Set Switch Password: ")


def cvp_create_container():
    cvpClient = CvpClient()
    cvpClient.connect(cvpIpList, cvpUsername, cvpPassword, 120, 120)
    newContainer = cvpClient.api.get_container_by_name("Tenant")
    containerName = labName
    try:
        print(f"Creating Container {containerName}\n")
        cvpClient.api.add_container(
            containerName, newContainer["name"], newContainer["key"]
        )
    except Exception as e:
        if "jsonData already exists in jsonDatabase" in str(e):
            print("Container already exists, continuing...")
    parentContainer = cvpClient.api.get_container_by_name("Undefined")
    mgmtIpListFile = labDir + "topology-jsonData.json"
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
    print("Moving devices to " + labName + " container")
    for device in deviceList:
        device = cvpClient.api.get_device_by_name(device["deviceName"])
        container = cvpClient.api.get_container_by_name(containerName)
        move = cvpClient.api.move_device_to_container("python", device, container)


def cvp_execute_tasks():
    cvpClient = CvpClient()
    cvpClient.connect(cvpIpList, cvpUsername, cvpPassword)
    tasks = cvpClient.api.get_tasks_by_status("Pending")
    for task in tasks:
        taskId = task["workOrderId"]
        result = cvpClient.api.execute_task(taskId)


def get_IP_info():
    global spineIp, leafIp, gatewayIp, managementRange
    os.system("clear")
    print(
        "Note: The generated configuration files assume a /24 management network, if a different subnet mask is required changes can be made to the /base_config/leaf.cfg and spine.cfg files"
    )
    managementRange = input("Management IP Range (i.e 192.168.0.0): ")
    validate_ip_address(managementRange)
    if validIp == False:
        os.system("clear")
        print("Invalid IP Address")
        input("Press any key try again...")
        get_IP_info()
    splitOctets = ".".join(managementRange.split(".")[:3])
    spineIp = (
        input(
            f"First management IP for Spines [Press enter for default ({splitOctets}.101)]: "
        )
        or splitOctets + ".101"
    )
    leafIp = (
        input(
            f"First management IP for Leafs [Press enter for default ({splitOctets}.111)]: "
        )
        or splitOctets + ".111"
    )
    gatewayIp = (
        input(
            f"Gateway IP Address for Management Range [Press enter for default ({splitOctets}.1)]: "
        )
        or splitOctets + ".1"
    )
    confirm_ip_info()


def confirm_ip_info():
    os.system("clear")
    print("IP Information")
    print("Management IP Range: " + managementRange)
    print("First Spine IP Address: " + spineIp)
    print("First Leaf IP Address: " + leafIp)
    print("Management Network Gateway: " + gatewayIp)
    infoCorrect = input("Is this information correct (Y/N): ")
    if infoCorrect == "N" or infoCorrect == "n":
        get_IP_info()
    elif infoCorrect == "Y" or infoCorrect == "y":
        return
    else:
        confirm_ip_info()


def select_image():
    global strippedImage
    os.system("clear")
    dockerClient = docker.from_env()
    dockerImages = dockerClient.images.list()
    imageDicts = []
    for image in dockerImages:
        imageDict = {"tags": image.tags}
        imageDicts.append(imageDict)
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
    strippedImage = ", ".join([tag.strip("[").strip("]") for tag in imageTags])


def update_mgmt_ip():
    template_file = Path("./base_config") / (labName + ".yml")
    output_file = Path("./inventory") / (labName + ".yml")
    if labName == "Arista-SDC-LS-MLAG":
        ips = {
            "MGMTRANGE": managementRange,
            "SPINE1IP": spineIp,
            "SPINE2IP": increment_ip(spineIp, 1),
            "LEAF1IP": leafIp,
            "LEAF2IP": increment_ip(leafIp, 1),
            "LEAF3IP": increment_ip(leafIp, 2),
            "LEAF4IP": increment_ip(leafIp, 3),
            "IMAGE": strippedImage,
        }
    elif labName == "Arista-DDC-LS-MLAG":
        ips = {
            "MGMTRANGE": managementRange,
            "SPINE1IP": spineIp,
            "SPINE2IP": increment_ip(spineIp, 1),
            "SPINE3IP": increment_ip(spineIp, 2),
            "SPINE4IP": increment_ip(spineIp, 3),
            "LEAF1IP": leafIp,
            "LEAF2IP": increment_ip(leafIp, 1),
            "LEAF3IP": increment_ip(leafIp, 2),
            "LEAF4IP": increment_ip(leafIp, 3),
            "LEAF5IP": increment_ip(leafIp, 4),
            "LEAF6IP": increment_ip(leafIp, 5),
            "LEAF7IP": increment_ip(leafIp, 6),
            "LEAF8IP": increment_ip(leafIp, 7),
            "LEAF9IP": increment_ip(leafIp, 8),
            "LEAF10IP": increment_ip(leafIp, 9),
            "LEAF11IP": increment_ip(leafIp, 10),
            "LEAF12IP": increment_ip(leafIp, 12),
            "IMAGE": strippedImage,
        }

    with open(template_file, "r") as f:
        content = f.read()

    for placeholder, ip in ips.items():
        content = content.replace("{" + placeholder + "}", ip)

    with open(output_file, "w") as f:
        f.write(content)


def increment_ip(ip, increment):
    octets = ip.split(".")
    octets[3] = str(int(octets[3]) + increment)
    return ".".join(octets)


def generate_spine_config():
    global spineIp
    startNumber = 1
    for i in range(1, noSpines + 1):
        startSpines = str(startNumber)
        if startNumber > 1:
            octets = spineIp.split(".")
            last_octet = int(octets[-1]) + 1
            octets[-1] = str(last_octet)
            spineIp = ".".join(octets)
        template_filename = "./base_config/spine.cfg"
        output_file = configDir + "ceos-spine-" + str(startSpines) + ".cfg"
        with open(template_filename, "r") as file:
            content = file.read()
        if cvpRequired == True:
            content = content.replace("{USERNAME}", cvpUsername)
            content = content.replace("{PASSWORD}", cvpPassword)
            content = content.replace("{CVPIP}", cvpIp)
        if cvpRequired == False:
            content = content.replace("{USERNAME}", swUsername)
            content = content.replace("{PASSWORD}", swPassword)
            content = content.replace("-cvaddr={CVPIP}:9910", "")
        content = content.replace("{NUMBER}", startSpines)
        content = content.replace("{SPINEIP}", spineIp)
        content = content.replace("{GATEWAYIP}", gatewayIp)
        with open(output_file, "w") as file:
            file.write(content)
        startNumber += 1


def generate_leaf_config():
    global leafIp
    startNumber = 1
    for i in range(1, noLeafs + 1):
        startLeafs = str(startNumber)
        if startNumber > 1:
            octets = leafIp.split(".")
            last_octet = int(octets[-1]) + 1
            octets[-1] = str(last_octet)
            leafIp = ".".join(octets)

        template_filename = "./base_config/leaf.cfg"
        output_file = configDir + "ceos-leaf-" + str(startLeafs) + ".cfg"
        with open(template_filename, "r") as file:
            content = file.read()

        if cvpRequired == True:
            content = content.replace("{USERNAME}", cvpUsername)
            content = content.replace("{PASSWORD}", cvpPassword)
            content = content.replace("{CVPIP}", cvpIp)
        if cvpRequired == False:
            content = content.replace("{USERNAME}", swUsername)
            content = content.replace("{PASSWORD}", swPassword)
            content = content.replace("-cvaddr={CVPIP}:9910", "")
        content = content.replace("{NUMBER}", startLeafs)
        content = content.replace("{LEAFIP}", leafIp)
        content = content.replace("{GATEWAYIP}", gatewayIp)

        with open(output_file, "w") as file:
            file.write(content)

        startNumber += 1


def deploy_lab():
    cvp_required()
    if cvpRequired == True:
        cvp_provision_required()
        if cvpProvision == True:
            get_cvp_info()
    elif cvpRequired == False:
        get_switch_info()
    get_IP_info()
    select_image()
    update_mgmt_ip()
    generate_spine_config()
    generate_leaf_config()
    os.system("clear")
    print("Generating Switch Configurations")
    time.sleep(10)
    os.system("clear")
    print("Deploying Lab Now... Please wait for lab information display")
    deployResult = subprocess.run(
        deploy_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    os.system("clear")
    if cvpRequired == True:
        if cvpProvision == True:
            print("Provisioning Devices into CVP")
            os.system("clear")
            print("Creating Lab Container")
            cvp_create_container()
            os.system("clear")
            cvp_execute_tasks()
            print("Executing Remaining tasks in CVP")
            os.system("clear")
            print(deployResult.stdout.decode())
            print("Lab has been deployed and is ready for use")
            input("Press any key to return to the Main Menu")
            main()
    else:
        print(deployResult.stdout.decode())
        print("Lab has been deployed and is ready for use")
        input("Press any key to return to the Main Menu")
        main()


def terminate_script():
    os.system("clear")
    sys.exit()


def destroy_lab():
    destroy_lab_info()
    delete_lab_files()
    decommission_required()
    if decommDevice == True:
        get_cvp_info()
        os.system("clear")
        print("Decommissioning Devices from CVP")
        cvp_decomm()
        cvp_delete_container()
    destroy_lab_commands()


def destroy_lab_info():
    os.system("clear")
    global deleteChoice, configPath, labName
    labInfo = "clab inspect --all --format json | jq -r '.containers | unique_by(.labPath)' > lab_info"
    subprocess.run(
        labInfo,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
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
        labChoice = int(input("Select the Lab you wish to Destroy: "))
        os.system("clear")
        deleteChoice = labjsonData[labChoice - 1]["labPath"]
        labName = labjsonData[labChoice - 1]["lab_name"]
        configPath = "./configs/" + labName


def delete_lab_files():
    global deleteFiles
    os.system("clear")
    print("Would you like to delete all lab files for the selected topology")
    print("1. Yes")
    print("2. No")
    labChoice = input("Enter your choice: ")
    if labChoice == "1":
        deleteFiles = True
    elif labChoice == "2":
        deleteFiles = False
    else:
        print("Invalid choice. Try again.")
        delete_lab_files()


def decommission_required():
    global decommDevice
    os.system("clear")
    print("Would you like to decommission devices in cloudvision")
    print("1. Yes")
    print("2. No")
    labChoice = input("Enter your choice: ")
    if labChoice == "1":
        decommDevice = True
    elif labChoice == "2":
        decommDevice = False
    else:
        print("Invalid choice. Try again.")
        decommission_required()


def cvp_decomm():
    cvpClient = CvpClient()
    cvpClient.connect(cvpIpList, cvpUsername, cvpPassword)
    deviceList = cvpClient.api.get_inventory()
    cvpClient.api.get_devices_in_container(labName)
    for v in deviceList:
        cvpDevice = v["serialNumber"]
        cvpRequest = str(uuid.uuid4())
        cvpClient.api.device_decommissioning(cvpDevice, cvpRequest)


def cvp_delete_container():
    cvp_client = CvpClient()
    cvp_client.connect(cvpIpList, cvpUsername, cvpPassword)
    devices = []
    for device in cvp_client.api.get_devices_in_container(labName):
        devices.append({"deviceName": device["fqdn"]})
    while True:
        os.system("clear")
        print(
            "Waiting for devices to be decommissioned (This can take up to 5 minutes)"
        )
        devices = []
        for device in cvp_client.api.get_devices_in_container(labName):
            devices.append({"deviceName": device["fqdn"]})
        if not devices:
            break
        time.sleep(20)
    container = cvp_client.api.get_container_by_name(labName)
    cvp_client.api.delete_container(
        container["name"], container["key"], "Tenant", "root"
    )


def destroy_lab_commands():
    if deleteFiles == True:
        destroyCommand = f"sudo clab destroy -t {deleteChoice} --cleanup"
        for confFile in os.scandir(configPath):
            if confFile.is_file():
                os.remove(confFile)
    elif deleteFiles == False:
        destroyCommand = f"sudo clab destroy -t {deleteChoice}"
    subprocess.run(
        destroyCommand,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    os.remove("lab_info")
    os.remove("./inventory/" + labName + ".yml")
    os.remove("./inventory/." + labName + ".yml.bak")
    os.system("clear")
    if deleteFiles == True:
        print(f"Lab {labName} and all associated files have been deleted")
        input("Press any key to return to main menu")
        main()
    else:
        print(
            f"Lab {labName} has been destroyed however all lab and configuration files can be found in the clab-{labName} folder"
        )
        input("Press any key to return to main menu")
        main()


def check_status():
    os.system("clear")
    command = "clab inspect --all"
    statusResult = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    statusOutput = statusResult.stdout.decode()
    if not statusOutput:
        print("There are no Labs running right now")
        input("Press any key to return to main menu")
        main()
    else:
        print(statusOutput)
        input("Press any key to return to main menu")
        main()


def validate_ip_address(ip):
    global validIp
    try:
        ipaddress.IPv4Address(ip)
        validIp = True
    except ipaddress.AddressValueError:
        validIp = False


def main():
    os.system("clear")
    if os.getuid() == 0:
        main_menu()
        choice = input("Enter your choice: ")
        if choice == "1":
            deployment_type_menu()
        elif choice == "2":
            destroy_lab()
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
