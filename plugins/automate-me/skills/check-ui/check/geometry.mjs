export class ConfigError extends Error {}

const CARD_RE = /^(card|tile|panel|.*-(card|tile|panel))$/
const GROUP_RE = /^.+-group$/
const BUTTON_RE = /^(btn|button|.*-(btn|button))$/
const PAD_CLASS = /^(p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml)-[\w.]+$/
const DROP_CLASS = new Set(["featured", "primary", "secondary", "compact", "loose", "highlighted", "large", "small", "muted", "active", "open", "selected", "disabled", "hover", "focus", "sm", "md", "lg", "xl", "2xl"])
const EXEMPT = new Set(["prose", "signin"])

const NUMBER_RULES = {
  whitespacePx: (n) => n >= 0,
  paddingPx: (n) => n >= 0,
  alignPx: (n) => n >= 0,
  scrollPx: (n) => n >= 0,
  betweenOverInside: (n) => n > 0,
  minWidthRatio: (n) => n > 0 && n <= 1,
  columnAtWidth: (n) => Number.isInteger(n) && n > 0,
}

const SELECTOR_KEYS = ["cards", "groups", "columns", "headings", "body", "buttons", "containers"]

export const DEFAULT_CONFIG = {
  auto: true,
  whitespacePx: 4,
  paddingPx: 2,
  alignPx: 2,
  scrollPx: 0,
  betweenOverInside: 2,
  minWidthRatio: 0.6,
  columnAtWidth: 1280,
  columnExemptions: ["prose", "signin"],
  explicitSelectors: [],
  selectors: {
    cards: "[data-ui='card'], [data-ui='tile'], [data-ui='panel']",
    groups: "[data-ui='group']",
    columns: "[data-ui='column'], [data-ui='main'], main, [role='main']",
    headings: "h1, h2, h3, h4, h5, h6",
    body: "p, [data-ui='body']",
    buttons: "button, [role='button']",
    containers: "[data-ui='container']",
  },
}

export function mergeConfig(file) {
  const config = structuredClone(DEFAULT_CONFIG)
  if (file == null) return config
  if (typeof file !== "object" || Array.isArray(file)) throw new ConfigError("config must be an object")
  const known = new Set(["auto", "selectors", "columnExemptions", ...Object.keys(NUMBER_RULES)])
  for (const key of Object.keys(file)) {
    if (!known.has(key)) throw new ConfigError(`unknown config key: ${key}`)
  }
  if ("auto" in file) {
    if (typeof file.auto !== "boolean") throw new ConfigError("auto must be true or false")
    config.auto = file.auto
  }
  for (const key of Object.keys(NUMBER_RULES)) {
    if (!(key in file)) continue
    const n = file[key]
    if (typeof n !== "number" || !Number.isFinite(n) || !NUMBER_RULES[key](n)) {
      throw new ConfigError(`bad ${key}`)
    }
    config[key] = n
  }
  if ("columnExemptions" in file) {
    const list = file.columnExemptions
    if (!Array.isArray(list) || list.some((item) => typeof item !== "string" || !EXEMPT.has(item))) {
      throw new ConfigError("bad columnExemptions")
    }
    config.columnExemptions = [...list]
  }
  if ("selectors" in file) {
    const sel = file.selectors
    if (typeof sel !== "object" || sel == null || Array.isArray(sel)) {
      throw new ConfigError("selectors must be an object")
    }
    for (const key of Object.keys(sel)) {
      if (!SELECTOR_KEYS.includes(key)) throw new ConfigError(`unknown selector: ${key}`)
      if (typeof sel[key] !== "string") throw new ConfigError(`selector ${key} must be a string`)
      config.selectors[key] = sel[key]
    }
    config.explicitSelectors = Object.keys(sel)
  }
  return config
}

function flagged(el, key) {
  return Boolean(el.match && el.match[key])
}

export function isCard(el, config) {
  if (flagged(el, "card")) return true
  if (el.dataUi === "card" || el.dataUi === "tile" || el.dataUi === "panel") return true
  if (config.auto === false) return false
  if ((el.classes || []).some((c) => CARD_RE.test(c))) return true
  return Boolean(el.cardLike)
}

export function isGroup(el, config) {
  if (flagged(el, "group")) return true
  if (el.dataUi === "group") return true
  if (config.auto === false) return false
  return (el.classes || []).some((c) => GROUP_RE.test(c))
}

