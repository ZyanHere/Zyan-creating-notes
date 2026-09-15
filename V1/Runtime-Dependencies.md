# Runtime Dependencies

Everything this system needs that `pip install` and `npm install` do **not** bring
with them. It exists because a missing Chromium cost three rounds of diagnosis:
the prerequisite was real, undocumented, and invisible until the last step of a
paid generation failed.

Status: **LOCKED** for the boundary in §1; **WORKING MODEL** for the provisioning
in §4, which is not yet wired up.

---

## 1. The dependency boundary — LOCKED

```
  end user's device            server(s)
  ┌───────────────┐    HTTP    ┌──────────────────────────────────────────┐
  │ a web browser │ ─────────► │ frontend (Next.js)                       │
  │ (any, current)│            │   └─► backend (FastAPI)                  │
  └───────────────┘            │         └─► Playwright ─► Chromium ─► PDF│
                               └──────────────────────────────────────────┘
```

**Chromium is a backend rendering runtime, not a client dependency.** The end
user needs a browser to *view* the app, exactly as for any web application. They
never need Chromium installed, never need Playwright, and never render anything
locally. The PDF is produced server-side and delivered over HTTP.

This is a boundary, not an implementation detail. Anything that would require a
capability on the end user's device to produce an artifact is out of bounds.

| Tier | Needs | Provisioned by |
|---|---|---|
| End user | A current web browser | Nothing — they have one |
| Frontend host | Node, the npm tree | `npm install` at build |
| Backend host | Python, the pip tree, **Chromium + its OS libraries**, fonts | The image (§4) |

The three-round failure happened because the *developer machine* is currently
also the backend host, which makes a server prerequisite look like a personal
setup chore. It is not one. When the backend is deployed, this moves into the
image and no human installs it again.

---

## 2. Inventory

### Installed by a package manager

| Dependency | Version | Manifest | Notes |
|---|---|---|---|
| Python | ≥ 3.12 | `pyproject.toml` | |
| `fastapi`, `uvicorn` | ≥ 0.115 / ≥ 0.30 | `pyproject.toml` | the API process |
| `pydantic` | ≥ 2.7 | `pyproject.toml` | `agent/contracts` |
| `anthropic` | ≥ 1.0 | `pyproject.toml` | `agent/` only |
| `jinja2` | ≥ 3.1 | `pyproject.toml` | `engine/merge` |
| `playwright` | ≥ 1.47 (1.62.0 in use) | `pyproject.toml` | **the driver library only — see below** |
| `psycopg[binary]` | ≥ 3.2 | `pyproject.toml` | declared; `FileStore` is what actually runs today |
| Node + npm tree | Next 16.3.1, React 19.2.8 | `frontend/package.json` | frontend host only |

### NOT installed by a package manager — the gap this document exists for

| Dependency | Why pip misses it | Consequence when absent |
|---|---|---|
| **Chromium browser binaries** | `pip install playwright` installs the driver, not the browser. A separate ~700 MB download fetched by `playwright install`. | Every PDF render fails. Planning, intake and approval all still work, so it surfaces only at the last step. |
| **Chromium headless shell** | A *second* build, downloaded alongside Chromium. Headless `launch()` runs this one, not full Chromium. | Same, and it defeats a check that stats only full Chromium — see §5. |
| **Chromium's OS shared libraries** (Linux) | `libnss3`, `libatk`, `libgbm`, `libasound2`, … | Chromium exits immediately on launch. Windows and macOS bundle these; Linux images do not. |
| **System fonts on the render host** | Not a package at all. | See §3 — silent, and it changes the output rather than failing. |
| **Outbound HTTPS to `fonts.googleapis.com`** | Needed by 3 of 4 templates at render time. | See §3. |

---

## 3. Two prerequisites that fail silently

Both change the artifact instead of raising, which makes them worse than a
missing browser.

**Fonts are a property of the render host.** The default `study-notes` template
asks for `Source Serif 4`, `Segoe UI` and `Cascadia Mono`, falling back to
Georgia / Helvetica / Arial / Consolas / DejaVu. On the Windows dev machine the
first choices resolve; in a slim Linux image none of them do and every fallback
fires. Different metrics mean different line breaks, which means different
pagination — and `engine/render.py` already treats pagination as artifact-owned
truth. **Any image must install a known font set, and `render_environment` must
keep recording the resolved faces** (System Design invariant 10 is unenforceable
otherwise). Golden-image tests are pinned to a browser *and font* version for
this reason.

