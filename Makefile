# one -ignore flag per non-empty line in .licenseignore (quoted to avoid shell globbing)
LICENSE_IGNORE := $(foreach pattern,$(shell cat .licenseignore 2>/dev/null),-ignore '$(pattern)')

# these targets mutate files and pr relies on their order; keep make serial even under -j so
# pr always runs license -> lint-fix -> fmt -> lint rather than racing them.
.NOTPARALLEL:

.PHONY: license
license: ## inject license headers into all supported code files
	@ go tool addlicense -c 'BitWise Media Group Ltd' -l mit -s=only $(LICENSE_IGNORE) .

.PHONY: fmt
fmt: node_modules ## format markdown in place with prettier
	@ npm run fmt

.PHONY: lint-fix
lint-fix: node_modules ## auto-fix markdown lint violations with markdownlint-cli2
	@ npm run lint:fix

.PHONY: lint
lint: node_modules ## check-mode static analysis: prettier formatting check + markdownlint
	go tool addlicense -check -c 'BitWise Media Group Ltd' -l mit -s=only $(LICENSE_IGNORE) .
	@ npm run fmt:check
	@ npm run lint

# This library is GitHub Actions YAML + Markdown only — nothing to compile, test, or
# exercise end-to-end — so these canonical targets are no-ops. They exist so the reusable
# ci/release workflows (which call `make build` / `make test` / `make e2e` unconditionally)
# always succeed here, the same contract every consuming repo follows.
.PHONY: build
build: ## no-op: nothing to build
	@:

.PHONY: test
test: ## no-op: nothing to test
	@:

.PHONY: e2e
e2e: ## no-op: no end-to-end tests
	@:

.PHONY: ci
ci: lint build test ## run the CI gates locally: lint, build, test

.PHONY: pr
pr: license lint-fix fmt lint build test ## run every pre-commit gate: license, lint-fix, fmt, lint, build, test

node_modules: package.json package-lock.json
	@ npm ci
	@ touch node_modules
