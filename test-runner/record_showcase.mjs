import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');
const DEMOS_DIR = path.join(REPO_ROOT, 'demos/latest');
const GALLERY_DIR = path.join(DEMOS_DIR, 'gallery');

// 1. Locate Playwright
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  const sm3Playwright = path.resolve(REPO_ROOT, '../sm3/node_modules/playwright/index.mjs');
  if (fs.existsSync(sm3Playwright)) {
    ({ chromium } = await import(sm3Playwright));
  } else {
    throw new Error('Playwright not found in environment or ../sm3/node_modules/playwright');
  }
}

// 2. Locate FFmpeg
function getFFmpegPath() {
  const msPlaywrightFFmpeg = path.resolve(process.env.HOME, 'Library/Caches/ms-playwright/ffmpeg-1013/ffmpeg-mac');
  if (fs.existsSync(msPlaywrightFFmpeg)) return msPlaywrightFFmpeg;
  try {
    const whichOut = spawn('which', ['ffmpeg'], { encoding: 'utf8' });
    if (whichOut && whichOut.stdout) return whichOut.stdout.trim();
  } catch (_) {}
  return null;
}

// 3. Optional local HTTP Server for html/ directory
function startLocalServer(port = 8788) {
  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
  };

  const htmlDir = path.join(REPO_ROOT, 'html');
  const server = http.createServer((req, res) => {
    let reqPath = req.url.split('?')[0];
    let filePath = path.join(htmlDir, reqPath === '/' ? 'index.html' : reqPath);
    fs.stat(filePath, (err, stats) => {
      if (err || !stats.isFile()) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, {
        'Content-Type': mimeTypes[ext] || 'application/octet-stream',
        'Cache-Control': 'no-cache',
      });
      fs.createReadStream(filePath).pipe(res);
    });
  });

  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => {
      console.log(`[HTTP] Serving nexttext/html on http://127.0.0.1:${port}`);
      resolve(server);
    });
  });
}

// 4. Cursor Helpers
async function injectCursor(page) {
  await page.evaluate(() => {
    if (document.getElementById('demo-cursor')) return;
    const c = document.createElement('div');
    c.id = 'demo-cursor';
    c.style.position = 'fixed';
    c.style.top = '0';
    c.style.left = '0';
    c.style.width = '18px';
    c.style.height = '18px';
    c.style.borderRadius = '50%';
    c.style.backgroundColor = 'rgba(110, 168, 254, 0.8)';
    c.style.border = '2px solid #ffffff';
    c.style.boxShadow = '0 0 14px rgba(110, 168, 254, 0.9)';
    c.style.pointerEvents = 'none';
    c.style.zIndex = '9999999';
    c.style.transform = 'translate(-50%, -50%)';
    c.style.transition = 'width 0.12s ease, height 0.12s ease, background-color 0.12s ease, transform 0.08s ease';
    document.body.appendChild(c);
    window.__setCursor = (x, y) => {
      c.style.left = `${x}px`;
      c.style.top = `${y}px`;
    };
  });
}

async function smoothMove(page, targetX, targetY, steps = 18, delayMs = 12) {
  await page.mouse.move(targetX, targetY, { steps });
  await page.evaluate(({ x, y }) => window.__setCursor?.(x, y), { x: targetX, y: targetY });
  if (delayMs > 0) await page.waitForTimeout(delayMs);
}

async function smoothClick(page, selector, steps = 16) {
  const loc = page.locator(selector).first();
  await loc.waitFor({ state: 'visible', timeout: 5000 });
  const box = await loc.boundingBox();
  if (!box) return;
  const targetX = box.x + box.width / 2;
  const targetY = box.y + box.height / 2;
  await smoothMove(page, targetX, targetY, steps);
  await page.evaluate(() => {
    const c = document.getElementById('demo-cursor');
    if (c) {
      c.style.width = '13px';
      c.style.height = '13px';
      c.style.backgroundColor = 'rgba(244, 63, 94, 0.95)';
    }
  });
  await page.waitForTimeout(100);
  await page.mouse.click(targetX, targetY);
  await page.evaluate(() => {
    const c = document.getElementById('demo-cursor');
    if (c) {
      c.style.width = '18px';
      c.style.height = '18px';
      c.style.backgroundColor = 'rgba(110, 168, 254, 0.8)';
    }
  });
  await page.waitForTimeout(200);
}

