import { readFileSync } from "node:fs"
import {
  ConfigError,
  buildReport,
  cardSlack,
  columnShare,
  evaluate,
  isCard,
  isGroup,
  kindKey,
  mergeConfig,
  scrollCheck,
} from "./geometry.mjs"

let passed = 0
let failed = 0

function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"} ${name}`)
  if (ok) passed += 1
  else {
    failed += 1
    if (detail) console.log(`    ${String(detail).replaceAll("\n", "\n    ")}`)
  }
}

function pad(n) {
  return { top: n, right: n, bottom: n, left: n }
}

function border(n) {
  return { top: n, right: n, bottom: n, left: n }
}

function boxEl(over) {
  return {
    i: over.i,
    parent: over.parent ?? null,
    tag: over.tag ?? "div",
    id: over.id ?? "",
    classes: over.classes ?? [],
    role: over.role ?? "",
    dataUi: over.dataUi ?? "",
    selector: over.selector ?? `e${over.i}`,
    position: over.position ?? "static",
    rect: over.rect,
    padding: over.padding ?? pad(0),
    border: over.border ?? border(0),
    text: over.text ?? null,
    match: over.match ?? {},
    ch: over.ch ?? 0,
    cardLike: over.cardLike ?? false,
    password: over.password ?? false,
    display: over.display || "",
  }
}

const fitted = {
  selector: "#fit",
  rect: { x: 16, y: 100, width: 400, height: 90 },
  padding: pad(16),
  border: border(1),
}
const child = { top: 117, bottom: 173 }

check("fitted card passes", cardSlack(fitted, [child], 4).status === "pass")
check("tall card fails", cardSlack({ ...fitted, rect: { ...fitted.rect, height: 220 } }, [child], 4).status === "fail")
check("slack equal to tolerance passes", cardSlack({ ...fitted, rect: { ...fitted.rect, height: 94 } }, [child], 4).status === "pass")
check("slack over tolerance fails", cardSlack({ ...fitted, rect: { ...fitted.rect, height: 95 } }, [child], 4).status === "fail")
check("empty tall card fails", cardSlack({ ...fitted, rect: { ...fitted.rect, height: 220 } }, [], 4).status === "fail")
check(
  "empty card that is only padding passes",
  cardSlack({ selector: "#empty", rect: { x: 0, y: 0, width: 100, height: 34 }, padding: pad(16), border: border(1) }, [], 4).status === "pass",
)
check("negative slack is not excess space", cardSlack(fitted, [{ top: 110, bottom: 173 }], 4).status === "pass")

const wide = { selector: "main", rect: { x: 0, y: 0, width: 768, height: 400 } }
const narrow = { selector: "main", rect: { x: 0, y: 0, width: 767, height: 400 } }
check("column at 60 percent passes", columnShare(wide, 1280, 0.6).status === "pass")
check("column under 60 percent fails", columnShare(narrow, 1280, 0.6).status === "fail")
check("full width column passes", columnShare({ ...wide, rect: { ...wide.rect, width: 1280 } }, 1280, 0.6).status === "pass")

const cfg = mergeConfig(null)
check("scroll equal to viewport passes", scrollCheck({ viewportWidth: 390, scrollWidth: 390 }, cfg).status === "pass")
check("scroll past viewport fails", scrollCheck({ viewportWidth: 390, scrollWidth: 391 }, cfg).status === "fail")
check("scroll allowance is configurable", scrollCheck({ viewportWidth: 390, scrollWidth: 391 }, mergeConfig({ scrollPx: 1 })).status === "pass")

function cardAt(i, parent, y, height, padding, x = 16) {
  return boxEl({
    i,
    parent,
    tag: "article",
    classes: ["card"],
    dataUi: "card",
    selector: `#c${i}`,
    rect: { x, y, width: 400, height },
    padding: pad(padding),
    border: border(1),
  })
}

function textIn(card, i, contentH) {
  const top = card.rect.y + card.border.top + card.padding.top
  const natural = card.rect.height - card.border.top - card.border.bottom - card.padding.top - card.padding.bottom
  return boxEl({
    i,
    parent: card.i,
    tag: "p",
    selector: `${card.selector} > p`,
    rect: { x: card.rect.x + 17, y: top, width: 120, height: contentH ?? natural },
  })
}

