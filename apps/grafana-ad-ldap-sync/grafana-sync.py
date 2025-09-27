#!/usr/bin/env python3
import requests
import random
import string
import socket
import os
import time
from requests.auth import HTTPBasicAuth
from ldap3 import Server, Connection, ALL, SUBTREE
import logging

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
GITLAB_CREATE_IGNOREUSER = os.getenv("GITLAB_CREATE_IGNOREUSER", "")  # eg... user1@dom,user2@dom .. csv list
GITLAB_REMOVE_BLOCKED = os.getenv("GITLAB_REMOVE_BLOCKED", False)
GITLAB_ENSURE_GROUP = os.getenv("GITLAB_ENSURE_GROUP", False)  # eg.... all-users-group
DEFAULT_REQUESTS_TIMEOUT = int(os.getenv("REQUESTS_TIMEOUT", "15"))  # seconds
DEFAULT_REQUESTS_RETRIES = int(os.getenv("REQUESTS_RETRIES", "3"))
SANITY_CHECK_COUNT_AD = int(os.getenv("SANITY_CHECK_COUNT_AD", "5"))  # at least expect 5 users in AD
SANITY_CHECK_COUNT_GRAFANA = int(os.getenv("SANITY_CHECK_COUNT_GRAFANA", "5"))  # at least expect 1 (admin) user on grafana
SANITY_CHECK_COUNT_GITLAB = int(os.getenv("SANITY_CHECK_COUNT_GITLAB", "5"))  # at least expect 2 users (root/ghost) on gitlab


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


class ColorCodes:
    RESET = "\033[0m"
    DEBUG = "\033[90m"  # Grey
    INFO = "\033[0m"  # Default (no color change)
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"  # Red
    CRITICAL = "\033[31;1m"  # Bold Red


class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: ColorCodes.DEBUG + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.INFO: ColorCodes.INFO + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.WARNING: ColorCodes.WARNING + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.ERROR: ColorCodes.ERROR + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.CRITICAL: ColorCodes.CRITICAL + "%(levelname)s: %(message)s" + ColorCodes.RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Get a logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the desired logging level

# Create a stream handler to output to the console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Set the custom formatter for the handler
ch.setFormatter(ColoredFormatter())

# Add the handler to the logger
logger.addHandler(ch)


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
                        response = requests.get(url, timeout=timeout, params=params, **kwargs)
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
                logger.debug(f"Status code: {response.status_code}, Response: {response.text}")
                return response
            elif response.status_code == 404 and "user not found" in response.text:
                return response
            elif response.status_code not in (200, 201):
                logger.debug(f"Status code: {response.status_code}, Response: {response.text}")
            response.raise_for_status()  # Raise error for bad status codes
            return response

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout on attempt {attempt} for {method.upper()} {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"⚠️ Request failed on attempt {attempt}: {e}")

        time.sleep(delay)

    logger.critical(f"❌ All {retries} attempts failed for {method.upper()} {url}")
    return None


