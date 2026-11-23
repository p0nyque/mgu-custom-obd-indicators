#!/usr/bin/env python3
"""Write the F-series analogue layout (apps/apex_dash/hud/layouts/f_analog.json).

    python3 design/gen_fa_layout.py

The analogue instrument cluster of the F-series (F10 / F01 / F15 / F25, 2009-2018), after BMW's own drawing of the
F10's cluster with the 6WA strip and a 2014 X5 photo (kept privately, not in this repo), lit in BMW orange as these
clusters are at night: fuel gauge, speedometer, rev counter, oil temperature gauge, each in a closed ring, and the strip between the big dials with orange
captions on orange hairlines (Time, Range, Temp). The shader layers fadash and faneedles draw the dials
(shared/shaders.js); this places the numbers and words around them, from the same geometry.

Geometry on the 1920x720 panel, the same as the F30 layouts (design/gen_f30_layouts.py): BMW paints a solid black
box over us at x 1406..1597, y 342..419 (shared/visible.js), so the rev counter is centred on it and both big dials
get a black hub cap of radius CAP that the box (its corners 103 px from the centre) disappears into. The small
gauges sit lower, as on the F10, but are smaller than BMW's (76 px, not 0.39 x the big ring): the panel's edges
leave no more room.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'apps', 'apex_dash', 'hud', 'layouts')
FONTS = os.path.join(ROOT, 'apps', 'apex_dash', 'hud', 'fonts')

TACH = (1501, 380, 262)                     # centred on BMW's gear box (1501.5, 380.5)
SPD = (1920 - TACH[0], TACH[1], TACH[2])    # (419, 380)
FUEL = (85, 520, 76)
OIL = (1835, 520, 76)
CAP = 108
BAND_IN = 228          # the scale band's inner edge (the shader: 0.87 R)
MARGIN = 26            # between a scale number and the band, as on BMW's drawing
A0, AW = -125, 250     # both big scales, clockwise degrees from 12 o'clock (as the shader)
S0, SW = -60, 120      # the small gauges
SPEED = {'metric': 260, 'us': 160}
CX = (SPD[0] + TACH[0]) / 2                 # 960
STRIP_Y = SPD[1] + 225                      # the hairlines (the shader's strip())
# Text goes into packed image sheets per (class, z) (shared/hud.js _plan): one z per region keeps each sheet's box
# tight (pixel memory is w x h x 8 per sheet). Z_SPD2 holds every other metric speed number (neighbours overlap).
Z_SPD, Z_SPD2, Z_STRIP, Z_REV = 5, 6, 7, 8


def font(name):
    with open(os.path.join(FONTS, name + '.json')) as f:
        return json.load(f)


def cell(name):
    return font(name)['cellHeight']


def pos(c, a, r):
    """The point at clockwise angle a (degrees from 12 o'clock), radius r round centre c."""
    return c[0] + r * math.sin(math.radians(a)), c[1] - r * math.cos(math.radians(a))


def T(id, x, y, w, h, text, fnt, color, align='center', z=Z_SPD, **kw):
    d = {'id': id, 'type': 'text', 'z': z, 'x': int(round(x)), 'y': int(round(y)), 'w': w, 'h': h, 'text': text, 'font': fnt, 'color': color, 'align': align}
    d.update(kw)
    return d


def at(id, c, a, r, w, text, fnt, color, **kw):
    """A text widget centred on a point of a dial."""
    x, y = pos(c, a, r)
    h = kw.pop('h', cell(fnt))
    return T(id, x - w / 2, y - h / 2, w, h, text, fnt, color, **kw)


def icon(id, c, a, r, name, z):
    x, y = pos(c, a, r)
    return {'id': id, 'type': 'icon', 'z': z, 'x': int(round(x - 12)), 'y': int(round(y - 12)), 'w': 24, 'h': 24, 'icon': name, 'color': 'label'}


def scale_number(id, c, a, text, fnt, z, **kw):
    """A scale number centred clear of the band by MARGIN; its extent along the radius counts, so wide numbers at
    3 and 9 o'clock sit further in."""
    f = font(fnt)
    adv = f['glyphs']['0']['advance']
    half_w, cap_h = len(text) * adv / 2, f['baseline'] * 0.72
    s, co = abs(math.sin(math.radians(a))), abs(math.cos(math.radians(a)))
    r = BAND_IN - MARGIN - (s * half_w + co * cap_h / 2)
    return at(id, c, a, r, len(text) * adv + 12, text, fnt, 'dim', z=z, valign='middle', **kw)


def speedo():
    out = []
    for unit, top in SPEED.items():
        for k in range(top // 20 + 1):
            a = A0 + AW * 20 * k / top
            z = Z_SPD2 if unit == 'metric' and k % 2 else Z_SPD
            out.append(scale_number('spd_%s_%d' % (unit, k * 20), SPD, a, str(k * 20), 'fa_spd', z, toggle='units=' + unit))
    out.append(at('spd_unit', SPD, 0, 124, 80, '{{u:speedLc}}', 'f30_unit', 'label'))
    # the range bar's ends: 0 over its left end, the unit by its right end
    out.append(at('range_0', SPD, 213, 210, 24, '0', 'f30_unit', 'label'))
    out.append(at('range_unit', SPD, 140, 222, 40, '{{u:distLc}}', 'f30_unit', 'label'))
    return out


def revs():
    out = [scale_number('rpm_%d' % k, TACH, A0 + AW * k * 1000 / 7500, str(k), 'fa_tach', Z_REV) for k in range(8)]
    # below the 3 and the 4 and above the hub cap; a touch right of centre, as on BMW's drawing
    out.append(T('rpm_unit', TACH[0] - 70, TACH[1] - 124 - cell('f30_unit') / 2, 160, cell('f30_unit'), '1/min x 1000', 'f30_unit', 'label', z=Z_REV))
    gy = TACH[1] + TACH[2] * 0.62           # the gear frame's centre (the shader's gearFrame)
    out.append(T('gear', TACH[0] - 32, gy - cell('f30_gear') / 2, 64, cell('f30_gear'), '{{gearF}}', 'f30_gear', 'fg', z=Z_REV))
    return out


def side_gauges():
    """Inside the ticks (which start at 0.64 r), in fa_small; the oil marks follow the units ({{faOil0..2}})."""
    out = [
        small_label('fuel_empty', FUEL, S0, '0'),
        small_label('fuel_half', FUEL, S0 + SW / 2, '1/2'),
        small_label('fuel_full', FUEL, S0 + SW, '1'),
        icon('fuel_icon', FUEL, -122, 42, 'fuel', Z_SPD),
        icon('oil_icon', OIL, 122, 42, 'oilcan', Z_REV),
        at('oil_unit', OIL, 180, 36, 30, '{{u:temp}}', 'fa_small', 'label', z=Z_REV),
    ]
    for k in range(3):
        out.append(small_label('oil_mark%d' % k, OIL, S0 + SW * k / 2, '{{faOil%d}}' % k, chars=3, z=Z_REV))
    return out


def small_label(id, c, a, text, chars=None, z=Z_SPD):
    """A small gauge's mark, its outer edge 4 px inside the ticks' inner ends."""
    f = font('fa_small')
    adv = f['glyphs']['0']['advance']
    n = chars or len(text)
    half_w, cap_h = n * adv / 2, f['baseline'] * 0.72
    s, co = abs(math.sin(math.radians(a))), abs(math.cos(math.radians(a)))
    r = c[2] * 0.64 - 4 - (s * half_w + co * cap_h / 2)
    return at(id, c, a, r, int(n * adv + 8), text, 'fa_small', 'label', z=z, valign='middle')


def strip():
    """Three readouts on the shader's hairlines: the caption above the line's left end, the value below."""
    uh, vh = cell('f30_unit'), cell('f30_val')
    cap_y, val_y = STRIP_Y - uh - 4, STRIP_Y + 7
    unit_y = val_y + font('f30_val')['baseline'] - font('f30_unit')['baseline']   # the unit on the value's baseline
    L, M, R = CX - 250, CX - 70, CX + 110
    return [
        T('time_cap', L, cap_y, 120, uh, 'Time', 'f30_unit', 'accent', 'left', z=Z_STRIP),
        T('time_val', L, val_y, 140, vh, '{{time}}', 'f30_val', 'fg', 'left', z=Z_STRIP),
        T('range_cap', M, cap_y, 120, uh, 'Range', 'f30_unit', 'accent', 'left', z=Z_STRIP),
        T('range_val', M, val_y, 90, vh, '{{range}}', 'f30_val', 'fg', 'right', z=Z_STRIP),
        T('range_unit2', M + 94, unit_y, 44, uh, '{{u:distLc}}', 'f30_unit', 'label', 'left', z=Z_STRIP),
        T('temp_cap', R, cap_y, 120, uh, 'Temp', 'f30_unit', 'accent', 'left', z=Z_STRIP),
        T('temp_val', R, val_y, 104, vh, '{{ambient1}}', 'f30_val', 'fg', 'right', z=Z_STRIP),
        T('temp_unit', R + 108, unit_y, 32, uh, '{{u:temp}}', 'f30_unit', 'label', 'left', z=Z_STRIP),
    ]


def layout():
    geo = {'spd': list(SPD), 'tach': list(TACH), 'fuelG': list(FUEL), 'oilG': list(OIL), 'cap': CAP}
    dash = dict({'id': 'fa_dash', 'type': 'fadash', 'class': 'ambient', 'z': -10, 'x': 0, 'y': 0, 'w': 1920, 'h': 720}, **geo)
    needles = dict({'id': 'fa_needles', 'type': 'faneedles', 'class': 'overlay', 'z': 10, 'x': 0, 'y': 0, 'w': 1920, 'h': 720}, **geo)
    return {
        'schemaVersion': 2,
        'name': 'F-series analogue',
        'theme': 'fa',
        '_about': 'The F-series analogue instrument cluster (F10 / F15 / F25). Made by design/gen_fa_layout.py; edit that, not this.',
        'widgets': [dash] + speedo() + side_gauges() + strip() + revs() + [needles],
    }


if __name__ == '__main__':
    L = layout()
    with open(os.path.join(OUT, 'f_analog.json'), 'w') as f:
        json.dump(L, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('f_analog', len(L['widgets']), 'widgets')
