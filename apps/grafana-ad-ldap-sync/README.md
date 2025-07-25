# sample grafana syncing helper for AD <-> local grafana instance (OSS)

sample tooling to help sync a local AD-server against a OSS grafana 
where the OSS grafana might be OIDC/OAUTH enabled and only needs user/group(/team) syncing and passwords would be through SSO.

would use AD as source-of-truth and delete/create users/teams on grafana
if a user or group does not exist on AD, they would be deleted from grafana.

example usage:

`AD_DOMAIN`: *AD has tendency to advertise its domain-controllers on its domain, 
           so if your domain = mydomain.com then it will use the A-record responses to randomly pick a server.*

`FILTER_LDAP_SERVER`: *to filter the IP-response, example, 10. would filter ^10.*

`LDAP_USER`: *the bind-cn for the ldap query-user*

`LDAP_PASSWORD`: *password for above*

`BASE_DN`: *base-dn to search users under*

`GROUP_BASE_DN`: *base-dn to search for groups*

`GRAFANA_SYNC_USER`: *username for grafana (needs admin power)*

`GRAFANA_SYNC_PASSWORD`: *password for grafana (needs admin power)*

`GRAFANA_URL`: *URL where grafana can be reached, example: https://grafana.mydomain.com*

`DRY_RUN`: `*true|false` (case-insensitive) *perform dry-run and show what would be done*


```
docker run -it --rm \
    -e AD_DOMAIN=mydomain.com -e GRAFANA_URL=https://grafana.mydomain.com \
    -e FILTER_LDAP_SERVER=10.20.30 \
    -e LDAP_USER="CN=grafanasyncuser,OU=Service Accounts,OU=Users,DC=mydomain,DC=com" \
    -e LDAP_PASSWORD="vault-injected" \
    -e GROUP_BASE_DN="OU=Groups,DC=mydomain,DC=com" \
    -e BASE_DN="DC=mydomain,DC=com" \
    -e GRAFANA_SYNC_USER="grafana-sync-admin" \
    -e GRAFANA_SYNC_PASSWORD="vault-injected" \
    -e DRY_RUN=true \
    dmclf/grafana-ad-oss-sync:0.1a`
```