def get_gitlab_users():
    response = make_request(
        "get",
        f"{GITLAB_URL}/api/v4/users",
        headers=GITLAB_HEADER,
        paginated=True,
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
    if len(gitlab_users) < SANITY_CHECK_COUNT_GITLAB:
        exit(f"GITLAB_usercount:{len(gitlab_users)} does not match minimal SANITY_CHECK_COUNT_GITLAB:{SANITY_CHECK_COUNT_GITLAB}")
    else:
        logger.debug(f"AD_usercount:{len(gitlab_users)} OK (>{SANITY_CHECK_COUNT_GITLAB} (SANITY_CHECK_COUNT_GITLAB)")
    return gitlab_users


def sync_ad_to_gitlab(ad_users, gitlab_users):
    # example usecase, gitlab with OAUTH SSO
    gitlab_user_emails = {user["email"] for user in gitlab_users}
    for user in gitlab_users:
        # do not block id=1 (root)
        # do not block users with 'bot' in note
        # only check for active user-states to block
        if user["id"] != 1 and user["email"] not in ad_users and "active" in user["state"] and "bot" not in user["note"]:
            logger.warning(f'❌user is not active, blocking: {user['email']}')
            action_gitlab_user(user, "block")
        # re-activate users if they were blocked but should be active.:
        if user["id"] != 1 and user["email"] in ad_users and "active" not in user["state"]:
            logger.warning(f"✅user is active, unblocking: {user}")
            action_gitlab_user(user, "unblock")
    for user in ad_users:
        if user not in gitlab_user_emails and user not in GITLAB_CREATE_IGNOREUSER.split(","):
            logger.warning(f"👤user not on gitlab, creating: {user}")
            action_gitlab_user(user, "create")
    if GITLAB_ENSURE_GROUP:
        gitlab_ensure_group_membership(gitlab_users)


def action_gitlab_user(user, action):
    if DRY_RUN:
        logger.debug(f"[DRY-RUN] Would {action} user: {user['email']}")
        return None
    else:
        if "create" in action:
            response = make_request(
                "post",
                f"{GITLAB_URL}/api/v4/users",
                headers=GITLAB_HEADER,
                json={
                    "email": user,
                    "username": user.split("@")[0],
                    "name": user.split("@")[0].replace(".", " "),
                    "password": generate_password(),
                    "skip_confirmation": True,
                },
            )
        else:
            response = make_request(
                "post",
                f"{GITLAB_URL}/api/v4/users/{user['id']}/{action}",
                headers=GITLAB_HEADER,
            )
        if response.status_code == 201 or response.status_code == 200:
            if "email" in user:
                logger.info(f"✅ User {user['email']} successfully {action}'ed.")
            else:
                logger.info(f"✅ User {user} successfully {action}'ed.")
        elif response.status_code == 403:
            logger.error("❌ Forbidden: You may not have permission to {action} users.")
        elif response.status_code == 404:
            logger.error("❌ User not found.")
        else:
            print("Unexpected", response.status_code, response.text)
            logger.critical(f"⚠️ Unexpected error: {response.status_code} - {response.text}")


def gitlab_ensure_group_membership(gitlab_users):
    group_name = GITLAB_ENSURE_GROUP
    group_id = gitlab_get_group_id(group_name)
    if not group_id:
        logger.error(f"❌ GitLab group '{group_name}' not found.")
        return

    current_members = gitlab_get_group_members(group_id)
    current_member_ids = {member["id"] for member in current_members}

    for user in gitlab_users:
        # if user not active, and its a current member, and GITLAB_REMOVE_BLOCKED, delete user from group
        if "active" not in user["state"]:
            if GITLAB_REMOVE_BLOCKED and user["id"] in current_member_ids:
                logger.debug(f"👥 removing GitLab user {user['email']} {user['state']} from {group_name}")
                gitlab_delete_user_from_group(group_id, user["id"])
            continue
        if user in GITLAB_CREATE_IGNOREUSER.split(","):
            logger.debug(f"👥 ignoring GitLab user {user['email']} -> in GITLAB_CREATE_IGNOREUSER")
            continue
        if user["id"] not in current_member_ids:
            logger.warning(f"👥 Adding GitLab user {user['email']} to group '{group_name}'")
            gitlab_add_user_to_group(group_id, user["id"])


def gitlab_get_group_id(group_name):
    response = make_request("get", f"{GITLAB_URL}/api/v4/groups", headers=GITLAB_HEADER, params={"search": group_name})

    # Ensure response is parsed as JSON
    if hasattr(response, "json"):
        response_data = response.json()
    else:
        response_data = response  # assume it's already a list of dicts

    for group in response_data:
        if isinstance(group, dict) and group.get("name") == group_name:
            return group["id"]
    return None


def gitlab_get_group_members(group_id):
    return make_request("get", f"{GITLAB_URL}/api/v4/groups/{group_id}/members", headers=GITLAB_HEADER, paginated=True)


def gitlab_delete_user_from_group(group_id, user_id):
    if DRY_RUN:
        logger.debug(f"[DRY-RUN] Would delete GitLab user {user_id} from group {group_id}")
        return
        # DELETE /groups/:id/members/:user_id
    response = make_request(
        "DELETE",
        f"{GITLAB_URL}/api/v4/groups/{group_id}/members/{user_id}",
        headers=GITLAB_HEADER,
    )
    if response.ok:
        logger.info(f"✅ GitLab user {user_id} deleted from group {group_id}")
    else:
        logger.error(f"❌ Failed to delete GitLab user {user_id} from group {group_id}: {response.text}")


def gitlab_add_user_to_group(group_id, user_id):
    if DRY_RUN:
        logger.debug(f"[DRY-RUN] Would add GitLab user {user_id} to group {group_id}")
        return
    response = make_request(
        "post",
        f"{GITLAB_URL}/api/v4/groups/{group_id}/members",
        headers=GITLAB_HEADER,
        json={
            "user_id": user_id,
            "access_level": 30,  # Developer access
        },
    )
    if response.ok:
        logger.info(f"✅ GitLab user {user_id} added to group {group_id}")
    else:
        logger.error(f"❌ Failed to add GitLab user {user_id} to group {group_id}: {response.text}")


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
        "get",
        f"{GRAFANA_URL}/api/teams/search",
        headers=HEADERS,
        auth=GRAFANA_AUTH,
    )
    if response.status_code == 200:
        teams = response.json().get("teams", [])
        return {team["name"]: {"id": team["id"]} for team in teams}
    elif response.status_code == 404:
        raise requests.exceptions.HTTPError(f"received {response.status_code} , did you specify correct grafana url/user/credentials?")
        return None
    return None


