# OpenTelemetry trace propagation (Phase 2)

Cross-layer correlation: **Gateway → Router → LiteLLM → Ollama**

## What is implemented

| Layer | Trace support |
|-------|---------------|
| **Router :3999** | Accepts `traceparent` + `X-Request-ID`; forwards to LiteLLM; writes `trace_id` to `decisions.jsonl` |
| **LiteLLM :4000** | Receives propagated `traceparent` (pass-through headers) |
| **Hermes Gateway** | Pass `traceparent` / `X-Request-ID` on OpenAI client if supported (see below) |
| **Collector (optional)** | Jaeger/OTel Collector — not deployed by default |

Implementation: [`trace_context.py`](trace_context.py) (W3C Trace Context, no heavy SDK).

## Header flow

```
Telegram → Gateway
              │  traceparent: 00-{trace_id}-{span_id}-01
              │  X-Request-ID: {uuid}
              ▼
         Router :3999
              │  new child span in traceparent
              │  append decisions.jsonl
              ▼
         LiteLLM :4000
              │  (optional OTEL_EXPORTER if enabled)
              ▼
         Ollama :11434
```

## Gateway configuration

If Hermes agent uses a custom OpenAI base URL pointing at the router (`http://127.0.0.1:3999`), ensure outbound requests include:

```yaml
# ~/.hermes/config.yaml (when supported)
openai:
  extra_headers:
    X-Request-ID: auto   # or let router generate
```

Until Gateway natively propagates traces, the router **generates** `traceparent` when missing. Correlation still works via `X-Request-ID` and `decisions.jsonl`.

## LiteLLM OpenTelemetry (optional)

LiteLLM supports OTel when env vars are set. Add to LiteLLM launchd or `.env`:

```bash
OTEL_EXPORTER=otlp
OTEL_ENDPOINT=http://127.0.0.1:4317
OTEL_SERVICE_NAME=hermes-litellm
```

Deploy an OTel Collector (future):

```yaml
# observability/docker-compose.yml — add when needed
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.109.0
    ports:
      - "4317:4317"
      - "4318:4318"
```

## Querying traces locally (Phase 1)

```bash
# Last routing decisions with trace ids
tail -5 ~/.hermes/logs/decisions.jsonl | python3 -m json.tool

# Match router log line by request_id
grep "request_id=YOUR-UUID" ~/.hermes/logs/router-launchd.error.log
```

## Jaeger (optional Phase 2+)

```bash
docker run -d --name jaeger \
  -p 16686:16686 -p 4317:4317 \
  jaegertracing/all-in-one:1.57
```

Point LiteLLM `OTEL_ENDPOINT` at `http://127.0.0.1:4317`.

## Related

- [`docs/OBSERVABILITY_EXPLAINABILITY.md`](../docs/OBSERVABILITY_EXPLAINABILITY.md)
- [`stack_observe.py`](stack_observe.py) — reads `decisions.jsonl`
- Router `/metrics` — Prometheus counters
