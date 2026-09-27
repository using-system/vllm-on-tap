# azure (Azure Container Apps, serverless GPU)

A Container Apps environment in which each serve provisions a Container
App with a serverless GPU, on demand, and removes it on destroy; an
optional storage account caches the model weights and vLLM's compiled
graphs across serves, and an optional Application Insights receives
vLLM's traces through an OpenTelemetry Collector in the environment.

## Prerequisites and install

- `az version` succeeds. Install: https://learn.microsoft.com/cli/azure/install-azure-cli (macOS: `brew install azure-cli`).
- `az account show` succeeds - otherwise the user runs `az login`; never run it for them.
- `az extension show --name containerapp` succeeds. Install: `az extension add --name containerapp --upgrade`.
- `az provider show --namespace Microsoft.App --query registrationState -o tsv` prints `Registered`. Install: `az provider register --namespace Microsoft.App --wait`.
- `jq --version` succeeds (to build the app spec below). Install: `brew install jq` / the distribution's package.
- `openssl version` succeeds (to generate the API key). Install: `brew install openssl` / the distribution's package.

## Config fields

- `subscription` - optional; absent means the subscription `az account show` reports (the logged-in default). Set it only to pin another one, by the name `az account list --query "[].name" -o tsv` prints. Leave it out of an environment committed to a public repository.
- `location` - a region with serverless A100 GPUs: `australiaeast`, `brazilsouth`, `canadacentral`, `eastus`, `italynorth`, `swedencentral`, `westus`, `westus3`. When `<environment>` resolves, its region wins: *Prepare* reads it (`az containerapp env show --name <environment> --resource-group <resource_group> --query location -o tsv`, lowercased without spaces) and writes it as `location`, and refuses when it is not one of these regions (in `/vot-config`, ask for another `resource_group`).
- `resource_group` - default `rg-vot`; dedicated to vllm-on-tap.
- `image` - optional; default `vllm/vllm-openai:v0.30.0`.
- `telemetry_enabled` - `true` or `false`, default `false`. `true`: *Prepare*
  makes sure the telemetry resources exist (see *Telemetry*), and *Serve*
  exports the traces to the collector. `false`: *Prepare* offers to delete
  them when present.

`environment`, `storage` and `api_key_env` fields from an earlier version
are ignored, and dropped on the next write.

The rest is not config: *Prepare* and *Serve* resolve it from
`<resource_group>`, and refuse when either list prints more than one name -
the resource group must hold one of each at most (in `/vot-config`, ask for
another, dedicated `resource_group`). *Destroy* needs neither and never
resolves: it only removes `vot-<preset>`, so a crowded resource group never
keeps a GPU billing.

```bash
az containerapp env list --resource-group <resource_group> --query "[].name" -o tsv
az storage account list --resource-group <resource_group> --query "[?kind=='StorageV2' && largeFileSharesState=='Enabled'].name" -o tsv
```

- `<environment>` - the Container Apps environment printed. None: *Prepare*
  creates it; *Serve* refuses and routes to `/vot-config`.
- `<storage>` - the storage account printed, whose Azure Files share
  `vot-cache` is mounted in every app on `/vot-cache` (the Hugging Face
  and vLLM caches). None: no storage - the weights download from Hugging
  Face and vLLM compiles at every start. Its presence is what turns the
  cache on.

When `subscription` is set, every command below runs with `--subscription "<subscription>"`; otherwise without it.

## Prepare

Every resource is reused when it exists. When one is missing - the
resource group, the Container Apps environment, the storage - ask the user
who creates it: vllm-on-tap, now, with the commands below; or the user,
beforehand, with their own network rules (a VNet, private endpoints...),
then `/vot-config` again, which discovers what they created. Only the
region and the resource group are config; vllm-on-tap finds the rest in
it. On "the user": write the environment, then stop and ask them to run
`/vot-config` again once it exists.

The resource group comes first; `<environment>` and `<storage>` resolve
after it (a resource group just created holds neither). The environment
exists when `<environment>` resolved; otherwise it is created as
`vot-env`, which then is `<environment>`. An environment the user created
must have workload profiles: `az containerapp env show --name <environment>
--resource-group <resource_group> --query properties.workloadProfiles -o tsv`
printing nothing means a Consumption-only environment, which cannot be
converted - refuse, and tell the user to recreate it with workload
profiles, or to remove it so vllm-on-tap creates `vot-env`. Its missing
`gpu-a100` profile is added the same way as below, on the user's yes.

