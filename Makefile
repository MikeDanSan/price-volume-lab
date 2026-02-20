IMAGE   := vpa-engine
VERSION := $(shell grep '^version' pyproject.toml | cut -d'"' -f2)
GIT_SHA := $(shell git rev-parse --short HEAD)
TAG     := $(VERSION)-$(GIT_SHA)

.PHONY: build up version

build:
	docker build \
		--build-arg VERSION=$(VERSION) \
		--build-arg GIT_SHA=$(GIT_SHA) \
		-t $(IMAGE):$(VERSION) \
		-t $(IMAGE):$(TAG) \
		-t $(IMAGE):latest \
		.

up: build
	VPA_VERSION=$(VERSION) VPA_GIT_SHA=$(GIT_SHA) docker compose up -d

version:
	@echo $(TAG)
