#!/usr/bin/env python3
"""
Covers old E-BEE watermarks (top-left AND top-right) and stamps the
new bee SVG logo in the TOP-RIGHT corner of all product images.
"""
from PIL import Image, ImageChops
import os, shutil, subprocess

IMG_DIR   = '/Users/rosh/Documents/ebee/images'
BACKUP_DIR = '/Users/rosh/Documents/ebee/images_backup'
SVG_PATH  = '/Users/rosh/Documents/ebee/images/logo-ebee.svg'
LOGO_TMP  = '/tmp/logo-ebee.svg.png'
LOGO_CROP = '/tmp/logo-ebee-cropped.png'

SKIP_KEYWORDS = ['Certificates', 'about-us', 'why_icon', 'application',
                 'news', 'footer', 'jieyang', 'page_banner', 'index_us',
                 'index_news', 'recyclable', 'logo', 'about_img']

# ── Rasterize & crop the SVG logo once ───────────────────────────────────────
print('Rasterizing bee logo...')
subprocess.run(['qlmanage', '-t', '-s', '800', '-o', '/tmp/', SVG_PATH],
               capture_output=True)

src = Image.open(LOGO_TMP).convert('RGBA')
w0, h0 = src.size
pix = src.load()
min_x, min_y, max_x, max_y = w0, h0, 0, 0
for y in range(h0):
    for x in range(w0):
        r, g, b, a = pix[x, y]
        if not (r > 235 and g > 235 and b > 235):
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y

pad = 10
logo_full = src.crop((max(0, min_x-pad), max(0, min_y-pad),
                       min(w0, max_x+pad), min(h0, max_y+pad)))
logo_full.save(LOGO_CROP)
print(f'  Logo cropped to {logo_full.size}')

def has_old_logo(img, x0, y0, x1, y1, saturation_threshold=35):
    """Return True if the region contains colourful (logo) pixels, not just grey/white."""
    for y in range(y0, min(y1, img.size[1]), 4):
        for x in range(x0, min(x1, img.size[0]), 4):
            r, g, b = img.getpixel((x, y))[:3]
            if max(r, g, b) - min(r, g, b) > saturation_threshold:
                return True
    return False

def is_white_bg(img, sample_pts=None):
    """Return True if the image background is near-white (r,g,b all > 230)."""
    w, h = img.size
    pts = sample_pts or [(w//2, 10), (10, h//2), (w-10, h//2), (w//2, h-10)]
    for x, y in pts:
        r, g, b = img.getpixel((min(x, w-1), min(y, h-1)))[:3]
        if r < 230 or g < 230 or b < 230:
            return False
    return True

def process_image(filepath, logo):
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()

    # Restore from backup each time so we always start from the original
    backup = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(backup):
        shutil.copy2(backup, filepath)
    else:
        shutil.copy2(filepath, backup)

    img = Image.open(filepath).convert('RGBA')
    w, h = img.size

    # ── Erase old watermark ──────────────────────────────────────────────────
    erase_w = min(190, int(w * 0.24))
    erase_h = min(210, int(h * 0.26))

    def erase_logo_zone(x0, y0, x1, y1, ref_x, ref_y):
        """Replace logo pixels in zone with background. Uses pixel-level diff
        so only coloured logo pixels are overwritten; background texture stays."""
        if not has_old_logo(img, x0, y0, x1, y1):
            return
        from PIL import ImageFilter
        # Average background colour from a small clean region outside the zone
        rx, ry = min(ref_x, w - 1), min(ref_y, h - 1)
        samples = []
        for dx in range(-10, 11, 5):
            for dy in range(-10, 11, 5):
                px = max(0, min(w-1, rx+dx))
                py = max(0, min(h-1, ry+dy))
                samples.append(img.getpixel((px, py))[:3])
        bg_r = sum(s[0] for s in samples) // len(samples)
        bg_g = sum(s[1] for s in samples) // len(samples)
        bg_b = sum(s[2] for s in samples) // len(samples)

        bg_solid  = Image.new('RGB', (x1 - x0, y1 - y0), (bg_r, bg_g, bg_b))
        zone_rgb  = img.crop((x0, y0, x1, y1)).convert('RGB')
        diff      = ImageChops.difference(zone_rgb, bg_solid)
        # Lower threshold + dilation to catch anti-aliased logo edges
        mask = diff.convert('L').point(lambda v: 255 if v > 18 else 0)
        mask = mask.filter(ImageFilter.MaxFilter(7))   # expand ~3px to cover edges
        fill = Image.new('RGBA', (x1 - x0, y1 - y0), (bg_r, bg_g, bg_b, 255))
        img.paste(fill, (x0, y0), mask)

    if is_white_bg(img):
        # White bg: fill entire logo zone with white (perfect, invisible)
        from PIL import ImageDraw as _ID
        draw = _ID.Draw(img)
        if has_old_logo(img, 0, 0, erase_w, erase_h):
            draw.rectangle([0, 0, erase_w, erase_h], fill=(255, 255, 255, 255))
        if has_old_logo(img, w - erase_w, 0, w, erase_h):
            draw.rectangle([w - erase_w, 0, w, erase_h], fill=(255, 255, 255, 255))
    else:
        # Grey bg: pixel-level replacement — only logo pixels are overwritten
        erase_logo_zone(0, 0, erase_w, erase_h,
                        ref_x=erase_w + 30, ref_y=20)
        erase_logo_zone(w - erase_w, 0, w, erase_h,
                        ref_x=w - erase_w - 30, ref_y=20)

    # ── Stamp new bee logo TOP-RIGHT ─────────────────────────────────────────
    # Scale logo to ~25% of image width, max 200px
    target_w = min(200, int(w * 0.25))
    lw, lh = logo.size
    scale = target_w / lw
    logo_resized = logo.resize((int(lw * scale), int(lh * scale)), Image.LANCZOS)

    margin = 12
    lw2, lh2 = logo_resized.size
    paste_x = w - lw2 - margin
    paste_y = margin

    # Composite logo directly — no backing box
    img.alpha_composite(logo_resized, (paste_x, paste_y))

    # Save
    if ext in ('.jpg', '.jpeg'):
        img.convert('RGB').save(filepath, 'JPEG', quality=93)
    else:
        img.save(filepath, 'PNG')

    print(f'  ✓ {filename}')

# ── Collect product images ────────────────────────────────────────────────────
os.makedirs(BACKUP_DIR, exist_ok=True)
logo = Image.open(LOGO_CROP).convert('RGBA')

all_images = [f for f in os.listdir(IMG_DIR)
              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
product_images = [f for f in all_images
                  if not any(k.lower() in f.lower() for k in SKIP_KEYWORDS)]

print(f'\nProcessing {len(product_images)} product images...\n')
for fname in sorted(product_images):
    try:
        process_image(os.path.join(IMG_DIR, fname), logo)
    except Exception as e:
        print(f'  ✗ {fname}: {e}')

print('\nDone.')
