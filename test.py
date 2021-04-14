import sys
sys.path.append("..")
import k8skit


svc = "backend-game"
print k8skit.get_replicas(svc)
