const base=require('@playwright/test');
const test=base.test.extend({
  page:async({page},use)=>{
    // Browser scenarios describe the committed snapshot, independent of cron/date.
    await page.clock.install({time:new Date('2026-10-16T09:30:00+08:00')});
    await use(page);
  }
});
module.exports={test,expect:base.expect};
