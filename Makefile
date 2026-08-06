.PHONY: install dev test lint build format check

install:
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

dev:
	@$(MAKE) -C backend dev & \
		backend_pid=$$!; \
		trap 'kill "$$backend_pid" 2>/dev/null || true' INT TERM EXIT; \
		$(MAKE) -C frontend dev

test:
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

lint:
	$(MAKE) -C backend lint
	cd frontend && pnpm check

build:
	$(MAKE) -C frontend build

format:
	$(MAKE) -C backend format
	$(MAKE) -C frontend format

check: lint test build
