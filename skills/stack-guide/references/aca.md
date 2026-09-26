# aca (Azure Container Apps, serverless GPU)

## Prerequisites and install

- `az version` succeeds. Install: https://learn.microsoft.com/cli/azure/install-azure-cli (macOS: `brew install azure-cli`).
- `az account show` succeeds - otherwise the user runs `az login`; never run it for them.
- `az extension show --name containerapp` succeeds. Install: `az extension add --name containerapp --upgrade`.
- `az provider show --namespace Microsoft.App --query registrationState -o tsv` prints `Registered`. Install: `az provider register --namespace Microsoft.App --wait`.
- `jq --version` succeeds (to build the app spec below). Install: `brew install jq` / the distribution's package.
- `openssl version` succeeds (to generate the API key). Install: `brew install openssl` / the distribution's package.

## Config fields

- `subscription` - optional; absent means the subscription `az account show` reports (the logged-in default). Set it only to pin another one, by the name `az account list --query "[].name" -o tsv` prints. Leave it out of an environment committed to a public repository.
- `location` - a region with serverless A100 GPUs: `australiaeast`, `brazilsouth`, `canadacentral`, `eastus`, `italynorth`, `swedencentral`, `westus`, `westus3`.
- `resource_group` - default `rg-vot`.
- `environment` - the Container Apps environment; default `vot-env`.
- `image` - optional; default `vllm/vllm-openai:v0.30.0`.
- `storage` - optional; the name of a storage account in `<resource_group>` whose Azure Files share `vot-cache` is mounted in every app on `/vot-cache` (the Hugging Face and vLLM caches). Set by *Prepare*, never asked with the other fields. Absent means the weights download from Hugging Face and vLLM compiles at every start.

An `api_key_env` field from an earlier version is ignored, and dropped on the next write.

When `subscription` is set, every command below runs with `--subscription "<subscription>"`; otherwise without it.

## Prepare

Each step: reuse when it exists, create on the user's yes otherwise.

```bash
az group show --name <resource_group>
az group create --name <resource_group> --location <location>

az containerapp env show --name <environment> --resource-group <resource_group>
az containerapp env create --name <environment> --resource-group <resource_group> --location <location> --enable-workload-profiles --logs-destination none

az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv
az containerapp env workload-profile add --name <environment> --resource-group <resource_group> --workload-profile-name gpu-a100 --workload-profile-type Consumption-GPU-NC24-A100
```

A profile `add` refused for quota: tell the user to request "Managed
Environment Consumption NCA100 GPUs" on the environment's Quota page
(https://learn.microsoft.com/azure/container-apps/quota-requests), and save
the environment anyway.

Then the optional storage - not required, an environment serves
without it. Look in `<resource_group>` first: an account found is proposed
for reuse and its name saved on the user's yes; none found -> offer to
create one, saying what it brings and what it costs; a no to a found
account leads to the same offer. On a no to creating, leave the field out.

**Storage (`storage`)**: the Hugging Face cache (`HF_HOME`)
and vLLM's cache (`VLLM_CACHE_ROOT`, its torch.compile artifacts) live on
an Azure Files share mounted in the app, so a preset's second serve reads
its weights from the share instead of downloading them, and reuses its
compiled graphs. A Standard account with a Hot share bills the GB stored
(~0.03 USD per GB per month, so a few models cost a few USD) plus its
transactions (cents per serve); the quota is a ceiling, not a charge.
The first serve of a preset still downloads, and writes the share as it
goes.

```bash
az storage account list --resource-group <resource_group> --query "[?kind=='StorageV2' && largeFileSharesState=='Enabled'].name" -o tsv
az storage account create --name <storage> --resource-group <resource_group> --location <location> --sku Standard_LRS --kind StorageV2 --enable-large-file-share --min-tls-version TLS1_2 --allow-blob-public-access false

az storage share-rm show --storage-account <storage> --resource-group <resource_group> --name vot-cache
az storage share-rm create --storage-account <storage> --resource-group <resource_group> --name vot-cache --quota 1024 --access-tier Hot --enabled-protocols SMB

az containerapp env storage show --name <environment> --resource-group <resource_group> --storage-name vot-cache
```

`<storage>` on create: ask a name, globally unique, 3-24 lowercase
letters and digits (`az storage account check-name --name <storage>`).
More than one account found: ask which one. The environment storage
`vot-cache` is missing -> register it. An SMB mount needs the account key
(NFS would need a custom VNet), so the key goes through `az rest` with a
body `jq` builds from the environment - never through
`az containerapp env storage set --azure-file-account-key`, whose argument
`ps` shows:

```bash
ENV_ID="$(az containerapp env show --name <environment> --resource-group <resource_group> --query id -o tsv)"
SA_KEY="$(az storage account keys list --account-name <storage> --resource-group <resource_group> --query "[0].value" -o tsv)"
[ -n "$SA_KEY" ] || { echo "no storage account key" >&2; exit 1; }
export SA_KEY
az rest --method put --url "https://management.azure.com${ENV_ID}/storages/vot-cache?api-version=2024-03-01" \
  --body @<(jq -n --arg acct "<storage>" \
    '{properties: {azureFile: {accountName: $acct, accountKey: env.SA_KEY, shareName: "vot-cache", accessMode: "ReadWrite"}}}') \
  --query name -o tsv
```

All the lines above run in one shell command: split across calls, `SA_KEY`
is lost and the storage would register without a key.

## Serve

Checks, in this order, stopping at the first refusal:

1. The preset lists `HF_TOKEN` and `printenv HF_TOKEN` prints nothing -> refuse before any Azure call: export it in the shell the agent session is started from, then restart the session; never paste it into the conversation or a command.
2. Profile: always `gpu-a100` (cpu `24`, memory `220Gi`, one A100 80 GB); a preset with `gpu_memory_gb` > 80 -> refuse (no serverless profile fits).
3. The profile exists: `az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv` lists it; otherwise refuse and route to `/vot-config` (quota).
4. `storage` set: `az containerapp env storage show --name <environment> --resource-group <resource_group> --storage-name vot-cache` fails -> refuse and route to `/vot-config`.
5. Already served: `az containerapp show --name vot-<preset> --resource-group <resource_group>` succeeds -> unit exists.

Create. `az containerapp create --args` cannot carry vLLM's `--flags` (az
parses them as its own), so the app is created from a YAML spec, built with
`jq` and streamed through process substitution. The API key is generated in
the same command and exported to jq only; jq reads the secrets' values from
its environment (`env[...]`), never from its arguments, so they appear in
no file, in no process's command line, and never in the conversation. The
Container App secret `vllm-api-key` is the only place the key lives - see
*API key* below.

