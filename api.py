import sys
import os
import argparse
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from pprint import pprint
import time
import yaml


class Singleton(object):
    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls)
        return cls._instance


class k8s_controller(Singleton):
    def __init__(self):
        config.kube_config.load_kube_config(config_file="/root/.kube/config")
        self.AppsV1 = client.AppsV1Api()
        self.CoreV1 = client.CoreV1Api()
        self.CustomV1 = client.CustomObjectsApi()
        self.namespace = 'default'

    def api_discover(self):
        print("Supported APIs (* is preferred version):")
        print("%-40s %s" %
              ("core", ",".join(client.CoreApi().get_api_versions().versions)))
        for api in client.ApisApi().get_api_versions().groups:
            versions = []
            for v in api.versions:
                name = ""
                if v.version == api.preferred_version.version and len(
                        api.versions) > 1:
                    name += "*"
                name += v.version
                versions.append(name)
            print("%-40s %s" % (api.name, ",".join(versions)))

    def read_pod_status(self):
        state = "Terminating"
        while (state == 'Terminating'):
            time.sleep(2)
            state = "Running"
            ret = self.CoreV1.list_namespaced_pod(namespace=self.namespace)
            for i in ret.items:
                if i.metadata.deletion_timestamp != None and i.status.phase == 'Running':
                    state = 'Terminating'
                    print "pod {} is Terminating".format(i.metadata.name)
                # else:
                #     state = str(i.status.phase)

    def get_deployment_replicas(self, svc):

        try:
            api_response = self.AppsV1.read_namespaced_deployment_scale(
                svc, self.namespace, pretty="true")
            return api_response.status.replicas
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->read_namespaced_deployment_scale: %s\n"
                % e)
            sys.exit(1)

    def read_deployment_status(self, svc):
        try:
            timeout = time.time() + 60 * 5
            unavailable_replicas = 0
            while unavailable_replicas is not None:
                time.sleep(5)
                ret = self.AppsV1.read_namespaced_deployment(svc,
                                                             self.namespace,
                                                             pretty="true")
                unavailable_replicas = ret.status.unavailable_replicas
                print "{} status warning: unavailable replicas: {}".format(
                    svc, unavailable_replicas)
                if time.time() > timeout:
                    print "task execute time out"
                    raise Exception("read deployment status timeout")
                    sys.exit(1)
            print "{} latest status: unavailable replicas: {}".format(
                svc, unavailable_replicas)
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->read_namespaced_deployment_status: %s\n"
                % e)
            sys.exit(1)

    def create_deployment(self, yamlpath):
        with open(yamlpath) as f:
            dep = yaml.safe_load(f)
            print type(dep)
            print dep
            resp = self.AppsV1.create_namespaced_deployment(
                body=dep, namespace=self.namespace)
            print("Deployment created. status='%s'" % resp.metadata.name)

    def delete_deployment(self, svc):
        # Delete deployment
        api_response = self.AppsV1.delete_namespaced_deployment(
            name=svc,
            namespace=self.namespace,
            body=client.V1DeleteOptions(propagation_policy='Foreground',
                                        grace_period_seconds=5))
        print("Deployment deleted. status='%s'" % str(api_response.status))

    def do_scale(self, svc, replicas):
        body = {"spec": {"replicas": replicas}}
        name = svc
        print "scale {} from {} to {} start".format(
            name, self.get_deployment_replicas(name), replicas)
        try:
            self.AppsV1.patch_namespaced_deployment_scale(
                name, self.namespace, body)
        except Exception as e:
            print "failed to scale '{s}' to {r} replicas: {e}".format(
                s=name, r=replicas, e=str(e))
            sys.exit(1)

    def update_deployment_image(self, svc, image):
        try:
            old_res = self.AppsV1.read_namespaced_deployment(
                svc, self.namespace)
            old_res.spec.template.spec.containers[0].image = image
            new_res = self.AppsV1.patch_namespaced_deployment(svc,
                                                              self.namespace,
                                                              body=old_res)
            print ""
            print "> {} update image: {}".format(svc, image)
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->patch_namespaced_deployment: %s\n"
                % e)
            sys.exit(1)

    def update_virtual_service_http(self,
                                    svc,
                                    match_header,
                                    flag=False,
                                    mode="v1tov2"):
        group = "networking.istio.io"
        version = "v1alpha3"
        plural = "virtualservices"
        match = False
        header_key = match_header.keys()[0]
        try:
            old_res = self.CustomV1.get_namespaced_custom_object(
                name=svc,
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
            )
        except ApiException as e:
            print(
                "Exception when calling CustomObjectsApi->get_namespaced_custom_object: %s\n"
                % e)
            sys.exit(1)

        new_res = old_res
        headers_list = new_res["spec"]["http"][0]["match"]
        for index in range(len(headers_list)):

            if headers_list[index]["headers"].has_key(header_key):
                headers_list[index]["headers"] = match_header
                new_res["spec"]["http"][0]["match"] = headers_list
                match = True

        if not match:

            match_header = {"headers": match_header}
            new_res["spec"]["http"][0]["match"].append(match_header)
        if mode == "v2tov1" and not flag:
            new_res["spec"]["http"][1]["route"][0]["destination"][
                "subset"] = "v2"
            new_res["spec"]["http"][0]["route"][0]["destination"][
                "subset"] = "v1"
        else:
            new_res["spec"]["http"][1]["route"][0]["destination"][
                "subset"] = "v1"
            new_res["spec"]["http"][0]["route"][0]["destination"][
                "subset"] = "v2"
        try:
            old_res = self.CustomV1.patch_namespaced_custom_object(
                name=svc,
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
                body=new_res,
            )
        except ApiException as e:
            print(
                "Exception when calling CustomObjectsApi->patch_namespaced_custom_object: %s\n"
                % e)
            sys.exit(1)

    def update_virtual_service_tcp(self, svc, route):
        group = "networking.istio.io"
        version = "v1alpha3"
        plural = "virtualservices"
        try:
            old_res = self.CustomV1.get_namespaced_custom_object(
                name=svc,
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
            )
        except ApiException as e:
            print(
                "Exception when calling CustomObjectsApi->get_namespaced_custom_object: %s\n"
                % e)
            sys.exit(1)

        new_res = old_res
        new_res["spec"]["tcp"] = route
        try:
            old_res = self.CustomV1.patch_namespaced_custom_object(
                name=svc,
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
                body=new_res,
            )
        except ApiException as e:
            print(
                "Exception when calling CustomObjectsApi->patch_namespaced_custom_object: %s\n"
                % e)
            sys.exit(1)


#k8s_controller().delete_deployment("backend-dir-v2")
#k8s_controller().read_pod_status()