export function isColumn(el, config) {
  if (flagged(el, "column")) return true
  if (el.dataUi === "column" || el.dataUi === "main") return true
  if (config.auto === false) return false
  return el.tag === "main" || el.role === "main"
}

export function isHeading(el, config) {
  if (flagged(el, "heading")) return true
  if (el.dataUi === "heading") return true
  if (config.auto === false) return false
  return /^h[1-6]$/.test(el.tag || "")
}

export function isBody(el, config) {
  if (flagged(el, "body")) return true
  if (el.dataUi === "body") return true
  if (config.auto === false) return false
  return el.tag === "p"
}

export function isButton(el, config) {
  if (flagged(el, "button")) return true
  if (el.role === "button" || el.dataUi === "button") return true
  if (config.auto === false) return false
  return el.tag === "button" || (el.classes || []).some((c) => BUTTON_RE.test(c))
}

export function isContainer(el, config) {
  if (flagged(el, "container")) return true
  if (el.dataUi === "container") return true
  return isCard(el, config)
}

export function inFlow(el) {
  const p = el.position || "static"
  return p === "static" || p === "relative" || p === "sticky"
}

function keptClasses(classes) {
  return (classes || []).filter((c) => {
    if (DROP_CLASS.has(c) || PAD_CLASS.test(c)) return false
    if (c.startsWith("is-") || c.startsWith("has-")) return false
    return true
  })
}

export function kindKey(el) {
  const classes = keptClasses(el.classes).sort()
  if (el.role || classes.length) return `${el.role || ""}|${classes.join(".")}`
  if (el.dataUi) return `data-ui:${el.dataUi}`
  if (el.cardLike) return "card-like"
  return ""
}

export function primaryColumn(elements, config) {
  const cols = elements.filter((e) => isColumn(e, config))
  return cols.find((e) => e.dataUi === "main" || e.dataUi === "column")
    || cols.find((e) => e.tag === "main" || e.role === "main")
    || cols[0]
    || null
}

function px(n) {
  return Math.round(n)
}

function r2(n) {
  return Math.round(n * 100) / 100
}

function roundObj(obj) {
  const out = {}
  for (const [k, v] of Object.entries(obj)) out[k] = typeof v === "number" ? r2(v) : v
  return out
}

function entry(id, status, element, measured, limit, message) {
  return { id, status, element: element || "", measured: roundObj(measured), limit: roundObj(limit), message }
}

function box(el) {
  const x = el.rect.x
  const y = el.rect.y
  return {
    left: x,
    top: y,
    right: x + el.rect.width,
    bottom: y + el.rect.height,
    width: el.rect.width,
    height: el.rect.height,
  }
}

function kids(elements, parentI) {
  return elements.filter((e) => e.parent === parentI && inFlow(e) && (e.rect.width > 0 || e.rect.height > 0))
}

function marginBox(el) {
  const b = box(el)
  const top = el.margin?.top || 0
  const bottom = el.margin?.bottom || 0
  return { left: b.left, right: b.right, top: b.top - top, bottom: b.bottom + bottom, width: b.width, height: b.height + top + bottom }
}

function contentBoxes(card, elements, seen = new Set()) {
  if (seen.has(card.i)) return []
  seen.add(card.i)
  const boxes = []
  for (const child of kids(elements, card.i)) {
    if (child.stretched) {
      const inner = contentBoxes(child, elements, seen)
      boxes.push(...(inner.length ? inner : [marginBox(child)]))
    } else boxes.push(marginBox(child))
  }
  if (card.text && (card.text.width > 0 || card.text.height > 0)) {
    boxes.push({
      left: card.text.x,
      top: card.text.y,
      right: card.text.x + card.text.width,
      bottom: card.text.y + card.text.height,
      width: card.text.width,
      height: card.text.height,
    })
  }
  return boxes
}

