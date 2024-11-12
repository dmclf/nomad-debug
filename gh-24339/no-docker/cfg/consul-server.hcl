datacenter = "global"
primary_datacenter = "global"
data_dir = "/tmp/consul-data"
bind_addr = "127.0.0.1"
client_addr = "0.0.0.0"
server = true
bootstrap = true

ui_config {
  enabled = true
}
peering {
  enabled = true
}
connect {
  enabled = true
}

ports {
  http  = 8500
}

disable_update_check = true
disable_remote_exec = true
enable_script_checks = true
