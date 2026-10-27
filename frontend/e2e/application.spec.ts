import {test,expect} from '@playwright/test';

test('landing page is responsive and links to working scanners',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await expect(page.getByRole('heading',{name:'A second look. A safer next step.'})).toBeVisible();
  await expect(page.getByText('Engine online')).toBeAttached();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/home-${info.project.name}.png`,fullPage:true});
  if(info.project.name==='mobile'){
    await page.getByRole('button',{name:'Open navigation'}).click();
    await expect(page.getByRole('complementary',{name:'Main navigation'})).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button',{name:'Open navigation'})).toBeFocused();
  }
  await page.getByRole('link',{name:'Scan a message',exact:true}).click();
  await expect(page.getByLabel('Your message')).toBeVisible();expect(errors).toEqual([]);
});

test('message scan computes risk and explains it',async({page},info)=>{
  await page.goto('/scan');await page.getByRole('button',{name:'Try a fictional example'}).click();await page.getByRole('button',{name:'Analyze now'}).click();
  await expect(page.getByRole('heading',{name:'High risk',exact:true})).toBeVisible();
  await expect(page.getByText('Upfront payment request',{exact:true})).toBeVisible();
  await expect(page.getByText('Heuristic · not a probability')).toBeVisible();
  await page.screenshot({path:`test-results/result-${info.project.name}.png`,fullPage:true});
});

test('URL scan is lexical and rejects unsupported schemes',async({page})=>{
  await page.goto('/url-checker');await page.getByLabel('Website address').fill('http://127.0.0.1/login');await page.getByRole('button',{name:'Analyze now'}).click();
  await expect(page.getByRole('heading',{name:'High risk',exact:true})).toBeVisible();await expect(page.getByText('Private or local destination',{exact:true})).toBeVisible();
  await page.getByLabel('Website address').fill('file:///etc/passwd');await page.getByRole('button',{name:'Analyze now'}).click();
  await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByRole('heading',{name:'High risk',exact:true})).not.toBeVisible();
});

test('Malay interface and dark theme are usable',async({page},info)=>{
  await page.goto('/scan');await page.getByRole('button',{name:'Switch to Bahasa Melayu'}).click();await expect(page.getByLabel('Mesej anda')).toBeVisible();
  await page.getByRole('button',{name:'Cuba contoh rekaan'}).click();await page.getByRole('button',{name:'Analisis sekarang'}).click();await expect(page.getByRole('heading',{name:'Risiko tinggi',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Tukar mod gelap'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.screenshot({path:`test-results/malay-dark-${info.project.name}.png`,fullPage:true});
});

test('lesson supports pre-assessment, content and post-assessment',async({page})=>{
  await page.goto('/learn?module=phishing');await page.getByLabel('Contact the bank through its official number').check();await page.getByRole('button',{name:'Check answer'}).click();await expect(page.getByText('You spotted it.')).toBeVisible();
  await page.getByRole('button',{name:'Read the lesson'}).click();await expect(page.getByText(/HTTPS encrypts transport/)).toBeVisible();await page.getByRole('button',{name:'Check my understanding'}).click();
  await page.getByLabel('Contact the bank through its official number').check();await page.getByRole('button',{name:'Check answer'}).click();await page.getByRole('button',{name:'See my progress'}).click();await expect(page.getByRole('heading',{name:'One more pattern you can recognize.'})).toBeVisible();
});

test('account history is optional and deletable',async({page})=>{
  const email=`browser-${Date.now()}@example.test`;
  await page.goto('/login');await page.getByRole('button',{name:'Create an account',exact:true}).click();await page.getByLabel('Email address').fill(email);await page.getByLabel('Account password').fill('browser-test-password-2026');await page.getByRole('button',{name:'Create account',exact:true}).click();await expect(page.getByRole('heading',{name:'Your saved second looks.'})).toBeVisible();
  await page.goto('/scan');await page.getByLabel('Your message').fill('Hello, our project meeting is at 10 today.');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Analyze now'}).click();await expect(page.getByRole('heading',{name:'Low risk',exact:true})).toBeVisible();
  await page.goto('/history');await expect(page.getByRole('button').filter({hasText:'Hello, our project meeting'})).toBeVisible();page.on('dialog',d=>d.accept());await page.getByRole('button',{name:'Delete history',exact:true}).click();await expect(page.getByRole('heading',{name:'Nothing saved. Everything private.'})).toBeVisible();
  await page.getByRole('button',{name:'Delete account and private records',exact:true}).click();await expect(page.getByRole('heading',{name:'Your account, your records.'})).toBeVisible();
});

test('resources and bot readiness reflect actual backend configuration',async({page})=>{
  await page.goto('/resources');await expect(page.getByRole('heading',{name:'PDRM Semak Mule'})).toBeVisible();await expect(page.getByRole('link',{name:'Visit official website'})).toHaveCount(5);
  await page.goto('/telegram');await expect(page.getByRole('heading',{name:'ScamShield AI Bot'})).toBeVisible();await expect(page.getByText('Bot credentials are not configured on this installation.')).toBeVisible();
  await page.goto('/dashboard');await expect(page.getByText('Live installation data')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
