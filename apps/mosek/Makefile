.PHONY: build

REGISTRY_NAME=dmclf
IMAGE_NAME=mosek
MAJOR_VERSION=11.0
MINOR_VERSION=21

IMAGE_TAG=$(REGISTRY_NAME)/$(IMAGE_NAME):$(MAJOR_VERSION).$(MINOR_VERSION)

build:
	docker buildx build --platform linux/amd64,linux/arm64 -t $(IMAGE_TAG) -f Dockerfile . --build-arg MAJOR_VERSION=${MAJOR_VERSION} --build-arg MINOR_VERSION=${MINOR_VERSION} --push

