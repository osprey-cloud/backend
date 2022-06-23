
from imp import reload
from time import clock_settime

import requests
from app.helpers.kube import create_kube_clients


def get_status(success, failed, partial=0):

    if partial > 0:
        return 'partial'
    elif failed == 0:
        return 'success'
    elif success == 0:
        return 'failed'
    else:
        return 'partial'


def get_kube_cluster_status(kube_client):
    # get cluster status
    try:
        cluster_status_list = kube_client.kube.list_component_status()
        cluster_status = []
        success = 0
        failed = 0
        for cluster_status_list_item in cluster_status_list.items:
            kubelet_status = cluster_status_list_item.conditions[0]
            cluster_status.append({
                'name': cluster_status_list_item.metadata.name,
                'status': kubelet_status.status,
                'type': kubelet_status.type,
                'error': kubelet_status.error
            })
            success += 1 if kubelet_status.status == 'True' else 0
            failed += 1 if kubelet_status.status == 'False' else 0

    # cluster_status = kube_client.kube.read_component_status()
        return {'status': get_status(success, failed),
                'data': cluster_status}
    except Exception:
        return {
            'status': 'failed',
            'data': []
        }


def get_cluster_status_info(clusters):
    clusters_status = []
    success = 0
    failed = 0
    partial = 0
    for cluster in clusters:
        kube_host = cluster.host
        kube_token = cluster.token

        kube_client = create_kube_clients(kube_host, kube_token)
        status = get_kube_cluster_status(kube_client)
        clusters_status.append({
            'cluster_name': cluster.name,
            'status': status['status'],
            'cluster_status': status['data']
        })
        success += 1 if status['status'] == 'success' else 0
        failed += 1 if status['status'] == 'failed' else 0
        partial += 1 if status['status'] == 'partial' else 0

    return {'status': get_status(success, failed, partial),
            'data': clusters_status}


def get_prometheus_status(prometheus_url):
    # get prometheus data
    try:
        response = requests.get(
            f'{prometheus_url}/api/v1/status/runtimeinfo')

        if response.status_code != 200:
            return {
                'status': 'failed',
                'data': {'status_code': response.status_code,
                         'error': response.text}
            }
        data = response.json()['data']
        reloadConfigStatus = data.get('reloadConfigSuccess', None)
        prometheus_data = {
            'reloadConfigSuccess': reloadConfigStatus,
            'lastConfigTime': data['lastConfigTime'],
        }
        return {'status': 'success' if reloadConfigStatus else 'Failed',
                'data': prometheus_data}
    except Exception as e:
        return {
            'status': 'failed',
            'data': str(e)
        }


def get_prometheus_status_info(clusters):
    # get prometheus status
    prometheus_status = []
    success = 0
    failed = 0
    partial = 0
    for cluster in clusters:
        kube_host = cluster.host
        kube_token = cluster.token

        kube_client = create_kube_clients(kube_host, kube_token)
        prometheus_url = cluster.prometheus_url
        if not prometheus_url:
            prometheus_status.append({
                'cluster_name': cluster.name,
                'status': 'failed',
                'prometheus_status': {
                    'error': 'Prometheus URL is not available'
                }
            })
            failed += 1
            continue
        status = get_prometheus_status(prometheus_url)
        prometheus_status.append({
            'cluster_name': cluster.name,
            'status': status['status'],
            'prometheus_status': status['data']
        })
        success += 1 if status['status'] == 'success' else 0
        failed += 1 if status['status'] == 'failed' else 0
        partial += 1 if status['status'] == 'partial' else 0

    return {'status': get_status(success, failed, partial),
            'data': prometheus_status}
