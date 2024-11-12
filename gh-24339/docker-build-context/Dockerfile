FROM ubuntu:24.04
ENV VNOMAD=1.9.3 VCONSUL=1.20.1 VCNI=1.6.0 ARCH=amd64
RUN apt-get update && apt-get install -y curl unzip iproute2 tini && rm -rf /var/lib/apt/lists/* && apt-get autoremove --yes && \
    curl -L -o /tmp/nomad.zip https://releases.hashicorp.com/nomad/${VNOMAD}/nomad_${VNOMAD}_linux_${ARCH}.zip && unzip /tmp/nomad.zip nomad && chmod 755 nomad && \
    mv nomad /usr/local/bin/ && \
    curl -L -o /tmp/consul.zip https://releases.hashicorp.com/consul/${VCONSUL}/consul_${VCONSUL}_linux_${ARCH}.zip && unzip /tmp/consul.zip consul && chmod 755 consul && \
    mv consul /usr/local/bin/ && \
    mkdir -p /opt/cni/bin && \
    curl -L -o /tmp/cni.tgz https://github.com/containernetworking/plugins/releases/download/v${VCNI}/cni-plugins-linux-${ARCH}-v${VCNI}.tgz && tar -zxf /tmp/cni.tgz -C /opt/cni/bin
WORKDIR /

ENTRYPOINT ["/sbin/tini","-v","--"]
