const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + process.cwd() + '/index.html');
  await p.evaluate(() => document.fonts.ready);
  await p.waitForFunction(() => [...document.images].every(i => i.complete));
  for (const t of process.argv.slice(2).map(Number)) {
    await p.evaluate(t => window.render(t), t);
    await p.screenshot({ path: `pv_${String(t).replace('.', '_')}.jpg`, type: 'jpeg', quality: 82 });
  }
  await b.close();
})();