```bash
ENV_ID="$(az containerapp env show --name <environment> --resource-group <resource_group> --query id -o tsv)"
CALLER_IP="$(curl -fsS https://api.ipify.org)"
VOT_API_KEY="$(openssl rand -hex 32)"; [ -n "$VOT_API_KEY" ] || exit 1; export VOT_API_KEY
ARGS='["<model>","--served-model-name","<served name>","--port","8000", <vllm args as JSON strings>]'
ENVS='[{"name":"VLLM_API_KEY","secretRef":"vllm-api-key"}]'   # + {"name":"HF_TOKEN","secretRef":"hf-token"}, {"name":"OTEL_SERVICE_NAME","value":"vot-<preset>"}, {"name":"OTEL_EXPORTER_OTLP_TRACES_PROTOCOL","value":"http/protobuf"} when they apply
az containerapp create --name vot-<preset> --resource-group <resource_group> --yaml <(jq -n \
  --arg loc "<location>" --arg env "$ENV_ID" --arg wp "<profile>" --arg img "<image>" \
  --arg ip "$CALLER_IP/32" --argjson cpu <cpu> --arg mem "<memory>" \
  --argjson args "$ARGS" --argjson envs "$ENVS" \
  --argjson hf <true when the preset lists HF_TOKEN, else false> \
  --argjson cache <true when storage is set, else false> '{
    location: $loc,
    properties: {
      environmentId: $env,
      workloadProfileName: $wp,
      configuration: {
        activeRevisionsMode: "Single",
        ingress: {external: true, targetPort: 8000, transport: "auto", allowInsecure: false,
          ipSecurityRestrictions: [{name: "caller", ipAddressRange: $ip, action: "Allow"}]},
        secrets: ([{name: "vllm-api-key", value: env.VOT_API_KEY}]
          + (if $hf then [{name: "hf-token", value: env.HF_TOKEN}] else [] end))
      },
      template: {
        containers: [{name: "vllm", image: $img,
          args: ($args + (if $cache then ["--safetensors-load-strategy", "prefetch"] else [] end)),
          env: ($envs + (if $cache then [{name: "HF_HOME", value: "/vot-cache/huggingface"},
            {name: "VLLM_CACHE_ROOT", value: "/vot-cache/vllm"}] else [] end)),
          resources: {cpu: $cpu, memory: $mem},
          volumeMounts: (if $cache then [{volumeName: "vot-cache", mountPath: "/vot-cache"}] else [] end)}],
        volumes: (if $cache then [{name: "vot-cache", storageType: "AzureFile", storageName: "vot-cache",
          mountOptions: "mfsymlinks,nobrl"}] else [] end),
        scale: {minReplicas: 1, maxReplicas: 1}
      }
    }
  }')
```