export function cardSlack(card, children, tolerance) {
  const b = box(card)
  const borderTop = card.border?.top || 0
  const borderBottom = card.border?.bottom || 0
  const padTop = card.padding?.top || 0
  const padBottom = card.padding?.bottom || 0
  const height = px(b.height)
  const inner = height - px(borderTop) - px(borderBottom) - px(padTop) - px(padBottom)
  let slackTop = 0
  let slackBottom = inner
  let contentSpan = 0
  if (children.length) {
    const contentTop = Math.min(...children.map((c) => c.top))
    const contentBottom = Math.max(...children.map((c) => c.bottom))
    const innerTop = b.top + borderTop + padTop
    const innerBottom = b.bottom - borderBottom - padBottom
    slackTop = px(contentTop - innerTop)
    slackBottom = px(innerBottom - contentBottom)
    contentSpan = px(contentBottom - contentTop)
  }
  const allowed = contentSpan + px(padTop) + px(padBottom) + px(borderTop) + px(borderBottom)
  const fail = Math.max(0, slackTop) + Math.max(0, slackBottom) > tolerance
  const measured = { height, contentSpan, slackTop, slackBottom, paddingTop: px(padTop), paddingBottom: px(padBottom) }
  const limit = { whitespacePx: tolerance }
  const message = fail
    ? `Card is ${height}px tall. Content plus padding and border allows ${allowed}px. Tolerance is ${tolerance}px.`
    : "Card height matches its content plus padding."
  return entry("G1", fail ? "fail" : "pass", card.selector, measured, limit, message)
}

export function columnShare(column, viewportWidth, minRatio) {
  const width = px(column.rect.width)
  const viewport = px(viewportWidth)
  const minWidth = minRatio * viewport
  const ratio = viewport ? width / viewport : 0
  const pct = r2(ratio * 100)
  const minPct = r2(minRatio * 100)
  const fail = width + 0.01 < minWidth
  return entry(
    "G1",
    fail ? "fail" : "pass",
    column.selector,
    { width, viewport, ratio: r2(ratio) },
    { minWidthRatio: minRatio },
    fail
      ? `Main column is ${width}px, ${pct}% of the ${viewport}px viewport. Minimum is ${minPct}%.`
      : `Main column covers ${pct}% of the viewport.`,
  )
}

function axisOf(els) {
  let x = 0
  let y = 0
  const sorted = [...els].sort((a, b) => a.rect.y - b.rect.y || a.rect.x - b.rect.x)
  for (let i = 1; i < sorted.length; i++) {
    const a = box(sorted[i - 1])
    const b = box(sorted[i])
    const vertical = b.top >= a.bottom - 1
    const horizontal = b.left >= a.right - 1
    if (vertical && !horizontal) y += 1
    else if (horizontal && !vertical) x += 1
    else if (b.top - a.top >= b.left - a.left) y += 1
    else x += 1
  }
  return x > y ? "x" : "y"
}

function pairGaps(els, axis) {
  const sorted = [...els].sort((a, b) => (axis === "x" ? a.rect.x - b.rect.x : a.rect.y - b.rect.y))
  const gaps = []
  for (let i = 1; i < sorted.length; i++) {
    const prev = box(sorted[i - 1])
    const next = box(sorted[i])
    const gap = axis === "x" ? next.left - prev.right : next.top - prev.bottom
    if (gap >= -1) gaps.push(px(gap))
  }
  return gaps
}

export function gapChecks(elements, config) {
  const groups = elements.filter((e) => isGroup(e, config) && inFlow(e))
  const byParent = new Map()
  for (const g of groups) {
    if (!byParent.has(g.parent)) byParent.set(g.parent, [])
    byParent.get(g.parent).push(g)
  }
  const out = []
  for (const siblings of byParent.values()) {
    if (siblings.length < 2) continue
    const betweenList = pairGaps(siblings, axisOf(siblings))
    if (!betweenList.length) continue
    const between = Math.min(...betweenList)
    for (const g of siblings) {
      const items = kids(elements, g.i).filter((e) => !isGroup(e, config))
      if (items.length < 2) continue
      const insideList = pairGaps(items, axisOf(items))
      if (!insideList.length) continue
      const inside = Math.max(...insideList)
      const need = config.betweenOverInside * inside
      const fail = between + 0.01 < need
      out.push(entry(
        "G2",
        fail ? "fail" : "pass",
        g.selector,
        { inside, between, ratio: inside ? r2(between / inside) : null },
        { betweenOverInside: config.betweenOverInside },
        fail
          ? `Gap inside this group is ${inside}px. Gap between groups is ${between}px. Between must be at least ${config.betweenOverInside} times inside.`
          : `Gap between groups is ${between}px, at least ${config.betweenOverInside} times the ${inside}px inside gap.`,
      ))
    }
  }
  if (!out.length) {
    out.push(entry("G2", "skip", "", {}, {}, "Need at least two groups that each contain two items."))
  }
  return out
}

