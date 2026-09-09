# Copyright 2026 BitWise Media Group Ltd
# SPDX-License-Identifier: MIT

# github-workflows — everything lives in mise tasks: the common-only contract
# (prose + license policy, workflow lint, pinned tools) comes from the shared
# toolchain submodule at .mise/, selected in the root mise.toml; tasks.toml
# extends the lint gate with zizmor over examples/. This Makefile is only the
# thin forwarding shim — `make <task>` == `mise run <task>`.
include .mise/common/include.mk
