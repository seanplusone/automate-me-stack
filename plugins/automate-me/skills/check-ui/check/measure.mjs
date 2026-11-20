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
Exit 0 when every rule passes, 1 when a rule fails, 2 on a usage error, a page that does not load, or an inconclusive run.`)
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
  const widths = []
  const seen = new Set()
  for (const p of parts) {
    if (!/^\d+$/.test(p)) die(`bad width: ${p}`)
    const n = Number(p)
    if (n < 200 || n > 10000) die(`width out of range: ${n}`)
    if (seen.has(n)) continue
    seen.add(n)
    widths.push(n)
  }
  return widths
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
  if (/^(https?|data|about):/i.test(input)) return input
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
  const hits = { cards: 0, groups: 0, columns: 0, headings: 0, body: 0, buttons: 0, containers: 0 }
  const iframes = []
  const chCache = new Map()
  function chWidth(style) {
    const key = style.font || ""
    if (chCache.has(key)) return chCache.get(key)
    const probe = document.createElement("span")
    probe.textContent = "0"
    probe.style.cssText = "position:absolute;visibility:hidden;margin:0;padding:0;border:0"
    probe.style.font = style.font
    document.body.appendChild(probe)
    const width = probe.getBoundingClientRect().width || 8
    probe.remove()
    chCache.set(key, width)
    return width
  }
  function matches(el, sel, key) {
    if (!sel) return false
    try {
      const ok = el.matches(sel)
      if (ok) hits[key] += 1
      return ok
    } catch (e) {
      errors.push(String(e.message || e))
      return false
    }
  }
  function union(box, piece) {
    if (!box) return { x: piece.x, y: piece.y, width: piece.width, height: piece.height }
    const right = Math.max(box.x + box.width, piece.x + piece.width)
    const bottom = Math.max(box.y + box.height, piece.y + piece.height)
    const x = Math.min(box.x, piece.x)
    const y = Math.min(box.y, piece.y)
    return { x, y, width: right - x, height: bottom - y }
  }
  function textBox(el, style) {
    let box = null
    const lh = parseFloat(style.lineHeight)
    for (const node of el.childNodes) {
      if (node.nodeType !== 3 || !node.textContent.trim()) continue
      const range = document.createRange()
      range.selectNodeContents(node)
      for (const r of range.getClientRects()) {
        const h = Number.isFinite(lh) && lh > 0 ? lh : r.height
        box = union(box, { x: r.x, y: r.y - Math.max(0, h - r.height) / 2, width: r.width, height: h })
      }
    }
    return box
  }
  const skipTags = new Set(["SCRIPT", "STYLE", "LINK", "META", "NOSCRIPT", "TEMPLATE", "HEAD"])
  const chrome = new Set(["button", "input", "textarea", "select", "a", "body", "html", "label"])
  const elements = []
  function walk(el, parent, parentSel, parentStyle, childIndex) {
    const style = getComputedStyle(el)
    if (skipTags.has(el.tagName) || el.hasAttribute("hidden") || style.display === "none" || style.visibility === "hidden") return
    const tag = el.tagName.toLowerCase()
    const selector = tag === "body" ? "body" : (el.id ? `#${CSS.escape(el.id)}` : `${parentSel} > ${tag}:nth-child(${childIndex})`)
    if (tag === "iframe") iframes.push(selector)
    const rect = el.getBoundingClientRect()
    const pad = {
      top: parseFloat(style.paddingTop) || 0,
      right: parseFloat(style.paddingRight) || 0,
      bottom: parseFloat(style.paddingBottom) || 0,
      left: parseFloat(style.paddingLeft) || 0,
    }
    const border = {
      top: parseFloat(style.borderTopWidth) || 0,
      right: parseFloat(style.borderRightWidth) || 0,
      bottom: parseFloat(style.borderBottomWidth) || 0,
      left: parseFloat(style.borderLeftWidth) || 0,
    }
    const bg = style.backgroundColor
    const hasBg = bg && bg !== "transparent" && bg !== "rgba(0, 0, 0, 0)"
    const hasShadow = style.boxShadow && style.boxShadow !== "none"
    const hasBorder = border.top + border.right + border.bottom + border.left > 0
    const hasPad = pad.top + pad.right + pad.bottom + pad.left > 0
    let align = "start"
    if (style.marginLeft === "auto" && style.marginRight === "auto") align = "center"
    else if (style.marginLeft === "auto" || style.float === "right") align = "end"
    if (parentStyle) {
      const shrink = rect.width + 4 < parentStyle.width
      const ta = parentStyle.align
      if (shrink && ta === "center") align = "center"
      if (shrink && (ta === "right" || ta === "end")) align = "end"
      const jc = parentStyle.justify
      if (jc === "center") align = "center"
      if (jc === "flex-end" || jc === "end" || jc === "right") align = "end"
    }
    const stretched = Boolean(parentStyle && (parentStyle.display.includes("flex") || parentStyle.display.includes("grid")) && ((style.alignSelf === "auto" || style.alignSelf === "normal") ? (parentStyle.alignItems === "stretch" || parentStyle.alignItems === "normal") : (style.alignSelf === "stretch" || style.alignSelf === "normal")))
    const i = elements.length
    elements.push({
      i,
      parent,
      tag,
      id: el.id || "",
      classes: [...el.classList],
      role: el.getAttribute("role") || "",
      dataUi: el.getAttribute("data-ui") || "",
      selector,
      position: style.position,
      display: style.display,
      align,
      stretched,
      cardLike: !chrome.has(tag) && hasPad && (hasBorder || hasBg || hasShadow),
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      padding: pad,
      border,
      ch: chWidth(style),
      margin: {
        top: parseFloat(style.marginTop) || 0,
        right: parseFloat(style.marginRight) || 0,
        bottom: parseFloat(style.marginBottom) || 0,
        left: parseFloat(style.marginLeft) || 0,
      },
      text: textBox(el, style),
      match: {
        card: matches(el, selectors.cards, "cards"),
        group: matches(el, selectors.groups, "groups"),
        column: matches(el, selectors.columns, "columns"),
        heading: matches(el, selectors.headings, "headings"),
        body: matches(el, selectors.body, "body"),
        button: matches(el, selectors.buttons, "buttons"),
        container: matches(el, selectors.containers, "containers"),
      },
    })
    const passed = { display: style.display, alignItems: style.alignItems, justify: style.justifyContent, align: style.textAlign, width: rect.width }
    const kids = [...el.children]
    if (el.shadowRoot) kids.push(...el.shadowRoot.children)
    kids.forEach((child, index) => walk(child, i, selector, passed, index + 1))
  }
  walk(document.body, null, "body", null, 1)
  const raw = document.body ? document.body.innerText.trim() : ""
  return {
    viewportWidth: window.innerWidth,
    scrollWidth: Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0),
    elements,
    errors,
    hits,
    iframes,
    empty: Boolean(document.body) && !raw && document.body.querySelectorAll("h1,h2,h3,p,button,article,section,div").length === 0,
    jsonError: Boolean(document.body) && document.body.children.length === 0 && /^[\[{]/.test(raw),
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

function until(promise, ms) {
  let timer
  const killer = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Stop("timed out")), ms)
  })
  return Promise.race([promise, killer]).finally(() => clearTimeout(timer))
}

