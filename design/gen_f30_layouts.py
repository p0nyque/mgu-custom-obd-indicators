#!/usr/bin/env python3
"""Write the F30 layouts (apps/apex_dash/hud/layouts/f30_comfort.json, f30_sport.json, f30_eco.json).

    python3 design/gen_f30_layouts.py

The 2017 F-series multifunction instrument display (option 6WB, F30 / F32 LCI), one layout per drive mode, for
the "byMode" setting (In Comfort / In Sport / In Eco Pro). The shader layers f30dash and f30needles draw the dials
(shared/shaders.js); this places the numbers and words around them, from the same geometry.

Geometry on the 1920x720 panel. BMW paints a solid black box over us at x 1406..1597, y 342..419 (its gear slot,
shared/visible.js), at the height where a round dial's hub sits. The rev counter is centred on it and both dials
get a black centre cap of radius CAP that the box (its corners 103 px from the centre) disappears into; the
speedometer mirrors the rev counter about x 960. Dials and the tucked-in side gauges keep the 2017 photo's
proportions (rim radius 262 = 0.87 x the photo's), fitted between the panel's edges.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'apps', 'apex_dash', 'hud', 'layouts')
FONTS = os.path.join(ROOT, 'apps', 'apex_dash', 'hud', 'fonts')

BOX = (1406, 342, 1597, 419)
TACH = (1501, 380, 262)                                                      # centred on the box (1501.5, 380.5)
SPD = (1920 - TACH[0], TACH[1], TACH[2])                                     # (419, 380)
FUEL = (SPD[0] - 334, SPD[1] + 92, 70)                                       # (85, 472)
OIL = (TACH[0] + 334, TACH[1] + 92, 70)                                      # (1835, 472)
CAP = 114
LABEL_R = 182          # the Sport scale's end numbers (no magnifier there)
TICK_IN = 200          # where the long ticks end inside (the shader: 0.855 R - 24)
MARGIN = 4             # between a magnified number and the ticks
DIGIT_ADV_L, CAP_H_L = 25, 34   # f30_numL: a digit's advance, the digits' height
SPD0, SPDW = -130, 260  # the speed scale, clockwise degrees from 12 o'clock (as the shader)
TACH0, TACHW = -113, 243
SPEED = {'metric': 260, 'us': 160}
# Text goes into packed image sheets per (class, z) (shared/hud.js _plan): one z per region keeps each sheet's box
# tight (pixel memory is w x h x 8 per sheet). Z_SPD2 holds every other metric speed number (neighbours overlap).
Z_SPD, Z_SPD2, Z_STRIP, Z_REV = 5, 6, 7, 8


def cell(font):
    with open(os.path.join(FONTS, font + '.json')) as f:
        return json.load(f)['cellHeight']


def pos(c, a, r):
    """The point at clockwise angle a (degrees from 12 o'clock), radius r round centre c."""
    return c[0] + r * math.sin(math.radians(a)), c[1] - r * math.cos(math.radians(a))


def T(id, x, y, w, h, text, font, color, align='center', z=5, **kw):
    d = {'id': id, 'type': 'text', 'z': z, 'x': int(round(x)), 'y': int(round(y)), 'w': w, 'h': h, 'text': text, 'font': font, 'color': color, 'align': align}
    d.update(kw)
    return d


def at(id, c, a, r, w, text, font, color, **kw):
    """A text widget centred on a point of a dial."""
    x, y = pos(c, a, r)
    h = kw.pop('h', cell(font))
    return T(id, x - w / 2, y - h / 2, w, h, text, font, color, **kw)


def label_r(a, text):
    """Where a scale number's centre goes: clear of the ticks' inner ends (TICK_IN) by MARGIN even when it is
    magnified, so its extent along the radius counts (wide numbers at 3 and 9 o'clock sit further in)."""
    half_w = len(text) * DIGIT_ADV_L / 2
    s, c = abs(math.sin(math.radians(a))), abs(math.cos(math.radians(a)))
    return TICK_IN - MARGIN - (s * half_w + c * CAP_H_L / 2)


def dial_number(id, c, a, text, near, z=5, **kw):
    """A scale number that grows (the 2017 magnifier) while it is the one nearest the needle."""
    w = 84 if len(text) > 1 else 50
    return at(id, c, a, label_r(a, text), w, text, 'f30_num', 'dim', h=cell('f30_numL'), z=z, near=near,
              nearFont='f30_numL', nearColor='fg', valign='middle', **kw)


def speed_numbers(magnify):
    out = []
    for unit, top in SPEED.items():
        for k in range(top // 20 + 1):
            a = SPD0 + SPDW * 20 * k / top
            # metric labels are 20 deg apart: neighbours' boxes overlap, so every other one sits on z 6 (its own sheet)
            z = Z_SPD2 if unit == 'metric' and k % 2 else Z_SPD
            kw = {'toggle': 'units=' + unit}
            if magnify:
                out.append(dial_number('spd_%s_%d' % (unit, k * 20), SPD, a, str(k * 20), ['f30spd', k], z=z, **kw))
            elif k in (0, top // 20):   # Sport: only the ends
                out.append(at('spd_%s_%d' % (unit, k * 20), SPD, a, LABEL_R, 84, str(k * 20), 'f30_num', 'fg', **kw))
    return out


def rev_numbers():
    return [dial_number('rpm_%d' % k, TACH, TACH0 + TACHW * k * 1000 / 7500, str(k), ['rpm', k], z=Z_REV) for k in range(1, 8)]


def side_gauges():
    return [
        at('fuel_full', FUEL, -32, 40, 20, '1', 'f30_unit', 'label'),
        at('fuel_empty', FUEL, 168, 40, 20, '0', 'f30_unit', 'label'),
        {'id': 'fuel_icon', 'type': 'icon', 'z': 5, 'x': int(round(pos(FUEL, 50, 30)[0] - 12)), 'y': int(round(pos(FUEL, 50, 30)[1] - 12)),
         'w': 24, 'h': 24, 'icon': 'fuel', 'color': 'label'},
        {'id': 'oil_icon', 'type': 'icon', 'z': Z_REV, 'x': int(round(pos(OIL, -50, 30)[0] - 12)), 'y': int(round(pos(OIL, -50, 30)[1] - 12)),
         'w': 24, 'h': 24, 'icon': 'oilcan', 'color': 'label'},
    ]


def speedo(mode):
    out = speed_numbers(mode != 'sport')
    if mode == 'sport':
        out.append(T('spd_unit', SPD[0] - 35, 290, 70, cell('f30_unit'), '{{u:speedLc}}', 'f30_unit', 'label'))
        out.append(T('spd_digital', SPD[0] - 115, 333, 230, cell('f30_speed'), '{{speed}}', 'f30_speed', 'fg'))
    else:
        out.append(T('spd_unit', SPD[0] - 35, 236, 70, cell('f30_unit'), '{{u:speedLc}}', 'f30_unit', 'label'))
        out.append(T('spd_digital', SPD[0] - 100, SPD[1] - 26, 200, cell('f30_spdM'), '{{speed}}', 'f30_spdM', 'fg'))
        # the range bar's ends: 0 at the left, the range on the right
        out.append(at('range_0', SPD, 214, 190, 30, '0', 'f30_num', 'dim'))
        out.append(T('range_val', 410, 524, 90, cell('f30_num'), '{{range}}', 'f30_num', 'fg', 'right'))
        out.append(T('range_unit', 503, 529, 40, cell('f30_unit'), '{{u:distLc}}', 'f30_unit', 'label', 'left'))
    return out


def strip():
    vh, uh = cell('f30_val'), cell('f30_unit')
    base = 596 + 34                        # the values' baseline (f30_val's is 34 px down its cell)
    return [
        T('time_cap', 690, 566, 80, uh, 'Time', 'f30_unit', 'faint', 'left', z=Z_STRIP),
        T('time_val', 690, 596, 130, vh, '{{time}}', 'f30_val', 'fg', 'left', z=Z_STRIP),
        T('temp_cap', 1150, 566, 80, uh, 'Temp', 'f30_unit', 'faint', 'right', z=Z_STRIP),
        T('temp_val', 1080, 596, 118, vh, '{{ambient1}}', 'f30_val', 'fg', 'right', z=Z_STRIP),
        T('temp_unit', 1200, base - 22, 32, uh, '{{u:temp}}', 'f30_unit', 'label', 'left', z=Z_STRIP),
    ]


def revs(mode):
    out = []
    if mode == 'eco':
        out.append(at('charge', TACH, -40, 168, 100, 'CHARGE', 'f30_label', 'label', z=Z_REV))
        out.append(at('power', TACH, 38, 168, 100, 'POWER', 'f30_label', 'label', z=Z_REV))
    else:
        out += rev_numbers()
        out.append(T('rpm_unit', TACH[0] - 80, 236, 160, cell('f30_unit'), '1/min x 1000', 'f30_unit', 'label', z=Z_REV))
        out.append(T('ready', 1309, 426, 90, cell('f30_label'), 'READY', 'f30_label', 'label', z=Z_REV))
        out.append(T('off', 1346, 470, 56, cell('f30_label'), 'OFF', 'f30_label', 'label', z=Z_REV))
    if mode != 'comfort':
        out.append(T('mode_name', TACH[0] - 80, 505, 160, cell('f30_label'), '{{plus:%s}}' % mode, 'f30_label', 'accent', z=Z_REV))
    out.append(T('gear', TACH[0] - 60, 544, 120, cell('f30_gear'), '{{gearF}}', 'f30_gear', 'fg', z=Z_REV))
    return out


def layout(mode):
    geo = {'mode': mode, 'spd': list(SPD), 'tach': list(TACH), 'fuelG': list(FUEL), 'oilG': list(OIL), 'cap': CAP}
    dash = dict({'id': 'f30_dash', 'type': 'f30dash', 'class': 'ambient', 'z': -10, 'x': 0, 'y': 0, 'w': 1920, 'h': 720}, **geo)
    if mode == 'sport':
        dash['flood'] = 0.9
    needles = dict({'id': 'f30_needles', 'type': 'f30needles', 'class': 'overlay', 'z': 10, 'x': 0, 'y': 0, 'w': 1920, 'h': 720}, **geo)
    name = {'comfort': 'F30 Comfort', 'sport': 'F30 Sport', 'eco': 'F30 Eco Pro'}[mode]
    return {
        'schemaVersion': 2,
        'name': name,
        'theme': {'comfort': 'f30', 'sport': 'f30s', 'eco': 'f30e'}[mode],
        '_about': 'The 2017 F-series multifunction instrument display (6WB), ' + mode + '. Made by design/gen_f30_layouts.py; edit that, not this.',
        'widgets': [dash] + speedo(mode) + side_gauges() + strip() + revs(mode) + [needles],
    }


if __name__ == '__main__':
    for mode, file in (('comfort', 'f30_comfort'), ('sport', 'f30_sport'), ('eco', 'f30_eco')):
        L = layout(mode)
        with open(os.path.join(OUT, file + '.json'), 'w') as f:
            json.dump(L, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(file, len(L['widgets']), 'widgets')
