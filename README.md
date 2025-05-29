# Repo to aid with reproducing issues on Nomad

# Nomad infra 

## overview

| Cluster       | Nomad Regions | Nomad Datacenters | Nomad Servers | Nomad Clients | Nomad Allocations | Nomad Total CPU | Nomad Total Memory | Consul Datacenters |
| :------------ | :-----------: | :---------------: | :-----------: | :-----------: | :---------------: | :-------------: | :----------------: | :----------------: |
| Development   | 1             | 1                 | 3             | 2             | 27                | 9 Ghz           | 16  GiB            | 1                  |
| Staging/UAT   | 2             | 4                 | 9             | 7             | 190               | 200 Ghz         | 240 GiB            | 2                  |
| Production    | 2             | 3                 | 9             | 17            | 410               | 2655 Ghz        | 1873 GiB           | 2                  |

- OIDC auth
- [Traefik & Consul Catalog](https://doc.traefik.io/traefik/providers/consul-catalog/)
 - [Oauth2Proxy](https://github.com/oauth2-proxy/oauth2-proxy)

- Staging/UAT and Production clusters
 - Consul [WAN federated datacenters](https://developer.hashicorp.com/consul/tutorials/archive/federation-gossip-wan)
 - Nomad [Multi-region federation](https://developer.hashicorp.com/nomad/tutorials/manage-clusters/federation)

## setup

- [Ubuntu (22.04)](https://releases.ubuntu.com/jammy/)
- servers/masters -> Nomad + Consul + Unbound (service.consul) + Traefik + Keepalived (vm)
  - keepalived for centralized UI and APP differentation.
    - example 
      - nomad-development.company.com   IN A -> nomad-development-keepalived-VIP
        *.nomad-development.company.com IN A -> nomad-development-keepalived-VIP
      - nomad-staging.company.com       IN A -> nomad-staging-keepalived-VIP
        *.nomad-staging.company.com     IN A -> nomad-staging-keepalived-VIP
      - nomad-production.company.com    IN A -> nomad-production-keepalived-VIP
        *.nomad-production.company.com  IN A -> nomad-production-keepalived-VIP
        -  why? 
          - OIDC / Oauth like to have consistent callback-URL's, so if you login to Nomad-UI with OIDC, and a server fails, users can just keep using same login-url.
          - in jobspecs, you can work with templated traefik-rules to more easily automate a staging-job to get templated to jobname.nomad-staging.company.com
          - and if you leverage Letsencrypt (natively supported by Traefik) less hassle with SSL certificates.
            - of course, traefik also supports including custom certificates if preferred.
          - developers can work without too much manual interference needed.
- Clients/Workers -> Nomad/Consul + Dockerd
  - DNS resolvers set to masters (service.consul)
- Job deployments through [Gitlab CI/CD](https://about.gitlab.com/)
  - custom templating on gitlab-side & on nomad side with [Levant](https://github.com/hashicorp/levant)

## default nomad job stack per environment

* may indicate jobs that do not run exactly on all environments.

- infrastructure/devops system jobs
  - [CSI-nfs](https://github.com/kubernetes-csi/csi-driver-nfs)
  - [CSI-smb](https://github.com/kubernetes-csi/csi-driver-smb)
  - [alloy](https://grafana.com/oss/alloy)
  - [cadvisor](https://github.com/google/cadvisor)
  - [vector](https://github.com/vectordotdev/vector)
  - ~~[promtail](https://grafana.com/oss/promtail)~~
- infrastructure/devops service jobs
  - [custom traefik errorpage](https://github.com/tarampampam/error-pages)
  - [elastic logstash](https://www.elastic.co/logstash)
  - [loki](https://grafana.com/oss/loki/)
  - [nomad-autoscaler](https://github.com/hashicorp/nomad-autoscaler)
  - [oauth2proxy](https://github.com/oauth2-proxy/oauth2-proxy)
  - [pyroscope](https://grafana.com/oss/pyroscope/)
  - [vault](https://github.com/hashicorp/vault)
    - also used to template secrets, again, in above setup, job-specs can be same, and environment helps differentiate for production / staging / development (as vault's are environment-specific)
    - [kv](https://developer.hashicorp.com/vault/docs/secrets/kv) / [totp](https://developer.hashicorp.com/vault/docs/secrets/totp) / [ssh](https://developer.hashicorp.com/vault/docs/secrets/ssh/signed-ssh-certificates) / [database](https://developer.hashicorp.com/vault/docs/secrets/databases)
  - [grafana](https://grafana.com/oss/grafana/)
  - * [netbox](https://github.com/netbox-community/netbox)
    - API backend for prometheus configuration
  - * [Ubuntu mirror]
  - * docker-registry-cache
  - * [devpi pypi.org caching](https://github.com/devpi/devpi)
  - monitoring stack
    - [alertmanager](https://github.com/prometheus/alertmanager)
    - [karma - unified alertmanager dashboard](https://github.com/prymitive/karma)
    - [ms-teams handlers](https://github.com/prometheus-msteams/prometheus-msteams)
    - [prometheus](https://github.com/prometheus/prometheus)
    - [thanos](https://github.com/thanos-io/thanos)
    - exporters
      - [blackbox](https://github.com/prometheus/blackbox_exporter)
        - SSH / VNC / SMTP / TCP / DNS probing
        - URL monitoring
          - certificate expiry monitoring
      - [clickhouse-exporter](https://clickhouse.com/docs/en/integrations/prometheus)
      - [graphite-exporter](https://github.com/prometheus/graphite_exporter)
      - [idrac-exporter](https://github.com/mrlhansen/idrac_exporter)
      - [mysql-exporter](https://github.com/prometheus/mysqld_exporter)
      - [postgres-exporter](https://github.com/prometheus-community/postgres_exporter)
      - [redis-exporter](https://github.com/oliver006/redis_exporter)
      - [rundeck-exporter](https://github.com/phsmith/rundeck_exporter)
      - [smokeping-prober](https://github.com/SuperQ/smokeping_prober)
      - [snmp-exporter](https://github.com/prometheus/snmp_exporter)
      - [solace-exporter](https://github.com/solacecommunity/solace-prometheus-exporter)
      - [vmware-exporter](https://github.com/pryorda/vmware_exporter)
      - proprietary custom exporters