(`jq` emits JSON, which is valid YAML.) All the lines above run in one
shell command, so the key dies with it. Base URL:
`https://$(az containerapp show --name vot-<preset> --resource-group <resource_group> --query properties.configuration.ingress.fqdn -o tsv)`.
Say it: billing runs until `/vot-destroy <preset>`, and only this machine's
public IP can reach the app (`/vot-serve` again from another network).

## API key

Generated by each create, stored only as the app's secret. Any session, or
the user, reads it back on demand:

```bash
az containerapp secret show --name vot-<preset> --resource-group <resource_group> --secret-name vllm-api-key --query value -o tsv
```

Every request below fetches it inline, never into a variable printed or a
file: `<auth header>` is
`-H @<(printf 'Authorization: Bearer %s' "$(az containerapp secret show --name vot-<preset> --resource-group <resource_group> --secret-name vllm-api-key --query value -o tsv)")`
(`printf` is a shell builtin, so the key is on no process's command line).
A new serve generates a new key; a destroy removes it with the app.

## Ready when

`curl -sf <auth header> <base url>/v1/models`
lists `<served name>`; poll every 20 s for up to 30 min (image pull ~10 GB,
then the weights, from Hugging Face or the `vot-cache` share). A poll that
keeps failing while the log shows `Application startup complete` means
the key fetch failed, not the app: check `az account show`. On timeout:
`az containerapp logs show --name vot-<preset> --resource-group <resource_group> --tail 50`;
when the container never started, also
`az containerapp logs show --name vot-<preset> --resource-group <resource_group> --type system --tail 50`.

## Destroy

```bash
az containerapp show --name vot-<preset> --resource-group <resource_group>
```

Fails: report that the unit does not exist, stop. Succeeds:

```bash
az containerapp delete --name vot-<preset> --resource-group <resource_group> --yes
```

The environment, its GPU profiles and the storage account stay (the
caches with it); `az group delete --name <resource_group>` removes
everything and is the user's call, never a destroy's.

## Traps

- The create spec must carry `ingress.allowInsecure: false`: without it `az containerapp create --yaml` fails with `400 ... could not be converted to System.Boolean. Path: $` (verified with containerapp 1.2.0b5 to 1.3.0b5).
- `--logs-destination none` keeps the environment from creating a billed Log Analytics workspace; `az containerapp logs show` streams console and system logs without it.
- GPU workload profiles get no default health probes, so a long model load is not restarted.
- One GPU per replica; `--tensor-parallel-size` stays 1.
- The platform driver sets the CUDA ceiling (driver 570 -> CUDA 12.x, 580 -> 13.x): an image built for a newer CUDA fails at start - check the log's CUDA error first.
- jq reads the secret values from the environment (`env[...]`), so they never go into a file or a command line; never move them to `--arg`/`--argjson`, which `ps` shows, and never echo the key - fetch it with `az containerapp secret show` where it is used.
- The API key covers `/v1`, `/v2`, `/inference`, `/cohere` only; `/invocations`, `/tokenize`, `/pause`, `/abort_requests`, `/update_weights` are protected by the ingress IP restriction alone - never remove it.
- The caller's IP changes (another network, a VPN): update the rule with `az containerapp ingress access-restriction set --name vot-<preset> --resource-group <resource_group> --rule-name caller --ip-address <new ip>/32 --action Allow`.
- An `otlp_endpoint` on `localhost` or a private address is unreachable from the app.
- The image sets no `HF_HOME` and its runtime home is not `/root` (vLLM writes `/tmp/.cache`): the cache must be pointed at the mount with `HF_HOME` and `VLLM_CACHE_ROOT`, never by mounting over `/root/.cache`, which stays empty.
- vLLM does not recognize the SMB (CIFS) mount as a network filesystem, so it disables auto-prefetch and reads the weights through mmap, page by page; the spec forces `--safetensors-load-strategy prefetch` when `storage` is set.
- The `vot-cache` mount needs `mfsymlinks`: the Hugging Face cache links its snapshots to its blobs, and SMB has no symlinks without it.
- The environment storage keeps a copy of the account key: after a key rotation, re-run the `az rest` registration of *Prepare*, or the mount fails at start.
- A storage account name is global: `check-name` before a create, and a name taken elsewhere is chosen again, never forced.
- `mountOptions` on the `vot-cache` volume accepts `mfsymlinks,nobrl`; `actimeo` is refused (`ContainerAppVolumeMountOptionsNotSupported`).