def get_grafana_users():
    response = make_request("get", f"{GRAFANA_URL}/api/users", headers=HEADERS, auth=GRAFANA_AUTH)
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
        logger.debug(f"[DRY-RUN] Would create Grafana user: {email}")
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
            logger.info(f"✅ Created Grafana user: {email}")
            return response.json().get("id")
        else:
            logger.error(f"❌ Failed to create user: {email} — {response.text}")
            return None


def create_team(team_name):
    if DRY_RUN:
        logger.debug(f"[DRY-RUN] Would create team: {team_name}")
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
            logger.info(f"✅ Created Team {team_name} ({response.status_code})")
            return response.json()["teamId"]
        else:
            logger.error(f"❌ Failed to create team: {team_name} ({response.status_code})")
            return None


def delete_team(team_id):
    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would delete team ID {team_id}")
    else:
        response = make_request(
            "delete",
            f"{GRAFANA_URL}/api/teams/{team_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )
        if response.status_code == 200:
            logger.warning(f"🗑️ Deleted team ID {team_id} ({response.status_code})")
            return True
        else:
            logger.error(f"❌ Failed to delete team ID {team_id} ({response.status_code})")
            return None


def delete_user(user_id):
    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would delete User ID {user_id}")
    else:
        response = make_request(
            "delete",
            f"{GRAFANA_URL}/api/admin/users/{user_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )
        if response.status_code == 200:
            logger.warning(f"🗑️ Deleted User ID {user_id} ({response.status_code})")
            return True
        else:
            logger.error(f"❌ Failed to delete User ID {user_id} ({response.status_code})")
            return None


def add_user_to_team(team_id, user_id):
    if DRY_RUN:
        logger.debug(f"[DRY-RUN] Would add user ID {user_id} to team ID {team_id}")
    else:
        response = make_request(
            "post",
            f"{GRAFANA_URL}/api/teams/{team_id}/members",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
            json={"userId": user_id},
        )
        if response.status_code == 200:
            logger.info(f"✅ added user {user_id} to team: {team_id} ({response.status_code})")
            return response
        else:
            logger.error(f"❌ Failed to add user {user_id} team: {team_id} ({response.status_code})")
            return None


def remove_user_from_team(team_id, user_id):
    if DRY_RUN:
        logger.debug(f"[DRY-RUN] Would remove user ID {user_id} from team ID {team_id}")
    else:
        response = make_request(
            "delete",
            f"{GRAFANA_URL}/api/teams/{team_id}/members/{user_id}",
            headers=HEADERS,
            auth=GRAFANA_AUTH,
        )
        if response.status_code == 200:
            logger.warning(f"🗑️  Deleted User ID {user_id} from team {team_id} ({response.status_code})")
            return True
        else:
            logger.error(f"❌ Failed to delete User ID {user_id} from team {team_id} ({response.status_code})")
            return None


# === SYNC FUNCTION ===
def sync_ad_to_grafana(ad_groups, ad_users):
    grafana_teams = get_grafana_teams()
    if not grafana_teams:
        exit("errors fetching Grafana teams")

    ad_group_names = set(ad_groups.keys())
    grafana_team_names = set(grafana_teams.keys())
    grafana_all_users = get_grafana_users()
    if len(grafana_all_users) < SANITY_CHECK_COUNT_GRAFANA:
        exit(f"GRAFANA_usercount:{len(grafana_all_users)} does not match minimal SANITY_CHECK_COUNT_GRAFANA:{SANITY_CHECK_COUNT_GRAFANA}")
    else:
        logger.debug(f"GRAFANA_usercount:{len(grafana_all_users)} OK (>{SANITY_CHECK_COUNT_GRAFANA} (SANITY_CHECK_COUNT_GRAFANA)")

    # === DELETE TEAMS NOT IN AD ===
    extra_teams = grafana_team_names - ad_group_names
    for team_name in extra_teams:
        team_id = grafana_teams[team_name]["id"]
        logger.warning(f"🗑️ Grafana team not in AD: {team_name}")
        delete_team(team_id)

    # === SYNC EXISTING OR CREATE MISSING TEAMS ===
    for group_name, ad_emails in ad_groups.items():
        logger.info(f"🔄 Syncing group: {group_name}")
        team = grafana_teams.get(group_name)
        if not team:
            logger.warning(f"🆕 Team missing in Grafana: {group_name}")
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
                    logger.warning(f"👤 User not found in Grafana: {email}")
                    user_id = create_grafana_user(email)
                if user_id:
                    logger.info(f"➕ Adding {email} to {group_name}")
                    add_user_to_team(team_id, user_id)
                else:
                    logger.warning(f"⚠️ User not found in Grafana: {email}")

        # Remove extra users
        for email in grafana_members:
            if email not in ad_emails:
                user_id = get_user_id_by_email(email)
                if not user_id:
                    logger.warning(f"🚫 Removing ghost user {email} from {group_name}")
                    remove_user_from_team(team_id, user_id)
                if user_id:
                    logger.warning(f"➖ Removing {email} from {group_name}")
                    remove_user_from_team(team_id, user_id)

    # === REMOVE USERS NO LONGER REFERENCED
    for grafana_user in grafana_all_users:
        if AD_DOMAIN in grafana_user:
            if grafana_user not in ad_users:
                logger.warning(f"➖ Removing {grafana_user} from grafana")
                delete_user(get_user_id_by_email(grafana_user))


# === RUN SYNC ===
if __name__ == "__main__":
    ad_groups = get_ad_groups_and_users()
    if not ad_groups:
        exit("errors fetching AD Info")
    ad_users = set(user for users in ad_groups.values() for user in users)
    if len(ad_users) < SANITY_CHECK_COUNT_AD:
        exit(f"AD_usercount:{len(ad_users)} does not match minimal SANITY_CHECK_COUNT_AD:{SANITY_CHECK_COUNT_AD}")
    else:
        logger.debug(f"AD_usercount:{len(ad_users)} OK (>{SANITY_CHECK_COUNT_AD} (SANITY_CHECK_COUNT_AD)")

    if GITLAB_TOKEN and GITLAB_URL:
        logger.debug("trying AD<->Gitlab sync")
        sync_ad_to_gitlab(ad_users, get_gitlab_users())

    logger.debug("trying AD<->Grafana sync")
    if "," in GRAFANA_URL:
        MULTIPLE_GRAFANA_URLS = GRAFANA_URL
        # assume multiple links given
        for GRAFANA_URL in MULTIPLE_GRAFANA_URLS.split(","):
            logger.debug(f"DRY_RUN: {DRY_RUN} @ {GRAFANA_URL}")
            sync_ad_to_grafana(ad_groups, ad_users)
    else:
        logger.debug(f"DRY_RUN: {DRY_RUN} @ {GRAFANA_URL}")
        sync_ad_to_grafana(ad_groups, ad_users)