The environment is **internal** when `az containerapp env show --name
<environment> --resource-group <resource_group> --query
properties.vnetConfiguration.internal -o tsv` prints `true` (created by the
user on their VNet, with no public endpoint). *Serve* then exposes the app
to that VNet only: say so at *Prepare*, since the model is then reached
from inside the VNet (a VPN, a bastion, a peered network).

```bash
az group show --name <resource_group>
az group create --name <resource_group> --location <location>

az containerapp env create --name vot-env --resource-group <resource_group> --location <location> --enable-workload-profiles --logs-destination none

az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv
az containerapp env workload-profile add --name <environment> --resource-group <resource_group> --workload-profile-name gpu-a100 --workload-profile-type Consumption-GPU-NC24-A100
```

A profile `add` refused for quota: tell the user to request "Managed
Environment Consumption NCA100 GPUs" on the environment's Quota page
(https://learn.microsoft.com/azure/container-apps/quota-requests), and save
the environment anyway, then continue with the storage and *Telemetry*.

Then the optional storage - not required, an environment serves
without it. `<storage>` resolved: reuse it, and make sure its share and
its environment storage below exist. None: offer to create one, saying
what it brings and what it costs - or to let the user create it (a
StorageV2 account with large file shares enabled, so it is discovered);
on a no, there is no storage.

**Storage (`<storage>`)**: the Hugging Face cache (`HF_HOME`)
and vLLM's cache (`VLLM_CACHE_ROOT`, its torch.compile artifacts) live on
an Azure Files share mounted in the app, so a preset's second serve reads
its weights from the share instead of downloading them, and reuses its
compiled graphs. A Standard account with a Hot share bills the GB stored
(~0.03 USD per GB per month, so a few models cost a few USD) plus its
transactions (cents per serve); the quota is a ceiling, not a charge.
The first serve of a preset still downloads, and writes the share as it
goes.

```bash
az storage account create --name <storage> --resource-group <resource_group> --location <location> --sku Standard_LRS --kind StorageV2 --enable-large-file-share --min-tls-version TLS1_2 --allow-blob-public-access false

az storage share-rm show --storage-account <storage> --resource-group <resource_group> --name vot-cache
az storage share-rm create --storage-account <storage> --resource-group <resource_group> --name vot-cache --quota 1024 --access-tier Hot --enabled-protocols SMB

az containerapp env storage show --name <environment> --resource-group <resource_group> --storage-name vot-cache
```

`<storage>` on create: generate it - `votcache` followed by 6 random hex
characters (`openssl rand -hex 3`), globally unique, checked with
`az storage account check-name --name <storage>` and generated again when
taken. The environment storage
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

### Telemetry

Driven by `telemetry_enabled` alone, every run of *Prepare*, with fixed
names in `<resource_group>`: a Log Analytics workspace `vot-logs`, a
workspace-based Application Insights `vot-appi` on it, and a Container App
`otel-collector` in `<environment>` - an OpenTelemetry Collector that
receives OTLP/HTTP from the apps of the environment and exports the traces
to `vot-appi`. vLLM exports traces only, so only a traces pipeline runs.

`true`: first `az extension show --name application-insights` succeeds -
otherwise offer `az extension add --name application-insights --upgrade`,
run on the user's yes (on a no, go on as `false`, which needs no
extension). Then create whichever is missing, in this order; an existing one
is reused as it is. Say what it costs first: Log Analytics bills the GB
ingested (the traces of a few serves stay within cents), and the collector
runs on the Consumption profile with 0.25 vCPU and 0.5 Gi, always on, a
few USD a month while idle.

```bash
az monitor log-analytics workspace show --workspace-name vot-logs --resource-group <resource_group>
az monitor log-analytics workspace create --workspace-name vot-logs --resource-group <resource_group> --location <location> --retention-time 30

az monitor app-insights component show --app vot-appi --resource-group <resource_group>
az monitor app-insights component create --app vot-appi --resource-group <resource_group> --location <location> --kind web --application-type web \
  --workspace "$(az monitor log-analytics workspace show --workspace-name vot-logs --resource-group <resource_group> --query id -o tsv)"

az containerapp show --name otel-collector --resource-group <resource_group>
```

