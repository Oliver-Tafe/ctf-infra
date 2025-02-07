# CTF Infrastructure

This is my template infrastructure for Capture the Flag competitions.

## Challenges

The challenges are managed using [ctftool](https://github.com/jedevc/mini-ctf-tool/),
a home-grown tool for managing challenge metadata and information. See the
GitHub page for more documentation on the exact formats allowed.

Essentially, all challenges are placed into the `challenges/` directory, and
should contain either a `challenge.yaml` or `challenge.json` file.

Useful ctftool commands used in development include:

- Listing:
  ```
  $ ./ctftool.py list
  ```
- Validation:
  ```
  $ ./ctftool.py validate
  ```

## Deployment

Deploying the CTF should be fairly simple once setup, but can be a little involved.

There are three options:

- Docker (not recommended)
- Docker Compose
- Kubernetes

For all of them, you'll need to point your DNS records in the right place.
It's recommended that if your challenges ues HTTP servers, you should access
your challenges over a different domain name than the CTFd instance -
otherwise, browsers will try and be "clever" and upgrade you to HTTPS for
your challenges

### Docker

The docker build steps contain basic primitives for building challenge images
and containers. They probably shouldn't be used on their own, and are
intended to be used in conjunction with either docker-compose or kubernetes.

Build the challenge images:

    $ ./ctftool.py build docker

Build and push challenge images to a private registry:

    $ export IMAGE_REPO=...
    $ ./ctftool.py build docker --push


The built docker containers can be started by running the generated deploy script

    $ ./deploy.sh


The next steps assume that you have configured your machines to automatically
pull from this private registry.

### Docker Compose

Deploying using docker-compose is a more lightweight alternative to building
and maintaining an entire cluster. However, it will definitely be less
flexible, so keep that in mind when making a decision.

Build the build step for the infrastructure:

    $ ./ctftool.py build docker-compose

Launch it!

    $ docker-compose up

### Kubernetes

To deploy using Kubernetes, you first need a cluster. Then, once you've
installed the dependencies (listed below), you can install the entire infra.

Export required environment variables (see `.env.sample` for more info):

    $ export DOMAIN=ctfd.example.com
    $ export CTFD_MYSQL_DB=ctfd
    $ export CTFD_MYSQL_USER=ctfd
    $ export CTFD_MYSQL_PASSWORD=password
    $ export CTFD_REDIS_PASSWORD=password
    $ export CTFD_SECRET=ctfd

#### Install dependencies

##### Ingress

You need to install [Nginx Ingress](https://kubernetes.github.io/ingress-nginx/).

The following installs it *without* a LoadBalancer service, for lower costs.

    $ helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    $ helm repo update
    $ kubectl create namespace ingress-nginx
    $ helm install ingress ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --set controller.hostNetwork=true \
        --set controller.kind=DaemonSet \
        --set controller.hostPort.enabled=true \
        --set controller.service.enabled=false \
        --set controller.publishService.enabled=false

##### Cert Manager

To handle TLS certificates, we use [Cert Manager](https://cert-manager.io).

**NOTE**: Make sure that your DNS records are pointing to the right place!

First we install it:

    $ helm repo add jetstack https://charts.jetstack.io
    $ helm repo update
    $ kubectl create namespace cert-manager
    $ helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version v1.0.3 \
        --set installCRDs=true

Then we need to setup a couple LetsEncrypt issuers (one for staging, one for
production):

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: letsencrypt@example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1alpha2
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: letsencrypt@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

When you setup the ClusterIssuers, the CTFd instance should automatically be
given a TLS certificate.

#### Build

Copy the infrastructure code to a build directory:

    $ mkdir -p build
    $ cp -R deploy/kube/ build/

Build the build step for the infrastructure:

    $ ./build/kube/generate.sh

Apply the infrastructure to the cluster:
  
    $ kubectl apply -k build/kube/

#### Notes

- The kubernetes infra uses NodePort to expose services ports to the
  internet. By default this range is 30000-32767, but it's often nice to
  expose ports lower than that.

  You can modify this range by modifying `apiserver.service-port-range`. For
  kubeadm, edit `/etc/kubernetes/manifests/kube-apiserver.yaml` and add
  `--service-node-port-range=<lower>-<upper>` to `spec.containers.command`.
