# local-vllm-metal (macOS, Apple Silicon)

## Prerequisites and install

- macOS 15 or later on Apple Silicon: `sw_vers -productVersion` >= 15 and `uname -m` = `arm64`. Not installable here.
- `vllm --version` succeeds with the vllm-metal plugin. Install: `brew tap vllm-project/vllm-metal https://github.com/vllm-project/vllm-metal && brew install vllm-project/vllm-metal/vllm-metal` (the tap is not a `homebrew-*` repository, so it needs its URL).
- `curl --version` succeeds.

## Config fields

- `port` - default `8000`.

## Prepare

None.

## Serve

Read local-vllm.md's *Serve* section only (not its banner or its
*Prerequisites and install*): same checks, same command, same `.vot/run/`
files, with the preset's `local-vllm-metal` model - MLX weights
(`mlx-community/...`); vllm-metal does not load compressed-tensors checkpoints.

## Ready when

Read local-vllm.md's *Ready when* section only, up to 15 min.

## Destroy

Read local-vllm.md's *Destroy* section only.

## Traps

- Unified memory is shared with the system: `gpu_memory_gb` compares with
  `sysctl -n hw.memsize` / 1e9, leaving ~8 GB to macOS; warn when tighter.
- Supported models: https://github.com/vllm-project/vllm-metal/blob/main/docs/supported_models.md
- `--dtype` and CUDA-only flags (`--tensor-parallel-size` > 1) do not apply.