export function paddingChecks(elements, config) {
  const items = elements.filter((e) => isContainer(e, config) && inFlow(e) && kindKey(e))
  const byKind = new Map()
  for (const el of items) {
    const key = kindKey(el)
    if (!byKind.has(key)) byKind.set(key, [])
    byKind.get(key).push(el)
  }
  const out = []
  const sides = ["top", "right", "bottom", "left"]
  for (const [key, group] of byKind) {
    if (group.length < 2) continue
    const pads = group.map((el) => Object.fromEntries(sides.map((s) => [s, px(el.padding?.[s] || 0)])))
    const spread = {}
    for (const s of sides) {
      const vals = pads.map((p) => p[s])
      spread[s] = Math.max(...vals) - Math.min(...vals)
    }
    const worst = Math.max(...sides.map((s) => spread[s]))
    const measured = { kind: key, spreadTop: spread.top, spreadRight: spread.right, spreadBottom: spread.bottom, spreadLeft: spread.left }
    if (worst <= config.paddingPx) {
      out.push(entry("G3", "pass", group[0].selector, measured, { paddingPx: config.paddingPx }, "Padding matches other containers of this kind."))
      continue
    }
    const floor = Object.fromEntries(sides.map((s) => [s, Math.min(...pads.map((p) => p[s]))]))
    for (let i = 0; i < group.length; i++) {
      const delta = Math.max(...sides.map((s) => pads[i][s] - floor[s]))
      if (delta <= config.paddingPx) continue
      out.push(entry(
        "G3",
        "fail",
        group[i].selector,
        { ...measured, paddingTop: pads[i].top, paddingRight: pads[i].right, paddingBottom: pads[i].bottom, paddingLeft: pads[i].left },
        { paddingPx: config.paddingPx },
        `Padding spread is ${px(worst)}px. Limit is ${config.paddingPx}px.`,
      ))
    }
  }
  if (!out.length) {
    out.push(entry("G3", "skip", "", {}, {}, "No kind has more than one container."))
  }
  return out
}

const INDENT_TAG = new Set(["blockquote", "li", "dd", "td", "th", "aside", "nav", "header", "footer"])

function ancestorChain(el, byIndex) {
  const out = []
  let p = el.parent
  while (p != null && byIndex[p]) {
    out.push(byIndex[p])
    p = byIndex[p].parent
  }
  return out
}

function overlaps(a, b) {
  return Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1
}

export function edgeChecks(elements, config) {
  const column = primaryColumn(elements, config) || elements.find((e) => e.tag === "body") || null
  if (!column) return [entry("G4", "skip", "", {}, {}, "No main column to align.")]
  const byIndex = Object.fromEntries(elements.map((e) => [e.i, e]))
  const candidates = elements.filter((el) => {
    if (el.i === column.i || !inFlow(el)) return false
    if (el.align === "center" || el.align === "end") return false
    if (INDENT_TAG.has(el.tag)) return false
    if (!(isHeading(el, config) || isBody(el, config) || isCard(el, config) || isButton(el, config))) return false
    const ancestors = ancestorChain(el, byIndex)
    if (!ancestors.some((a) => a.i === column.i)) return false
    const between = ancestors.filter((a) => a.i !== column.i)
    if (between.some((a) => INDENT_TAG.has(a.tag) || isCard(a, config) || isContainer(a, config))) return false
    if (between.some((a) => (a.padding?.left || 0) > config.alignPx || (a.border?.left || 0) > 0)) return false
    return el.rect.width > 0 || el.rect.height > 0
  })
  if (candidates.length < 2) {
    return [entry("G4", "skip", column.selector, {}, {}, "No column with two stacked headings, paragraphs, cards, or buttons.")]
  }
  const sorted = [...candidates].sort((a, b) => a.rect.y - b.rect.y || a.rect.x - b.rect.x)
  const bands = []
  for (const el of sorted) {
    const b = box(el)
    let band = bands.find((item) => overlaps(item, b))
    if (!band) {
      band = { top: b.top, bottom: b.bottom, left: b.left, selector: el.selector }
      bands.push(band)
    } else {
      band.top = Math.min(band.top, b.top)
      band.bottom = Math.max(band.bottom, b.bottom)
      if (b.left < band.left) {
        band.left = b.left
        band.selector = el.selector
      }
    }
  }
  const lefts = bands.map((b) => px(b.left))
  const shared = Math.min(...lefts)
  const spread = Math.max(...lefts) - shared
  if (spread <= config.alignPx) {
    return [entry(
      "G4",
      "pass",
      column.selector,
      { spread, edges: lefts.length },
      { alignPx: config.alignPx },
      "Headings, text, cards, and buttons share a left edge.",
    )]
  }
  return bands.flatMap((band, i) => {
    const delta = lefts[i] - shared
    if (delta <= config.alignPx) return []
    return [entry(
      "G4",
      "fail",
      band.selector,
      { left: lefts[i], sharedLeft: shared, delta, spread },
      { alignPx: config.alignPx },
      `Left edge is ${delta}px off the shared line. Limit is ${config.alignPx}px.`,
    )]
  })
}

