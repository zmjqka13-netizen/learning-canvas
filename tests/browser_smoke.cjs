#!/usr/bin/env node
/* Optional dev-only real-browser checks; no downloads or installation. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

(async () => {
  const file = process.argv[2];
  if (!file) throw new Error('Usage: node tests/browser_smoke.cjs report.html --out <output directory>');
  const flag = process.argv.indexOf('--out');
  const out = path.resolve(flag >= 0 ? process.argv[flag+1] : 'browser-check');
  fs.mkdirSync(out, {recursive:true});
  const browser = await chromium.launch({headless:true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE} : {})});
  const results=[]; const errors=[]; const requests=[];
  const check = (name, condition) => {assert.ok(condition,name); results.push({name,passed:true});};
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
    const page = await context.newPage(); page.on('pageerror',e=>errors.push(e.message)); page.on('request',r=>requests.push(r.url()));
    const url=pathToFileURL(path.resolve(file)).href;
    await page.goto(url);
    check('learner response starts blank', await page.locator('#own-words').inputValue()==='');
    check('answer starts concealed', !await page.locator('.reveal').first().evaluate(el=>el.open));
    await page.locator('.reveal summary').first().click();
    check('native answer reveal works',await page.locator('.reveal').first().evaluate(el=>el.open));
    await page.locator('[data-done]').first().check();
    check('self-evaluation updates progress',await page.locator('#read-progress').evaluate(el=>el.value)===1);
    await page.locator('#own-words').fill('这是测试者自己填写的复述；不由程序代写。');
    await page.locator('#probe-L1').fill('遗漏了能力边界。');
    await page.locator('[data-gap]').last().check();
    await page.reload();
    check('response restored from local storage',(await page.locator('#own-words').inputValue()).includes('测试者自己填写'));
    check('probe restored from local storage',await page.locator('#probe-L1').inputValue()==='遗漏了能力边界。');
    check('progress restored from local storage',await page.locator('[data-done]').first().isChecked());
    check('gap restored from local storage',await page.locator('[data-gap]').last().isChecked());
    await page.locator('#collapse-frames').click();
    check('recall action hides all frames',await page.locator('.frame details[open]').count()===0);
    check('recall action focuses learner field',await page.locator('#own-words').evaluate(el=>el===document.activeElement));
    await page.locator('#expand-frames').click();
    check('walk-through action expands all frames',await page.locator('.frame details[open]').count()===await page.locator('.frame').count());
    await page.locator('.body-copy a').first().click();
    check('source badge navigates to correct anchor',new URL(page.url()).hash==='#S1');
    const downloading=page.waitForEvent('download'); await page.locator('#export-record').click();
    const download=await downloading; const exported=path.join(out,'practice-export.json'); await download.saveAs(exported);
    const record=JSON.parse(fs.readFileSync(exported,'utf8'));
    check('export contains learner-authored record',record.values['own-words'].includes('测试者自己填写'));
    await page.goto(url); await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    check('mobile layout has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1100});
    await page.pdf({path:path.join(out,'print-preview.pdf'),format:'A4',printBackground:true});
    check('print artifact created',fs.readFileSync(path.join(out,'print-preview.pdf')).subarray(0,5).toString()==='%PDF-');
    const blocked=await browser.newContext();
    await blocked.addInitScript(()=>{Storage.prototype.setItem=function(){throw new Error('storage disabled by test');};});
    const blockedPage=await blocked.newPage(); await blockedPage.goto(url);
    check('storage failure is explained', (await blockedPage.locator('#save-status').innerText()).includes('不允许本地保存'));
    await blockedPage.locator('#own-words').fill('存储不可用时仍然可以练习');
    check('storage failure keeps learner field usable',await blockedPage.locator('#own-words').inputValue()==='存储不可用时仍然可以练习');
    const nojs=await browser.newContext({javaScriptEnabled:false}); const plain=await nojs.newPage(); await plain.goto(url);
    await plain.locator('.reveal summary').first().click();
    check('no-JS native answer reveal works',await plain.locator('.reveal > div').first().isVisible());
    check('no external network requests',requests.every(u=>u.startsWith('file:')||u.startsWith('blob:')));
    check('no JavaScript runtime errors',errors.length===0);
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,checks:results.length,results,errors,requests},null,2));
    console.log(JSON.stringify({passed:true,checks:results.length,output:out},null,2));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
