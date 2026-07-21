# Hermes observability (Phase 1 on 36 GB Mac)

Prometheus + Grafana + Ollama VRAM exporter — promoted from Phase 2 for M3 Max / 36 GB unified memory.

**RAM footprint:** ~600–800 MB (Prometheus + Grafana) + negligible exporter. Safe alongside Option A (1 hot Ollama model).

## Quick start

```bash
# All observability (Docker + host exporter)
~/clawd/Hermes_Switch/stackctl.sh start observability

# Or manually
cd observability
docker compose up -d
./run_ollama_exporter.sh
```

| Service | URL | Notes |
|---------|-----|-------|
| Grafana | http://127.0.0.1:3000 | admin / admin — import `grafana/hermes-stack-overview.json` |
| Prometheus | http://127.0.0.1:9090 | Scrapes router, LiteLLM, Ollama VRAM |
| Ollama exporter | http://127.0.0.1:9101/metrics | Host process, started by stackctl |

## Scrape targets

Configured in [`prometheus.yml`](prometheus.yml):

| Job | Target | Metrics |
|-----|--------|---------|
| `hermes-router` | `host.docker.internal:3999/metrics` | Request counts, latency |
| `litellm` | `host.docker.internal:4000/metrics/` | TTFT, P50–P99, ITL histograms |
| `ollama-vram` | `host.docker.internal:9101/metrics` | VRAM, models loaded |
| `ollama-inference` | `host.docker.internal:9102/metrics` | Prefill, decode, TTFT, ITL |
| `prometheus` | self | Self-monitoring |

## LLM latency dashboard (Phase A)

Grafana: http://127.0.0.1:3000/d/hermes-llm-latency/hermes-llm-latency

Panels: TTFT P50–P99, end-to-end latency, ITL, tokens/sec (LiteLLM) + prefill/decode/ITL (Ollama proxy).

## Ollama inference proxy (Phase B)

```
LiteLLM :4000 → proxy :11435 → Ollama :11434
                      ↓
              metrics :9102/metrics
```

- Configured in `LiteLLM/litellm_config.yaml` (`api_base: http://127.0.0.1:11435`)
- Jupyter-learning / `ollama` CLI stay on **:11434** direct
- Start: `~/clawd/observability/run_ollama_inference_proxy.sh`

Metrics exposed:
- `ollama_prefill_seconds` — prompt eval (prefill)
- `ollama_decode_seconds` — token generation (decode)
- `ollama_ttft_seconds` — first streamed token
- `ollama_itl_seconds` — inter-token latency

Restart LiteLLM after first enable of `LITELLM_ENABLE_PROMETHEUS=true`:

```bash
~/clawd/Hermes_Switch/stackctl.sh restart litellm
```

## VRAM alert threshold (36 GB)

Default `HERMES_VRAM_WARN_MODELS=2` — warn/alert when **3+** models loaded. Option A still keeps `OLLAMA_MAX_LOADED_MODELS=1` for Telegram.

## Verify data is flowing

```bash
~/clawd/observability/verify-observability.sh
```

**Prometheus** (Hermes only — NOT object_detection_working):
- Targets: http://127.0.0.1:9090/targets → jobs `hermes-router`, `litellm`, `ollama-vram`
- Query: http://127.0.0.1:9090/graph → `up{project="hermes"}` or `ollama_models_loaded`

**Grafana**:
- Dashboard: http://127.0.0.1:3000/d/hermes-stack-overview/hermes-stack-overview
- Folder: **Hermes Stack** (auto-provisioned from `grafana/provisioning/`)
- Datasource must be **Prometheus (Hermes)** with uid `prometheus`

If panels show "No data" after manual JSON import, the datasource UID was wrong. Fix:

```bash
~/clawd/observability/fix-grafana-datasource.sh
```

Do **not** import the old `grafana/hermes-stack-overview.json` manually — use the provisioned copy in `grafana/provisioning/dashboards/json/`.

## Project layout (clawd)

```
observability/
├── prometheus.yml              # Hermes scrape config (router, litellm, ollama)
├── docker-compose.yml          # hermes-prometheus + hermes-grafana
├── ollama_vram_exporter.py     # :9101 metrics
├── verify-observability.sh     # one-shot health check
└── grafana/provisioning/       # auto-loaded datasource + dashboard
```

- OTel Collector + Jaeger UI — see [`OTEL.md`](OTEL.md)
- Loki log aggregation
- Langfuse LLM session UI
