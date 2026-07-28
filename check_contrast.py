import math

def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    R = srgb_to_linear(r)
    G = srgb_to_linear(g)
    B = srgb_to_linear(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def contrast_ratio(c1, c2):
    l1 = relative_luminance(c1)
    l2 = relative_luminance(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def wcag_check(ratio, size='normal'):
    if size == 'large':
        return 'PASS' if ratio >= 3.0 else 'FAIL'
    return 'PASS' if ratio >= 4.5 else 'FAIL'

# UPDATED Light theme colors from tokens.css
colors = {
    'primary': '#0070D2',
    'primary-hover': '#005BB5',
    'text': '#0F172A',
    'text-2': '#475569',
    'text-3': '#64748B',       # UPDATED from #94A3B8
    'text-inverse': '#FFFFFF',
    'surface-page': '#F8FAFC',
    'surface-card': '#FFFFFF',
    'surface-subtle': '#F1F5F9',
    'border': '#E2E8F0',
    'border-2': '#CBD5E1',
    'success': '#047857',      # UPDATED from #059669
    'warning': '#B45309',      # UPDATED from #D97706
    'danger': '#DC2626',
    'purple': '#7C3AED',
    'orange': '#C2410C',       # UPDATED - darkened for 4.5:1
    'gold': '#B45309',         # UPDATED from #D97706
    'whatsapp': '#15803D',     # UPDATED - darkened for 4.5:1
}

print('=' * 80)
print('LIGHT THEME - WCAG AA CONTRAST RATIOS (UPDATED)')
print('=' * 80)
print('{:<45} {:>7} {:>8} {:>8}'.format('Pair', 'Ratio', 'Normal', 'Large'))
print('-' * 80)

tests = [
    ('Text on Page BG', 'text', 'surface-page'),
    ('Text on Card BG', 'text', 'surface-card'),
    ('Text-2 on Page BG', 'text-2', 'surface-page'),
    ('Text-2 on Card BG', 'text-2', 'surface-card'),
    ('Text-3 on Page BG', 'text-3', 'surface-page'),
    ('Text-3 on Card BG', 'text-3', 'surface-card'),
    ('Primary on White', 'primary', 'surface-card'),
    ('White on Primary', 'text-inverse', 'primary'),
    ('White on Primary-Hover', 'text-inverse', 'primary-hover'),
    ('Success on White', 'success', 'surface-card'),
    ('Warning on White', 'warning', 'surface-card'),
    ('Danger on White', 'danger', 'surface-card'),
    ('Purple on White', 'purple', 'surface-card'),
    ('Orange on White', 'orange', 'surface-card'),
    ('Gold on White', 'gold', 'surface-card'),
    ('Primary on Page BG', 'primary', 'surface-page'),
    ('Text on Subtle BG', 'text', 'surface-subtle'),
    ('Text-2 on Subtle BG', 'text-2', 'surface-subtle'),
    ('Primary on Subtle', 'primary', 'surface-page'),
    ('Text-2 on Border', 'text-2', 'border'),
    ('WhatsApp on White', 'whatsapp', 'surface-card'),
]

fails = 0
for name, fg, bg in tests:
    ratio = contrast_ratio(colors[fg], colors[bg])
    normal = wcag_check(ratio, 'normal')
    large = wcag_check(ratio, 'large')
    marker = '' if normal == 'PASS' else ' FAIL'
    if normal == 'FAIL':
        fails += 1
    print('{:<45} {:>7.2f}:1 {:>8} {:>8}{}'.format(name, ratio, normal, large, marker))

# UPDATED Dark theme colors
dark = {
    'primary': '#3B9AFF',
    'primary-hover': '#2B8AEE',
    'text': '#F9FAFB',
    'text-2': '#D1D5DB',
    'text-3': '#94A3B8',       # UPDATED from #6B7280
    'text-inverse': '#000000',
    'surface-page': '#0B0F1A',
    'surface-card': '#111827',
    'surface-subtle': '#1F2937',
    'success': '#34D399',
    'warning': '#FBBF24',
    'danger': '#F87171',
    'purple': '#A78BFA',
    'orange': '#FB923C',
    'gold': '#FBBF24',
}

print()
print('=' * 80)
print('DARK THEME - WCAG AA CONTRAST RATIOS (UPDATED)')
print('=' * 80)
print('{:<45} {:>7} {:>8} {:>8}'.format('Pair', 'Ratio', 'Normal', 'Large'))
print('-' * 80)

dark_tests = [
    ('Text on Page BG', 'text', 'surface-page'),
    ('Text on Card BG', 'text', 'surface-card'),
    ('Text-2 on Page BG', 'text-2', 'surface-page'),
    ('Text-2 on Card BG', 'text-2', 'surface-card'),
    ('Text-3 on Page BG', 'text-3', 'surface-page'),
    ('Text-3 on Card BG', 'text-3', 'surface-card'),
    ('Primary on Card BG', 'primary', 'surface-card'),
    ('Black on Primary', 'text-inverse', 'primary'),
    ('Black on Primary-Hover', 'text-inverse', 'primary-hover'),
    ('Success on Card BG', 'success', 'surface-card'),
    ('Warning on Card BG', 'warning', 'surface-card'),
    ('Danger on Card BG', 'danger', 'surface-card'),
    ('Purple on Card BG', 'purple', 'surface-card'),
    ('Orange on Card BG', 'orange', 'surface-card'),
    ('Gold on Card BG', 'gold', 'surface-card'),
    ('Primary on Page BG', 'primary', 'surface-page'),
    ('Text on Subtle BG', 'text', 'surface-subtle'),
    ('Text-2 on Subtle BG', 'text-2', 'surface-subtle'),
]

for name, fg, bg in dark_tests:
    ratio = contrast_ratio(dark[fg], dark[bg])
    normal = wcag_check(ratio, 'normal')
    large = wcag_check(ratio, 'large')
    marker = '' if normal == 'PASS' else ' FAIL'
    if normal == 'FAIL':
        fails += 1
    print('{:<45} {:>7.2f}:1 {:>8} {:>8}{}'.format(name, ratio, normal, large, marker))

print()
print('=' * 80)
total = len(tests) + len(dark_tests)
if fails == 0:
    print('RESULT: ALL {} combinations PASS WCAG AA'.format(total))
else:
    print('RESULT: {} of {} combinations FAIL WCAG AA'.format(fails, total))
print('=' * 80)