async function settle(page, cap, remaining) {
  const start = Date.now()
  let last = ""
  let stable = 0
  while (Date.now() - start < cap) {
    const sig = await until(page.evaluate(() => {
      const b = document.body
      if (!b) return "0"
      return `${b.childElementCount}:${b.scrollWidth}:${b.scrollHeight}:${b.innerHTML.length}`
    }), remaining())
    if (sig === last) {
      stable += 1
      if (stable >= 2) return
    } else {
      last = sig
      stable = 0
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
}

async function measureWidth(browser, target, width, widths, config, timeout) {
  const context = await browser.newContext({
    viewport: { width, height: VIEWPORT_HEIGHT },
    deviceScaleFactor: 1,
  })
  const page = await context.newPage()
  const pageErrors = []
  let navError = false
  page.on("pageerror", (err) => pageErrors.push(String(err)))
  page.on("console", (msg) => {
    if (msg.type() !== "error") return
    const text = msg.text()
    if (/Failed to load resource|favicon|net::ERR/i.test(text)) return
    pageErrors.push(text)
  })
  page.on("requestfailed", (req) => {
    if (req.isNavigationRequest()) navError = true
  })
  const deadline = Date.now() + timeout
  const remaining = () => Math.max(1, deadline - Date.now())
  try {
    let response
    try {
      response = await until(page.goto(target, { waitUntil: "networkidle", timeout: remaining() }), remaining())
    } catch (e) {
      if (e instanceof Stop) throw e
      stop(`page did not load: ${e.message}`)
    }
    if (response && response.status() >= 400) stop(`page returned HTTP ${response.status()}`)
    await settle(page, Math.min(1600, remaining()), remaining)
    const snapshot = await until(page.evaluate(collect, { selectors: config.selectors }), remaining())
    if (snapshot.errors && snapshot.errors.length) stop(`bad selector: ${snapshot.errors[0]}`)
    for (const key of config.explicitSelectors || []) {
      if (!snapshot.hits[key]) console.error(`measure: selector ${key} matched nothing`)
    }
    if (!config.auto && !snapshot.elements.some((el) => el.cardLike || el.dataUi || (el.match && (el.match.card || el.match.group || el.match.column)))) {
      console.error("measure: auto is off and a rule has no marked target")
    }
    snapshot.requestedWidth = width
    snapshot.widths = widths
    return {
      width: Math.round(snapshot.viewportWidth),
      rules: evaluate(snapshot, config),
      pageError: pageErrors.length > 0,
      empty: snapshot.empty,
      jsonError: snapshot.jsonError,
      navError,
    }
  } finally {
    await Promise.race([context.close(), new Promise((resolve) => setTimeout(resolve, 500))])
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
  if (args.out) {
    const outAbs = path.resolve(args.out)
    const configAbs = args.config ? path.resolve(args.config) : ""
    let pageAbs = ""
    if (!/^(https?|data|about):/i.test(args.url)) {
      pageAbs = /^file:\/\//i.test(args.url) ? fileURLToPath(args.url) : path.resolve(args.url)
    }
    if ((pageAbs && outAbs === pageAbs) || (configAbs && outAbs === configAbs)) die("refusing to overwrite the page or the config")
  }
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
    for (const width of widths) reports.push(await measureWidth(browser, target, width, widths, config, timeout))
    const report = buildReport(args.url, reports, {
      empty: reports.some((item) => item.empty),
      pageError: reports.some((item) => item.pageError),
      jsonError: reports.some((item) => item.jsonError),
      navError: reports.some((item) => item.navError),
    })
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
    process.exit(report.verdict === "pass" ? 0 : report.verdict === "fail" ? 1 : 2)
  } catch (e) {
    if (browser) await browser.close().catch(() => {})
    die(e instanceof Stop ? e.message : installHint(e.message || String(e)))
  }
}

main()
