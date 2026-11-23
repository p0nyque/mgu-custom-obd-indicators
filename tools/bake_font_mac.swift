// Bake one HUD bitmap font atlas with CoreText, for a Mac without Pillow.
//
//     swiftc -O tools/bake_font_mac.swift -o /tmp/bake_font_mac
//     /tmp/bake_font_mac <out.json> <font.ttf> <px size> <characters>
//
// Same output and the same metrics rules as tools/bake_fonts.py (the reference baker): every cell is the
// height of the font's whole glyph set, digits share one advance (tabular), PAD 2, a 1024 px wide atlas,
// one alpha byte per pixel, base64 in "alpha". Static fonts only (no variable-font instance, no stroke).
// The coverage is CoreText's, not FreeType's: against a Pillow bake of the same spec, cell heights and glyph
// widths can differ by a pixel (checked on scale.json: cell 27 vs 26, advances equal).
import CoreText
import Foundation

let args = CommandLine.arguments
guard args.count == 5, let size = Double(args[3]) else {
    FileHandle.standardError.write("usage: bake_font_mac <out.json> <font.ttf> <px size> <characters>\n".data(using: .utf8)!)
    exit(2)
}
let outPath = args[1], fontPath = args[2], chars = Array(args[4])
let PAD = 2, ATLAS_W = 1024
let DIGITS = Set("0123456789")

guard let provider = CGDataProvider(url: URL(fileURLWithPath: fontPath) as CFURL), let cg = CGFont(provider) else {
    FileHandle.standardError.write("cannot read \(fontPath)\n".data(using: .utf8)!)
    exit(1)
}
let font = CTFontCreateWithGraphicsFont(cg, CGFloat(size), nil, nil)

func glyph(_ c: Character) -> CGGlyph {
    let u = Array(String(c).utf16)
    var g = [CGGlyph](repeating: 0, count: u.count)
    CTFontGetGlyphsForCharacters(font, u, &g, u.count)
    return g[0]
}
func advance(_ c: Character) -> Double {
    var g = glyph(c), a = CGSize.zero
    CTFontGetAdvancesForGlyphs(font, .horizontal, &g, &a, 1)
    return Double(a.width)
}
/// Ink box as Pillow's getbbox(anchor='ls'): x right, y down from the baseline, whole pixels.
func bbox(_ c: Character) -> (l: Int, t: Int, r: Int, b: Int) {
    var g = glyph(c), r = CGRect.zero
    CTFontGetBoundingRectsForGlyphs(font, .horizontal, &g, &r, 1)
    return (Int(floor(r.minX)), -Int(ceil(r.maxY)), Int(ceil(r.maxX)), -Int(floor(r.minY)))
}

let ink = chars.filter { $0 != " " }
var boxes: [Character: (l: Int, t: Int, r: Int, b: Int)] = [:]
for c in ink { boxes[c] = bbox(c) }
let top = boxes.values.map { $0.t }.min() ?? 0
let bottom = boxes.values.map { $0.b }.max() ?? 0
let height = bottom - top + 2 * PAD
let tab = chars.contains(where: { DIGITS.contains($0) }) ? chars.filter { DIGITS.contains($0) }.map(advance).max()! : 0

struct Cell { let c: Character; let w: Int; let px: [UInt8]?; let ox: Int; let adv: Int }
var cells: [Cell] = []
for c in chars {
    let adv = advance(c)
    if c == " " { cells.append(Cell(c: c, w: 0, px: nil, ox: 0, adv: Int((adv > 0 ? adv : size * 0.25).rounded()))); continue }
    let b = boxes[c]!
    let w = b.r - b.l + 2 * PAD
    var px = [UInt8](repeating: 0, count: w * height)
    px.withUnsafeMutableBytes { buf in
        let ctx = CGContext(data: buf.baseAddress, width: w, height: height, bitsPerComponent: 8, bytesPerRow: w,
                            space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
        ctx.setAllowsAntialiasing(true); ctx.setShouldAntialias(true)
        ctx.setAllowsFontSmoothing(false); ctx.setShouldSmoothFonts(false)
        ctx.setFillColor(gray: 1, alpha: 1)
        var g = glyph(c)
        // CoreGraphics is y-up from the bottom row; the baseline sits PAD - top rows below the cell's top
        var pos = CGPoint(x: CGFloat(PAD - b.l), y: CGFloat(height - (PAD - top)))
        CTFontDrawGlyphs(font, &g, &pos, 1, ctx)
    }
    let shift = DIGITS.contains(c) ? (tab - adv) / 2 : 0
    cells.append(Cell(c: c, w: w, px: px, ox: Int((Double(b.l - PAD) + shift).rounded()), adv: Int((DIGITS.contains(c) ? tab : adv).rounded())))
}

// simple row packing, as bake_fonts.py
var x = 0, y = 0
var placed: [Character: (Int, Int)] = [:]
for cell in cells where cell.px != nil {
    if x + cell.w > ATLAS_W { x = 0; y += height }
    placed[cell.c] = (x, y)
    x += cell.w
}
let atlasH = y + height
var atlas = [UInt8](repeating: 0, count: ATLAS_W * atlasH)
var glyphs: [String: [String: Int]] = [:]
for cell in cells {
    guard let px = cell.px else { glyphs[String(cell.c)] = ["x": 0, "y": 0, "w": 0, "h": 0, "ox": 0, "advance": cell.adv]; continue }
    let (gx, gy) = placed[cell.c]!
    for row in 0..<height { for col in 0..<cell.w { atlas[(gy + row) * ATLAS_W + gx + col] = px[row * cell.w + col] } }
    glyphs[String(cell.c)] = ["x": gx, "y": gy, "w": cell.w, "h": height, "ox": cell.ox, "advance": cell.adv]
}
let meta: [String: Any] = ["source": (fontPath as NSString).lastPathComponent, "size": Int(size), "cellHeight": height,
                           "baseline": PAD - top, "glyphs": glyphs, "width": ATLAS_W, "height": atlasH,
                           "alpha": Data(atlas).base64EncodedString()]
let data = try! JSONSerialization.data(withJSONObject: meta, options: [.sortedKeys])
try! data.write(to: URL(fileURLWithPath: outPath))
print(String(format: "%@  %dpx  cell height %d  atlas %dx%d  %d glyphs", (outPath as NSString).lastPathComponent, Int(size), height, ATLAS_W, atlasH, glyphs.count))
