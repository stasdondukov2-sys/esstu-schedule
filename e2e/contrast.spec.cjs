const {test,expect}=require('./fixtures.cjs');
const {PNG}=require('playwright-core/lib/utilsBundle');
const luminance=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
const contrast=(a,b)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
test('small labels meet 4.5 contrast against rendered gradients in both themes',async({page},testInfo)=>{
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');const results=[];
 for(const theme of ['dark','light']){
  await page.evaluate(theme=>{themeMode=theme;applyTheme();},theme);
  for(const selector of ['.calendar-count','.pair-time>div:nth-child(3)','.lesson-warning .lesson-kind','#compactFreshnessText','.hero-lesson-meta']){
   const node=page.locator(selector).first();const style=await node.evaluate(node=>{const css=getComputedStyle(node);return {color:css.color,fontSize:css.fontSize,inline:node.getAttribute('style')};});
   const rgb=style.color.match(/[\d.]+/g).slice(0,3).map(Number);await node.evaluate(node=>node.style.setProperty('color','transparent','important'));
   let minimum=Infinity;
   try{const bitmap=PNG.sync.read(await node.screenshot({animations:'disabled'}));for(let i=0;i<bitmap.data.length;i+=4)if(bitmap.data[i+3]===255)minimum=Math.min(minimum,contrast(rgb,[...bitmap.data.subarray(i,i+3)]));}
   finally{await node.evaluate((node,inline)=>{if(inline===null)node.removeAttribute('style');else node.setAttribute('style',inline);},style.inline);}
   results.push({theme,selector,minContrast:minimum,fontSize:style.fontSize});expect(minimum,theme+' '+selector).toBeGreaterThanOrEqual(4.5);expect(parseFloat(style.fontSize)).toBeGreaterThanOrEqual(12);
  }
 }
 await testInfo.attach('rendered-contrast',{body:JSON.stringify(results,null,2),contentType:'application/json'});
});
