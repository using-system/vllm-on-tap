# aws (Amazon ECS, GPU instances)

Not supported in this version of vllm-on-tap; planned for a later version:
an ECS service on GPU EC2 capacity - Fargate has no GPUs - with EFS
caching the model weights.

Every vllm-on-tap command on an environment of this type stops here: tell
the user the type is not supported in this version yet.
