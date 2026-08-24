// Test driver for the packaged OpenCode adapter.
//
// The adapter's public contract is the OpenCode plugin hook: a module export
// that returns hook functions, one of which mutates the merged configuration.
// This driver loads the real adapter file, invokes the hook against a complete
// configuration object, and prints the effective result as JSON so Python
// contract tests can assert on observable behavior only.
//
// Usage: node opencode_adapter_driver.mjs <instruction-file>
//
// Instruction file shape:
//   {
//     "adapterPath": "...",      // absolute path to opencode/index.js
//     "exportName": "...",       // plugin export to invoke (default UnicaOpenCodePlugin)
//     "config": { ... },         // complete configuration object passed to the hook
//     "platform": "win32",       // optional process.platform override
//     "arch": "x64",             // optional process.arch override
//     "env": { "KEY": "val" }    // optional environment overlay applied before the hook
//   }
//
// Output on stdout: {"ok": true, "hooks": [...], "exports": [...], "config": {...}}
// or {"ok": false, "error": "message"}.

import { readFile } from "node:fs/promises"
import { pathToFileURL } from "node:url"

const instruction = JSON.parse(await readFile(process.argv[2], "utf8"))

if (instruction.platform !== undefined) {
  Object.defineProperty(process, "platform", { value: instruction.platform })
}
if (instruction.arch !== undefined) {
  Object.defineProperty(process, "arch", { value: instruction.arch })
}
if (instruction.env !== undefined) {
  for (const [key, value] of Object.entries(instruction.env)) {
    if (value === null) {
      delete process.env[key]
    } else {
      process.env[key] = value
    }
  }
}

const report = await (async () => {
  const module = await import(pathToFileURL(instruction.adapterPath).href)
  const exportName = instruction.exportName ?? "UnicaOpenCodePlugin"
  const plugin = module[exportName]
  if (typeof plugin !== "function") {
    return { ok: false, error: `adapter does not export ${exportName}` }
  }
  const hooks = await plugin({})
  if (typeof hooks.config !== "function") {
    return { ok: false, error: "adapter returns no config hook" }
  }
  await hooks.config(instruction.config)
  return {
    ok: true,
    exports: Object.keys(module),
    hooks: Object.keys(hooks),
    config: instruction.config,
  }
})().catch((error) => ({ ok: false, error: String(error?.message ?? error) }))

process.stdout.write(JSON.stringify(report))
