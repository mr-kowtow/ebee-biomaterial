#!/usr/bin/env python3
"""
Covers old E-BEE watermarks (top-left AND top-right) and stamps the
new bee SVG logo in the TOP-RIGHT corner of all product images.
"""
from PIL import Image, ImageDraw
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

def sample_bg(img, x, y, radius=12):
    """Average colour from a region, clamped to image bounds."""
    w, h = img.size
    pixels = []
    for dx in range(-radius, radius+1, 3):
        for dy in range(-radius, radius+1, 3):
            nx, ny = max(0, min(w-1, x+dx)), max(0, min(h-1, y+dy))
            p = img.getpixel((nx, ny))
            pixels.append(p[:3])
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b, 255)

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
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # ── Erase TOP-LEFT old watermark (scale with image size) ─────────────────
    erase_w = min(170, int(w * 0.22))
    erase_h = min(190, int(h * 0.22))
    sample_offset = min(200, int(w * 0.28))
    bg_tl = sample_bg(img, sample_offset, sample_offset)
    draw.rectangle([0, 0, erase_w, erase_h], fill=bg_tl)

    # ── Erase TOP-RIGHT old watermark ────────────────────────────────────────
    bg_tr = sample_bg(img, w - sample_offset, sample_offset)
    draw.rectangle([w - erase_w, 0, w, erase_h], fill=bg_tr)

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

    # Create a white semi-transparent backing so logo is readable on any bg
    backing = Image.new('RGBA', (lw2 + 16, lh2 + 10), (255, 255, 255, 200))
    img.alpha_composite(backing, (paste_x - 8, paste_y - 5))
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
