# local-vllm-docker (Linux, NVIDIA GPU)

> Not yet verified live: written from vLLM's documentation. Remove this line
> once a Linux machine with an NVIDIA GPU has run config, serve and destroy.

## Prerequisites and install

- `docker info` succeeds. Install: https://docs.docker.com/engine/install/
- GPU access: `docker run --rm --gpus all ubuntu nvidia-smi` succeeds. Install the NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
- `curl --version` succeeds.

## Config fields

- `port` - default `8000`.
- `image` - optional; default `vllm/vllm-openai:v0.30.0`.

## Prepare

None.

## Serve

1. Already served: `docker ps -a --filter name=^vot-<preset>$ --format '{{.Names}}'` prints a name -> unit exists.
2. Port taken: `lsof -iTCP:<port> -sTCP:LISTEN` prints a line -> refuse, naming the port.

Start (the image's entrypoint is `vllm serve`, so the arguments start with the model):

```bash
docker run -d --name vot-<preset> --gpus all --ipc=host \
  -p 127.0.0.1:<port>:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  [-e HF_TOKEN] [-e OTEL_SERVICE_NAME=vot-<preset> -e OTEL_RESOURCE_ATTRIBUTES='<resource attributes>'] [-e OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf] \
  <image> <model> --served-model-name <served name> <vllm args>
```

Base URL: `http://127.0.0.1:<port>`.

## Ready when

`curl -sf http://127.0.0.1:<port>/v1/models` lists `<served name>`; poll every
10 s for up to 15 min. On timeout or exit: `docker logs --tail 50 vot-<preset>`.

## Destroy

```bash
docker rm -f vot-<preset>
```

`No such container`: report that the unit does not exist.

## Traps

- An `otlp_endpoint` on `localhost` means the container itself: use
  `host.docker.internal` (with `--add-host=host.docker.internal:host-gateway`) to reach the host.
- `-e HF_TOKEN` (no value) passes the shell's variable by name.
