.PHONY: build

REGISTRY_NAME=dmclf
IMAGE_NAME=nomad-juggler
MAJOR_VERSION=0
MINOR_VERSION=1a

IMAGE_TAG=$(REGISTRY_NAME)/$(IMAGE_NAME):$(MAJOR_VERSION).$(MINOR_VERSION)

build:
	docker buildx build --platform linux/amd64 -t $(IMAGE_TAG) -f Dockerfile . --build-arg MAJOR_VERSION=${MAJOR_VERSION} --build-arg MINOR_VERSION=${MINOR_VERSION} --load 
push:
	docker buildx build --platform linux/amd64,linux/arm64 -t $(IMAGE_TAG) -f Dockerfile . --build-arg MAJOR_VERSION=${MAJOR_VERSION} --build-arg MINOR_VERSION=${MINOR_VERSION} --push --provenance=false --cache-to=type=inline,mode=min,image-manifest=true
