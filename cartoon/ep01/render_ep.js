// Usage: node render_ep.js <episode.html> <timeline.json> <audio.wav> <out.mp4> [workers]
// or:    node render_ep.js <episode.html> <timeline.json> --preview <out.png> t1,t2,...
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs'), os = require('os');
const { execFileSync } = require('child_process');
(async () => {
  const [html, tlPath, a3, a4, a5] = process.argv.slice(2);
  const TLd = JSON.parse(fs.readFileSync(tlPath, 'utf8'));
  const browser = await chromium.launch();
  const mk = async () => { const p = await browser.newPage({ viewport: { width: 720, height: 1280 } });
    await p.goto('file://' + path.resolve(html)); await p.evaluate(d => { TL = d; }, TLd); return p; };
  if (a3 === '--preview') {
    const p = await mk(); const ts = a5.split(',').map(Number); const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pv-'));
    for (let i = 0; i < ts.length; i++) { await p.evaluate(t => render(t), ts[i]); await p.screenshot({ path: path.join(dir, `p${String(i).padStart(3,'0')}.png`) }); }
    await browser.close();
    execFileSync('ffmpeg', ['-v','error','-y','-framerate','1','-i',path.join(dir,'p%03d.png'),'-vf',`scale=240:-1,tile=${Math.min(6,ts.length)}x${Math.ceil(ts.length/6)}`,'-frames:v','1',a4]);
    return;
  }
  const fps = TLd.fps, n = Math.ceil(TLd.duration * fps), W = +(a5 || 4);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ep-'));
  await Promise.all(Array.from({ length: W }, async (_, w) => {
    const p = await mk();
    for (let i = w; i < n; i += W) { await p.evaluate(t => render(t), i / fps);
      await p.screenshot({ path: path.join(dir, `f${String(i).padStart(5, '0')}.png`) }); }
  }));
  await browser.close();
  execFileSync('ffmpeg', ['-v','error','-y','-framerate',String(fps),'-i',path.join(dir,'f%05d.png'),'-i',a3,
    '-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-c:a','aac','-b:a','160k','-shortest',a4]);
  fs.rmSync(dir, { recursive: true }); console.log('done', a4, n, 'frames');
})();
