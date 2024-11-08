#!/bin/sh
if test ! -f /scripts/tls/nomad-agent-ca.pem
then
	mkdir /scripts/tls
        cd /scripts/tls
        nomad tls ca create
        nomad tls cert create -server -region global
        #nomad tls cert create -client
        #nomad tls cert create -cli
	chmod 644 /scripts/tls/*pem
fi

mkdir /etc/consul
cat << EOF > /etc/consul/consul.hcl
datacenter = "global"
primary_datacenter = "global"
data_dir = "/tmp/consul-data"
bind_addr = "0.0.0.0"
client_addr = "0.0.0.0"
server = true
bootstrap_expect=1

ui_config {
  enabled = true
}
peering {
  enabled = true
}
connect {
  enabled = true
}

encrypt = "HpjGMVT26dfxEBAELf4iztKCBZw2RikX7co3GEl7FB8="
encrypt_verify_incoming = true
encrypt_verify_outgoing = true

tls = {
  defaults = {
    verify_incoming = false
    verify_outgoing = true
    ca_file = "/scripts/tls/nomad-agent-ca.pem"
    cert_file = "/scripts/tls/global-server-nomad.pem"
    key_file = "/scripts/tls/global-server-nomad-key.pem"
  }
  internal_rpc = {
    verify_server_hostname = false
    verify_incoming = false
  }
}

auto_encrypt = {
  allow_tls = true
}


acl = {
  enabled = true
  default_policy = "allow"
  down_policy = "extend-cache"
  enable_key_list_policy = true
  enable_token_persistence = true
}

ports {
  http  = 8500
  https = 8501
  grpc = 8502
  grpc_tls = 8503
}

disable_update_check = true
disable_remote_exec = true
enable_script_checks = true
EOF

if test -d /tmp/consul-data/raft;then
rm -rf /tmp/consul-data
fi

hostname | grep -q server && /usr/local/bin/consul agent -config-dir=/etc/consul/ &
while true;do 
echo "${CONSUL_HTTP_TOKEN}" | consul acl bootstrap -http-addr=https://localhost:8501 -  2> /tmp/bootstrap-response
grep 'Bootstrap Token' /tmp/bootstrap-response && break
grep 'ACL bootstrap no longer allowed' /tmp/bootstrap-response && break
sleep 3
done

wait

