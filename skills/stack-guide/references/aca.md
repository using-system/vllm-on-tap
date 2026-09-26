# aca (Azure Container Apps, serverless GPU)

## Prerequisites and install

- `az version` succeeds. Install: https://learn.microsoft.com/cli/azure/install-azure-cli (macOS: `brew install azure-cli`).
- `az account show` succeeds - otherwise the user runs `az login`; never run it for them.
- `az extension show --name containerapp` succeeds. Install: `az extension add --name containerapp --upgrade`.
- `az provider show --namespace Microsoft.App --query registrationState -o tsv` prints `Registered`. Install: `az provider register --namespace Microsoft.App --wait`.
- `jq --version` succeeds (to build the app spec below). Install: `brew install jq` / the distribution's package.

## Config fields

- `subscription` - name as `az account list --query "[].name" -o tsv` prints it.
- `location` - a region with serverless GPUs; T4 and A100: `australiaeast`, `brazilsouth`, `canadacentral`, `eastus`, `italynorth`, `swedencentral`, `westus`, `westus3`; T4 only: `centralindia`, `francecentral`, `japaneast`, `northcentralus`, `southcentralus`, `southeastasia`, `southindia`, `westeurope`, `westus2`.
- `resource_group` - default `rg-vot`.
- `environment` - the Container Apps environment; default `vot-env`.
- `api_key_env` - the name of the shell variable holding the API key; default `VOT_API_KEY`.
- `image` - optional; default `vllm/vllm-openai:v0.30.0`.

Every command below runs with `--subscription "<subscription>"`.

## Prepare

Each step: reuse when it exists, create on the user's yes otherwise.

```bash
az group show --name <resource_group>
az group create --name <resource_group> --location <location>

az containerapp env show --name <environment> --resource-group <resource_group>
az containerapp env create --name <environment> --resource-group <resource_group> --location <location> --enable-workload-profiles

az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv
az containerapp env workload-profile add --name <environment> --resource-group <resource_group> --workload-profile-name gpu-t4 --workload-profile-type Consumption-GPU-NC8as-T4
az containerapp env workload-profile add --name <environment> --resource-group <resource_group> --workload-profile-name gpu-a100 --workload-profile-type Consumption-GPU-NC24-A100
```

A profile `add` refused for quota: tell the user to request "Managed
Environment Consumption T4 GPUs" / "Managed Environment Consumption NCA100
GPUs" on the environment's Quota page
(https://learn.microsoft.com/azure/container-apps/quota-requests), and save
the environment anyway.

## Serve

Checks, in this order, stopping at the first refusal:

1. `printenv <api_key_env>` prints nothing (unset, or set but not exported) -> refuse before any Azure call, naming the variable: export it in the shell the agent session is started from, then restart the session; never paste the key into the conversation or a command; generate one with `openssl rand -hex 32` run by the user in that shell. The same holds for `HF_TOKEN` when the preset lists it.
2. Profile from `gpu_memory_gb`: <= 16 -> `gpu-t4` (cpu `8`, memory `56Gi`); <= 80 -> `gpu-a100` (cpu `24`, memory `220Gi`); > 80 -> refuse (no serverless profile fits).
3. The profile exists: `az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv` lists it; otherwise refuse and route to `/vot-config` (quota).
4. Already served: `az containerapp show --name vot-<preset> --resource-group <resource_group>` succeeds -> unit exists.

Create. `az containerapp create --args` cannot carry vLLM's `--flags` (az
parses them as its own), so the app is created from a YAML spec, built with
`jq` and streamed through process substitution. jq reads the secrets'
values from its environment (`env[...]`), never from its arguments, so they
appear in no file and in no process's command line.

```bash
ENV_ID="$(az containerapp env show --name <environment> --resource-group <resource_group> --query id -o tsv)"
CALLER_IP="$(curl -fsS https://api.ipify.org)"
ARGS='["<model>","--served-model-name","<served name>","--port","8000", <vllm args as JSON strings>]'
ENVS='[{"name":"VLLM_API_KEY","secretRef":"vllm-api-key"}]'   # + {"name":"HF_TOKEN","secretRef":"hf-token"}, {"name":"OTEL_SERVICE_NAME","value":"vot-<preset>"}, {"name":"OTEL_EXPORTER_OTLP_TRACES_PROTOCOL","value":"http/protobuf"} when they apply
az containerapp create --name vot-<preset> --resource-group <resource_group> --yaml <(jq -n \
  --arg loc "<location>" --arg env "$ENV_ID" --arg wp "<profile>" --arg img "<image>" \
  --arg ip "$CALLER_IP/32" --argjson cpu <cpu> --arg mem "<memory>" \
  --argjson args "$ARGS" --argjson envs "$ENVS" \
  --arg keyvar "<api_key_env>" --argjson hf <true when the preset lists HF_TOKEN, else false> '{
    location: $loc,
    properties: {
      environmentId: $env,
      workloadProfileName: $wp,
      configuration: {
        activeRevisionsMode: "Single",
        ingress: {external: true, targetPort: 8000, transport: "auto",
          ipSecurityRestrictions: [{name: "caller", ipAddressRange: $ip, action: "Allow"}]},
        secrets: ([{name: "vllm-api-key", value: env[$keyvar]}]
          + (if $hf then [{name: "hf-token", value: env.HF_TOKEN}] else [] end))
      },
      template: {
        containers: [{name: "vllm", image: $img, args: $args, env: $envs,
          resources: {cpu: $cpu, memory: $mem}}],
        scale: {minReplicas: 1, maxReplicas: 1}
      }
    }
  }')
```

(`jq` emits JSON, which is valid YAML.) Base URL:
`https://$(az containerapp show --name vot-<preset> --resource-group <resource_group> --query properties.configuration.ingress.fqdn -o tsv)`.
Say it: billing runs until `/vot-destroy <preset>`, and only this machine's
public IP can reach the app (`/vot-serve` again from another network).

## Ready when

`curl -sf -H @<(printf 'Authorization: Bearer %s' "${<api_key_env>}") <base url>/v1/models`
lists `<served name>`; poll every 20 s for up to 30 min (image pull ~10 GB,
then the weights). On timeout:
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

The environment and its GPU profiles stay; `az group delete --name <resource_group>` removes
everything and is the user's call, never a destroy's.

## Traps

- GPU workload profiles get no default health probes, so a long model load is not restarted.
- One GPU per replica; `--tensor-parallel-size` stays 1.
- The platform driver sets the CUDA ceiling (driver 570 -> CUDA 12.x, 580 -> 13.x): an image built for a newer CUDA fails at start - check the log's CUDA error first.
- jq reads the secret values from the environment (`env[...]`), so they never go into a file or a command line; never move them to `--arg`/`--argjson`, which `ps` shows.
- The API key covers `/v1`, `/v2`, `/inference`, `/cohere` only; `/invocations`, `/tokenize`, `/pause`, `/abort_requests`, `/update_weights` are protected by the ingress IP restriction alone - never remove it.
- The caller's IP changes (another network, a VPN): update the rule with `az containerapp ingress access-restriction set --name vot-<preset> --resource-group <resource_group> --rule-name caller --ip-address <new ip>/32 --action Allow`.
- An `otlp_endpoint` on `localhost` or a private address is unreachable from the app.
