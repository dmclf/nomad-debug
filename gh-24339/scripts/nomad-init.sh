#!/bin/sh
if test ! -d /etc/nomad;then mkdir /etc/nomad;fi
cat << EOHCL > /etc/nomad/nomad.hcl
region = "`hostname | cut -f1 -d\.`"
datacenter = "`hostname | cut -f2 -d\.`"
data_dir  = "/tmp/nomad-data"
bind_addr = "${HOSTNAME}"
#bind_addr = "0.0.0.0"

name = "${HOSTNAME}"

ports {
  http = ${NOMAD_HTTP}
  rpc  = ${NOMAD_RPC}
  serf = ${NOMAD_SERF}
}

acl {
  enabled = true
  token_min_expiration_ttl = "1m"
  token_max_expiration_ttl = "8904h"
EOHCL
if (echo $HOSTNAME | grep -q region2.dc3.server)
then
cat << EOHCL >> /etc/nomad/nomad.hcl
  replication_token = "${NOMAD_TOKEN}"
EOHCL
fi

cat << EOHCL >> /etc/nomad/nomad.hcl
}

ui {
  enabled =  true
  consul {
    ui_url = "https://localhost:8501/"
  }

  vault {
    ui_url = "https://localhost:8200/"
  }
}

consul {
  address = "consulserver:8501"
  grpc_address = "consulserver:8503"
  grpc_ca_file = "/scripts/tls/nomad-agent-ca.pem"
  ca_file = "/scripts/tls/nomad-agent-ca.pem"
  cert_file = "/scripts/tls/global-server-nomad.pem"
  key_file  = "/scripts/tls/global-server-nomad-key.pem"
  allow_unauthenticated = true
  server_service_name = "nomad"
  client_service_name = "nomad-client"
  auto_advertise      = true
  server_auto_join    = true
  client_auto_join    = true
  token               = "${CONSUL_HTTP_TOKEN}"
  ssl                 = true
  verify_ssl          = false
}

telemetry {
  collection_interval = "3s"
  disable_hostname = true
  prometheus_metrics = true
  publish_allocation_metrics = true
  publish_node_metrics = true
}


tls {
  http = true
  rpc  = true
  ca_file = "/scripts/tls/nomad-agent-ca.pem"
  cert_file = "/scripts/tls/global-server-nomad.pem"
  key_file = "/scripts/tls/global-server-nomad-key.pem"
  verify_server_hostname = false
  verify_https_client    = false
}

disable_update_check = true

log_rotate_duration = "24h"
log_rotate_max_files = "14"
log_level = "INFO"

http_api_response_headers {
  "Access-Control-Allow-Origin" = "*"
}

EOHCL

if (echo $HOSTNAME | grep -q client)
then
cat << EOHCL >> /etc/nomad/nomad.hcl
client {
  enabled = true
}

plugin "docker" {
  config {
    #infra_image = "gcr.io/google_containers/pause-amd64:3.2"
    extra_labels = ["job_name", "task_group_name", "task_name", "namespace", "node_name"]
    logging {
      type = "gelf"
      config = {
        "gelf-compression-type" = "none" # vector doesnt support gelf-compression?
        "gelf-address" = "udp://localhost:12201"
        "labels-regex" = "^(com.hashicorp.nomad)"
      }
    }
    gc {
      image       = true
      image_delay = "3h"
      container   = true
      dangling_containers {
        enabled        = true
        dry_run        = false
        period         = "15m"
        creation_grace = "5m"
      }
    }
    volumes {
      enabled = true
      selinuxlabel = "z"
    }
    allow_privileged = true
    allow_caps       = ["audit_write", "chown", "dac_override", "fowner", "fsetid", "kill", "mknod", "net_bind_service", "setfcap", "setgid", "setpcap", "setuid", "sys_chroot", "net_raw","sys_admin"]
  }
}
EOHCL
fi

if (echo $HOSTNAME | grep -q server)
then
cat << EOHCL >> /etc/nomad/nomad.hcl
server {
  authoritative_region = "region1"
  enabled          = true
  bootstrap_expect = 3
  encrypt = "0CMZJT5GUFOp19QiTxO5IDP+qCQhOntJsw3gV4ghaQ0="
}
EOHCL
fi

cat << EOHCL >> /tmp/anonymous.policy.hcl
namespace "default" {
  policy       = "read"
  capabilities = ["list-jobs", "read-job"]
}

agent {
  policy = "read"
}

operator {
  policy = "read"
}

quota {
  policy = "read"
}

node {
  policy = "read"
}

host_volume "*" {
  policy = "read"
}

EOHCL

#exit 0

if test -f /tmp/nomad-data/server/raft/raft.db
then
rm -rf /tmp/nomad-data/
fi

if test ! -L /usr/libexec/cni
then 
mkdir /usr/libexec
ln -s  /opt/cni/bin/ /usr/libexec/cni
fi

/usr/local/bin/nomad agent -config /etc/nomad & 
sleep 10

aclloop=0
hostname | grep -q region1.dc1.server$ && aclloop=1

if test $aclloop -eq 1;
then
echo ${NOMAD_TOKEN} > token
nomad acl bootstrap -tls-skip-verify token 2> /tmp/bootstrap 
nomad acl policy apply -description "Anonymous policy" anonymous /tmp/anonymous.policy.hcl 2>/tmp/bootstrap.anon
grep 'Bootstrap Token' /tmp/bootstrap && break
grep 'Successfully wrote' /tmp/bootstrap.anon && break
fi

hostname | grep -q client && /usr/local/bin/dockerd &


client=0
hostname | grep -q region1.dc1.client$ && client=1
if test $client -eq 1;
then
sleep 10
for job in $(seq 1 20)
do
cat << EOF > /tmp/test-job-${job}
#  from https://github.com/hashicorp/nomad/issues/24339
job "example-${job}" {
  group "cache" {
    task "redis" {
      driver = "docker"
      config {
        image          = "redis:7"
        # ports          = ["db"]
        auth_soft_fail = true
      }

      identity {
        env  = true
        file = true
      }

      resources {
        cpu    = 100
        memory = 128
      }
    }
  }
}
EOF

nomad job run -detach /tmp/test-job-${job} &
done
fi

wait
