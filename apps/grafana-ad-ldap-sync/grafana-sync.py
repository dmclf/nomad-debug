#!/usr/bin/env python3
import requests
import random
import string
import socket
import os
import time
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
USER_ATTR = os.getenv("USER_ATTR", "mail")  # "mail" or "userPrincipalName"
STATUS_ATTR = "userAccountControl"
HEADERS = {"Content-Type": "application/json"}
GRAFANA_AUTH = HTTPBasicAuth(GRAFANA_SYNC_USER, GRAFANA_SYNC_PASSWORD)
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_TOKEN_TYPE = os.getenv("GITLAB_TOKEN_TYPE", "PRIVATE-TOKEN")  # ex.. PRIVATE-TOKEN
GITLAB_URL = os.getenv("GITLAB_URL")  # ex.. https://gitlab.my-ad-domain
GITLAB_HEADER = {GITLAB_TOKEN_TYPE: GITLAB_TOKEN}
DEFAULT_REQUESTS_TIMEOUT = int(os.getenv("REQUESTS_TIMEOUT", "15"))  # seconds
DEFAULT_REQUESTS_RETRIES = int(os.getenv("REQUESTS_RETRIES", "3"))


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


def make_request(
    method,
    url,
    paginated=False,
    retries=DEFAULT_REQUESTS_RETRIES,
    delay=2,
    timeout=DEFAULT_REQUESTS_TIMEOUT,
    **kwargs,
):
    method = method.lower()
    assert method in ["get", "post", "delete"], "Unsupported HTTP method"

    for attempt in range(1, retries + 1):
        try:
            if method == "get":
                if paginated:
                    all_items = []
                    page = 1
                    params = {}
                    while True:
                        params.update({"page": page})
                        response = requests.get(
                            url, timeout=timeout, params=params, **kwargs
                        )
                        data = response.json()
                        all_items.extend(data)
                        next_page = response.headers.get("X-Next-Page")
                        if not next_page:
                            break
                        page = int(next_page)
                    return all_items
                else:
                    response = requests.get(url, timeout=timeout, **kwargs)

            elif method == "post":
                response = requests.post(url, timeout=timeout, **kwargs)
            elif method == "delete":
                response = requests.delete(url, timeout=timeout, **kwargs)

            if response.status_code == 400 and "already added" in response.text:
                print(response.status_code, response.text)
                return response
            elif response.status_code == 404 and "user not found" in response.text:
                return response
            elif response.status_code != 200:
                print(response.status_code, response.text)
            response.raise_for_status()  # Raise error for bad status codes
            return response

        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout on attempt {attempt} for {method.upper()} {url}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request failed on attempt {attempt}: {e}")

        time.sleep(delay)

    print(f"❌ All {retries} attempts failed for {method.upper()} {url}")
    return None


def get_gitlab_users():
    response = make_request(
        "get", f"{GITLAB_URL}/api/v4/users", headers=GITLAB_HEADER, paginated=True
    )
    gitlab_users = [
        {
            "email": x["email"],
            "state": x["state"],
            "id": x["id"],
            "bot": x["bot"],
            "username": x["username"],
            "is_admin": x["is_admin"],
            "note": x["note"],
        }
        for x in response
        if not x["bot"] and AD_DOMAIN in x["email"]
    ]
    return gitlab_users


def sync_ad_to_gitlab(ad_groups, gitlab_users):
    # example usecase, gitlab with OAUTH SSO
    ad_users = set(user for users in ad_groups.values() for user in users)
    for user in gitlab_users:
        # do not block id=1 (root)
        # do not block users with 'bot' in note
        # only check for active user-states to block
        if (
            user["id"] != 1
            and user["email"] not in ad_users
            and "active" in user["state"]
            and "bot" not in user["note"]
        ):
            print(f'user is not active, blocking: {user['email']}')
            action_gitlab_user(user, "block")

        # re-activate users if they were blocked but should be active.:
        if (
            user["id"] != 1
            and user["email"] in ad_users
            and "active" not in user["state"]
        ):
            print(f"user is active, unblocking: {user}")
            action_gitlab_user(user, "unblock")
        # delete_gitlab_user(user)  # Your custom deletion function


def action_gitlab_user(user, action):
    if DRY_RUN:
        print(f"[DRY-RUN] Would block user: {user['email']}")
        return None
    else:
        response = make_request(
            "post",
            f"{GITLAB_URL}/api/v4/users/{user['id']}/{action}",
            headers=GITLAB_HEADER,
        )
        if response.status_code == 201:
            print(f"✅ User {user['email']} successfully {action}'ed.")
        elif response.status_code == 403:
            print("❌ Forbidden: You may not have permission to {action} users.")
        elif response.status_code == 404:
            print("❌ User not found.")
        else:
            print(f"⚠️ Unexpected error: {response.status_code} - {response.text}")


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
                    emails.append(email.value.lower())

        ad_data[group_name] = emails

    conn.unbind()
    return ad_data


