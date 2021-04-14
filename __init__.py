from api import k8s_controller

update_image = k8s_controller().update_deployment_image
get_replicas = k8s_controller().get_deployment_replicas
read_deployment_status = k8s_controller().read_deployment_status
read_pod_status = k8s_controller().read_pod_status
do_scale = k8s_controller().do_scale
update_virtual_service_http = k8s_controller().update_virtual_service_http
update_virtual_service_tcp = k8s_controller().update_virtual_service_tcp

__all__ = []