export function scrollCheck(snapshot, config) {
  const viewport = px(snapshot.viewportWidth)
  const scrollWidth = px(snapshot.scrollWidth)
  const limit = viewport + config.scrollPx
  const fail = scrollWidth > limit
  return entry(
    "G9",
    fail ? "fail" : "pass",
    "html",
    { scrollWidth, viewport },
    { scrollPx: config.scrollPx },
    fail
      ? `scrollWidth ${scrollWidth}px is wider than the ${viewport}px viewport.`
      : "No sideways scroll.",
  )
}

function childMap(elements) {
  const map = new Map()
  for (const el of elements) {
    if (!map.has(el.parent)) map.set(el.parent, [])
    map.get(el.parent).push(el)
  }
  return map
}

function descendantsOf(id, map, out = []) {
  for (const child of map.get(id) || []) {
    out.push(child)
    descendantsOf(child.i, map, out)
  }
  return out
}

function effectiveColumn(column, elements) {
  if (!column) return null
  if (column.display !== "contents" && column.rect.width >= 1) return column
  const boxes = descendantsOf(column.i, childMap(elements)).filter((e) => e.display !== "contents" && e.rect.width > 0)
  if (!boxes.length) return column
  const left = Math.min(...boxes.map((e) => e.rect.x))
  const right = Math.max(...boxes.map((e) => e.rect.x + e.rect.width))
  const top = Math.min(...boxes.map((e) => e.rect.y))
  const bottom = Math.max(...boxes.map((e) => e.rect.y + e.rect.height))
  return { ...column, rect: { x: left, y: top, width: right - left, height: bottom - top } }
}

function readingCh(column) {
  if (!column.ch) return 0
  const inner = column.rect.width - (column.padding?.left || 0) - (column.padding?.right || 0) - (column.border?.left || 0) - (column.border?.right || 0)
  return inner / column.ch
}

function columnExemption(column, elements, config, viewport) {
  const allowed = new Set(config.columnExemptions || [])
  if (!allowed.size || !column) return ""
  const tree = descendantsOf(column.i, childMap(elements))
  const cards = tree.filter((e) => isCard(e, config))
  const forms = tree.filter((e) => e.tag === "form")
  const paragraphs = tree.filter((e) => isBody(e, config))
  const ch = readingCh(column)
  if (allowed.has("prose") && ch >= 55 && ch <= 80 && paragraphs.length >= 1 && cards.length === 0) return "prose"
  const left = column.rect.x
  const right = viewport - (column.rect.x + column.rect.width)
  const centered = left >= 24 && right >= 24 && Math.abs(left - right) <= Math.max(24, viewport * 0.04)
  const selfCard = isCard(column, config)
  const singleCard = (selfCard && cards.length === 0) || cards.length === 1
  const singleForm = forms.length === 1 && cards.length <= 1
  if (allowed.has("signin") && centered && (singleForm || singleCard) && cards.length <= 1) return "signin"
  return ""
}

