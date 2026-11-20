import { readFileSync, writeFileSync, existsSync } from "node:fs"
import path from "node:path"
import { pathToFileURL, fileURLToPath } from "node:url"
import { buildReport, evaluate, mergeConfig, ConfigError } from "./geometry.mjs"

const VIEWPORT_HEIGHT = 1600

class Stop extends Error {}

function die(msg) {
  console.error(`measure: ${msg}`)
  process.exit(2)
}

function stop(msg) {
  throw new Stop(msg)
}

function help() {
  console.log(`measure --url <url|file> [--widths 390,1280] [--config rules.json] [--out report.json] [--timeout 20000]

Opens the page in Chromium and writes a JSON report for rules G1, G2, G3, G4 and G9.
Exit 0 when every rule passes, 1 when a rule fails, 2 on a usage error or a page that does not load.`)
}

function parseArgs(argv) {
  const out = { url: "", widths: "390,1280", config: "", out: "", timeout: "20000", help: false }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    const next = () => {
      if (i + 1 >= argv.length || argv[i + 1].startsWith("--")) die(`missing value for ${a}`)
      return argv[++i]
    }
    if (a === "--url") out.url = next()
    else if (a === "--widths") out.widths = next()
    else if (a === "--config") out.config = next()
    else if (a === "--out") out.out = next()
    else if (a === "--timeout") out.timeout = next()
    else if (a === "--help" || a === "-h") out.help = true
    else die(`unknown argument: ${a}`)
  }
  return out
}

function parseWidths(text) {
  const parts = String(text).split(",").map((s) => s.trim()).filter(Boolean)
  if (!parts.length) die("widths are empty")
  return parts.map((p) => {
    if (!/^\d+$/.test(p)) die(`bad width: ${p}`)
    const n = Number(p)
    if (n < 1 || n > 10000) die(`width out of range: ${n}`)
    return n
  })
}

function parseTimeout(text) {
  if (!/^\d+$/.test(String(text))) die(`bad timeout: ${text}`)
  const n = Number(text)
  if (n < 1) die(`bad timeout: ${text}`)
  return n
}

function loadConfig(file) {
  if (!file) return mergeConfig(null)
  if (!existsSync(file)) die(`config not found: ${file}`)
  let parsed
  try {
    parsed = JSON.parse(readFileSync(file, "utf8"))
  } catch (e) {
    die(`cannot read config: ${e.message}`)
  }
  try {
    return mergeConfig(parsed)
  } catch (e) {
    if (e instanceof ConfigError) die(e.message)
    throw e
  }
}