function layout(over = {}) {
  const columnWidth = over.columnWidth ?? 1280
  const cardH = 90
  const inside = over.inside ?? 8
  const between = over.between ?? 24
  const g1y = 96
  const c1 = cardAt(4, 3, g1y, over.tall ?? cardH, 16)
  const c2y = g1y + cardH + inside
  const c2 = cardAt(6, 3, c2y, cardH, over.loose ?? 16)
  const g1h = (c2y + cardH) - g1y
  const g2y = g1y + g1h + between
  const c3 = cardAt(9, 8, g2y, cardH, 16)
  const c4 = cardAt(11, 8, g2y + cardH + inside, cardH, 16)
  const elements = [
    boxEl({ i: 0, tag: "main", selector: "main", rect: { x: 0, y: 0, width: columnWidth, height: 800 }, padding: pad(16) }),
    boxEl({ i: 1, parent: 0, tag: "h1", selector: "h1", rect: { x: 16, y: 16, width: 200, height: 32 } }),
    boxEl({ i: 2, parent: 0, tag: "p", selector: "p", rect: { x: 16, y: 56, width: 240, height: 24 } }),
    boxEl({
      i: 3, parent: 0, tag: "section", classes: ["group"], dataUi: "group", selector: "#g1",
      rect: { x: 16, y: g1y, width: columnWidth - 32, height: g1h },
    }),
    c1,
    textIn(c1, 5, over.tall ? 56 : undefined),
    c2,
    textIn(c2, 7),
    boxEl({
      i: 8, parent: 0, tag: "section", classes: ["group"], dataUi: "group", selector: "#g2",
      rect: { x: 16, y: g2y, width: columnWidth - 32, height: (cardH + inside + cardH) },
    }),
    c3,
    textIn(c3, 10),
    c4,
    textIn(c4, 12),
    boxEl({
      i: 13, parent: 0, tag: "button", selector: "#save",
      rect: { x: 16 + (over.shift ?? 0), y: g2y + cardH + inside + cardH + 24, width: 120, height: 40 },
    }),
  ]
  return {
    viewportWidth: over.viewport ?? 1280,
    scrollWidth: over.scrollWidth ?? (over.viewport ?? 1280),
    requestedWidth: over.requested ?? (over.viewport ?? 1280),
    elements,
  }
}

function badIds(rules) {
  return [...new Set(rules.filter((r) => r.status === "fail").map((r) => r.id))]
}

function checkClean(name, rules) {
  const bad = rules.filter((r) => r.status !== "pass")
  check(name, bad.length === 0, JSON.stringify(bad, null, 2))
}

function checkOnly(name, rules, id) {
  const bad = badIds(rules)
  check(name, bad.length === 1 && bad[0] === id, JSON.stringify(rules.filter((r) => r.status === "fail"), null, 2))
}

checkClean("plain layout passes every rule at 1280", evaluate(layout(), cfg))
checkClean("plain layout passes every rule at 390", evaluate(layout({ viewport: 390, requested: 390, columnWidth: 390 }), cfg))
checkOnly("tall card fails only G1", evaluate(layout({ tall: 220 }), cfg), "G1")
checkOnly("narrow column fails only G1", evaluate(layout({ columnWidth: 480 }), cfg), "G1")
check(
  "narrow column is not judged at 390",
  badIds(evaluate(layout({ viewport: 390, requested: 390, columnWidth: 200 }), cfg)).length === 0,
)
checkOnly("tight group gap fails only G2", evaluate(layout({ between: 8 }), cfg), "G2")
checkOnly("loose padding fails only G3", evaluate(layout({ loose: 36 }), cfg), "G3")
checkOnly("shifted button fails only G4", evaluate(layout({ shift: 28 }), cfg), "G4")
checkOnly(
  "sideways scroll fails only G9",
  evaluate(layout({ viewport: 390, requested: 390, columnWidth: 390, scrollWidth: 640 }), cfg),
  "G9",
)
checkOnly(
  "a higher gap ratio fails a page the default allows",
  evaluate(layout(), mergeConfig({ betweenOverInside: 4 })),
  "G2",
)
check(
  "a larger whitespace tolerance lets the tall card pass",
  badIds(evaluate(layout({ tall: 220 }), mergeConfig({ whitespacePx: 200 }))).length === 0,
)