function rowAdjusted(card, elements, config) {
  const boxes = contentBoxes(card, elements)
  if (!card.stretched || !boxes.length) return boxes
  const siblings = elements.filter((e) => e.parent === card.parent && e.i !== card.i && isCard(e, config) && e.rect.height > 0)
  const row = siblings.filter((e) => overlaps(box(e), box(card)))
  let maxBottom = Math.max(...boxes.map((item) => item.bottom))
  for (const sib of row) {
    const sibBoxes = contentBoxes(sib, elements)
    if (sibBoxes.length) maxBottom = Math.max(maxBottom, ...sibBoxes.map((item) => item.bottom))
  }
  const innerBottom = card.rect.y + card.rect.height - (card.border?.bottom || 0) - (card.padding?.bottom || 0)
  const target = Math.min(maxBottom, innerBottom)
  return boxes.map((item) => (item.bottom >= target ? item : { ...item, bottom: item.bottom === Math.max(...boxes.map((b) => b.bottom)) ? target : item.bottom }))
}

export function evaluate(snapshot, config) {
  const elements = snapshot.elements || []
  const rules = []
  const cards = elements.filter((e) => isCard(e, config) && e.rect.height > 0 && (inFlow(e) || e.position === "absolute" || e.position === "fixed"))
  for (const card of cards) rules.push(cardSlack(card, rowAdjusted(card, elements, config), config.whitespacePx))
  const width = snapshot.requestedWidth ?? px(snapshot.viewportWidth)
  const widths = snapshot.widths
  if (width === config.columnAtWidth) {
    const column = effectiveColumn(primaryColumn(elements, config) || elements.find((e) => e.tag === "body") || null, elements)
    if (!column) rules.push(entry("G1", "skip", "", {}, {}, config.auto ? "No main column to measure." : "auto is off and no column was marked."))
    else {
      const share = columnShare(column, snapshot.viewportWidth, config.minWidthRatio)
      const exempt = share.status === "fail" ? columnExemption(column, elements, config, snapshot.viewportWidth) : ""
      if (exempt) {
        const ch = r2(readingCh(column))
        const message = exempt === "prose"
          ? `Exempt: prose, a reading column ${ch}ch wide.`
          : "Exempt: signin, a centered card or form."
        rules.push(entry("G1", "skip", column.selector, { width: px(column.rect.width), viewport: px(snapshot.viewportWidth), ch, exemption: exempt }, { minWidthRatio: config.minWidthRatio }, message))
      } else rules.push(share)
    }
  } else if (widths && !widths.includes(config.columnAtWidth) && width === widths[0]) {
    rules.push(entry("G1", "skip", "", { columnAtWidth: config.columnAtWidth }, {}, `Column width is checked at ${config.columnAtWidth}px, which is not in this run.`))
  }
  if (!cards.length && !rules.some((rule) => rule.id === "G1")) {
    rules.push(entry("G1", "skip", "", {}, {}, config.auto ? "No card to measure at this width." : "auto is off and no card was marked."))
  }
  for (const key of config.explicitSelectors || []) {
    if ((snapshot.hits || {})[key]) continue
    const id = key === "groups" ? "G2" : key === "headings" || key === "body" || key === "buttons" ? "G4" : "G1"
    rules.push(entry(id, "skip", config.selectors[key] || "", {}, {}, "Selector matched nothing."))
  }
  rules.push(...gapChecks(elements, config))
  rules.push(...paddingChecks(elements, config))
  rules.push(...edgeChecks(elements, config))
  if (widths && !widths.includes(390) && width === widths[0]) {
    rules.push(entry("G9", "skip", "html", {}, {}, "G9 runs at 390, which is not in this run."))
  }
  rules.push(scrollCheck(snapshot, config))
  for (const frame of snapshot.iframes || []) {
    rules.push(entry("G1", "skip", frame, {}, {}, "Iframes are not measured."))
  }
  return rules
}

export function verdictOf(widthReports) {
  const rules = widthReports.flatMap((w) => w.rules)
  if (rules.some((rule) => rule.status === "fail")) return "fail"
  if (!rules.some((rule) => rule.status === "pass")) return "inconclusive"
  return "pass"
}

export function buildReport(page, widthReports, flags = {}) {
  const widths = widthReports.map((w) => ({ width: w.width, rules: w.rules }))
  let verdict = verdictOf(widths)
  if (flags.empty || flags.pageError || flags.jsonError || flags.navError) verdict = "inconclusive"
  return { page, widths, verdict }
}