function resolveTarget(input) {
  if (/^https?:\/\//i.test(input)) return input
  if (/^file:\/\//i.test(input)) {
    let local
    try {
      local = fileURLToPath(input)
    } catch (e) {
      die(`bad file url: ${e.message}`)
    }
    if (!existsSync(local)) die(`file not found: ${local}`)
    return input
  }
  const abs = path.resolve(input)
  if (!existsSync(abs)) die(`file not found: ${abs}`)
  return pathToFileURL(abs).href
}

function collect(opts) {
  const selectors = opts.selectors || {}
  const errors = []
  function matches(el, sel) {
    if (!sel) return false
    try {
      return el.matches(sel)
    } catch (e) {
      errors.push(String(e.message || e))
      return false
    }
  }
  function selectorFor(el) {
    if (el.id) return `#${CSS.escape(el.id)}`
    const parts = []
    let node = el
    while (node && node.nodeType === 1 && node !== document.body) {
      if (node.id) {
        parts.unshift(`#${CSS.escape(node.id)}`)
        break
      }
      let part = node.tagName.toLowerCase()
      const ui = node.getAttribute("data-ui")
      if (ui) part += `[data-ui="${ui.replace(/"/g, "")}"]`
      const parent = node.parentElement
      if (parent) {
        const same = [...parent.children].filter((c) => c.tagName === node.tagName)
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`
      }
      parts.unshift(part)
      node = parent
    }
    return parts.join(" > ") || node.tagName.toLowerCase()
  }
  function textBox(el) {
    let box = null
    for (const node of el.childNodes) {
      if (node.nodeType !== 3 || !node.textContent.trim()) continue
      const range = document.createRange()
      range.selectNodeContents(node)
      const r = range.getBoundingClientRect()
      if (r.width === 0 && r.height === 0) continue
      if (!box) box = { x: r.x, y: r.y, width: r.width, height: r.height }
      else {
        const right = Math.max(box.x + box.width, r.x + r.width)
        const bottom = Math.max(box.y + box.height, r.y + r.height)
        box.x = Math.min(box.x, r.x)
        box.y = Math.min(box.y, r.y)
        box.width = right - box.x
        box.height = bottom - box.y
      }
    }
    return box
  }
  const skipTags = new Set(["SCRIPT", "STYLE", "LINK", "META", "NOSCRIPT", "TEMPLATE", "HEAD"])
  const elements = []
  function visible(el, style) {
    if (skipTags.has(el.tagName)) return false
    if (el.hasAttribute("hidden")) return false
    if (style.display === "none" || style.visibility === "hidden") return false
    return true
  }
  function walk(el, parent) {
    const style = getComputedStyle(el)
    if (!visible(el, style)) return
    const rect = el.getBoundingClientRect()
    const i = elements.length
    elements.push({
      i,
      parent,
      tag: el.tagName.toLowerCase(),
      id: el.id || "",
      classes: [...el.classList],
      role: el.getAttribute("role") || "",
      dataUi: el.getAttribute("data-ui") || "",
      selector: selectorFor(el),
      position: style.position,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      padding: {
        top: parseFloat(style.paddingTop) || 0,
        right: parseFloat(style.paddingRight) || 0,
        bottom: parseFloat(style.paddingBottom) || 0,
        left: parseFloat(style.paddingLeft) || 0,
      },
      border: {
        top: parseFloat(style.borderTopWidth) || 0,
        right: parseFloat(style.borderRightWidth) || 0,
        bottom: parseFloat(style.borderBottomWidth) || 0,
        left: parseFloat(style.borderLeftWidth) || 0,
      },
      text: textBox(el),
      match: {
        card: matches(el, selectors.cards),
        group: matches(el, selectors.groups),
        column: matches(el, selectors.columns),
        heading: matches(el, selectors.headings),
        body: matches(el, selectors.body),
        button: matches(el, selectors.buttons),
        container: matches(el, selectors.containers),
      },
    })
    for (const child of el.children) walk(child, i)
  }
  walk(document.body, null)
  return {
    viewportWidth: window.innerWidth,
    scrollWidth: Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0),
    elements,
    errors,
  }
}

function installHint(msg) {
  if (/Executable doesn't exist|playwright install|browserType\.launch|Please run the following/i.test(msg)) {
    return `${msg} Install from the skill folder: npm install && npx playwright install chromium`
  }
  return msg
}

async function launch(chromium) {
  try {
    return await chromium.launch({ headless: true })
  } catch (e) {
    const msg = String(e && e.message || e)
    if (/sandbox|zygote|namespace/i.test(msg)) {
      return chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] })
    }
    throw new Error(installHint(msg))
  }
}

async function measureWidth(browser, target, width, config, timeout) {
  const context = await browser.newContext({
    viewport: { width, height: VIEWPORT_HEIGHT },
    deviceScaleFactor: 1,
  })
  try {
    const page = await context.newPage()
    let response
    try {
      response = await page.goto(target, { waitUntil: "load", timeout })
    } catch (e) {
      stop(`page did not load: ${e.message}`)
    }
    if (response && response.status() >= 400) stop(`page returned HTTP ${response.status()}`)
    const snapshot = await page.evaluate(collect, { selectors: config.selectors })
    if (snapshot.errors && snapshot.errors.length) stop(`bad selector: ${snapshot.errors[0]}`)
    snapshot.requestedWidth = width
    return { width: Math.round(snapshot.viewportWidth), rules: evaluate(snapshot, config) }
  } finally {
    await context.close()
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    help()
    process.exit(0)
  }
  if (!args.url) die("missing --url")
  const widths = parseWidths(args.widths)
  const timeout = parseTimeout(args.timeout)
  const config = loadConfig(args.config)
  const target = resolveTarget(args.url)
  let chromium
  try {
    ;({ chromium } = await import("playwright"))
  } catch (e) {
    die("Playwright is not installed. From the skill folder run: npm install && npx playwright install chromium")
  }
  let browser
  try {
    browser = await launch(chromium)
    const reports = []
    for (const width of widths) reports.push(await measureWidth(browser, target, width, config, timeout))
    const report = buildReport(args.url, reports)
    const text = `${JSON.stringify(report, null, 2)}\n`
    if (args.out) {
      try {
        writeFileSync(args.out, text)
      } catch (e) {
        stop(`cannot write report: ${e.message}`)
      }
    }
    process.stdout.write(text)
    await browser.close()
    browser = null
    process.exit(report.verdict === "pass" ? 0 : 1)
  } catch (e) {
    if (browser) await browser.close().catch(() => {})
    die(e instanceof Stop ? e.message : installHint(e.message || String(e)))
  }
}

main()
