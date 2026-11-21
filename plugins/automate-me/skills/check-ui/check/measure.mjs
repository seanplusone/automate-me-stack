import { readFileSync, writeFileSync, writeSync, existsSync, realpathSync, mkdirSync, mkdtempSync } from "node:fs"
import { tmpdir } from "node:os"
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
Exit 0 when every rule passes, 1 when a rule fails, 3 when nothing fails but a row needs a look, 2 on a usage error or an inconclusive run.
--timeout is the whole run, in milliseconds. --wait-for is a selector to wait for after load. --shots is the folder for review crops.`)
}

function parseArgs(argv) {
  const out = { url: "", widths: "390,1280", config: "", out: "", timeout: "20000", help: false, waitFor: "", shots: "" }
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
    else if (a === "--wait-for") out.waitFor = next()
    else if (a === "--shots") out.shots = next()
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

function canon(file) {
  try {
    return realpathSync(file)
  } catch (e) {
    return path.resolve(file)
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

async function collect(opts) {
  const selectors = opts.selectors || {}
  const deadline = opts.deadline || 0
  const moved = new Set()
  if (document.body) {
    const sample = [...document.body.querySelectorAll("*")].slice(0, 120)
    const before = sample.map((el) => {
      const r = el.getBoundingClientRect()
      return [el, r.x, r.y, r.width, r.height]
    })
    const pause = Math.min(300, Math.max(0, (deadline || Date.now() + 300) - Date.now()))
    if (pause > 40) {
      await new Promise((resolve) => {
        const start = performance.now()
        let done = false
        const finish = () => { if (!done) { done = true; resolve() } }
        const step = () => {
          if (performance.now() - start >= pause) finish()
          else requestAnimationFrame(step)
        }
        requestAnimationFrame(step)
        setTimeout(finish, pause + 50)
      })
    }
    for (const [el, x, y, w, h] of before) {
      const r = el.getBoundingClientRect()
      if (Math.abs(r.x - x) > 1 || Math.abs(r.y - y) > 1 || Math.abs(r.width - w) > 1 || Math.abs(r.height - h) > 1) moved.add(el)
    }
  }
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
  let firstBand = true
  function slotBoxes(el) {
    const nodes = []
    if (el.tagName === "SLOT" && el.assignedElements) nodes.push(...el.assignedElements())
    if (el.shadowRoot) el.shadowRoot.querySelectorAll("slot").forEach((slot) => nodes.push(...slot.assignedElements()))
    const placed = nodes.filter((node) => {
      const pos = getComputedStyle(node).position
      return pos !== "absolute" && pos !== "fixed"
    })
    if (!placed.length) return null
    return placed.map((node) => {
      const r = node.getBoundingClientRect()
      return { left: r.x, top: r.y, right: r.x + r.width, bottom: r.y + r.height, width: r.width, height: r.height }
    }).filter((r) => r.width > 0 || r.height > 0)
  }
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
    const image = style.backgroundImage || "none"
    const gradient = image !== "none" && image.includes("gradient")
    const hasShadow = style.boxShadow && style.boxShadow !== "none"
    const outline = style.outlineStyle !== "none" ? (parseFloat(style.outlineWidth) || 0) : 0
    const before = getComputedStyle(el, "::before")
    const beforeOn = before && ((before.backgroundImage && before.backgroundImage !== "none") || (before.backgroundColor && before.backgroundColor !== "transparent" && before.backgroundColor !== "rgba(0, 0, 0, 0)"))
    const hasBorder = border.top + border.right + border.bottom + border.left > 0
    const hasPad = pad.top + pad.right + pad.bottom + pad.left > 0
    const childBorder = [...el.children].some((child) => {
      const name = child.tagName
      if (name === "BUTTON" || name === "INPUT" || name === "TEXTAREA" || name === "SELECT" || name === "A") return false
      const cs = getComputedStyle(child)
      return (parseFloat(cs.borderTopWidth) || 0) + (parseFloat(cs.borderBottomWidth) || 0) > 0
    })
    const blocked = new Set(["html", "body", "header", "nav", "footer", "pre", "code", "td", "th", "tr", "table", "button", "input", "textarea", "select", "option", "label", "iframe"])
    const textLen = (el.innerText || "").trim().length
    const radius = parseFloat(style.borderRadius) || 0
    const avatar = rect.width >= 16 && rect.width <= 64 && Math.abs(rect.width - rect.height) <= 6 && radius >= rect.width * 0.4
    const oneLine = el.querySelectorAll("h1,h2,h3,p,ul,ol,table").length === 0
    const controlBox = rect.height > 0 && rect.height <= 48 && rect.width > 0 && rect.width <= 280 && oneLine && textLen > 0 && textLen < 40
    const sidebar = tag === "aside" && rect.height > window.innerHeight * 0.55 && rect.width < window.innerWidth * 0.45
    const inlineOnly = style.display === "inline"
    const parentLayout = parentStyle && (parentStyle.display.includes("flex") || parentStyle.display.includes("grid"))
    let fills = false
    if (parentLayout && parentStyle.boxHeight > 80 && Math.abs(rect.height - parentStyle.boxHeight) <= 4 && el.parentElement) {
      const stretch = style.alignSelf === "stretch" || ((style.alignSelf === "auto" || style.alignSelf === "normal") && (parentStyle.alignItems === "stretch" || parentStyle.alignItems === "normal"))
      const others = [...el.parentElement.children].filter((sib) => sib !== el).map((sib) => sib.getBoundingClientRect().height)
      const tallestOther = others.length ? Math.max(...others) : 0
      fills = stretch && tallestOther >= rect.height - 8
      const grand = el.parentElement.parentElement
      if (!fills && grand) {
        const gd = getComputedStyle(grand).display
        if (gd.includes("flex") || gd.includes("grid")) {
          const row = [...grand.children].filter((sib) => sib !== el.parentElement).map((sib) => sib.getBoundingClientRect().height)
          const tallestRow = row.length ? Math.max(...row) : 0
          const parentH = el.parentElement.getBoundingClientRect().height
          if (Math.abs(rect.height - parentH) <= 4 && tallestRow >= rect.height - 8) fills = true
        }
      }
    }
    let cardLike = false
    let guess = ""
    const strong = hasBorder || hasShadow || (hasBg && (hasPad || rect.height >= 48))
    const weak = outline > 0 || beforeOn || (image !== "none" && !hasBg) || (hasPad && childBorder)
    if (!blocked.has(tag) && !fills && !inlineOnly && !controlBox && !avatar && !sidebar && textLen > 0 && (strong || weak)) {
      cardLike = true
      guess = strong ? "high" : "low"
    }
    const minH = parseFloat(style.minHeight) || 0
    const band = tag === "section" || tag === "header" || el.classList.contains("hero")
    if (tag === "section" || tag === "header") firstBand = false
    const fullBleed = hasBg && rect.width >= window.innerWidth - 32 && rect.top < 280 && minH >= 160
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
      flow: style.flexDirection || "",
      stretched,
      cardLike,
      guess,
      moved: moved.has(el),
      strict: Boolean(el.id && false),
      minHeight: parseFloat(style.minHeight) || 0,
      hero: fullBleed || (band && minH >= 160 && hasBg && rect.top < 280 && !hasBorder),
      password: tag === "input" && (el.getAttribute("type") || "") === "password",
      slotted: slotBoxes(el),
      control: tag === "input" || tag === "textarea" || tag === "select",
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
    if (deadline && elements.length % 400 === 0 && Date.now() > deadline) throw new Error("timed out while measuring the page")
    const passed = { display: style.display, alignItems: style.alignItems, boxHeight: rect.height }
    ;[...el.children].forEach((child, index) => walk(child, i, selector, passed, index + 1))
    if (el.shadowRoot) [...el.shadowRoot.children].forEach((child, index) => walk(child, i, `${selector} >>>`, passed, index + 1))
  }
  walk(document.body, null, "body", null, 1)
  function visibleText(node) {
    if (!node) return ""
    let text = ""
    if (node.nodeType === 3) return node.textContent || ""
    if (node.nodeType !== 1 && node.nodeType !== 11) return ""
    if (node.nodeType === 1 && /^(SCRIPT|STYLE)$/.test(node.tagName || "")) return ""
    if (node.shadowRoot) text += visibleText(node.shadowRoot)
    for (const child of node.childNodes || []) text += visibleText(child)
    return text
  }
  const raw = visibleText(document.body).trim()
  const shown = [...(document.body ? document.body.children : [])].filter((el) => !/^(SCRIPT|STYLE)$/.test(el.tagName))
  const onlyPre = shown.length === 1 && shown[0].tagName === "PRE"
  const preText = onlyPre ? shown[0].innerText.trim() : ""
  const statusHeading = [...document.querySelectorAll("h1,h2")].some((h) => /^(?:(?:erreur|error|fehler|http)\s+)?\d{3}(?:\s+(?:not found|error|erreur|introuvable|unavailable|service unavailable|internal server error|bad gateway))?$/i.test((h.innerText || "").trim()))
  const statusNode = document.querySelector("[role='status'], [role='progressbar']")
  const statusText = statusNode ? (statusNode.innerText || "").trim() : ""
  const busy = Boolean(document.querySelector("[aria-busy='true']")) && raw.length < 120 || (statusText.length > 0 && raw.length < 120 && statusText.length >= Math.max(1, raw.length) * 0.7)
  const bars = [...document.querySelectorAll("div, span")].filter((el) => {
    if (el.children.length || [...el.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim())) return false
    const s = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    const bg = s.backgroundColor && s.backgroundColor !== "transparent" && s.backgroundColor !== "rgba(0, 0, 0, 0)"
    return bg && r.height >= 8 && r.height <= 48 && r.width >= 40
  })
  const skeleton = bars.length >= 3 && raw.length < 40
  const emptyRoot = shown.length === 1 && !raw && shown[0].children.length === 0
  function hasControl(node) {
    if (!node) return false
    if (node.nodeType === 1) {
      const name = node.tagName
      if (name === "BUTTON" || name === "INPUT" || name === "TEXTAREA" || name === "SELECT" || name === "FORM") return true
      if (name === "A" && node.hasAttribute("href")) return true
    }
    if (node.shadowRoot && hasControl(node.shadowRoot)) return true
    for (const child of node.children || []) if (hasControl(child)) return true
    return false
  }
  const controls = hasControl(document.body)
  const heroEl = document.querySelector("section, header, .hero")
  let hero = false
  if (heroEl) {
    const s = getComputedStyle(heroEl)
    const r = heroEl.getBoundingClientRect()
    const bg = s.backgroundColor && s.backgroundColor !== "transparent" && s.backgroundColor !== "rgba(0, 0, 0, 0)"
    const border = (parseFloat(s.borderTopWidth) || 0) + (parseFloat(s.borderBottomWidth) || 0) > 0
    hero = (!border && (heroEl.matches("section, header") || heroEl.classList.contains("hero"))) || (bg && !border && r.width >= window.innerWidth - 24)
  }
  const thin = raw.length < 40 && !controls && !hero
  const heads = [...document.querySelectorAll("h1,h2,h3")].map((h) => (h.innerText || "").trim()).join(" ")
  const blob = `${heads} ${raw}`.toLowerCase()
  const paras = document.querySelectorAll("p").length
  const errorish = raw.length < 500 && paras < 5 && /something went wrong|try again|could not load|unable to|page not found|introuvable|nicht verf|nicht gefunden|erreur|fehler|cargando|読み込み|エラー|\bloading\b/.test(blob)
  const spinner = [...document.querySelectorAll("div,span")].some((el) => {
    const s = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    const spin = s.animationName && s.animationName !== "none"
    return spin && r.width >= 12 && r.width <= 80 && Math.abs(r.width - r.height) <= 8 && raw.length < 220
  })
  const root = document.querySelector("#root, #app")
  const shell = Boolean(root) && !(root.innerText || "").trim() && root.children.length === 0 && raw.length < 80
  return {
    viewportWidth: window.innerWidth,
    scrollWidth: Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0),
    elements,
    errors,
    hits,
    iframes,
    bodyBox: document.body ? (() => { const r = document.body.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: Math.min(r.height, 800) } })() : { x: 0, y: 0, width: 320, height: 180 },
    text: raw.slice(0, 240),
    thin,
    errorish,
    spinner,
    shell,
    busy,
    skeleton,
    emptyRoot,
    statusHeading,
    empty: !raw && elements.length <= 1 && !emptyRoot,
    jsonError: Boolean((document.body && document.body.children.length === 0 && /^[\[{]/.test(raw)) || (onlyPre && preText)),
    reason: onlyPre ? (/^[\[{]/.test(preText) ? "The page is a JSON error." : "The page is a plain text body.") : "",
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
  let stableSince = 0
  while (Date.now() - start < cap) {
    const sig = await until(page.evaluate(() => {
      const running = document.getAnimations ? document.getAnimations().filter((item) => item.playState === "running").length : 0
      const b = document.body
      const nodes = b ? [...b.querySelectorAll("*")].slice(0, 40) : []
      const spot = nodes.map((node) => {
        const r = node.getBoundingClientRect()
        return `${Math.round(r.x)},${Math.round(r.y)}`
      }).join(";")
      if (!b) return `0|${running}|${spot}`
      return `${b.childElementCount}|${b.scrollWidth}|${b.scrollHeight}|${running}|${spot}`
    }), remaining())
    const calm = sig.split("|")[3] === "0"
    if (sig === last && calm) {
      if (!stableSince) stableSince = Date.now()
      if (Date.now() - stableSince >= 500) return true
    } else {
      last = sig
      stableSince = 0
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  return false
}

function writeAll(fd, text) {
  const buf = Buffer.from(text)
  let off = 0
  while (off < buf.length) {
    try {
      const n = writeSync(fd, buf, off, buf.length - off)
      if (!n) throw new Error("report write returned no bytes")
      off += n
    } catch (e) {
      if (e && (e.code === "EAGAIN" || e.code === "EWOULDBLOCK")) continue
      throw e
    }
  }
}

async function shoot(page, rules, width, dir, remaining, stamp) {
  if (!dir) return true
  mkdirSync(dir, { recursive: true })
  let n = 0
  for (const rule of rules) {
    if (remaining && remaining() < 150) return false
    if (rule.status !== "review") continue
    const box = rule.measured || {}
    if (!(box.width > 1) || !(box.height > 1)) continue
    const file = path.join(dir, `${stamp}-${width}-${n}.png`)
    n += 1
    try {
      const placed = await page.evaluate(({ x, y, w, h }) => {
        const nodes = [...document.querySelectorAll("body *")]
        const el = nodes.find((node) => {
          const r = node.getBoundingClientRect()
          return Math.abs(r.x - x) < 3 && Math.abs(r.y - y) < 3 && Math.abs(r.width - w) < 6 && Math.abs(r.height - h) < 6
        })
        if (el) el.scrollIntoView({ block: "center", inline: "center" })
        window.scrollBy(-16, -16)
        let r = el ? el.getBoundingClientRect() : { x, y: y - window.scrollY, width: w, height: h }
        if (el && (r.x < 0 || r.y < 0 || r.right > window.innerWidth - 2 || r.bottom > window.innerHeight - 2)) {
          el.style.setProperty("position", "relative", "important")
          el.style.setProperty("left", "8px", "important")
          el.style.setProperty("top", "8px", "important")
          r = el.getBoundingClientRect()
        }
        return { x: r.x, y: r.y, width: r.width, height: r.height }
      }, { x: box.x || 0, y: box.y || 0, w: box.width, h: box.height })
      const clip = {
        x: Math.max(0, placed.x || 0),
        y: Math.max(0, placed.y || 0),
        width: Math.min(Math.max(2, placed.width || box.width), 1200),
        height: Math.min(Math.max(2, placed.height || box.height), 800, VIEWPORT_HEIGHT - 2),
      }
      if (clip.x + clip.width > width) clip.width = Math.max(2, width - clip.x - 1)
      if (clip.y + clip.height > VIEWPORT_HEIGHT) clip.height = Math.max(2, VIEWPORT_HEIGHT - clip.y - 1)
      await page.screenshot({ path: file, clip })
      rule.shot = file
    } catch (e) {
      rule.shot = ""
    }
  }
  return true
}

async function measureWidth(browser, target, width, widths, config, remaining, waitFor) {
  const context = await browser.newContext({
    viewport: { width, height: VIEWPORT_HEIGHT },
    deviceScaleFactor: 1,
  })
  const page = await context.newPage()
  const warnings = []
  const early = []
  let loaded = false
  page.on("pageerror", (err) => {
    const text = String(err)
    if (!loaded) early.push(text)
    else warnings.push(text)
  })
  page.on("console", (msg) => {
    if (msg.type() !== "error") return
    const text = msg.text()
    if (/Failed to load resource|favicon|net::ERR/i.test(text)) warnings.push(text)
    else warnings.push(text)
  })
  page.on("requestfailed", (req) => {
    if (req.frame() === page.mainFrame() && req.isNavigationRequest()) warnings.push(`navigation failed: ${req.url()}`)
    else warnings.push(`request failed: ${req.url()}`)
  })
  try {
    if (!/^https?:/i.test(target) && /\.(xml|json)$/i.test(target)) {
      return {
        width,
        rules: [{ id: "G1", status: "skip", element: "", measured: {}, limit: {}, message: "The document is not HTML." }],
        warnings,
        fatal: true,
        reason: "The document is not HTML.",
        page,
        context,
      }
    }
    let response
    try {
      response = await until(page.goto(target, { waitUntil: "load", timeout: remaining() }), remaining())
    } catch (e) {
      if (e instanceof Stop) throw e
      stop(`page did not load: ${e.message}`)
    }
    loaded = true
    const status = response ? response.status() : 0
    const type = response ? (response.headers()["content-type"] || "") : ""
    if (type && !/html/i.test(type)) {
      return {
        width,
        rules: [{ id: "G1", status: "skip", element: "", measured: {}, limit: {}, message: "The document is not HTML." }],
        warnings,
        fatal: true,
        reason: "The document is not HTML.",
        page,
        context,
      }
    }
    if (waitFor) await until(page.waitForSelector(waitFor, { timeout: remaining() }), remaining())
    const still = await settle(page, Math.min(3000, remaining()), remaining)
    const snapshot = await until(page.evaluate(collect, { selectors: config.selectors, deadline: Date.now() + remaining() }), remaining())
    snapshot.moving = !still
    if (snapshot.errors && snapshot.errors.length) stop(`bad selector: ${snapshot.errors[0]}`)
    for (const key of config.explicitSelectors || []) {
      if (!snapshot.hits[key]) console.error(`measure: selector ${key} matched nothing`)
    }
    snapshot.requestedWidth = width
    snapshot.widths = widths
    snapshot.deadline = Date.now() + remaining()
    let rules
    try {
      rules = evaluate(snapshot, config)
    } catch (e) {
      if (/scoring/.test(String(e.message || e))) {
        return {
          width: Math.round(snapshot.viewportWidth || width),
          rules: [{ id: "G1", status: "skip", element: "", measured: {}, limit: {}, message: "Scoring stopped at the deadline." }],
          warnings,
          fatal: true,
          reason: "timed out while scoring the page",
          page,
          context,
        }
      }
      throw e
    }
    const box = snapshot.bodyBox || { x: 0, y: 0, width: 320, height: 180 }
    if (snapshot.statusHeading || snapshot.skeleton || snapshot.busy || snapshot.emptyRoot || snapshot.shell || snapshot.spinner || snapshot.errorish || snapshot.thin) {
      const message = snapshot.statusHeading
        ? "The main heading is a status code. It needs a look."
        : snapshot.spinner
          ? "This page is only a spinner. It needs a look."
          : snapshot.skeleton
            ? "This page is a skeleton. It needs a look."
            : snapshot.busy
              ? "This page is still busy. It needs a look."
              : snapshot.emptyRoot || snapshot.shell
                ? "This page is an empty app shell. It needs a look."
                : snapshot.errorish
                  ? "This looks like an error screen. It needs a look."
                  : "This page has almost no text. It needs a look."
      rules.push(pageReview(box, message))
    }
    let reason = snapshot.reason || ""
    let fatal = Boolean(snapshot.jsonError)
    if (status >= 400) {
      fatal = true
      reason = `HTTP ${status}.`
    }
    if (/\.xml$/i.test(target) || (type && !/html/i.test(type)) || /\.json$/i.test(target)) {
      fatal = true
      reason = reason || "The document is not HTML."
    }
    if (snapshot.empty) {
      fatal = true
      reason = reason || "The page has no visible content."
    }
    if (early.length && snapshot.empty) {
      fatal = true
      reason = reason || `A script error happened before the page rendered. ${early[0]}`
    } else if (early.length) warnings.push(...early)
    return {
      width: Math.round(snapshot.viewportWidth),
      rules,
      warnings,
      fatal,
      reason,
      page,
      context,
    }
    } catch (e) {
    await Promise.race([context.close(), new Promise((resolve) => setTimeout(resolve, 500))])
    if (loaded && (!(e instanceof Stop) || /timed out|navigation/.test(e.message || ""))) {
      stop(/scoring/.test(String(e.message || "")) ? "timed out while scoring the page" : "timed out while measuring the page")
    }
    throw e
  }
}

function pageReview(box, message) {
  return {
    id: "G1",
    status: "review",
    element: "body",
    measured: { x: box.x || 0, y: box.y || 0, width: box.width || 320, height: box.height || 180 },
    limit: {},
    message,
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
    const outAbs = canon(args.out)
    const configAbs = args.config ? canon(args.config) : ""
    let pageAbs = ""
    if (!/^(https?|data|about):/i.test(args.url)) {
      pageAbs = canon(/^file:\/\//i.test(args.url) ? fileURLToPath(args.url) : path.resolve(args.url))
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
    const deadline = Date.now() + timeout
    const remaining = () => Math.max(1, deadline - Date.now())
    const shots = args.shots || (args.out ? path.join(path.dirname(path.resolve(args.out)), "shots") : mkdtempSync(path.join(tmpdir(), "check-ui-")))
    const stamp = Date.now().toString(36)
    const open = []
    const reports = []
    let timedOut = false
    for (const width of widths) {
      if (Date.now() >= deadline) { timedOut = true; break }
      const item = await measureWidth(browser, target, width, widths, config, remaining, args.waitFor)
      open.push(item)
      if (shots) {
        const ok = await shoot(item.page, item.rules, item.width, shots, remaining, stamp)
        if (!ok) timedOut = true
      }
      reports.push(item)
      if (timedOut) break
    }
    if (!reports.length) stop("timed out")
    const warnings = [...new Set(reports.flatMap((item) => item.warnings || []))]
    const fatal = timedOut || reports.some((item) => item.fatal)
    const report = buildReport(args.url, reports, {
      fatal,
      reason: timedOut ? "timed out" : ((reports.find((item) => item.reason) || {}).reason || ""),
      warnings,
      shots,
    })
    const text = `${JSON.stringify(report, null, 2)}\n`
    if (args.out) writeFileSync(args.out, text)
    writeAll(1, text)
    for (const item of open) await Promise.race([item.context.close(), new Promise((resolve) => setTimeout(resolve, 300))])
    await browser.close()
    browser = null
    const code = report.verdict === "pass" ? 0 : report.verdict === "fail" ? 1 : report.verdict === "review" ? 3 : 2
    process.exit(code)
  } catch (e) {
    if (browser) await browser.close().catch(() => {})
    die(e instanceof Stop ? e.message : installHint(e.message || String(e)))
  }
}

main()