function moveCard(elements, cardI, rect) {
  const card = elements.find((e) => e.i === cardI)
  const dx = rect.x - card.rect.x
  const dy = rect.y - card.rect.y
  card.rect = { ...card.rect, ...rect }
  for (const child of elements.filter((e) => e.parent === cardI)) {
    child.rect = { ...child.rect, x: child.rect.x + dx, y: child.rect.y + dy }
  }
}

const sideBySide = layout()
moveCard(sideBySide.elements, 6, { x: 424, y: 96, width: 400, height: 90 })
checkClean("cards in a row share the row's left edge", evaluate(sideBySide, cfg))

const floated = layout()
floated.elements.push(boxEl({
  i: 40, parent: 0, tag: "article", classes: ["card"], dataUi: "card", selector: "#float",
  position: "absolute", rect: { x: 16, y: 96, width: 100, height: 400 }, padding: pad(16), border: border(1),
}))
checkOnly("a tall absolute card fails only G1", evaluate(floated, cfg), "G1")

const manual = {
  viewportWidth: 800,
  scrollWidth: 800,
  requestedWidth: 800,
  elements: [
    boxEl({ i: 0, tag: "div", dataUi: "main", selector: "#col", rect: { x: 0, y: 0, width: 800, height: 200 } }),
    boxEl({ i: 1, parent: 0, tag: "div", dataUi: "card", selector: "#a", rect: { x: 8, y: 8, width: 100, height: 40 }, padding: pad(8) }),
    boxEl({ i: 2, parent: 1, tag: "span", selector: "#a-t", rect: { x: 16, y: 16, width: 40, height: 24 } }),
    boxEl({ i: 3, parent: 0, tag: "div", dataUi: "card", selector: "#b", rect: { x: 8, y: 64, width: 100, height: 40 }, padding: pad(8) }),
    boxEl({ i: 4, parent: 3, tag: "span", selector: "#b-t", rect: { x: 16, y: 72, width: 40, height: 24 } }),
  ],
}
const manualRules = evaluate(manual, mergeConfig({ auto: false }))
check(
  "data-ui cards with no class still compare",
  manualRules.filter((r) => r.id === "G1" || r.id === "G3").every((r) => r.status === "pass")
    && manualRules.some((r) => r.id === "G3" && r.status === "pass"),
  JSON.stringify(manualRules.filter((r) => r.status !== "pass"), null, 2),
)
check("data-ui kind is shared", kindKey(manual.elements[1]) === "data-ui:card")

const hidden = {
  viewportWidth: 800, scrollWidth: 800, requestedWidth: 800,
  elements: [
    boxEl({ i: 0, tag: "main", selector: "main", rect: { x: 0, y: 0, width: 800, height: 100 } }),
    boxEl({ i: 1, parent: 0, tag: "div", classes: ["card"], selector: "#guess", rect: { x: 0, y: 0, width: 80, height: 80 } }),
  ],
}
check(
  "auto off ignores a class guess",
  evaluate(hidden, mergeConfig({ auto: false })).filter((r) => r.id === "G1").every((r) => r.status === "skip"),
)
check("auto on sees a card class", isCard(hidden.elements[1], cfg) === true)
check(
  "a selector flag marks a card",
  isCard({ classes: [], dataUi: "", match: { card: true } }, mergeConfig({ auto: false })) === true,
)

check("example config merges", mergeConfig(JSON.parse(readFileSync(new URL("../rules.example.json", import.meta.url)))).minWidthRatio === 0.6)
check("unknown config key is an error", (() => { try { mergeConfig({ color: "red" }); return false } catch (e) { return e instanceof ConfigError } })())
check("bad ratio is an error", (() => { try { mergeConfig({ betweenOverInside: 0 }); return false } catch (e) { return e instanceof ConfigError } })())
check("empty config keeps defaults", mergeConfig({}).whitespacePx === 4 && mergeConfig({}).columnAtWidth === 1280)

const report = buildReport("page.html", [
  { width: 390, rules: evaluate(layout({ viewport: 390, requested: 390, columnWidth: 390 }), cfg) },
  { width: 1280, rules: evaluate(layout(), cfg) },
])
check("report verdict passes when rules pass", report.verdict === "pass" && report.page === "page.html" && report.widths.length === 2)
const failedReport = buildReport("bad.html", [{ width: 390, rules: [{ id: "G9", status: "fail" }] }])
check("report verdict fails when any rule fails", failedReport.verdict === "fail")