**Three templates fetch webfonts at render time.** `grimoire`, `module-guide`
and `night-lab` each carry a `<link>` to `fonts.googleapis.com`;
`study-notes`, the default, does not. `render_pdf` loads with
`wait_until="networkidle"` and then awaits `document.fonts.ready`, so on a host
with no egress those three templates stall until timeout and then render with
fallback fonts.

Worth naming plainly: `tests/test_boundaries.py` forbids `engine/` from importing
`httpx`, `requests` or `socket`, and Build-Spec §8 leans on that purity to
justify golden-image testing. The Python package makes no network call — but the
browser it drives does. **The engine is not network-pure in the way the boundary
test implies.** Not resolving that here; it belongs with the renderer work that
is explicitly deferred.

---

## 4. Local development setup — exact commands

Everything below runs **on the machine that runs the backend**.

```bash
pip install -e .                       # or: pip install fastapi uvicorn pydantic jinja2 playwright anthropic
python -m playwright install chromium  # the browser payload — the step pip does not do
npm --prefix frontend install
```

`python -m playwright install chromium` rather than the bare `playwright`
command, which is not on `PATH` in a user-site install.

It downloads **both** required builds into Playwright's registry:

| OS | Registry location |
|---|---|
| Windows | `%LOCALAPPDATA%\ms-playwright\` |
| macOS | `~/Library/Caches/ms-playwright/` |
| Linux | `~/.cache/ms-playwright/` |

Override with `PLAYWRIGHT_BROWSERS_PATH`. Expect `chromium-<build>/` and
`chromium_headless_shell-<build>/`, about 700 MB on disk together.

On Linux also install the OS libraries Chromium links against:

```bash
python -m playwright install --with-deps chromium
```

Then create `.env` from `.env.example` and set one model provider key.

### Confirming it worked

```bash
curl http://127.0.0.1:8000/health
```

`renderer.ok` must be `true`. When it is `false`, `renderer.reason` and
`renderer.registry` name what was looked for and where. `python -m backend.app`
prints the same verdict at startup as `renderer  chromium ready`.

**Ask the server, not a shell.** A check run in a terminal proves nothing about
a server started elsewhere: during the incident that produced this document, an
agent's sandbox had its `%LOCALAPPDATA%` redirected into an app container, so
every check it ran reported a complete install while the backend — running
outside that container, against the same path string — correctly reported it
missing. `/health` is authoritative because the answering process is the one
that renders.

---

## 5. Deployment — how Chromium gets there automatically

Not yet wired up. This is the intended shape, recorded so it is a decision
rather than a discovery.

**The backend image owns the renderer.** Chromium is baked into the image at
build time; nothing is installed at deploy or at runtime, and no operator ever
runs `playwright install` against a live host.

The base image already solves browser, OS libraries and version-matching
together:

```dockerfile
# The tag MUST match the `playwright` version in pyproject.toml. A driver and a
# browser build are a matched pair; a mismatch reports the browser as missing.
FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Fonts are part of the artifact, not of the machine (§3). Pin them explicitly
# so a base-image bump cannot silently change pagination.
RUN apt-get update && apt-get install -y --no-install-recommends \
      fonts-dejavu-core fonts-liberation2 \
 && rm -rf /var/lib/apt/lists/*

COPY . .
CMD ["python", "-m", "backend.app"]
```

Rolling your own base instead of the Playwright image means doing all three by
hand:

```dockerfile
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install playwright==1.62.0 \
 && python -m playwright install --with-deps chromium
```

`PLAYWRIGHT_BROWSERS_PATH` is set to a root-owned path deliberately: the default
registry is under `$HOME`, and an image that installs as root then runs as a
non-root user leaves the browser somewhere the runtime user cannot read — the
same "installed, but not for this process" failure as the sandbox one in §4.

Checklist for any backend image or host:

- [ ] `playwright` pip version and browser build match
- [ ] Chromium **and** the headless shell present
- [ ] Chromium's OS libraries present (`--with-deps`, or the Playwright base image)
- [ ] The runtime user can read `PLAYWRIGHT_BROWSERS_PATH`
- [ ] A pinned font set installed, and recorded in `render_environment`
- [ ] Egress to `fonts.googleapis.com`, **or** only the `study-notes` template in use
- [ ] `/health` returns `renderer.ok: true` as a deploy smoke test
- [ ] Enough memory for a Chromium process per worker (Build-Spec §8: one long-lived browser per worker, recycled every 200 renders)

---

## 6. Changing any of this

Adding a runtime prerequisite means adding a row here in the same change. The
cost of not doing so is measured in this document's first paragraph.
