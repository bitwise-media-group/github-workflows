# one -ignore flag per non-empty line in .licenseignore (quoted to avoid shell globbing)
LICENSE_IGNORE := $(foreach pattern,$(shell cat .licenseignore 2>/dev/null),-ignore '$(pattern)')

# pinned dev tools — the binaries installed from package.json/package-lock, so make runs the
# exact prettier/markdownlint-cli2 versions this repo pins rather than whatever npx might fetch.
PRETTIER := node_modules/.bin/prettier
MARKDOWNLINT := node_modules/.bin/markdownlint-cli2

# these targets mutate files and pr relies on their order; keep make serial even under -j so
# pr always runs license -> lint-fix -> fmt -> lint rather than racing them.
.NOTPARALLEL:

.PHONY: license
license: ## inject license headers into all supported code files
	go tool addlicense -c 'BitWise Media Group Ltd' -l mit -s=only $(LICENSE_IGNORE) $(CURDIR)

.PHONY: fmt
fmt: ## format markdown in place with prettier
	$(PRETTIER) --write "**/*.md"

.PHONY: lint
lint: ## lint markdown with markdownlint-cli2
	$(MARKDOWNLINT)

.PHONY: lint-fix
lint-fix: ## auto-fix markdown lint violations with markdownlint-cli2
	$(MARKDOWNLINT) --fix

.PHONY: pr
pr: license lint-fix fmt lint ## run every pre-commit gate: license headers, lint-fix, format, lint
