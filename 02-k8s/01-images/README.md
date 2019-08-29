# Images used by k8s deployment
Custom docker images are created and pushed on private registry

## Minikue ##
Follow post [Sharing a local registry with minikube](https://blog.hasura.io/sharing-a-local-registry-for-minikube-37c7240d0615/)
1. Create a registry on minikube
```
kubectl create -f kube-registry.yaml
```
2. Map the host port 5000 to minikube registry pod
```
kubectl port-forward --namespace kube-system $(kubectl get po -n kube-system | grep kube-registry-v0 | \awk '{print $1;}') 5000:5000
```
3. Build image (in opendnssec folder for instance)
```
docker build -t signer:1.0 .
```
4. Tag image
```
docker image tag  signer:1.0 localhost:5000/signer:1.0
```

5. Push to registry
```
docker image push localhost:5000/signer:1.0
```


## Production ##
Create private registry following official docker [registry](https://docs.docker.com/registry/deploying/)[configuration](https://docs.docker.com/registry/configuration/) or [harbor](https://goharbor.io/) documentation. Create [imagePullSecrets](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/) in k8s. If required follow instruction in this [post](https://blog.cloudhelix.io/using-a-private-docker-registry-with-kubernetes-f8d5f6b8f646?gi=cbdd0e08812b).

Follow steps `3` to `5`. Make sure to change `localhost:5000` with the private registry IP/domain and port.
