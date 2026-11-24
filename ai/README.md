# Planespotter with AI on VKS

This overlay deploys Planespotter with its two AI features, Ask Planespotter and the aircraft
descriptions, to a VKS cluster. Everything runs on processor cores, with no GPU:

| Piece | What it is |
|---|---|
| `images.yaml` | kpack Images that build the api-server, frontend and adsb-sync from the `ai` branch with Cloud Native Buildpacks, into `ghcr.io/darrylcauldwell/planespotter-ai/*` |
| `llm.yaml` | llama.cpp's server running Qwen3 4B, answering the OpenAI API at `http://llm:8080/v1` |
| `fetch-model.sh` | The init container that fetches the model file from Docker Hub once and checks its digest |
| `kustomization.yaml` | Everything above plus the upstream manifests, in namespace `planespotter-ai` |

Nothing in the application is specific to VKS. The api-server only knows `LLM_BASE_URL`, so the
same images run against llama.cpp on a laptop, this overlay, Private AI Services or OpenAI.

## What the cluster needs

The buildpacks deployment's setup provides most of it:

- kpack with the `python-node` ClusterBuilder, and the package mirror at `packages.mirror.svc`
- A node pool whose VM class gives a node at least 4 vCPU and 8 GiB. `best-effort-medium`
  (2 vCPU) is too small for the model server, whose pod requests 4 cores and 6 GiB
- The storage class `vsan-default-storage-policy`
- Outbound HTTPS to `ghcr.io`, `github.com`, Docker Hub (`auth.docker.io`, `registry-1.docker.io`
  and the CDN it redirects to) and `opensky-network.org`

## Deploy

kpack builds from GitHub, so the `ai` branch must be pushed first.

```bash
kubectl apply -k ai/
kubectl -n planespotter-ai create secret docker-registry ghcr \
  --docker-server=ghcr.io --docker-username=darrylcauldwell --docker-password="$GHCR_TOKEN"
```

The registry Secret stays out of git. kpack pushes the images with it and the pods pull with it.

Then watch the builds and the model server:

```bash
kubectl -n planespotter-ai get images                      # kpack builds, READY True when pushed
kubectl -n planespotter-ai logs statefulset/llm -c fetch-model -f
kubectl -n planespotter-ai rollout status statefulset/llm
```

The first start fetches the 2.5 GB model; later starts find it on the volume.

## Open it

The lab has no LoadBalancer address to spare, so the frontend is a ClusterIP Service:

```bash
kubectl -n planespotter-ai port-forward svc/frontend 8080:80
```

Then browse to http://localhost:8080/search.

Before an audience, ask one question first. The first request makes the model read its
instructions and examples, which takes several times longer than every request after it.

## Upgrade

Push to the `ai` branch. kpack rebuilds the changed images under `:latest`, then restart the
Deployments to pull them:

```bash
kubectl -n planespotter-ai rollout restart deployment api-server frontend adsb-sync
```

## Change the model or where it runs

- **Another model.** Change `MODEL_REPOSITORY` and `MODEL_DIGEST` in `llm.yaml` to another GGUF
  layer on Docker Hub's `ai/` namespace, and `--alias` to its name. The digest is the layer's,
  from the tag's manifest.
- **Another server.** Set `LLM_BASE_URL` in the api-server ConfigMap to any OpenAI-compatible
  endpoint, such as a Private AI Services model endpoint, put its token in `LLM_API_KEY` from a
  Secret, and scale `statefulset/llm` to zero. The application does not change.
