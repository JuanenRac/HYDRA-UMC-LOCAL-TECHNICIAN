<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - docs/WEB_API.md
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Read-only local API and web page (Fase 5)

`hydra-umc-local-technician serve` starts a small HTTP server (`webapi.py`)
and a single-page web UI (`webui/`) that show what the technician has already
produced. It changes nothing and runs nothing: it does not call a tool, does
not call a model and never opens a file for writing.

```
hydra-umc-local-technician serve --data-dir DIR [--config FILE]
                                 [--host 127.0.0.1] [--port 8780] [--token-file FILE]
```

Open `http://127.0.0.1:8780/` in a browser on the same machine.

## What it serves

`--data-dir` holds three folders of `*.json` files, the output of the CLI saved
by the operator:

| Folder | Content | Produced by |
|---|---|---|
| `tool-results/` | `ToolResult` | `tools call ... > tool-results/NAME.json` |
| `evidence/` | `EvidenceBundle` | `escalation evidence ... > evidence/NAME.json` |
| `proposals/` | `MaintenanceProposal` | `escalation propose ... > proposals/NAME.json` |

The project manifests come from `ecosystemRoot` of `--config` (the same
allow-list `manifest.read` uses), and the document index from its
`knowledgeSources`. Without `--config` the documented defaults apply, which
have no ecosystem root and no knowledge source.

## Routes

Every route is `GET`. Anything else (`POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`,
`OPTIONS`, `TRACE`) answers `405` with `Allow: GET`, and the request body is
never read.

| Route | Answer |
|---|---|
| `/` , `/app.js`, `/app.css`, `/i18n/<lang>.json` | the page; no token needed |
| `/api/v1/health` | `{"status", "version", "readOnly": true}`; no token needed |
| `/api/v1/tools` | the tool registry: name, risk level, implemented, description |
| `/api/v1/tool-results`, `/api/v1/evidence`, `/api/v1/proposals` | a page of summaries: `items`, `total`, `offset`, `limit` (`?offset=`, `?limit=`) |
| `/api/v1/<store>/<id>` | one item: `{"id", "item"}` |
| `/api/v1/manifests`, `/api/v1/manifests/<project>` | the same four short fields `manifest.read` returns |
| `/api/v1/docs` | per knowledge source, the indexed document paths |
| `/api/v1/docs/<source>?path=<document>` | the chunks of one indexed document |

`401` means a token is required or wrong, `404` an unknown route or item,
`413` an item over 1 MiB, `422` an item that is not valid JSON, `403` a Host
header that is not a loopback name (see below).

## Access

- It binds to `127.0.0.1` by default.
- Any other address (including `0.0.0.0`) is refused unless a bearer token of
  at least 24 characters is set. The token comes from `--token-file` or the
  `HYDRA_UMC_LOCAL_TECHNICIAN_TOKEN` environment variable, never from the
  command line (`--token` is not an option, and option abbreviations are off).
- On a loopback bind a token is optional; if one is set it is enforced for
  every `/api/v1/` route except `health`. The page and its translations never
  contain data, so they need no token; the page asks for one in a field and
  keeps it only in memory.
- On a loopback bind, a request whose `Host` header is not `127.0.0.1`,
  `localhost` or `::1` is refused, so a web page on another site cannot reach
  it through a DNS name that points at 127.0.0.1.

## What keeps it read-only and contained

- No code path writes: the module contains no file write, delete, rename or
  subprocess call, and a test checks that.
- An item is found by listing its folder and matching the requested id against
  the names found (ids are `[A-Za-z0-9._-]`, at most 81 characters), never by
  joining the request path onto a directory. `..`, encoded separators, absolute
  paths, backslashes and NUL bytes match nothing. A symbolic link in a store is
  not followed. A document is served only if the index itself listed its path.
- Every JSON answer goes out through one function that applies the same
  redaction as the CLI (`knowledge/redaction.py`: `KEY=VALUE`, `--token VALUE`,
  `Bearer`/`Basic`, cookies, URL credentials, private keys, known token
  formats, and the value of any key named like a secret). Document text is
  redacted too.
- Sizes are bounded: a file over 1 MiB is not read (413); a list has at most
  500 entries (100 by default); a document answer at most 200,000 characters
  and says when it was cut; at most 300 manifests; the standard library bounds
  the request line and headers.
- The page is served with `Content-Security-Policy: default-src 'none';
  script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'
  data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and
  `Cache-Control: no-store`. It writes with `textContent` only.

## The page

One HTML page with a section bar (tools, tool results, evidence bundles,
proposals, manifests, documents), a list and a detail pane. It loads nothing
from the internet, so it works offline; it has a skip link, labelled controls,
a polite live status region, visible keyboard focus, light and dark colours,
reduced-motion support and a single-column layout below 760 px.

Languages: English, Spanish, German, French, Italian, Japanese, Chinese and
European Portuguese (`webui/i18n/<code>.json`, codes `en es de fr it ja zh
pt`). The first visit uses the browser language when it is one of those, and
the choice is remembered in the browser (when storage is available). A string
missing from a language falls back to English. A test checks that every
language has exactly the same keys, that none is empty and that every string the
page asks for exists.

## Not included

It does not run tools (use `tools call`), does not read the escalation outbox,
does not push anything to HYDRA-UMC-SERVER and does not do TLS: for access
from another machine put it behind a reverse proxy that terminates TLS, since a
bearer token over plain HTTP can be read on the network.
