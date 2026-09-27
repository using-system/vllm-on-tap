## [0.2.3] - 2026-09-27

### 🚀 Features

- *(stack-guide)* Add resource attributes to vllm traces and document conversation correlation (#44)
## [0.2.2] - 2026-09-27

### 🚀 Features

- *(presets)* Add /vot-instrument-preset to create or edit a custom preset (#34)
- *(presets)* Add a qwen3.8 27b builtin preset for agentic coding (#38)
- *(azure)* Add optional application insights telemetry through an otel collector (#40)

### 📚 Documentation

- Describe the azure stack in one sentence and keep the readme simple (#32)
## [0.2.1] - 2026-09-26

### 🚀 Features

- *(azure)* Discover the environment and the storage in the resource group (#28)
## [0.2.0] - 2026-09-26

### 🚀 Features

- *(aca)* Cache models on an azure files storage and generate the api key at serve time (#19)
- Rename the aca stack to azure and list the planned kubernetes, aws and gcp stacks (#23)

### 🐛 Bug Fixes

- *(publish)* Create the version tag with --no-sign (#17)

### 📚 Documentation

- Align the plugin description and simplify the readme (#25)

### ⚙️ Miscellaneous Tasks

- *(deps)* Bump astral-sh/setup-uv from 10.1.0 to 10.2.0 (#11)
- *(deps)* Bump orhun/git-cliff-action from 4.9.0 to 4.9.1 (#12)
## [0.1.0] - 2026-09-26

### 🚀 Features

- Vllm-on-tap v0.1 plugin - skills, presets, ci and release (#2)
- *(aca)* Optional subscription, and the repository's own .vot/ environments (#14)

### 🐛 Bug Fixes

- Live acceptance on local-vllm-metal and aca - gemma4 e2b/e4b presets, aca on the A100 (#5)

### 🚜 Refactor

- *(ci)* The repository check under .github/scripts, its tests under tests/ (#6)

### 📚 Documentation

- *(spec)* Vllm-on-tap design and implementation plan (#1)
- *(agents)* AGENTS.md with the repository's working rules, a generic README presets section (#8)
- *(community)* Security policy, contributing guide, code of conduct, issue and pr templates (#10)
