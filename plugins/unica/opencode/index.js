// OpenCode host adapter for Unica.
//
// Unica is the product; this module is only the OpenCode host adapter, and
// npm is its delivery address. It exposes exactly one plugin hook — the
// configuration hook — which adds the packaged skills root to OpenCode's
// skill discovery, takes ownership of the `unica` entry in the MCP map by
// launching the packaged native bootstrap directly, and grants one narrow
// external_directory rule so skills can read the packaged references/
// without a permission prompt. Runtime download, verification, and caching
// stay in the bootstrap: they are not reimplemented here
// (DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY).
//
// A local-debug candidate carries the generated marker `opencode/
// local-debug.json` (CTR.HOST.OPENCODE-LAUNCH-MODES): with a valid marker
// the MCP entry launches the packaged current-host core binary directly
// instead of the bootstrap. A missing or unparsable marker keeps the release
// behavior.

import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"

const PACKAGE_ROOT = toPosix(
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".."),
)
const SKILLS_ROOT = `${PACKAGE_ROOT}/skills`
const REFERENCES_GLOB = `${PACKAGE_ROOT}/references/*`
const LOCAL_DEBUG_MARKER = `${PACKAGE_ROOT}/opencode/local-debug.json`

// The MCP timeout covers connection startup as well as requests in the
// supported OpenCode API, so the verified cold runtime acquisition of the
// core artifact has to fit inside this budget.
const MCP_TIMEOUT_MS = 900000

const RUNTIME_CACHE_ENV = "UNICA_RUNTIME_CACHE_DIR"
const PROVIDER_STATE_ENV = "UNICA_PROVIDER_STATE_DIR"

// Resolved while the module loads: an unsupported platform must refuse during
// initialization, before any hook runs and before any configuration mutation.
// Function declarations hoist, so calling hostTarget() here is valid.
const HOST_TARGET = hostTarget()

// The marker is read once at initialization. A local-debug candidate always
// carries a well-formed marker; anything else — absent file, broken JSON, a
// foreign shape — is treated as the release package.
const LOCAL_DEBUG = validateLocalDebugTarget(readLocalDebugMarker(), HOST_TARGET)

function toPosix(value) {
  return value.split("\\").join("/")
}

function validateLocalDebugTarget(marker, host) {
  if (marker === null) {
    return marker
  }
  if (marker.target !== host.target) {
    // Init-time refusal: the hook never runs, so the configuration object
    // stays byte-for-byte what the host passed in.
    throw new Error(
      `@apshendev/unica-opencode local-debug candidate targets ` +
        `${marker.target}, but this host is ${host.target}: refusing to ` +
        `launch a foreign core binary.`,
    )
  }
  return marker
}

function readLocalDebugMarker() {
  let raw
  try {
    raw = fs.readFileSync(LOCAL_DEBUG_MARKER, "utf8")
  } catch {
    return null
  }
  try {
    const marker = JSON.parse(raw)
    if (marker && marker.mode === "local-debug" && typeof marker.target === "string") {
      return marker
    }
  } catch {
    // A corrupt marker cannot prove the mode: fall back to the release path.
  }
  return null
}

// Only Windows x64 and Linux x64 are part of the OpenCode support promise.
// Everything else fails during initialization rather than launching a wrong
// binary or silently downloading a runtime it cannot run.
function hostTarget() {
  const key = `${process.platform}-${process.arch}`
  if (key === "win32-x64") {
    return { target: "win-x64", executable: "unica-bootstrap.exe" }
  }
  if (key === "linux-x64") {
    return { target: "linux-x64", executable: "unica-bootstrap" }
  }
  throw new Error(
    `@apshendev/unica-opencode supports only Windows x64 and Linux x64; ` +
      `refusing to initialize on ${key}. macOS and other architectures are ` +
      `outside the OpenCode support promise.`,
  )
}

