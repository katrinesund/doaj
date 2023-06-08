import csv
import json
import os

import requests
from requests.auth import HTTPBasicAuth

REPO = "https://api.github.com/repos/DOAJ/doajPM/"
PROJECTS = REPO + "projects"
PROJECT_NAME = "DOAJ Kanban"
DEFAULT_COLUMNS = ["Review", "In progress", "To Do"]
HEADERS = {"Accept": "application/vnd.github+json"}


class GithubReqSender:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.req_kwargs = self.create_github_request_kwargs()

    def create_github_request_kwargs(self) -> dict:
        req_kwargs = {'headers': dict(HEADERS)}
        if self.username is None or self.password is None:
            api_key = os.environ.get("DOAJ_GITHUB_KEY")
            if api_key:
                req_kwargs['headers']['Authorization'] = f'Bearer {api_key}'
            else:
                raise ValueError("No username or password provided and no GITHUB_USERNAME env variable set")
        else:
            req_kwargs['auth'] = HTTPBasicAuth(self.username, self.password)
        return req_kwargs

    def get(self, url):
        return requests.get(url, **self.req_kwargs)


def priorities(priorities_file, outfile, username=None, password=None, ):
    """

    ENV VARIABLE `DOAJ_GITHUB_KEY` will be used if username and password are not provided

    :param priorities_file:
    :param outfile:
    :param username:
    :param password:
    :return:
    """

    with open(priorities_file, "r") as f:
        reader = csv.DictReader(f)
        rules = []
        for row in reader:
            rules.append({
                "id": row["id"],
                "labels": [l.strip() for l in row["labels"].split(",") if l.strip() != ""],
                "columns": [c.strip() for c in row["columns"].split(",") if c.strip() != ""]
            })

    sender = GithubReqSender(username=username, password=password)
    resp = sender.get(PROJECTS)
    if resp.status_code >= 400:
        print(f'Error fetching github projects: {resp.status_code} {resp.text}')
        return
    project_list = resp.json()
    project = [p for p in project_list if p.get("name") == PROJECT_NAME][0]

    user_priorities = {}

    for priority in rules:
        print("Applying rule {x}".format(x=json.dumps(priority)))
        issues_by_user = _issues_by_user(project, priority, sender)
        print("Unfiltered matches for rule {x}".format(x=issues_by_user))
        for user, issues in issues_by_user.items():
            if user not in user_priorities:
                user_priorities[user] = []
            novel_issues = [i for i in issues if i not in [u[0] for u in user_priorities[user]]]
            print("Novel issues for rule for user {x} {y}".format(x=user, y=novel_issues))
            user_priorities[user] += [(n, priority.get("id")) for n in novel_issues]

    table = _tabulate(user_priorities)
    with open(outfile, "w") as f:
        writer = csv.writer(f)
        writer.writerows(table)

    print(table)


def _issues_by_user(project, priority, sender):
    cols = priority.get("columns", [])
    if len(cols) == 0:
        cols = DEFAULT_COLUMNS

    user_issues = {}
    for col in cols:
        column_issues = _get_column_issues(project, col, sender)
        labels = priority.get("labels", [])
        if len(labels) == 0:
            _split_by_user(user_issues, column_issues)
            continue

        labelled_issues = _filter_issues_by_label(column_issues, labels)
        _split_by_user(user_issues, labelled_issues)

    return user_issues


COLUMN_CACHE = {}


def _get_column_issues(project, col, sender: GithubReqSender):
    if col in COLUMN_CACHE:
        return COLUMN_CACHE[col]

    print("Fetching column issues {x}".format(x=col))
    cols_url = project.get("columns_url")
    resp = sender.get(cols_url)
    col_data = resp.json()

    column_record = [c for c in col_data if c.get("name") == col][0]
    cards_url = column_record.get("cards_url")

    resp = sender.get(cards_url)
    cards_data = resp.json()

    issues = []
    for card_data in cards_data:
        content_url = card_data.get("content_url")
        resp = sender.get(content_url)
        issue_data = resp.json()
        issues.append(issue_data)

    COLUMN_CACHE[col] = issues
    print("Column issues {x}".format(x=[i.get("url") for i in issues]))
    return issues


def _filter_issues_by_label(issues, labels):
    filtered = []
    for issue in issues:
        issue_labels = issue.get("labels", [])
        label_names = [l.get("name") for l in issue_labels]
        found = 0
        for label in labels:
            if label in label_names:
                found += 1
        if found == len(labels):
            filtered.append(issue)
    return filtered


def _split_by_user(registry, issues):
    for issue in issues:
        assignees = issue.get("assignees", [])
        if len(assignees) == 0:
            if "Claimable" not in registry:
                registry["Claimable"] = []
            registry["Claimable"].append(issue.get("url"))

        for assignee in assignees:
            login = assignee.get("login")
            if login not in registry:
                registry[login] = []
            registry[login].append(issue.get("url"))


def _tabulate(user_priorities):
    users = list(user_priorities.keys())
    users.sort(key=lambda x: x.lower() if x != "Claimable" else "zzzzzz")

    header = []
    for user in users:
        header += [user, user]
    table = [header]

    i = 0
    while True:
        row = []
        for user in users:
            val = ""
            rule = ""
            if len(user_priorities[user]) > i:
                rec = user_priorities[user][i]
                val = _ui_url(rec[0])  # + " (" + rec[1] + ")"
                rule = rec[1]
            row += [rule, val]

        is_empty = [c for c in row if c != ""]
        if len(is_empty) == 0:
            break

        table.append(row)
        i += 1

    return table


def _ui_url(api_url):
    return "https://github.com/" + api_url[len("https://api.github.com/repos/"):]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")
    parser.add_argument("-r", "--rules")
    parser.add_argument("-o", "--out")
    args = parser.parse_args()

    priorities(args.rules, args.out,
               username=args.username, password=args.password, )
