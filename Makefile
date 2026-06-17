# one -ignore flag per non-empty line in .licenseignore (quoted to avoid shell globbing)
LICENSE_IGNORE := $(foreach pattern,$(shell cat .licenseignore 2>/dev/null),-ignore '$(pattern)')

.PHONY: license
license: ## inject license headers into all supported code files
	go tool addlicense -c 'BitWise Media Group Ltd' -l mit -s=only $(LICENSE_IGNORE) $(CURDIR)