// 5. WebP Thumbnail Generator
async function generateWebPThumbnail(browser, sourcePngPath, outWebPPath) {
  console.log(`[Thumbnail] Generating WebP from ${sourcePngPath}...`);
  const page = await browser.newPage();
  const pngDataUrl = `data:image/png;base64,${fs.readFileSync(sourcePngPath).toString('base64')}`;

  const webpBase64 = await page.evaluate(async (dataUrl) => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 384;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const webpData = canvas.toDataURL('image/webp', 0.88);
        resolve(webpData.split(',')[1]);
      };
      img.src = dataUrl;
    });
  }, pngDataUrl);

  fs.writeFileSync(outWebPPath, Buffer.from(webpBase64, 'base64'));
  await page.close();
}

// 6. Main Orchestrator
async function main() {
  fs.mkdirSync(GALLERY_DIR, { recursive: true });

  const tempVideoDir = path.join(REPO_ROOT, 'demos/.temp_video');
  fs.mkdirSync(tempVideoDir, { recursive: true });

  const ffmpegBin = getFFmpegPath();
  console.log(`[Config] FFmpeg binary: ${ffmpegBin || 'NOT FOUND (raw video will be retained)'}`);

  console.log('[Browser] Launching Chromium (1280x720 recording mode)...');
  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    recordVideo: {
      dir: tempVideoDir,
      size: { width: 1280, height: 720 },
    },
  });

  const page = await context.newPage();
  const startTime = Date.now();

  try {
    const targetUrl = process.env.LOCAL_DEMO ? 'http://127.0.0.1:8788/' : 'https://jpeckenpaugh.github.io/nexttext/';
    console.log(`[Nav] Opening ${targetUrl}...`);
    await page.goto(targetUrl, { waitUntil: 'networkidle' });
    await injectCursor(page);

    console.log('[Init] Waiting for Pyodide runtime ready state...');
    await page.waitForSelector('#runtime-status[data-state="ready"]', { timeout: 35000 });
    console.log('[Init] Runtime is ready!');

    // 00:00 - 00:04: Hover status badge & hero
    const statusBox = await page.locator('#runtime-status').boundingBox();
    if (statusBox) {
      await smoothMove(page, statusBox.x + statusBox.width / 2, statusBox.y + statusBox.height / 2, 20);
    }
    await page.waitForTimeout(1000);

    // Capture Gallery Still 1: Pyodide Runtime Ready
    const still1 = path.join(GALLERY_DIR, '01-pyodide-runtime-ready.png');
    await page.screenshot({ path: still1 });
    console.log(`[Gallery] Saved 01-pyodide-runtime-ready.png`);

    // 00:04 - 00:09: Scenario 1 - Debias Basics
    console.log('[Scenario 1] Selecting Debias basics...');
    await smoothClick(page, '[data-scenario="debias"]');
    await page.waitForTimeout(600);

    // Move to Run button and click
    await smoothClick(page, '#run-button');
    await page.waitForTimeout(1200);

    // Capture Gallery Still 2: Debias Basics
    const still2 = path.join(GALLERY_DIR, '02-debias-basics.png');
    await page.screenshot({ path: still2 });
    console.log(`[Gallery] Saved 02-debias-basics.png`);
    await page.waitForTimeout(1200);

    // 00:09 - 00:14: Scenario 2 - Rebias Contextual (Male cues)
    console.log('[Scenario 2] Selecting Rebias contextual (male cues)...');
    await smoothClick(page, '[data-scenario="rebias-male"]');
    await page.waitForTimeout(1400);

    // Hover over diagnostic badge
    const diagBox = await page.locator('#diagnostics').boundingBox();
    if (diagBox) {
      await smoothMove(page, diagBox.x + diagBox.width / 2, diagBox.y + diagBox.height / 2, 14);
    }
    await page.waitForTimeout(800);

    // Capture Gallery Still 3: Rebias Contextual Male
    const still3 = path.join(GALLERY_DIR, '03-rebias-contextual-male.png');
    await page.screenshot({ path: still3 });
    console.log(`[Gallery] Saved 03-rebias-contextual-male.png`);
    await page.waitForTimeout(1000);

    // 00:14 - 00:19: Scenario 3 - Rebias Contextual (Female cues)
    console.log('[Scenario 3] Selecting Rebias contextual (female cues)...');
    await smoothClick(page, '[data-scenario="rebias-female"]');
    await page.waitForTimeout(1400);

    // Hover over output text
    const outBox = await page.locator('#output').boundingBox();
    if (outBox) {
      await smoothMove(page, outBox.x + 120, outBox.y + 40, 14);
    }
    await page.waitForTimeout(800);

    // Capture Gallery Still 4: Rebias Contextual Female
    const still4 = path.join(GALLERY_DIR, '04-rebias-contextual-female.png');
    await page.screenshot({ path: still4 });
    console.log(`[Gallery] Saved 04-rebias-contextual-female.png`);
    await page.waitForTimeout(1000);

    // 00:19 - 00:24: Scenario 4 - Round Trip
    console.log('[Scenario 4] Selecting Round Trip...');
    await smoothClick(page, '[data-scenario="round-trip"]');
    await page.waitForTimeout(1800);

    // Capture Gallery Still 5: Round Trip Validation
    const still5 = path.join(GALLERY_DIR, '05-roundtrip-validation.png');
    await page.screenshot({ path: still5 });
    console.log(`[Gallery] Saved 05-roundtrip-validation.png`);
    await page.waitForTimeout(1000);

    // 00:24 - 00:27: Operation word_frequencies
    console.log('[Utility] Switching operation to word_frequencies...');
    await smoothClick(page, '#operation');
    await page.selectOption('#operation', 'word_frequencies');
    await page.waitForTimeout(400);
    await smoothClick(page, '#run-button');
    await page.waitForTimeout(1400);

    // 00:27 - 00:30.5: Smooth scroll down to About & Metadata
    console.log('[About] Smooth scrolling to Metadata & Specifications...');
    await page.evaluate(() => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    });
    await page.waitForTimeout(1200);

    // Hover over meta dl
    const metaBox = await page.locator('.meta').boundingBox();
    if (metaBox) {
      await smoothMove(page, metaBox.x + metaBox.width / 2, metaBox.y + metaBox.height / 2, 16);
    }
    await page.waitForTimeout(600);

    // Capture Gallery Still 6: Token Frequencies & Metadata
    const still6 = path.join(GALLERY_DIR, '06-token-frequencies-metadata.png');
    await page.screenshot({ path: still6 });
    console.log(`[Gallery] Saved 06-token-frequencies-metadata.png`);

    // Complete exact 30.5s recording
    const elapsed = Date.now() - startTime;
    const remainingMs = Math.max(0, 30500 - elapsed);
    if (remainingMs > 0) {
      console.log(`[Hold] Holding final steady state for ${(remainingMs / 1000).toFixed(1)}s to reach 30.5s...`);
      await page.waitForTimeout(remainingMs);
    }
  } finally {
    const videoObj = page.video();
    await context.close();
    await browser.close();

    const rawVideoPath = await videoObj.path();
    console.log(`[Video] Raw recording saved at: ${rawVideoPath}`);

    const finalWebM = path.join(DEMOS_DIR, 'demo.webm');
    if (ffmpegBin) {
      console.log(`[FFmpeg] Transcoding video with VP9 to exact 30.5s duration...`);
      await new Promise((resolve, reject) => {
        const proc = spawn(ffmpegBin, [
          '-y',
          '-i', rawVideoPath,
          '-t', '30.5',
          '-c:v', 'libvpx-vp9',
          '-b:v', '750k',
          '-crf', '32',
          '-an',
          finalWebM,
        ], { stdio: 'inherit' });
        proc.on('close', (code) => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg exited with code ${code}`));
        });
      });
    } else {
      console.log(`[Video] Moving raw WebM to ${finalWebM}...`);
      fs.copyFileSync(rawVideoPath, finalWebM);
    }

    try {
      fs.rmSync(tempVideoDir, { recursive: true, force: true });
    } catch (_) {}

    // Generate WebP thumbnail from Still 2
    const helperBrowser = await chromium.launch({ headless: true });
    try {
      const sourceStill = path.join(GALLERY_DIR, '02-debias-basics.png');
      const cardThumbWebP = path.join(DEMOS_DIR, 'thumb.webp');
      await generateWebPThumbnail(helperBrowser, sourceStill, cardThumbWebP);

      // Copy thumbnail into netfix / beta-livive-net / livive-net
      const rootThumb = path.resolve(REPO_ROOT, '../thumbnails/nexttext.webp');
      const betaThumb = path.resolve(REPO_ROOT, '../beta-livive-net/thumbnails/nexttext.webp');
      const liviveThumb = path.resolve(REPO_ROOT, '../livive-net/thumbnails/nexttext.webp');

      for (const tPath of [rootThumb, betaThumb, liviveThumb]) {
        if (fs.existsSync(path.dirname(tPath))) {
          fs.copyFileSync(cardThumbWebP, tPath);
          console.log(`[Thumbnail] Copied to ${tPath}`);
        }
      }
    } finally {
      await helperBrowser.close();
    }

    console.log('[SUCCESS] All nexttext showcase assets captured!');
    console.log(`  - Video: ${finalWebM} (${fs.statSync(finalWebM).size} bytes)`);
    for (const f of fs.readdirSync(GALLERY_DIR).sort()) {
      const p = path.join(GALLERY_DIR, f);
      console.log(`  - Gallery: ${f} (${fs.statSync(p).size} bytes)`);
    }
  }
}

main().catch((err) => {
  console.error('[FATAL]', err);
  process.exit(1);
});
