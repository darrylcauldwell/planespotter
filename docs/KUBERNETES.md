# Kubernetes Deployment Guide

## Overview

The Kubernetes manifests use Kustomize for configuration management. All resources are deployed to the `planespotter` namespace.

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured to access your cluster
- Container images available (see Building Images)

## Building Images

Build and tag images for your registry:

```bash
# Using GitHub Container Registry
REGISTRY=ghcr.io/your-username/planespotter

docker build -t $REGISTRY/db-install:latest ./db-install
docker build -t $REGISTRY/api-server:latest ./api-server
docker build -t $REGISTRY/frontend:latest ./frontend
docker build -t $REGISTRY/adsb-sync:latest ./adsb-sync

# Push images
docker push $REGISTRY/db-install:latest
docker push $REGISTRY/api-server:latest
docker push $REGISTRY/frontend:latest
docker push $REGISTRY/adsb-sync:latest
```

## Deployment

### Using Kustomize

```bash
# Preview what will be deployed
kubectl kustomize kubernetes/

# Deploy all resources
kubectl apply -k kubernetes/

# Check deployment status
kubectl get all -n planespotter
```

### Verifying Deployment

```bash
# Check pods are running
kubectl get pods -n planespotter

# Check services
kubectl get svc -n planespotter

# View logs
kubectl logs -n planespotter -l app=api-server
kubectl logs -n planespotter -l app=frontend
kubectl logs -n planespotter -l app=adsb-sync
```

## Manifest Structure

```
kubernetes/
├── kustomization.yaml      # Main Kustomize config
├── namespace.yaml          # planespotter namespace
├── database/
│   ├── deployment.yaml     # PostgreSQL StatefulSet
│   ├── service.yaml        # ClusterIP service
│   ├── configmap.yaml      # Database config
│   └── pvc.yaml            # Persistent volume claim
├── cache/
│   ├── deployment.yaml     # Valkey deployment
│   └── service.yaml        # ClusterIP service
├── api-server/
│   ├── deployment.yaml     # API server deployment
│   ├── service.yaml        # ClusterIP service
│   └── configmap.yaml      # Environment config
├── frontend/
│   ├── deployment.yaml     # Frontend deployment
│   ├── service.yaml        # LoadBalancer/NodePort
│   └── configmap.yaml      # Environment config
└── adsb-sync/
    ├── deployment.yaml     # Sync service deployment
    └── configmap.yaml      # Sync configuration
```

## Configuration

### Updating Image References

Edit `kubernetes/kustomization.yaml` to set your registry:

```yaml
images:
  - name: planespotter-db
    newName: ghcr.io/your-username/planespotter/db-install
    newTag: latest
  - name: planespotter-api
    newName: ghcr.io/your-username/planespotter/api-server
    newTag: latest
  - name: planespotter-frontend
    newName: ghcr.io/your-username/planespotter/frontend
    newTag: latest
  - name: planespotter-adsb-sync
    newName: ghcr.io/your-username/planespotter/adsb-sync
    newTag: latest
```

### Environment Variables

Configuration is managed via ConfigMaps. Edit the configmap.yaml in each service folder to adjust settings.

## Accessing the Application

### Port Forward (Development)

```bash
# Frontend
kubectl port-forward -n planespotter svc/frontend 8080:8080

# API Server (for debugging)
kubectl port-forward -n planespotter svc/api-server 8000:8000
```

### LoadBalancer (Cloud)

If your cluster supports LoadBalancer services:

```bash
kubectl get svc -n planespotter frontend
# Note the EXTERNAL-IP
```

### Ingress (Production)

For production, configure an Ingress resource:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: planespotter
  namespace: planespotter
spec:
  rules:
    - host: planespotter.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 8080
```

## Health Checks

All deployments include health checks:

- **Liveness Probe**: `/health` - Restarts pod if unhealthy
- **Readiness Probe**: `/health/ready` - Removes from service if not ready

## Scaling

```bash
# Scale API server
kubectl scale deployment api-server -n planespotter --replicas=3

# Scale frontend
kubectl scale deployment frontend -n planespotter --replicas=2
```

Note: PostgreSQL and Valkey are single-replica by default. For high availability, consider using managed services or operators.

## Cleanup

```bash
# Delete all resources
kubectl delete -k kubernetes/

# Or delete namespace (removes everything)
kubectl delete namespace planespotter
```

## Network Policies

For micro-segmentation demos, you can add NetworkPolicy resources to restrict traffic between services. Example:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-server-policy
  namespace: planespotter
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: valkey
      ports:
        - port: 6379
```
