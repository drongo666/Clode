// Usage: node render.js <scene.html> <out.mp4> [seconds] [fps]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execFileSync } = require('child_process');

(async () => {
  const [scene, out, secs = '4', fps = '24'] = process.argv.slice(2);
  const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'frames-'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 720, height: 1280 } });
  await page.goto('file://' + path.resolve(scene));
  const n = Math.round(+secs * +fps);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => render(t), i / +fps);
    await page.screenshot({ path: path.join(dir, `f${String(i).padStart(5, '0')}.png`) });
  }
  await browser.close();
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', fps, '-i', path.join(dir, 'f%05d.png'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out]);
  fs.rmSync(dir, { recursive: true });
  console.log('done', out, n, 'frames');
})();
