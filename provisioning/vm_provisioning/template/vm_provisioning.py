from pyVim import connect
from pyVmomi import vim
import ssl

# vCenter 접속 정보
vcenter_host = "your-vcenter-host"
vcenter_user = "your-vcenter-username"
vcenter_password = "your-vcenter-password"
vm_name = "new-vm-name"
network_name = "your-network-name"


def find_available_ip(service_instance, network_name):
    """
    주어진 네트워크에서 사용 가능한 IP를 찾아 반환합니다.
    """
    content = service_instance.RetrieveContent()

    # 네트워크 가져오기
    network = None
    for network_obj in content.viewManager.networkView:
        if network_obj.name == network_name:
            network = network_obj
            break

    if not network:
        raise RuntimeError(f"Network '{network_name}' not found")

    # IP 할당 확인
    ip_pool = network.config.ipPoolConfig.ipPool
    for ip_range in ip_pool:
        start_ip = ip_range.range.startAddress
        end_ip = ip_range.range.endAddress

        # TODO: 여기에 사용 가능한 IP 확인 로직 추가
        # 예를 들어, 해당 범위에서 이미 사용 중이지 않은 IP를 찾는 등의 로직을 구현해야 합니다.

        # 임시로 첫 번째 IP를 반환하는 예제
        return start_ip

    raise RuntimeError(f"No available IP found in network '{network_name}'")


def create_vm(service_instance, vm_name, network_name):
    """
    주어진 vCenter에 새로운 VM을 생성합니다.
    """
    content = service_instance.RetrieveContent()

    # VM 생성 설정
    vm_folder = content.rootFolder
    datacenter = vm_folder.childEntity[0]
    vm_resource_pool = datacenter.hostFolder.childEntity[0].resourcePool
    vm_datastore = datacenter.datastore[0]

    # VM 생성 스펙
    vmx_file_path = f"[{vm_datastore.info.name}] {vm_name}/{vm_name}.vmx"
    vm_file_layout = vim.vm.FileLayout()
    vm_file_layout.vmPathName = vmx_file_path

    # 네트워크 설정
    network_adapter = vim.vm.device.VirtualVmxnet3()
    network_adapter.deviceInfo = vim.Description()
    network_adapter.deviceInfo.label = network_name

    # IP 할당
    available_ip = find_available_ip(service_instance, network_name)
    ip_settings = vim.vm.customization.IPSettings()
    ip_settings.ip = vim.vm.customization.FixedIp()
    ip_settings.ip.ipAddress = available_ip
    ip_settings.subnetMask = "255.255.255.0"  # 예시에서는 하드코딩되어 있음

    network_adapter.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
    network_adapter.backing.deviceName = network_name
    network_adapter.backing.network = network

    # VM 생성
    config_spec = vim.vm.ConfigSpec()
    config_spec.name = vm_name
    config_spec.memoryMB = 4096
    config_spec.numCPUs = 2
    config_spec.deviceChange = [
        vim.vm.device.VirtualDeviceConfigSpec(
            device=network_adapter,
            operation=vim.vm.device.VirtualDeviceConfigSpec.Operation.add,
        )
    ]
    config_spec.files = vm_file_layout
    config_spec.guestId = "ubuntu64Guest"
    config_spec.version = "vmx-14"

    # VM 생성 요청
    task = vm_folder.CreateVM_Task(config=config_spec, pool=vm_resource_pool)

    # 작업 완료 대기
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        continue

    if task.info.state == vim.TaskInfo.State.error:
        raise RuntimeError(f"VM creation failed: {task.info.error.msg}")

    print(f"VM '{vm_name}' created successfully with IP '{available_ip}'")


def main():
    # SSL 인증서 오류 방지
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE

    # vCenter에 연결
    service_instance = connect.SmartConnect(
        host=vcenter_host, user=vcenter_user, pwd=vcenter_password, sslContext=context
    )

    if not service_instance:
        print(
            "Could not connect to the specified host using specified username and password"
        )
        return

    try:
        # VM 생성
        create_vm(service_instance, vm_name, network_name)
    except Exception as e:
        print(f"Error creating VM: {str(e)}")
    finally:
        # 연결 닫기
        connect.Disconnect(service_instance)


if __name__ == "__main__":
    main()
