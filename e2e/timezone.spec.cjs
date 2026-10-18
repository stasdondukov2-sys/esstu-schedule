const {test,expect}=require('./fixtures.cjs');
test.use({timezoneId:'America/New_York'});
for(const [instant,label,day]of[['2026-10-18T23:30:00+08:00','I неделя','18'],['2026-10-19T00:30:00+08:00','II неделя','19']]){
 test(`campus week at ${instant} on a New York device`,async({page})=>{
   await page.clock.setFixedTime(new Date(instant));await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
   await expect(page.locator('#weekBadge')).toHaveText(label);await expect(page.locator('#campusDate')).toContainText(day+' окт');
   await expect(page.locator('#campusDate')).toHaveAttribute('title',new RegExp(day+' октября'));
   expect(await page.evaluate(()=>[getUlanUdeNow().getHours(),getUlanUdeNow().getMinutes()])).toEqual(instant.includes('23:30')?[23,30]:[0,30]);
 });
}
