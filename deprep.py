#!/usr/bin/env python

import sys
import re
import csv
import urllib.parse
import logging
import requests
from environs import Env
import github

env = Env()
env.read_env()
github_api = github.Github(env("GITHUB_API_TOKEN"))

def parse_overrides(f):
    d = {}
    for s in f:
        s = s.strip()
        logging.info(f"Override {s}")
        k, v = s.split()
        d[k] = v
    return d

parse_requirement_re = re.compile("^(.*)==(.*?)$")

def parse_requirement(s):
    s = s.strip()
    if s.startswith("-e"):
        logging.warning(f"Skipped {s}")
        return None, None

    logging.info(f"Parsing {s}")
    x = s.split(";")[0]
    m = parse_requirement_re.search(x)
    if m:
        ret = m.group(1, 2)
        logging.info(f"Extracted {ret}")
        return ret
    else:
        raise ValueError(f"Failed to parse {s}")


github_url_re = re.compile("^https?://github.com.*")

def get_source_url_from_pypi(name, overrides):
    obj = requests.get(f"https://pypi.org/pypi/{name}/json").json()
    urls = obj["info"]["project_urls"]

    if name in overrides:
        return overrides[name]

    if urls:
        for x in ("Source", "Code", "Source Code", "Homepage", "Repository"):
            url = urls.get(x)
            if url and github_url_re.search(url):
                return url

    logging.warning(f"Couldn't find source URL for {name} in {urls!r}")
    return None


def get_github_license(url):
    if not url:
        return None, None
    u = urllib.parse.urlsplit(str(url))
    repo_name = "/".join(u.path.strip("/").split("/", 2)[:2])
    logging.info(f"Retrieving repo {repo_name}")
    repo = github_api.get_repo(repo_name)
    try:
        license = repo.get_license()
    except github.GithubException:
        logging.warning(f"Couldn't retrieve license for {repo_name}")
        return None, None
    return license.license.name, license.url


def process_requirement(s, overrides):
    name, version = parse_requirement(s)
    if not name:
        logging.warning(f"Ignored {s.strip()}")
        return {}

    source_url = get_source_url_from_pypi(name, overrides)
    license, license_url = get_github_license(source_url)
    ret = locals()
    del ret["s"]
    del ret["overrides"]
    return ret


def process_extra(s):
    name = version = ""
    source_url = s.strip()
    license, license_url = get_github_license(source_url)
    ret = locals()
    del ret["s"]
    return ret


def main(requirements, overrides, extras, manual, output):
    with open(overrides) as f:
        overrides = parse_overrides(f)

    with open(manual) as f:
        reader = csv.DictReader(f)
        items = list(reader)

    with open(requirements) as f:
        items.extend(process_requirement(s, overrides) for s in f)

    with open(extras) as f:
        items.extend(process_extra(s) for s in f)

    with open(output, "w") as f:
        writer = csv.DictWriter(f, ("name", "version", "source_url", "license", "license_url"))
        writer.writeheader()
        writer.writerows(i for i in items if i)

if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    main(*sys.argv[1:])


