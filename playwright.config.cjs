const {defineConfig,devices}=require('@playwright/test');
module.exports=defineConfig({
  testDir:'./e2e', testMatch:'**/*.spec.cjs', fullyParallel:true,
  retries:0, timeout:30000, reporter:'list',
  use:{baseURL:'http://127.0.0.1:8768/esstu-schedule/',trace:'retain-on-failure'},
  projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},
            {name:'mobile',use:{...devices['Pixel 7']}}],
  webServer:{command:'node e2e/serve.cjs',url:'http://127.0.0.1:8768/esstu-schedule/',reuseExistingServer:false}
});
