import subprocess
from pathlib import Path
from signal import SIGTERM
from typing import List, Optional, Union

import psutil
import yaml
from kubernetes_asyncio import config as k8s_config, client as k8s_client
from kubernetes_asyncio.client import V1Namespace, V1Service
from kubernetes_asyncio.client.api_client import ApiClient
from psutil import process_iter
from urllib3.exceptions import NewConnectionError, ConnectTimeoutError, MaxRetryError

from youwol.exceptions import CommandException
from youwol.utils.utils_low_level import execute_shell_cmd
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_yaml


async def k8s_access_token():
    await k8s_config.load_kube_config()
    async with ApiClient() as api:
        api_key = api.configuration.api_key
    return api_key['BearerToken'].strip('Bearer').strip()


async def k8s_namespaces() -> List[str]:

    async with ApiClient() as api:
        v1 = k8s_client.CoreV1Api(api)
        namespaces = await v1.list_namespace()
        names = [n.metadata.name for n in namespaces.items]
        return names


async def k8s_secrets(namespace: str) -> List[str]:

    async with ApiClient() as api:
        v1 = k8s_client.CoreV1Api(api)
        secrets = await v1.list_namespaced_secret(namespace)
        names = [n.metadata.name for n in secrets.items]
        return names


async def k8s_create_secret(namespace: str, file_path: Path):
    with open(file_path) as f:
        data = yaml.safe_load(f)
        async with ApiClient() as api:
            k8s_client.CoreV1Api(api).create_namespaced_secret(namespace=namespace, body=data)


async def k8s_create_secrets_if_needed(namespace: str, secrets: List[Path], context: Context = None):
    existing = await k8s_secrets(namespace=namespace)
    names = [parse_yaml(s)['metadata']['name'] for s in secrets]
    needed = [(n, s) for n, s in zip(names, secrets) if n not in existing]
    for name, secret in needed:
        context and context.info(f"Create secret {name} in namespace {namespace}")
        await k8s_create_secret(namespace=namespace, file_path=secret)


async def k8s_create_namespace(name: str):

    async with ApiClient() as api:
        v1 = k8s_client.CoreV1Api(api)
        await v1.create_namespace(body=V1Namespace(metadata=dict(name=name)))


async def k8s_get_service(namespace: str, name: str) -> Optional[V1Service]:

    async with ApiClient() as api:
        v1 = k8s_client.CoreV1Api(api)
        services = await v1.list_namespaced_service(namespace)
        service = next((s for s in services.items if s.metadata.name == name), None)
        return service


async def k8s_pod_exec(pod_name: str, namespace: str, commands: List[str], context: Context = None):

    cmd_outputs = []
    for cmd in commands:
        full = f'kubectl exec -i  {pod_name} -n {namespace} -- bash -c "{cmd}"'
        context and context.info(full)
        return_code, outputs = await execute_shell_cmd(full, context=context)
        if return_code > 0:
            raise CommandException(command=full, outputs=outputs)
        cmd_outputs.append(outputs)

    return cmd_outputs


def kill_k8s_proxy(port: int):
    for proc in process_iter():
        try:
            for conns in proc.connections(kind='inet'):
                if conns.laddr.port == port:
                    proc.send_signal(SIGTERM)  # or SIGKILL
        except psutil.Error:
            pass


async def k8s_port_forward(namespace: str, service_name: str, target_port: Optional[Union[str, int]],
                           local_port: int, context: Context):

    service = await k8s_get_service(namespace=namespace, name=service_name)
    ports = service.spec.ports

    port_number = ports[0].target_port

    if isinstance(target_port, int):
        port_number = ports[target_port].target_port
    if isinstance(target_port, str):
        port_number = next(p for p in ports if p.name == target_port).target_port

    cmd = f"kubectl port-forward -n {namespace} service/{service_name} {local_port}:{port_number}"
    kill_k8s_proxy(local_port)
    subprocess.Popen(cmd, shell=True)
    await context.info(f"Port forward {namespace}#{service_name} using local port {local_port}")


async def start_k8s_proxy(
        config_file: Path,
        context_name: str,
        proxy_port: int
):
    await k8s_config.load_kube_config(
        config_file=str(config_file),
        context=context_name
    )
    cmd = f"kubectl config use-context {context_name} && kubectl proxy --port={proxy_port}"
    subprocess.Popen(cmd, shell=True)


async def get_api_gateway_ip() -> Optional[str]:
    kong = await k8s_get_service(namespace='api_gateway', name='kong-kong-proxy')
    if not kong:
        return None
    return None


async def get_cluster_info():

    try:
        async with ApiClient() as api:
            nodes = await k8s_client.CoreV1Api(api).list_node(_request_timeout=2)
            return [n.status.to_dict() for n in nodes.items]
    except (NewConnectionError, ConnectTimeoutError, MaxRetryError):
        return None
