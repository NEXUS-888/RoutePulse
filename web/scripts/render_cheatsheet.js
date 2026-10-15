import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DIST_DIR = path.resolve(__dirname, '../dist');
const DOCS_DIR = path.resolve(__dirname, '../../docs');
const IMG_DIR = path.resolve(__dirname, '../../docs/img');

// Find CSS bundle
const files = fs.readdirSync(path.join(DIST_DIR, 'assets'));
const cssFile = files.find(f => f.startsWith('index-') && f.endsWith('.css'));

function startServer(port = 4174) {
  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.svg': 'image/svg+xml'
  };

  const server = http.createServer((req, res) => {
    let reqPath = req.url.split('?')[0];
    let filePath = path.join(DIST_DIR, reqPath);
    if (!fs.existsSync(filePath)) {
      res.writeHead(404);
      res.end('Not Found');
      return;
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
    fs.createReadStream(filePath).pipe(res);
  });

  return new Promise((resolve) => {
    server.listen(port, () => resolve(server));
  });
}

const htmlContent = `<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <title>RoutePulse Cheat Sheet</title>
  <link rel="stylesheet" href="http://localhost:4174/assets/${cssFile}">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: #121110;
      color: #F4EEE2;
      font-family: var(--font-body, system-ui, sans-serif);
      padding: 24px;
      width: 1440px;
      height: 900px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .header-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 20px;
      background: #1A1917;
      border: 1px solid #34312D;
      border-radius: 8px;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 32px;
      height: 32px;
      background: #F4EEE2;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 14px;
      color: #121110;
    }
    .title-text {
      font-family: var(--font-display, sans-serif);
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .tagline {
      font-size: 12px;
      color: #B8B1A4;
      font-family: var(--font-mono, monospace);
    }
    .banner-badges {
      display: flex;
      gap: 10px;
    }
    .badge {
      font-size: 11px;
      font-family: var(--font-mono, monospace);
      padding: 4px 8px;
      border-radius: 4px;
      font-weight: 600;
    }
    .badge-teal { background: rgba(61, 214, 140, 0.15); color: #3DD68C; border: 1px solid rgba(61, 214, 140, 0.4); }
    .badge-blue { background: rgba(244, 238, 226, 0.15); color: #F4EEE2; border: 1px solid rgba(244, 238, 226, 0.4); }

    .grid-container {
      display: grid;
      grid-template-columns: 1fr 1.25fr 1fr;
      gap: 16px;
      flex: 1;
    }
    .panel {
      background: #1A1917;
      border: 1px solid #34312D;
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .panel-title {
      font-family: var(--font-display, sans-serif);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #B8B1A4;
      border-bottom: 1px solid #34312D;
      padding-bottom: 6px;
    }
    .legend-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 12px;
    }
    .legend-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .line-indicator { width: 18px; height: 4px; border-radius: 2px; }

    .step-card {
      background: #121110;
      border: 1px solid #34312D;
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 11.5px;
      line-height: 1.35;
    }
    .step-header {
      font-weight: 700;
      color: #F4EEE2;
      font-family: var(--font-mono, monospace);
      margin-bottom: 3px;
      display: flex;
      justify-content: space-between;
    }
    .step-desc {
      color: #D9D2C4;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    th, td {
      padding: 5px 6px;
      text-align: left;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    th { color: #B8B1A4; font-family: var(--font-mono, monospace); font-size: 10px; }
    kbd {
      background: #121110;
      border: 1px solid #4A463F;
      padding: 1px 5px;
      border-radius: 3px;
      font-family: var(--font-mono, monospace);
      font-size: 10px;
      color: #F4EEE2;
    }

    .math-box {
      background: #121110;
      border: 1px solid #34312D;
      border-radius: 6px;
      padding: 8px;
      font-family: var(--font-mono, monospace);
      font-size: 10px;
      color: #F4EEE2;
      line-height: 1.4;
    }
  </style>
</head>
<body>
  <div class="header-banner">
    <div class="title-row">
      <div class="brand-icon">RP</div>
      <div>
        <div class="title-text">RoutePulse — Quick Reference Cheat Sheet</div>
        <div class="tagline">"Plan the campus. Don't just watch it." · Single Source of Truth</div>
      </div>
    </div>
    <div class="banner-badges">
      <span class="badge badge-teal">0 Hard Violations</span>
      <span class="badge badge-blue">100% Offline Bundled</span>
    </div>
  </div>

  <div class="grid-container">
    <!-- Column 1: Legend -->
    <div class="panel">
      <div class="panel-title">1. Transit Visual Legend</div>

      <div style="font-size: 11px; font-weight: 700; color: #B8B1A4; margin-top: 2px;">PASSENGER LOAD SEMANTICS</div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="dot" style="background: #3DD68C; box-shadow: 0 0 6px rgba(61, 214, 140, 0.5);"></span>
          <strong>&lt; 85% Load</strong>
        </div>
        <span style="color: #3DD68C;">Seats Available (Green)</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="dot" style="background: #FFB02E; box-shadow: 0 0 6px rgba(255, 176, 46, 0.5);"></span>
          <strong>85%–100% Load</strong>
        </div>
        <span style="color: #FFB02E;">Standing Room (Amber)</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="dot" style="background: #FF5F52; box-shadow: 0 0 6px rgba(255, 95, 82, 0.5);"></span>
          <strong>&gt; 100% Load</strong>
        </div>
        <span style="color: #FF5F52;">Overcrowded (Red)</span>
      </div>

      <div style="font-size: 11px; font-weight: 700; color: #B8B1A4; margin-top: 6px;">ROUTES &amp; CORRIDORS</div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="line-indicator" style="background: #4DB8FF;"></span>
          <strong>Route R1</strong>
        </div>
        <span style="color: #B8B1A4;">Main Loop (Gate ↔ Hub)</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="line-indicator" style="background: #7C8CFF;"></span>
          <strong>Route R2</strong>
        </div>
        <span style="color: #B8B1A4;">Hostel Express Loop</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="line-indicator" style="background: #C77BFF;"></span>
          <strong>Route R3</strong>
        </div>
        <span style="color: #B8B1A4;">Metro Gateway Connector</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span class="line-indicator" style="background: #FF70C4;"></span>
          <strong>Route R4</strong>
        </div>
        <span style="color: #B8B1A4;">Research &amp; Sports Loop</span>
      </div>

      <div style="font-size: 11px; font-weight: 700; color: #B8B1A4; margin-top: 6px;">KEY TRANSIT NODES</div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span style="font-family: var(--font-mono, monospace); font-weight: 700; color: #F4EEE2;">◎ S03</span>
          <strong>Central Hub</strong>
        </div>
        <span style="color: #D9D2C4;">4m Walk Transfer Ring</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span style="font-family: var(--font-mono, monospace); font-weight: 700; color: #F4EEE2;">■ S13</span>
          <strong>Metro Gateway</strong>
        </div>
        <span style="color: #D9D2C4;">Regional Rail Entry</span>
      </div>
      <div class="legend-row">
        <div class="legend-indicator">
          <span style="font-family: var(--font-mono, monospace); font-weight: 700; color: #FF5F52;">◌ S2</span>
          <strong>Breakdown Bus</strong>
        </div>
        <span style="color: #FF5F52;">Ghost Marker (B3)</span>
      </div>
    </div>

    <!-- Column 2: 5-Step Workflows -->
    <div class="panel">
      <div class="panel-title">2. Operational Workflows (5 Steps)</div>

      <div style="font-size: 11px; font-weight: 700; color: #F4EEE2;">OPERATOR WORKFLOW (FIX OVERCROWDING)</div>
      <div class="step-card">
        <div class="step-header"><span>STEP 1: MONITOR HEALTH</span><span>08:00</span></div>
        <div class="step-desc">Check the top bar: Network health score (target &gt;80, green).</div>
      </div>
      <div class="step-card">
        <div class="step-header"><span>STEP 2: SPOT BOTTLENECK</span><span>08:15</span></div>
        <div class="step-desc">Watch Route R3 turn red at Metro Gateway S13 under morning surge.</div>
      </div>
      <div class="step-card">
        <div class="step-header"><span>STEP 3: REVIEW TICKET</span><span>08:18</span></div>
        <div class="step-desc">Open Suggestions. Inspect Rec-0007: delta wait time and riders rescued.</div>
      </div>
      <div class="step-card">
        <div class="step-header"><span>STEP 4: ACCEPT &amp; APPLY</span><span>08:19</span></div>
        <div class="step-desc">Verify 0 rule violations (H1–H12 checkmarks). Click "Accept &amp; Apply Live".</div>
      </div>
      <div class="step-card">
        <div class="step-header"><span>STEP 5: REVEAL GAIN</span><span>08:30</span></div>
        <div class="step-desc">Open What-if. Drag Before/After slider to confirm ~71% left-behind drop.</div>
      </div>

      <div style="font-size: 11px; font-weight: 700; color: #3DD68C; margin-top: 4px;">STUDENT WORKFLOW (CATCH A BUS)</div>
      <div class="step-card">
        <div class="step-desc">
          <strong>1. Open Student app:</strong> Click Student app in left rail.<br>
          <strong>2. Pick Route:</strong> Select Metro S13 to Science S05.<br>
          <strong>3. Read ETA Window:</strong> Trust p10–p90 band (e.g. 08:27–08:33) over single minutes.<br>
          <strong>4. Avoid Crowds:</strong> If 88% full, take comfortable alternative 8 min later.<br>
          <strong>5. Wheelchair Filter:</strong> Toggle ramp switch for accessible buses only.
        </div>
      </div>
    </div>

    <!-- Column 3: Shortcuts & Core Math -->
    <div class="panel">
      <div class="panel-title">3. Shortcuts &amp; Core Math</div>

      <table>
        <thead>
          <tr>
            <th>SHORTCUT</th>
            <th>ACTION</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><kbd>?</kbd> or <kbd>H</kbd></td>
            <td>Open / Close Help Centre</td>
          </tr>
          <tr>
            <td><kbd>Esc</kbd></td>
            <td>Close open modal or drawer</td>
          </tr>
          <tr>
            <td><kbd>Ctrl+K</kbd> / <kbd>/</kbd></td>
            <td>Command Palette (Instant jump)</td>
          </tr>
          <tr>
            <td><kbd>Space</kbd></td>
            <td>Play / Pause Simulation Clock</td>
          </tr>
          <tr>
            <td><kbd>1</kbd> – <kbd>6</kbd></td>
            <td>Direct switch to Screens 1–6</td>
          </tr>
          <tr>
            <td><kbd>T</kbd></td>
            <td>Toggle Dark / Light Theme</td>
          </tr>
          <tr>
            <td><kbd>M</kbd></td>
            <td>Toggle Metro / Geographic Map</td>
          </tr>
        </tbody>
      </table>

      <div style="font-size: 11px; font-weight: 700; color: #B8B1A4; margin-top: 6px;">NETWORK HEALTH FORMULA</div>
      <div class="math-box">
        Health = max(0, 100 - 40*overcap - 30*leftbehind - 20*missedconn - 10*delays)<br>
        • 80–100: Green (Optimal)<br>
        • 60–79:  Amber (Strained)<br>
        • &lt; 60:   Red (Critical)
      </div>

      <div style="font-size: 11px; font-weight: 700; color: #B8B1A4; margin-top: 6px;">CONSTRAINTS &amp; GUARANTEES</div>
      <div style="font-size: 11px; color: #D9D2C4; line-height: 1.4;">
        • <strong>H1–H12 Rules:</strong> Strictly 0 violations (capacity, breaks, battery, 4m walk).<br>
        • <strong>Offline Guarantee:</strong> 100% self-hosted, 0 external network requests.<br>
        • <strong>Conformal ETAs:</strong> 80% coverage on p10–p90 arrival windows.
      </div>
    </div>
  </div>
</body>
</html>`;

async function capture() {
  console.log('Starting static server for cheatsheet...');
  const server = await startServer(4174);

  const browser = await chromium.launch({ headless: true, channel: process.env.PW_CHANNEL || undefined });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  console.log('Rendering cheatsheet template...');
  await page.setContent(htmlContent);
  await page.waitForTimeout(1000);

  const pngPathDocs = path.join(DOCS_DIR, 'CHEATSHEET.png');
  const pngPathImg = path.join(IMG_DIR, 'cheatsheet.png');

  console.log('Saving screenshots to:', pngPathDocs, 'and', pngPathImg);
  await page.screenshot({ path: pngPathDocs });
  await page.screenshot({ path: pngPathImg });

  await browser.close();
  server.close();
  console.log('✓ Successfully rendered and saved CHEATSHEET.png!');
}

capture().catch(err => {
  console.error('Error generating cheatsheet:', err);
  process.exit(1);
});
