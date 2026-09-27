# local-vllm (Linux, NVIDIA GPU)

> Not yet verified live on Linux: written from vLLM's documentation. Its
> *Serve*, *Ready when* and *Destroy* commands are verified through
> local-vllm-metal (2026-09-26). Remove this line once a Linux machine with an
> NVIDIA GPU has run config, serve and destroy.

## Prerequisites and install

- `nvidia-smi` succeeds (an NVIDIA driver is installed) - not installable here; the user's.
- `vllm --version` succeeds. Install: `uv tool install vllm` (or `pip install vllm`).
- `curl --version` succeeds.

## Config fields

- `port` - default `8000`.

## Prepare

None.

## Serve

1. Already served: `test -f .vot/run/vot-<preset>.pid && kill -0 "$(cat .vot/run/vot-<preset>.pid)"` succeeds -> unit exists.
2. Port taken: `lsof -iTCP:<port> -sTCP:LISTEN` prints a line -> refuse, naming the port.

Start:

```bash
mkdir -p .vot/run
[OTEL_SERVICE_NAME=vot-<preset> OTEL_RESOURCE_ATTRIBUTES='<resource attributes>'] [OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf] \
nohup vllm serve <model> --host 127.0.0.1 --port <port> --served-model-name <served name> <vllm args> \
  > .vot/run/vot-<preset>.log 2>&1 &
echo $! > .vot/run/vot-<preset>.pid
```

Base URL: `http://127.0.0.1:<port>`.

## Ready when

`curl -sf http://127.0.0.1:<port>/v1/models` lists `<served name>`, up to 15 min
(the first run downloads the weights). One bounded call (about 5 min), repeated
until ready, the PID dies, or 15 min pass:

```bash
PID="$(cat .vot/run/vot-<preset>.pid)"
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:<port>/v1/models | grep -q '"<served name>"' && { echo READY; break; }
  kill -0 "$PID" 2>/dev/null || { echo DIED; break; }
  sleep 10
done
```

On `DIED` or timeout: `tail -n 50 .vot/run/vot-<preset>.log`.

## Destroy

```bash
PID="$(cat .vot/run/vot-<preset>.pid)"
kill -0 "$PID" 2>/dev/null && kill "$PID"   # a crashed serve leaves a dead PID: never signal a reused number
for i in $(seq 1 30); do kill -0 "$PID" 2>/dev/null || break; sleep 2; done
kill -0 "$PID" 2>/dev/null && { pkill -9 -P "$PID"; kill -9 "$PID"; }
pgrep -f "vllm serve" && echo "leftover vllm serve process(es) - report them"
rm -f .vot/run/vot-<preset>.pid .vot/run/vot-<preset>.log .vot/run/<preset>.yaml
```

No PID file: report that the unit does not exist.

## Traps

- The weights land in `~/.cache/huggingface`; a destroy keeps them.
- `nohup` output goes to the log file only; read it on failure, never assume.
