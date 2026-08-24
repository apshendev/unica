// OpenCode host adapter for Unica.
//
// Unica is the product; this module is only the OpenCode host adapter, and
// npm is its delivery address. It exposes exactly one plugin hook — the
// configuration hook — which adds the packaged skills root to OpenCode's
// skill discovery and takes ownership of the `unica` entry in the MCP map by
// launching the packaged native bootstrap directly. Runtime download,
// verification, and caching stay in the bootstrap: they are not reimplemented
// here (DEC.2026-08-24.OPENCODE-ADAPTER-DELIVERY).

import os from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"

const PACKAGE_ROOT = toPosix(
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".."),
)
const SKILLS_ROOT = `${PACKAGE_ROOT}/skills`

// The MCP timeout covers connection startup as well as requests in the
// supported OpenCode API, so the verified cold runtime acquisition of the
// core artifact has to fit inside this budget.
const MCP_TIMEOUT_MS = 900000

const RUNTIME_CACHE_ENV = "UNICA_RUNTIME_CACHE_DIR"
const PROVIDER_STATE_ENV = "UNICA_PROVIDER_STATE_DIR"

function toPosix(value) {
  return value.split("\\").join("/")
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

function installMcp(config) {
  const mcp = config.mcp ?? (config.mcp = {})
  const { target, executable } = hostTarget()
  const bootstrap = toPosix(
    path.join(PACKAGE_ROOT, "bootstrap", "bin", target, executable),
  )
  // The adapter owns `unica` and always replaces the value present when its
  // hook runs, so a stale or incompatible user entry cannot keep the packaged
  // server from starting. Every other MCP entry stays untouched.
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
  },
})
