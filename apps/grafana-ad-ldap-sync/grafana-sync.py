#!/usr/bin/env python3
import requests
import random
import string
import socket
import os
from requests.auth import HTTPBasicAuth
from ldap3 import Server, Connection, ALL, SUBTREE

# CONFIGURATION
AD_DOMAIN = os.getenv("AD_DOMAIN", "my-ad-domain")
GRAFANA_URL = os.getenv("GRAFANA_URL", f"https://my-grafana-url.{AD_DOMAIN}")
FILTER_LDAP_SERVER = os.getenv("FILTER_LDAP_SERVER", "10.")
LDAP_SERVER = f"ldap://{random.choice([ip for ip in list({result[4][0] for result in socket.getaddrinfo(AD_DOMAIN, None)}) if ip.startswith(FILTER_LDAP_SERVER)])}"
LDAP_USER = os.getenv("LDAP_USER")
LDAP_PASSWORD = os.getenv("LDAP_PASSWORD")
GROUP_BASE_DN = os.getenv("GROUP_BASE_DN")
BASE_DN = os.getenv("BASE_DN")
GRAFANA_SYNC_USER = os.getenv("GRAFANA_SYNC_USER")
GRAFANA_SYNC_PASSWORD = os.getenv("GRAFANA_SYNC_PASSWORD")
GROUP_FILTER = "(objectClass=group)"
USER_ATTR = "mail"  # or "userPrincipalName"
STATUS_ATTR = "userAccountControl"
HEADERS = {"Content-Type": "application/json"}
GRAFANA_AUTH = HTTPBasicAuth(GRAFANA_SYNC_USER, GRAFANA_SYNC_PASSWORD)


def parse_bool(value: str) -> bool:
    value_lower = value.strip().lower()
    if value_lower == "true":
        return True
    elif value_lower == "false":
        return False
    else:
        raise ValueError(f"Invalid boolean string: '{value}'")

# simplistic dry-run toggle
DRY_RUN = parse_bool(os.getenv("DRY_RUN", "True"))

def is_enabled(uac_attr):
    try:
        uac_value = int(uac_attr.value)  # Extract the actual integer value
        return not (uac_value & 2)  # 2 = ACCOUNTDISABLE
    except (TypeError, ValueError, AttributeError):
        return False  # Treat as disabled if value is missing or invalid


def generate_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(random.choice(characters) for _ in range(length))
    return password


def get_ad_groups_and_users():
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(server, LDAP_USER, LDAP_PASSWORD, auto_bind=True)

    # Search for all groups
    conn.search(
        search_base=GROUP_BASE_DN,
        search_filter=GROUP_FILTER,
        search_scope=SUBTREE,
        attributes=["cn", "member"],
    )

    ad_data = {}

    for entry in conn.entries:
        group_name = entry.cn.value
        if len(entry.member.values) == 0:
            continue
        members = entry.member.values if "member" in entry else []

        emails = []
        for member_dn in members:
            conn.search(
                search_base=member_dn,
                search_filter="(objectClass=user)",
                search_scope=SUBTREE,
                attributes=[USER_ATTR, STATUS_ATTR],
            )
            if conn.entries:
                user_entry = conn.entries[0]
                email = getattr(user_entry, USER_ATTR, None)
                status = getattr(user_entry, STATUS_ATTR, None)
                if email and is_enabled(status):
                    emails.append(email.value)

        ad_data[group_name] = emails

    conn.unbind()
    return ad_data


# === GRAFANA API FUNCTIONS ===
def get_grafana_teams():
    response = requests.get(
        f"{GRAFANA_URL}/api/teams/search", headers=HEADERS, auth=GRAFANA_AUTH
    )
    teams = response.json().get("teams", [])
    return {team["name"]: {"id": team["id"]} for team in teams}


def get_team_members(team_id):
    response = requests.get(
        f"{GRAFANA_URL}/api/teams/{team_id}/members", headers=HEADERS, auth=GRAFANA_AUTH
    )
    members = response.json()
    return [member["email"] for member in members]


