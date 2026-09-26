# local-vllm (Linux, NVIDIA GPU)

> Not yet verified live: written from vLLM's documentation. Remove this line
> once a Linux machine with an NVIDIA GPU has run config, serve and destroy.

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
[OTEL_SERVICE_NAME=vot-<preset>] [OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf] \
nohup vllm serve <model> --host 127.0.0.1 --port <port> --served-model-name <served name> <vllm args> \
  > .vot/run/vot-<preset>.log 2>&1 &
echo $! > .vot/run/vot-<preset>.pid
```

Base URL: `http://127.0.0.1:<port>`.

## Ready when

`curl -sf http://127.0.0.1:<port>/v1/models` lists `<served name>`; poll every
10 s for up to 15 min (the first run downloads the weights). On timeout or
when the PID dies: `tail -n 50 .vot/run/vot-<preset>.log`.

## Destroy

```bash
kill "$(cat .vot/run/vot-<preset>.pid)"; sleep 5; kill -9 "$(cat .vot/run/vot-<preset>.pid)" 2>/dev/null
rm -f .vot/run/vot-<preset>.pid .vot/run/vot-<preset>.log .vot/run/<preset>.yaml
```

No PID file: report that the unit does not exist.

## Traps

- The weights land in `~/.cache/huggingface`; a destroy keeps them.
- `nohup` output goes to the log file only; read it on failure, never assume.