# === GRAFANA API FUNCTIONS ===
def get_grafana_teams():
    response = make_request(
        "get", f"{GRAFANA_URL}/api/teams/search", headers=HEADERS, auth=GRAFANA_AUTH
    )
    if response.status_code == 200:
        teams = response.json().get("teams", [])
        return {team["name"]: {"id": team["id"]} for team in teams}
    elif response.status_code == 404:
        raise requests.exceptions.HTTPError(
            f"received {response.status_code} , did you specify correct grafana url/user/credentials?"
        )
        return None
    return None


def get_grafana_users():
    response = make_request(
        "get", f"{GRAFANA_URL}/api/users", headers=HEADERS, auth=GRAFANA_AUTH
    )
    if response.status_code == 200:
        users = response.json()
        return [member["email"] for member in users]
    return None


def get_team_members(team_id):
    response = make_request(
        "get",
        f"{GRAFANA_URL}/api/teams/{team_id}/members",
        headers=HEADERS,
        auth=GRAFANA_AUTH,
    )
    if response.status_code == 200:
        members = response.json()
        return [member["email"] for member in members]
    return None


def get_user_id_by_email(email):
    response = make_request(
        "get",
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
        "password": generate_password(),
    }
    if DRY_RUN:
        print(f"[DRY-RUN] Would create Grafana user: {email}")
        return None
    else:
        response = make_request(
            "post",
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
    else:
        response = make_request(
            "post",
            f"{GRAFANA_URL}/api/teams",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
            json={"name": team_name},
        )
        if response.status_code == 200:
            print(f"✅ Created Team {team_name} ({response.status_code})")
            return response.json()["teamId"]
        else:
            print(f"❌ Failed to create team: {team_name} ({response.status_code})")
            return None


def delete_team(team_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would delete team ID {team_id}")
    else:
        response = make_request(
            "delete",
            f"{GRAFANA_URL}/api/teams/{team_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )
        if response.status_code == 200:
            print(f"🗑️ Deleted team ID {team_id} ({response.status_code})")
            return True
        else:
            print(f"❌ Failed to delete team ID {team_id} ({response.status_code})")
            return None


def delete_user(user_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would delete User ID {user_id}")
    else:
        response = make_request(
            "delete",
            f"{GRAFANA_URL}/api/admin/users/{user_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )
        if response.status_code == 200:
            print(f"🗑️ Deleted User ID {user_id} ({response.status_code})")
            return True
        else:
            print(f"❌ Failed to delete User ID {user_id} ({response.status_code})")
            return None


def add_user_to_team(team_id, user_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would add user ID {user_id} to team ID {team_id}")
    else:
        response = make_request(
            "post",
            f"{GRAFANA_URL}/api/teams/{team_id}/members",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
            json={"userId": user_id},
        )
        if response.status_code == 200:
            print(
                f"✅ added user {user_id} to team: {team_id} ({response.status_code})"
            )
            return response
        else:
            print(
                f"❌ Failed to add user {user_id} team: {team_id} ({response.status_code})"
            )
            return None


def remove_user_from_team(team_id, user_id):
    if DRY_RUN:
        print(f"[DRY-RUN] Would remove user ID {user_id} from team ID {team_id}")
    else:
        response = make_request(
            "delete",
            f"{GRAFANA_URL}/api/teams/{team_id}/members/{user_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )
        if response.status_code == 200:
            print(
                f"🗑️  Deleted User ID {user_id} from team {team_id} ({response.status_code})"
            )
            return True
        else:
            print(
                f"❌ Failed to delete User ID {user_id} from team {team_id} ({response.status_code})"
            )
            return None


# === SYNC FUNCTION ===
def sync_ad_to_grafana(ad_groups):
    grafana_teams = get_grafana_teams()
    if not grafana_teams:
        exit("errors fetching Grafana teams")

    ad_group_names = set(ad_groups.keys())
    grafana_team_names = set(grafana_teams.keys())
    grafana_all_users = get_grafana_users()

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

    # === REMOVE USERS NO LONGER REFERENCED
    ad_users = set(user for users in ad_groups.values() for user in users)
    for grafana_user in grafana_all_users:
        if AD_DOMAIN in grafana_user:
            if grafana_user not in ad_users:
                print(f"➖ Removing {grafana_user} from grafana")
                delete_user(get_user_id_by_email(grafana_user))


# === RUN SYNC ===
if __name__ == "__main__":
    ad_groups = get_ad_groups_and_users()
    if not ad_groups:
        exit("errors fetching AD Info")

    if GITLAB_TOKEN and GITLAB_URL:
        print("trying AD<->Gitlab sync")
        sync_ad_to_gitlab(ad_groups, get_gitlab_users())

    print("trying AD<->Grafana sync")
    if "," in GRAFANA_URL:
        MULTIPLE_GRAFANA_URLS = GRAFANA_URL
        # assume multiple links given
        for GRAFANA_URL in MULTIPLE_GRAFANA_URLS.split(","):
            print(f"DRY_RUN: {DRY_RUN} @ {GRAFANA_URL}")
            sync_ad_to_grafana(ad_groups)
    else:
        print(f"DRY_RUN: {DRY_RUN} @ {GRAFANA_URL}")
        sync_ad_to_grafana(ad_groups)