The collector is created like a serve's app, from a `jq` spec: image
`otel/opentelemetry-collector-contrib:0.161.0`, its configuration in the
environment variable `OTELCOL_CONFIG` (read with `--config=env:`), and the
Application Insights connection string as the app secret
`appinsights-connection-string`, exported to jq only and read from its
environment, like the API key:

```bash
ENV_ID="$(az containerapp env show --name <environment> --resource-group <resource_group> --query id -o tsv)"
APPI_CS="$(az monitor app-insights component show --app vot-appi --resource-group <resource_group> --query connectionString -o tsv)"
[ -n "$APPI_CS" ] || { echo "no application insights connection string" >&2; exit 1; }
export APPI_CS
OTELCOL_CONFIG='receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
exporters:
  azure_monitor:
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [azure_monitor]'
az containerapp create --name otel-collector --resource-group <resource_group> --yaml <(jq -n \
  --arg loc "<location>" --arg env "$ENV_ID" --arg cfg "$OTELCOL_CONFIG" \
  --arg img "otel/opentelemetry-collector-contrib:0.161.0" '{
    location: $loc,
    properties: {
      environmentId: $env,
      workloadProfileName: "Consumption",
      configuration: {
        activeRevisionsMode: "Single",
        ingress: {external: false, targetPort: 4318, transport: "http", allowInsecure: true},
        secrets: [{name: "appinsights-connection-string", value: env.APPI_CS}]
      },
      template: {
        containers: [{name: "otel-collector", image: $img,
          args: ["--config=env:OTELCOL_CONFIG"],
          env: [{name: "OTELCOL_CONFIG", value: $cfg},
            {name: "APPLICATIONINSIGHTS_CONNECTION_STRING", secretRef: "appinsights-connection-string"}],
          resources: {cpu: 0.25, memory: "0.5Gi"}}],
        scale: {minReplicas: 1, maxReplicas: 1}
      }
    }
  }')
```

All the lines above run in one shell command, so the connection string
dies with it. The traces go to `http://<collector fqdn>/v1/traces`,
where `<collector fqdn>` is what
`az containerapp show --name otel-collector --resource-group <resource_group> --query properties.configuration.ingress.fqdn -o tsv`
prints (`otel-collector.internal.<environment default domain>`): the apps
of the environment reach it, and nothing outside the environment does.
*Serve* resolves it at every serve; the environment stores no
`otlp_endpoint`, so no live domain lands in a committed file and a
recreated environment never leaves a stale endpoint.

`false`: never delete silently - the names are fixed, but a resource
under one of them may be the user's, not vllm-on-tap's. Check which of
the four exist (the `show` and `list` commands below, the smart-detection
rule included); none: nothing to do. Otherwise list them, with the served
apps (`az containerapp list --resource-group <resource_group> --query "[?starts_with(name,'vot-')].name" -o tsv`),
which keep exporting to a deleted collector and lose their traces until
served again, and ask the user's permission for each one before deleting
it - the user may keep a workspace and drop the collector. Delete the
ones allowed, the collector first, and say what was deleted and what was
kept. A kept collector keeps `telemetry_enabled: true`; otherwise it is
written `false`. `az resource` needs no extension:

```bash
az containerapp show --name otel-collector --resource-group <resource_group>
az containerapp delete --name otel-collector --resource-group <resource_group> --yes

az resource show --name vot-appi --resource-group <resource_group> --resource-type Microsoft.Insights/components
az resource delete --name vot-appi --resource-group <resource_group> --resource-type Microsoft.Insights/components

az monitor log-analytics workspace show --workspace-name vot-logs --resource-group <resource_group>
az monitor log-analytics workspace delete --workspace-name vot-logs --resource-group <resource_group> --yes

az resource list --resource-group <resource_group> --resource-type microsoft.alertsmanagement/smartDetectorAlertRules --query "[?name=='Failure Anomalies - vot-appi'].id" -o tsv
az resource delete --ids "<id>"   # the id holds spaces: keep the quotes
```

The last pair removes the smart-detection rule Azure adds with
`vot-appi`, a few minutes after its create.

## Serve

