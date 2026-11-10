#!/usr/bin/env python3
"""Post release embeds to #changelogs and link to the confirmed Discord message."""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

CHANGELOG_GUILD = "1447333772419928256"
CHANGELOG_CHANNEL = "1569406962800656495"
NO_MENTIONS = {"parse": []}


class DeliveryError(RuntimeError):
    """Discord delivery could not be verified."""


class RejectedPost(DeliveryError):
    """Discord rejected the request without creating a message."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def webhook_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.netloc not in {"discord.com", "discordapp.com"}
            or not re.fullmatch(r"/api/(?:v[0-9]+/)?webhooks/[0-9]+/[A-Za-z0-9_-]+/?", parsed.path)
            or parsed.fragment):
        raise ValueError("Use a Discord HTTPS webhook URL in Actions secrets.")
    query = dict(parse_qsl(parsed.query))
    query.pop("wait", None)
    if query.keys() - {"thread_id"} or ("thread_id" in query and not snowflake(query["thread_id"])):
        raise ValueError("Discord webhook URLs may specify only a numeric thread_id.")
    return urlunsplit(parsed._replace(query=urlencode(query)))


def snowflake(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9]+", value) is not None


def request_json(url, payload=None):
    request = Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "DiscordBot (https://github.com/snapetech-org, 1.0)"},
    )
    for attempt in range(4):
        try:
            with build_opener(NoRedirect()).open(request, timeout=20) as response:
                result = json.load(response)
            break
        except HTTPError as error:
            if error.code == 429 and attempt < 3:
                try:
                    delay = float(json.load(error)["retry_after"])
                except (ValueError, TypeError, KeyError):
                    delay = 1
                if 0 <= delay <= 30:
                    time.sleep(delay)
                    continue
            failure = RejectedPost if 400 <= error.code < 500 else DeliveryError
            raise failure(f"Discord returned HTTP {error.code}.") from None
        except (URLError, OSError, ValueError):
            raise DeliveryError("Discord did not return a readable response. Check delivery before retrying.") from None
    if not isinstance(result, dict):
        raise DeliveryError("Discord returned an invalid response.")
    return result


def destination(url, request):
    parsed = urlsplit(url)
    meta = request(urlunsplit(parsed._replace(query="")))
    guild, channel = meta.get("guild_id"), meta.get("channel_id")
    if not snowflake(guild) or not snowflake(channel):
        raise DeliveryError("Discord did not confirm the webhook destination.")
    thread = dict(parse_qsl(parsed.query)).get("thread_id")
    return guild, thread or channel


def post(url, target, payload, request):
    separator = "&" if urlsplit(url).query else "?"
    message = request(url + separator + "wait=true", {**payload, "allowed_mentions": NO_MENTIONS})
    message_id, channel = message.get("id"), message.get("channel_id")
    if not snowflake(message_id) or channel != target[1] or message.get("guild_id", target[0]) != target[0]:
        raise DeliveryError("Discord did not confirm a message in the expected channel.")
    link = f"https://discord.com/channels/{target[0]}/{channel}/{message_id}"
    expected = payload.get("embeds")
    if expected:
        embeds = message.get("embeds") or []
        if (len(embeds) != len(expected) or any(
            want["title"] != got.get("title")
            or want["description"].strip() != str(got.get("description", "")).strip()
            for want, got in zip(expected, embeds)
        )):
            raise DeliveryError(f"Discord returned different changelog text for {link}.")
    elif message.get("content", "").strip() != payload["content"].strip():
        raise DeliveryError(f"Discord returned different announcement text for {link}.")
    return link


def split_description(text, limit=3800):
    """Fit Discord's UTF-16 limit without dropping text or splitting a code point."""
    chunks = []
    remaining = text
    while remaining:
        encoded = remaining.encode("utf-16-le")
        if len(encoded) <= limit * 2:
            chunks.append(remaining)
            break
        prefix = encoded[:limit * 2].decode("utf-16-le", errors="ignore")
        end = prefix.rfind("\n") + 1 or len(prefix)
        chunks.append(remaining[:end])
        remaining = remaining[end:]
    return [chunk for chunk in chunks if chunk.strip()]


def pages(payload):
    embed = payload["embeds"][0]
    chunks = split_description(embed["description"])
    for index, chunk in enumerate(chunks):
        page = copy.deepcopy(payload)
        item = page["embeds"][0]
        suffix = f" ({index + 1}/{len(chunks)})" if len(chunks) > 1 else ""
        item["title"] = item["title"][:256 - len(suffix)] + suffix
        item["description"] = chunk.strip()
        if index:
            item.pop("fields", None)
        yield page


def report(label, link):
    print(f"{label}: {link}", flush=True)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as file:
            file.write(f"{label}: {link}\n")


def resolve_routes(app_value, changelog_value, request=request_json):
    app = webhook_url(app_value)
    app_target = destination(app, request)
    if not changelog_value:
        if app_target == (CHANGELOG_GUILD, CHANGELOG_CHANNEL):
            raise DeliveryError("Configure a separate project-channel webhook before enabling Discord routing.")
        print("::warning::DISCORD_CHANGELOG_WEBHOOK is unset; using the existing project channel.")
        return (app, app_target), None

    changelog = webhook_url(changelog_value)
    if urlsplit(changelog).query or destination(changelog, request) != (CHANGELOG_GUILD, CHANGELOG_CHANNEL):
        raise DeliveryError("DISCORD_CHANGELOG_WEBHOOK must target #changelogs in the expected server.")
    if app_target[0] != CHANGELOG_GUILD or app_target[1] == CHANGELOG_CHANNEL:
        raise DeliveryError("The project webhook must target a different channel in the same Discord server.")
    return (changelog, (CHANGELOG_GUILD, CHANGELOG_CHANNEL)), (app, app_target)


def publish(payloads, project, tag, app_value, changelog_value, *, request=request_json):
    (source_url, source_target), app = resolve_routes(app_value, changelog_value, request)
    messages = [page for payload in payloads for page in pages(payload)]
    if not messages:
        raise ValueError("The release notes are empty.")
    links = []
    for page in messages:
        link = post(source_url, source_target, page, request)
        links.append(link)
        report("Changelog message" if app else "Project message", link)
    app_link = None
    if app:
        pointer = {
            "username": messages[0]["username"],
            "flags": 4,  # Suppress link previews in the project channel.
            "content": f"**{project} {tag}**\n[Read the changelog]({links[0]})",
        }
        app_link = post(*app, pointer, request)
        report("Project link", app_link)
    return {"changelog_messages": links, "project_message": app_link}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("tag")
    parser.add_argument("payload", nargs="+", type=argparse.FileType(encoding="utf-8"))
    args = parser.parse_args()
    try:
        publish([json.load(file) for file in args.payload], args.project, args.tag,
                os.environ["DISCORD_PROJECT_WEBHOOK"], os.environ.get("DISCORD_CHANGELOG_WEBHOOK"))
    except (DeliveryError, OSError, ValueError) as error:
        parser.exit(1, f"Discord release delivery: {error}\n")


if __name__ == "__main__":
    main()
