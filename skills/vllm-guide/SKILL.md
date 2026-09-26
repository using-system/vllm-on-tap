---
name: vllm-guide
description: vLLM capabilities a vllm-on-tap preset or serve needs - the serve flags, tracing over OTLP, the API key, the OpenAI-compatible API and tuning for a GPU - each linked to vLLM's documentation. Read when writing or adjusting a preset, or when a serve adds tracing or an API key.
---

# vllm-guide

Documentation root: https://docs.vllm.ai/en/latest/

## Serve flags

- `vllm serve <model>` - the model is the positional argument; the
  `vllm/vllm-openai` image's entrypoint is already `vllm serve`, so a
  container's arguments start with the model.
- `--host 127.0.0.1 --port <port>` - bind address and port (default port 8000).
- `--served-model-name <name>` - the name clients send as `model`.
- `--max-model-len <tokens>` - context length; lower it when the KV cache does not fit.
- `--gpu-memory-utilization <0..1>` - share of GPU memory vLLM takes (default 0.9).
- `--dtype float16|bfloat16|auto` - T4 (compute capability 7.5) has no bf16: vLLM falls back to fp16 there.
- `--tensor-parallel-size <n>` - split over n GPUs; ACA serverless has one GPU per replica, so 1.
- `--quantization <method>` - usually inferred from the checkpoint (compressed-tensors w4a16 needs compute capability >= 7.5).
- Reference: https://docs.vllm.ai/en/latest/cli/serve.html

## Traces over OTLP

- `--otlp-traces-endpoint <url>` - vLLM exports one span per request over OTLP.
- Protocol: gRPC by default; set `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf`
  when the endpoint is OTLP/HTTP (port 4318, or a URL ending in `/v1/traces`).
- OTLP/HTTP: vLLM hands the flag's value to the exporter verbatim, with no
  path appended - the value must be the full URL ending in `/v1/traces`
  (`http://host:4318` alone posts to `/` and the traces are lost). gRPC
  takes `host:port` or `http(s)://host:port` with no path.
- `OTEL_SERVICE_NAME=vot-<preset>` names the service the spans belong to.
- Metrics have no OTLP export (Prometheus `/metrics` only); vllm-on-tap exports traces only.
- The OpenTelemetry packages are part of vLLM's base requirements; an install
  that reports them missing is repaired with `pip install 'vllm[otel]'`.
- Reference: https://docs.vllm.ai/en/latest/examples/online_serving/opentelemetry.html

## API key

- When `VLLM_API_KEY` is set in its environment (or `--api-key <key>` is
  passed), vLLM requires `Authorization: Bearer <key>` on the `/v1`, `/v2`,
  `/inference` and `/cohere` routes only. Other routes - `/invocations`
  (full inference), `/tokenize`, `/pause`, `/abort_requests`,
  `/update_weights` - stay open (vLLM docs, "API Key Authentication
  Limitations"): a public endpoint also needs a network restriction.
- Prefer the environment variable so the key never appears in a command line.
- Reference: https://docs.vllm.ai/en/latest/usage/security.html

## OpenAI API

- `GET /v1/models` - lists the served name; the readiness check.
- `POST /v1/chat/completions` - chat:

```bash
curl -s <base url>/v1/chat/completions -H 'Content-Type: application/json' \
  [-H "Authorization: Bearer $VOT_API_KEY"] \
  -d '{"model":"<served name>","messages":[{"role":"user","content":"Say hello in one sentence."}],"max_tokens":64}'
```

- Reference: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

## Tuning

- Out of memory at start: lower `--max-model-len`, then `--gpu-memory-utilization`.
- Weights size ~ parameters x bytes per weight (4-bit ~ 0.5 byte, bf16 2 bytes);
  `gpu_memory_gb` must hold the weights plus the KV cache.