function cacheHome() {
  const env = process.env
  if (env.XDG_CACHE_HOME && env.XDG_CACHE_HOME.trim() !== "") {
    return env.XDG_CACHE_HOME
  }
  if (process.platform === "win32") {
    if (env.LOCALAPPDATA && env.LOCALAPPDATA.trim() !== "") {
      return env.LOCALAPPDATA
    }
    return path.join(os.homedir(), "AppData", "Local")
  }
  return path.join(os.homedir(), ".cache")
}

// Existing process values win so centrally managed storage policies keep
// working; without overrides, runtime and provider state live in an
// OpenCode-specific area of the user's cache home instead of leaking into a
// Codex-named fallback directory.
function bootstrapEnvironment() {
  const stateRoot = toPosix(path.join(cacheHome(), "opencode", "unica"))
  const environment = {}
  environment[RUNTIME_CACHE_ENV] =
    process.env[RUNTIME_CACHE_ENV] || `${stateRoot}/runtime`
  environment[PROVIDER_STATE_ENV] =
    process.env[PROVIDER_STATE_ENV] || `${stateRoot}/provider-state`
  return environment
}

function installSkills(config) {
  const skills = config.skills ?? (config.skills = {})
  if (!Array.isArray(skills.paths)) {
    skills.paths = []
  }
  skills.paths = skills.paths.filter((entry) => entry !== SKILLS_ROOT)
  skills.paths.push(SKILLS_ROOT)
  if (!Array.isArray(skills.urls)) {
    skills.urls = []
  }
}

// The packaged skills read shared material through `../../references/...`
// links, and the installed package root is external to the OpenCode
// workspace, so every read would otherwise raise an external_directory
// prompt. The adapter owns exactly one narrow rule — the packaged
// references glob — and never widens access to the rest of the package,
// node_modules, or any other directory: user rules survive untouched, and
// a string policy becomes a map that keeps the original policy on "*"
// (CTR.HOST.OPENCODE-REFERENCE-ACCESS).
function installReferenceAccess(config) {
  const permission = config.permission ?? (config.permission = {})
  const external = permission.external_directory
  if (typeof external === "string") {
    permission.external_directory = { "*": external }
  } else if (
    external === null ||
    typeof external !== "object" ||
    Array.isArray(external)
  ) {
    permission.external_directory = {}
  }
  // Assignment, not append: a repeated hook run and any previous value for
  // the glob leave exactly one owned entry.
  permission.external_directory[REFERENCES_GLOB] = "allow"
}

// The packaged core binary name: the release pipeline writes `unica.exe` on
// win-x64, while a hand-assembled debug root may carry the extension-less
// spelling. The launcher uses the first name that exists.
function coreBinary(target) {
  const names = target === "win-x64" ? ["unica.exe", "unica"] : ["unica"]
  for (const name of names) {
    const candidate = path.join(PACKAGE_ROOT, "bin", target, name)
    if (fs.existsSync(candidate)) {
      return toPosix(candidate)
    }
  }
  throw new Error(
    `@apshendev/unica-opencode local-debug candidate is missing its core ` +
      `binary: expected bin/${target}/unica(.exe) under the package root.`,
  )
}

function installMcp(config) {
  const mcp = config.mcp ?? (config.mcp = {})
  const { target, executable } = HOST_TARGET
  // The adapter owns `unica` and always replaces the value present when its
  // hook runs, so a stale or incompatible user entry cannot keep the packaged
  // server from starting. Every other MCP entry stays untouched.
  if (LOCAL_DEBUG) {
    mcp.unica = {
      type: "local",
      command: [coreBinary(target)],
      environment: bootstrapEnvironment(),
      enabled: true,
      timeout: MCP_TIMEOUT_MS,
    }
    return
  }
  const bootstrap = toPosix(
    path.join(PACKAGE_ROOT, "bootstrap", "bin", target, executable),
  )
  mcp.unica = {
    type: "local",
    command: [bootstrap, "run", "--plugin-root", PACKAGE_ROOT],
    environment: bootstrapEnvironment(),
    enabled: true,
    timeout: MCP_TIMEOUT_MS,
  }
}

export const UnicaOpenCodePlugin = async () => ({
  config: async (config) => {
    installSkills(config)
    installMcp(config)
    installReferenceAccess(config)
  },
})
