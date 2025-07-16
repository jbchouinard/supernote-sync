VERSION := $(shell poetry version --short)
DOCKER_REPO := ghcr.io/jbchouinard/supernote-sync

build:
	poetry build

publish:
	poetry publish

docker-build:
	docker build --tag $(DOCKER_REPO):$(VERSION) .
	docker tag $(DOCKER_REPO):$(VERSION) $(DOCKER_REPO):latest

docker-publish:
	docker push $(DOCKER_REPO):$(VERSION)
	docker push $(DOCKER_REPO):latest

clean:
	rm -rf dist

test:
	poetry run pytest -v tests/

.PHONY: build publish docker-build docker-publish clean test