check("padding spread of 4 fails G3", badIds(evaluate(layout({ loose: 20 }), cfg)).includes("G3"))
const edge = layout()
edge.elements[2].rect = { ...edge.elements[2].rect, x: 20 }
checkOnly("edges 4px apart fail only G4", evaluate(edge, cfg), "G4")
check("bare group class is not a layout group", isGroup({ classes: ["group"], dataUi: "", match: {} }, cfg) === false)
check("card-group is a layout group", isGroup({ classes: ["card-group"], dataUi: "", match: {} }, cfg) === true)
check("padding utilities share a kind", kindKey({ classes: ["card", "p-4"], role: "" }) === kindKey({ classes: ["card", "p-10", "featured"], role: "" }))
check("infinity config is rejected", (() => { try { mergeConfig({ whitespacePx: 1e309 }); return false } catch (e) { return e instanceof ConfigError } })())
check("negative config is rejected", (() => { try { mergeConfig({ alignPx: -1 }); return false } catch (e) { return e instanceof ConfigError } })())
const skipped = buildReport("empty.html", [{ width: 390, rules: [{ id: "G9", status: "skip", element: "html", measured: {}, limit: {}, message: "No." }] }])
function readingPage(width, extra) {
  const x = (1280 - width) / 2
  const elements = [
    boxEl({ i: 0, tag: "main", selector: "main", rect: { x, y: 0, width, height: 500 }, ch: (extra && extra.columnCh) || 9, cardLike: Boolean(extra && extra.cardLike) }),
    boxEl({ i: 1, parent: 0, tag: "h1", selector: "h1", rect: { x: x + 16, y: 16, width: 200, height: 32 } }),
    boxEl({ i: 2, parent: 0, tag: "p", selector: "p", rect: { x: x + 16, y: 64, width: 240, height: 48 }, ch: (extra && extra.paragraphCh) || 9 }),
  ]
  if (extra && extra.cards) {
    for (let n = 0; n < extra.cards; n++) {
      elements.push(boxEl({
        i: 10 + n, parent: 0, tag: "article", classes: ["card"], selector: `#c${n}`,
        rect: { x: x + 16, y: 140 + n * 100, width: 200, height: 90 }, padding: pad(16), border: border(1),
      }))
      elements.push(boxEl({
        i: 40 + n, parent: 10 + n, tag: "p", selector: `#c${n} p`,
        rect: { x: x + 33, y: 157 + n * 100, width: 120, height: 56 },
      }))
    }
  }
  if (extra && extra.form) {
    elements.push(boxEl({ i: 3, parent: 0, tag: "form", selector: "form", rect: { x: x + 16, y: 16, width: width - 32, height: 220 } }))
  }
  if (extra && extra.password) {
    elements.push(boxEl({ i: 4, parent: 3, tag: "input", selector: "input", rect: { x: x + 24, y: 80, width: 200, height: 32 }, password: true }))
  }
  return { viewportWidth: 1280, scrollWidth: 1280, requestedWidth: 1280, widths: [1280], elements }
}

const proseRules = evaluate(readingPage(680), cfg)
check(
  "a 680px reading column is an exempt skip",
  proseRules.some((r) => r.status === "skip" && r.measured.exemption === "prose") && badIds(proseRules).length === 0,
  JSON.stringify(proseRules.filter((r) => r.status !== "pass"), null, 2),
)
const signinRules = evaluate(readingPage(360, { form: true, password: true }), cfg)
check(
  "a centered sign-in card is an exempt skip",
  signinRules.some((r) => r.status === "skip" && r.measured.exemption === "signin") && badIds(signinRules).length === 0,
  JSON.stringify(signinRules.filter((r) => r.status !== "pass"), null, 2),
)
checkOnly("a half-width dashboard still fails G1", evaluate(readingPage(640, { cards: 3 }), cfg), "G1")
check(
  "clearing exemptions judges the reading column",
  badIds(evaluate(readingPage(680), mergeConfig({ columnExemptions: [] }))).includes("G1"),
)
check("all skips are inconclusive", skipped.verdict === "inconclusive")
check("a fatal page is inconclusive", buildReport("bad.html", [{ width: 390, rules: [{ id: "G9", status: "pass", element: "html", measured: {}, limit: {}, message: "No sideways scroll." }] }], { fatal: true, reason: "The page has no visible content." }).verdict === "inconclusive")

console.log(`${passed} passed, ${failed} failed`)
process.exit(failed ? 1 : 0)
