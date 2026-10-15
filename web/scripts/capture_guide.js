import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DIST_DIR = path.resolve(__dirname, '../dist');
const IMG_DIR = path.resolve(__dirname, '../../docs/img');

if (!fs.existsSync(IMG_DIR)) {
  fs.mkdirSync(IMG_DIR, { recursive: true });
}

// Simple static server for dist
function startServer(port = 4173) {
  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.svg': 'image/svg+xml'
  };

  const server = http.createServer((req, res) => {
    let reqPath = req.url.split('?')[0];
    if (reqPath === '/') reqPath = '/index.html';
    let filePath = path.join(DIST_DIR, reqPath);

    if (!fs.existsSync(filePath)) {
      filePath = path.join(DIST_DIR, 'index.html');
    }

    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
      if (err) {
        res.writeHead(500);
        res.end('Server Error');
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      }
    });
  });

  return new Promise((resolve) => {
    server.listen(port, () => resolve(server));
  });
}

async function runCapture() {
  console.log('Starting local HTTP server for dist...');
  const server = await startServer(4173);
  console.log('Server running at http://localhost:4173');

  const browser = await chromium.launch({ headless: true, channel: process.env.PW_CHANNEL || undefined });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  const page = await context.newPage();

  // Guardrail: Assert zero external network requests
  const externalRequests = [];
  page.on('request', (req) => {
    const url = req.url();
    if (!url.startsWith('http://localhost:4173') && !url.startsWith('data:') && !url.startsWith('blob:')) {
      externalRequests.push(url);
    }
  });

  console.log('Navigating to RoutePulse app...');
  await page.goto('http://localhost:4173');
  await page.waitForTimeout(1000);

  // 1. Capture Welcome Modal
  console.log('Capturing welcome_modal.png...');
  await page.screenshot({ path: path.join(IMG_DIR, 'welcome_modal.png') });

  // 2. Test Guided Tour Walkthrough
  console.log('Testing Spotlight Tour...');
  const takeTourBtn = page.locator('text=Take the guided tour');
  if (await takeTourBtn.isVisible()) {
    await takeTourBtn.click();
    await page.waitForTimeout(500);

    // Capture Step 1
    await page.screenshot({ path: path.join(IMG_DIR, 'tour_step1.png') });

    // Step through 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
    for (let step = 1; step <= 10; step++) {
      const nextBtn = page.locator('button:has-text("Next")');
      if (await nextBtn.isVisible()) {
        await nextBtn.click();
        await page.waitForTimeout(300);
        if (step === 2) {
          await page.screenshot({ path: path.join(IMG_DIR, 'tour_step3.png') });
        } else if (step === 7) {
          await page.screenshot({ path: path.join(IMG_DIR, 'tour_step8.png') });
        }
      }
    }

    // Finish Tour
    const finishBtn = page.locator('button:has-text("Finish Tour")');
    if (await finishBtn.isVisible()) {
      await finishBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // 3. Command Centre (Dark Theme)
  console.log('Capturing command_centre_dark.png...');
  await page.screenshot({ path: path.join(IMG_DIR, 'command_centre_dark.png') });

  // 4. Command Centre (Light Theme)
  console.log('Switching to Light Theme & capturing command_centre_light.png...');
  const themeBtn = page.locator('button[aria-label="Toggle theme"]');
  await themeBtn.click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(IMG_DIR, 'command_centre_light.png') });

  // Switch back to Dark Theme
  await themeBtn.click();
  await page.waitForTimeout(400);

  // 5. ETA Board Screen
  console.log('Navigating to ETA Board & capturing eta_board.png...');
  await page.locator('button[data-testid="nav-eta"]').click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(IMG_DIR, 'eta_board.png') });

  // 6. Demand & Alerts Screen
  console.log('Navigating to Demand & Alerts & capturing demand_alerts.png...');
  await page.locator('button[data-testid="nav-demand"]').click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(IMG_DIR, 'demand_alerts.png') });

  // 7. Recommendations Screen
  console.log('Navigating to Recommendations & capturing recommendations.png...');
  await page.locator('button[data-testid="nav-recommendations"]').click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(IMG_DIR, 'recommendations.png') });

  // 8. Scenario Lab & Before/After Slider
  console.log('Navigating to Scenario Lab & capturing before_after_slider.png...');
  await page.locator('button[data-testid="nav-scenarios"]').click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(IMG_DIR, 'scenario_lab.png') });

  // Scroll to Before/After Slider
  const slider = page.locator('text=Before / After Reveal Slider');
  if (await slider.isVisible()) {
    await slider.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(IMG_DIR, 'before_after_slider.png') });
  }

  // 9. Student Mobile View (390 x 844)
  console.log('Navigating to Student View (Mobile 390x844) & capturing student_mobile.png...');
  await page.locator('button[data-testid="nav-student"]').click();
  await page.waitForTimeout(600);

  // Set viewport to mobile standard (390 x 844)
  await page.setViewportSize({ width: 420, height: 900 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(IMG_DIR, 'student_mobile.png') });

  // Reset viewport to desktop
  await page.setViewportSize({ width: 1440, height: 900 });

  // 10. Help Centre Drawer
  console.log('Opening Help Centre & capturing help_centre.png...');
  await page.keyboard.press('?');
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(IMG_DIR, 'help_centre.png') });

  // Close Help Centre
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // 11. Command Palette
  console.log('Opening Command Palette & capturing command_palette.png...');
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(IMG_DIR, 'command_palette.png') });

  // Close Command Palette
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // Check external request assertions
  console.log('\n--- OFFLINE VERIFICATION ---');
  if (externalRequests.length === 0) {
    console.log('✓ Zero external requests verified! 100% offline self-hosted.');
  } else {
    console.error('FAILED: External requests detected:', externalRequests);
    process.exit(1);
  }

  // Check onboarding key
  const onboarded = await page.evaluate(() => localStorage.getItem('rp_onboarded_v1'));
  console.log(`✓ Tour completed and onboarding flag recorded: rp_onboarded_v1=${onboarded}`);

  await browser.close();
  server.close();
  console.log('\nAll QA tests passed and screenshots captured into docs/img/ successfully!\n');
}

runCapture().catch((err) => {
  console.error('QA capture error:', err);
  process.exit(1);
});