def get_user_id_by_email(email):
    response = requests.get(
        f"{GRAFANA_URL}/api/users/lookup?loginOrEmail={email}",
        headers=HEADERS,
        auth=GRAFANA_AUTH,
    )
    if response.status_code == 200:
        return response.json().get("id")
    return None


def create_grafana_user(email, name=None):
    payload = {
        "name": name or email.split("@")[0],
        "email": email,
        "login": email,
        "password": generate_password,
    }
    if DRY_RUN:
        print(f"[DRY-RUN] Would create Grafana user: {email}")
        return None
    response = requests.post(
        f"{GRAFANA_URL}/api/admin/users",
        headers=HEADERS,
        auth=GRAFANA_AUTH,
        json=payload,
    )
    if response.status_code == 200:
        print(f"✅ Created Grafana user: {email}")
        return response.json().get("id")
    else:
        print(f"❌ Failed to create user: {email} — {response.text}")
        return None


def create_team(team_name):
    if DRY_RUN:
        print(f"[DRY-RUN] Would create team: {team_name}")
        return None
    response = requests.post(
        f"{GRAFANA_URL}/api/teams",
        headers=HEADERS,
        auth=GRAFANA_AUTH,
        json={"name": team_name},
    )
    if response.status_code == 200:
        return response.json()["teamId"]
    print(f"❌ Failed to create team: {team_name}")
    return None


def delete_team(team_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would delete team ID {team_id}")
    else:
        response = requests.delete(
            f"{GRAFANA_URL}/api/teams/{team_id}", headers=HEADERS, auth=GRAFANA_AUTH
        )
        if response.status_code == 200:
            print(f"🗑️ Deleted team ID {team_id}")
        else:
            print(f"❌ Failed to delete team ID {team_id}")


def add_user_to_team(team_id, user_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would add user ID {user_id} to team ID {team_id}")
    else:
        requests.post(
            f"{GRAFANA_URL}/api/teams/{team_id}/members",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
            json={"userId": user_id},
        )


def remove_user_from_team(team_id, user_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would remove user ID {user_id} from team ID {team_id}")
    else:
        requests.delete(
            f"{GRAFANA_URL}/api/teams/{team_id}/members/{user_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )


# === SYNC FUNCTION ===
def sync_ad_to_grafana():
    ad_groups = get_ad_groups_and_users()
    grafana_teams = get_grafana_teams()

    ad_group_names = set(ad_groups.keys())
    grafana_team_names = set(grafana_teams.keys())

    # === DELETE TEAMS NOT IN AD ===
    extra_teams = grafana_team_names - ad_group_names
    for team_name in extra_teams:
        team_id = grafana_teams[team_name]["id"]
        print(f"🗑️ Grafana team not in AD: {team_name}")
        delete_team(team_id)

    # === SYNC EXISTING OR CREATE MISSING TEAMS ===
    for group_name, ad_emails in ad_groups.items():
        print(f"🔄 Syncing group: {group_name}")
        team = grafana_teams.get(group_name)
        if not team:
            print(f"🆕 Team missing in Grafana: {group_name}")
            team_id = create_team(group_name)
            if team_id is None and DRY_RUN:
                continue
        else:
            team_id = team["id"]

        grafana_members = get_team_members(team_id)

        # Add missing users
        for email in ad_emails:
            if email not in grafana_members:
                user_id = get_user_id_by_email(email)
                if not user_id:
                    print(f"👤 User not found in Grafana: {email}")
                    user_id = create_grafana_user(email)
                if user_id:
                    print(f"➕ Adding {email} to {group_name}")
                    add_user_to_team(team_id, user_id)
                else:
                    print(f"⚠️ User not found in Grafana: {email}")

        # Remove extra users
        for email in grafana_members:
            if email not in ad_emails:
                user_id = get_user_id_by_email(email)
                if not user_id:
                    print(f"🚫 Removing ghost user {email} from {group_name}")
                    remove_user_from_team(team_id, user_id)
                if user_id:
                    print(f"➖ Removing {email} from {group_name}")
                    remove_user_from_team(team_id, user_id)


# === RUN SYNC ===
if __name__ == "__main__":
    print(f"DRY_RUN: {DRY_RUN} @ {GRAFANA_URL}")
    sync_ad_to_grafana()
