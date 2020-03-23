#!/usr/bin/env python

import sys
import re
import csv
import urllib.parse
import logging
import requests
from environs import Env
from github import Github

env = Env()
env.read_env()
github_api = Github(env("GITHUB_API_TOKEN"))

parse_requirement_re = re.compile("^(.*)==(.*)$")

def parse_requirement(s):
    logging.info(f"Parsing {s}")
    m = parse_requirement_re.search(s)
    if m:
        return m.groups()
    else:
        raise ValueError(f"Failed to parse {s}")


def get_source_url_from_pypi(name):
    obj = requests.get(f"https://pypi.org/pypi/{name}/json").json()
    urls = obj["info"]["project_urls"]

    if (url := urls.get("Source")) and "github.com" in url:
        return url
    elif (url := urls.get("Code")) and "github.com" in url:
        return url
    elif (url := urls.get("Homepage")) and "github.com" in url:
        return url
    else:
        logging.warning(f"Couldn't find source URL for {name} in {urls!r}")


def get_github_license(url):
    if not url:
        return None, None
    u = urllib.parse.urlsplit(str(url))
    license = github_api.get_repo(u.path.strip("/")).get_license()
    return license.license.name, license.url


def process_requirement(s):
    name, version = parse_requirement(s)
    source_url = get_source_url_from_pypi(name)
    license, license_url = get_github_license(source_url)
    ret = locals()
    del ret["s"]
    return ret


def process_extra(s):
    name = version = ""
    source_url = s.strip()
    license, license_url = get_github_license(source_url)
    ret = locals()
    del ret["s"]
    return ret


def main(requirements, extras, output):
    with open(requirements) as f:
        items = [process_requirement(s) for s in f]

    with open(extras) as f:
        items.extend(process_extra(s) for s in f)

    with open(output, "w") as f:
        writer = csv.DictWriter(f, ("name", "version", "source_url", "license", "license_url"))
        writer.writerows(items)

if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    main(*sys.argv[1:])


