# Planespotter with AI on VCF

This overlay deploys Planespotter to a VKS cluster and connects it to two VCF services instead of
running its own: a Private AI Services model endpoint answers Ask Planespotter and writes the
aircraft descriptions, and a Data Services Manager PostgreSQL holds the aircraft data. Everything
runs on processor cores, with no GPU.

| Piece | Where it runs | What it is |
|---|---|---|
| frontend, api-server, adsb-sync, Valkey | this VKS namespace, `planespotter-ai` | the app, from `../kubernetes` |
| `db-seed.yaml` | this namespace, once | a Job that loads the OpenSky aircraft data into the database |
| the database | Data Services Manager | PostgreSQL 17: a `PostgresCluster` in a Supervisor namespace |
| the model | Private AI Services | Qwen3 4B on the llama.cpp engine: a `ModelEndpoint` in a Supervisor namespace |

Nothing in the application is specific to VCF. The api-server knows a database host and a model
URL, so the same images run against docker-compose's Postgres and llama.cpp on a laptop.

## What it needs

- A VKS cluster. The app's pods are small; the model runs in Private AI Services, not here.
- Outbound HTTPS from the cluster to `ghcr.io` and `opensky-network.org`.
- From the cluster's pods, the database's address on port 5432 and the Private AI Services
  address on 443. With DSM's network isolation on, a database admits only its organization's
  SNAT address and DSM's own, so any other source needs an Extra Clients entry.
- In a Supervisor namespace, through VCF Automation's Cloud Consumption Interface:
  - a DSM `PostgresCluster` at version 17 with `databaseName: planespotter`, keeping the
    default admin user, `pgadmin`
  - a Private AI Services `ModelEndpoint` with engine `LlamaCPP` and routing name `qwen3-4b`,
    serving the Qwen3 4B GGUF that docker-compose fetches (`ai/qwen3` at the digest in
    `docker-compose.yaml`) after `vcf pais models push` has put it in the model gallery. Give
    llama.cpp `--reasoning off` among its arguments: Qwen3 otherwise thinks aloud before every
    answer. docker-compose also passes `--ctx-size 8192 --parallel 2`.

## Build the images

Each service builds from its Dockerfile. The lab's nodes are x86, so build for `linux/amd64`:

```bash
for service in api-server frontend adsb-sync db-install; do
  docker buildx build --platform linux/amd64 --push \
    -t ghcr.io/darrylcauldwell/planespotter-ai/$service:latest ./$service
done
```

Make the four packages public on GitHub, and the cluster pulls them without a registry Secret.

## Point it at the services

Two values in [services.yaml](services.yaml) exist only once the services are provisioned:

- `DATABASE_HOST`: the database's address, from the `PostgresCluster`'s status
- `LLM_BASE_URL`: `https://<Private AI Services address>/api/v1/compatibility/openai/v1`

Fill them in and commit them. The credentials stay out of git.

**From the database.** In the Supervisor namespace that holds it:

```bash
kubectl get postgrescluster planespotter -o jsonpath='{.status.connection}'   # host, port, passwordRef
kubectl get secret <passwordRef> -o jsonpath='{.data.password}' | base64 -d > db-password
kubectl get secret <passwordRef> -o jsonpath='{.data.ca\.crt}' | base64 -d > db-ca.crt
openssl x509 -in db-ca.crt -noout -ext keyUsage
```

The last line must print a key usage. Python 3.13 refuses a CA certificate without one, although
`psql` accepts it, so the seed Job would load the data and the api-server would still fail to
connect.

**From Private AI Services.** Put an API token in `pais-token`: a local account's `pais-sc-…`
token, or a VCF Automation API token. Put the CA certificate that signed the Private AI Services
address's certificate in `pais-ca.crt`; `openssl s_client -connect <address>:443 -showcerts`
shows the chain.

## Deploy

```bash
kubectl apply -k ai/
kubectl -n planespotter-ai create secret generic planespotter-db \
  --from-file=password=db-password --from-file=ca.crt=db-ca.crt
kubectl -n planespotter-ai create secret generic pais \
  --from-file=token=pais-token --from-file=ca.crt=pais-ca.crt
rm db-password pais-token
```

The api-server and the seed Job wait for their Secrets and start once both exist. Then:

```bash
kubectl -n planespotter-ai logs job/db-seed -f    # "Import complete!" after the data load
kubectl -n planespotter-ai get pods
```

## Open it

The lab has no LoadBalancer address to spare, so the frontend is a ClusterIP Service:

```bash
kubectl -n planespotter-ai port-forward svc/frontend 8080:80
```

Then browse to http://localhost:8080/search.

Before an audience, ask one question first. The first request makes the model read its
instructions and examples, which takes several times longer than every request after it.

## Upgrade

Build and push again, then restart the Deployments to pull the new `:latest`:

```bash
kubectl -n planespotter-ai rollout restart deployment api-server frontend adsb-sync
```

## Change the model or where it runs

- **Another model.** Create another `ModelEndpoint` and set `LLM_MODEL` in `services.yaml` to its
  routing name. Private AI Services does not let an existing endpoint's fields change, so a new
  llama.cpp argument also means a new endpoint.
- **Another server.** Set `LLM_BASE_URL` to any OpenAI-compatible endpoint and give the `pais`
  Secret its token and CA. The application does not change.
