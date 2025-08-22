A simple FastAPI application to manage supermarket products and sales, with Prometheus metrics exposed at `/metrics`. Includes unit tests (pytest), Dockerfile, Kubernetes manifests, and a GitHub Actions CI/CD pipeline that:

1. Builds & tests the app
2. Builds and pushes a Docker image to Docker Hub
3. Deploys to DigitalOcean Kubernetes (DOKS)
4. Installs Prometheus + Grafana (kube-prometheus-stack) and sets up a ServiceMonitor for the app

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API.

## API Overview
- `POST /products` – create a product `{name, price}`
- `GET /products` – list products
- `POST /sales` – create a sale `{product_id, quantity}`
- `GET /sales` – list sales
- `GET /reports/daily?d=YYYY-MM-DD` – revenue and items sold for a day
- `GET /metrics` – Prometheus metrics
- `GET /healthz` – liveness/readiness

## Running tests
```bash
pytest -q
```

## Docker
```bash
docker build -t <user>/supermarket-api:local .
docker run -p 8000:8000 <user>/supermarket-api:local
```

## Kubernetes (manually)
Assuming you have `kubectl` wired to your cluster:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
# kubectl apply -f k8s/ingress.yaml  # if using Ingress
```

## Grafana & Prometheus
The CI installs `kube-prometheus-stack` (Prometheus + Grafana) into a `monitoring` namespace and exposes Grafana via a LoadBalancer. After deployment, check the service:
```bash
kubectl -n monitoring get svc grafana
```
Use admin user `admin` and the password set in `GRAFANA_ADMIN_PASSWORD` (GitHub secret). Add a Prometheus data source pointing at the in-cluster Prometheus (usually pre-provisioned by the chart). The provided `ServiceMonitor` will let Prometheus scrape the app's `/metrics` endpoint.

## GitHub Actions – required secrets
Add these repository secrets:

- `DOCKERHUB_USERNAME` – your Docker Hub username
- `DOCKERHUB_TOKEN` – a Docker Hub access token
- `DO_API_TOKEN` – DigitalOcean API token with read/write on Kubernetes
- `KUBE_CLUSTER_NAME` – your DOKS cluster name
- `GRAFANA_ADMIN_PASSWORD` – password to set for Grafana admin user

> Optional: if your DOKS cluster is in a team, make sure the token has access.

Once merged to `main`, CI will:
- run tests
- publish Docker image as `${DOCKERHUB_USERNAME}/supermarket-api:latest` and `:<short-sha>`
- deploy to Kubernetes
- install Grafana + Prometheus
- register a ServiceMonitor to scrape `/metrics`

## Notes
- The sample uses SQLite with an `emptyDir` volume. For production, swap to a managed database and use a `Secret` for credentials.
- The Service is type `LoadBalancer` to get a public IP on DOKS. You can switch to Ingress if you run an ingress controller.
- The app includes Prometheus counters/histograms and a `/metrics` endpoint compatible with Grafana dashboards via Prometheus.