Checks, in this order, stopping at the first refusal (`<environment>` and
`<storage>` resolved as *Config fields* says, before check 3):

1. The preset lists `HF_TOKEN` and `printenv HF_TOKEN` prints nothing -> refuse before any Azure call: export it in the shell the agent session is started from, then restart the session; never paste it into the conversation or a command.
2. Profile: always `gpu-a100` (cpu `24`, memory `220Gi`, one A100 80 GB); a preset with `gpu_memory_gb` > 80 -> refuse (no serverless profile fits).
3. The profile exists: `az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv` lists it; otherwise refuse and route to `/vot-config` (quota).
4. `<storage>` resolved: `az containerapp env storage show --name <environment> --resource-group <resource_group> --storage-name vot-cache` fails -> refuse and route to `/vot-config`.
5. `telemetry_enabled` is `true`: `<collector fqdn>` (see *Telemetry*) prints nothing -> refuse and route to `/vot-config`; otherwise `http://<collector fqdn>/v1/traces` is the `otlp_endpoint` of stack-guide's tracing rule for this serve.
6. Internal environment (see *Prepare*): `<internal>` is `true`, otherwise `false`.
7. Already served: `az containerapp show --name vot-<preset> --resource-group <resource_group>` succeeds -> unit exists.

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
CALLER_IP="$(curl -fsS https://api.ipify.org)"; [ -n "$CALLER_IP" ] || exit 1   # only when not internal
VOT_API_KEY="$(openssl rand -hex 32)"; [ -n "$VOT_API_KEY" ] || exit 1; export VOT_API_KEY
ARGS='["<model>","--served-model-name","<served name>","--port","8000", <vllm args as JSON strings>]'
ENVS='[{"name":"VLLM_API_KEY","secretRef":"vllm-api-key"}]'   # + {"name":"HF_TOKEN","secretRef":"hf-token"}, {"name":"OTEL_SERVICE_NAME","value":"vot-<preset>"}, {"name":"OTEL_EXPORTER_OTLP_TRACES_PROTOCOL","value":"http/protobuf"} when they apply
az containerapp create --name vot-<preset> --resource-group <resource_group> --yaml <(jq -n \
  --arg loc "<location>" --arg env "$ENV_ID" --arg wp "<profile>" --arg img "<image>" \
  --arg ip "${CALLER_IP:-}/32" --argjson internal <internal> --argjson cpu <cpu> --arg mem "<memory>" \
  --argjson args "$ARGS" --argjson envs "$ENVS" \
  --argjson hf <true when the preset lists HF_TOKEN, else false> \
  --argjson cache <true when <storage> resolved, else false> '{
    location: $loc,
    properties: {
      environmentId: $env,
      workloadProfileName: $wp,
      configuration: {
        activeRevisionsMode: "Single",
        ingress: ({external: true, targetPort: 8000, transport: "auto", allowInsecure: false}
          + (if $internal then {} else {ipSecurityRestrictions: [{name: "caller", ipAddressRange: $ip, action: "Allow"}]} end)),
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
public IP can reach the app (`/vot-serve` again from another network) - or,
on an internal environment, only the environment's VNet, with a private
base URL.

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
then the weights, from Hugging Face or the `vot-cache` share). On an
internal environment the base URL only answers from inside its VNet: try
the `curl` once, and when it cannot resolve or connect (curl exit 6 or 7,
not an HTTP status), poll the log instead - the readiness proof is then
the line `Application startup complete` in
`az containerapp logs show --name vot-<preset> --resource-group <resource_group> --tail 50`,
and the report hands the user the `curl` to run from inside the VNet (with
`az` logged in there, since `<auth header>` reads the key with it). On a
base URL this machine reaches, a poll that keeps failing while the log
shows `Application startup complete` means the key fetch failed, not the
app: check `az account show`. On timeout:
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

The environment, its GPU profiles, the storage account (the caches
with it) and the telemetry resources stay; `az group delete --name
<resource_group>` removes everything and is the user's call, never a
destroy's.

## Traps

- A create spec must carry `ingress.allowInsecure` explicitly - `false` for `vot-<preset>`, `true` for `otel-collector` (see below): without it `az containerapp create --yaml` fails with `400 ... could not be converted to System.Boolean. Path: $` (verified with containerapp 1.2.0b5 to 1.3.0b5).
- `--logs-destination none` keeps the environment from creating a billed Log Analytics workspace; `az containerapp logs show` streams console and system logs without it.
- GPU workload profiles get no default health probes, so a long model load is not restarted.
- One GPU per replica; `--tensor-parallel-size` stays 1.
- The platform driver sets the CUDA ceiling (driver 570 -> CUDA 12.x, 580 -> 13.x): an image built for a newer CUDA fails at start - check the log's CUDA error first.
- jq reads the secret values from the environment (`env[...]`), so they never go into a file or a command line; never move them to `--arg`/`--argjson`, which `ps` shows, and never echo the key - fetch it with `az containerapp secret show` where it is used.
- The API key covers `/v1`, `/v2`, `/inference`, `/cohere` only; `/invocations`, `/tokenize`, `/pause`, `/abort_requests`, `/update_weights` are protected by the ingress IP restriction alone - never remove it (on an internal environment no IP rule is ever added: see the internal trap below).
- The caller's IP changes (another network, a VPN), not internal: update the rule with `az containerapp ingress access-restriction set --name vot-<preset> --resource-group <resource_group> --rule-name caller --ip-address <new ip>/32 --action Allow`.
- An `otlp_endpoint` on `localhost` or a private address is unreachable from the app.
- The image sets no `HF_HOME` and its runtime home is not `/root` (vLLM writes `/tmp/.cache`): the cache must be pointed at the mount with `HF_HOME` and `VLLM_CACHE_ROOT`, never by mounting over `/root/.cache`, which stays empty.
- vLLM does not recognize the SMB (CIFS) mount as a network filesystem, so it disables auto-prefetch and reads the weights through mmap, page by page; the spec forces `--safetensors-load-strategy prefetch` when `<storage>` resolved.
- The `vot-cache` mount needs `mfsymlinks`: the Hugging Face cache links its snapshots to its blobs, and SMB has no symlinks without it.
- The environment storage keeps a copy of the account key: after a key rotation, re-run the `az rest` registration of *Prepare*, or the mount fails at start.
- An internal environment has no IP rule on the app (its callers come from private addresses): the ingress is reachable from the whole VNet, the API key still guards `/v1` - the routes it leaves open are reachable from the VNet too.
- An internal environment's FQDN resolves only through a private DNS zone for the environment's default domain, pointing to its static IP, which the user creates on their VNet; without it even a caller inside the VNet gets no answer.
- A storage account with network rules or private endpoints only must let the environment's subnet reach it, or the `vot-cache` mount fails at start and the revision never runs.
- An environment on a VNet needs outbound access to the image registry (Docker Hub), to `huggingface.co` and, with `telemetry_enabled`, to the Application Insights ingestion endpoint (`*.in.applicationinsights.azure.com`); a route table or firewall that blocks it stops the pull or the weights download, or drops the collector's spans silently.
- A storage account name is global: the generated name is checked with `check-name` before a create, and generated again when taken.
- Another StorageV2 account with large file shares, or a second Container Apps environment, in `<resource_group>` makes *Prepare* and *Serve* refuse (*Destroy* still runs): move it out, or use a resource group dedicated to vllm-on-tap.
- `mountOptions` on the `vot-cache` volume accepts `mfsymlinks,nobrl`; `actimeo` is refused (`ContainerAppVolumeMountOptionsNotSupported`).
- The collector's ingress is internal with `allowInsecure: true`, so the apps post plain HTTP to `http://<collector fqdn>`; with `allowInsecure: false` the ingress redirects the POST to HTTPS and the spans are lost.
- The collector exporter's type is `azure_monitor`; `azuremonitor` is its deprecated name. It reads the connection string from `APPLICATIONINSIGHTS_CONNECTION_STRING`, so the configuration holds no secret.
- A Log Analytics workspace delete is a soft delete for 14 days: creating `vot-logs` again in the same resource group within that time recovers it, data included.
- An existing collector is reused as it is, never updated: to move it to another image, delete `otel-collector` alone (`az containerapp delete`) and run `/vot-config` again; the workspace and its data stay.
- The bare app name `otel-collector` does not resolve from another app (`NameResolutionError`, the spans are lost): the endpoint is the internal FQDN.
