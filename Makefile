VERSION := $(shell poetry version --short)
DOCKER_IMAGE_NAME ?= "supernote-sync"

build:
	poetry build

publish:
	poetry publish

docker-build:
	docker build --tag $(DOCKER_IMAGE_NAME):$(VERSION) .
	docker tag $(DOCKER_IMAGE_NAME):$(VERSION) $(DOCKER_REPO):latest

docker-publish:
	docker push $(DOCKER_IMAGE_NAME):$(VERSION)
	docker push $(DOCKER_IMAGE_NAME):latest

clean:
	rm -rf dist

test:
	poetry run pytest -v tests/

.PHONY: build publish docker-build docker-publish clean test
