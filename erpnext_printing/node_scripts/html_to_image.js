const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
    const htmlContent = process.argv[2]; // 从命令行接收 HTML
    const outputPath = process.argv[3];  // 输出路径

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'] // 服务器环境需要
    });
    const page = await browser.newPage();
    
    // 设置页面内容
    await page.setContent(htmlContent, { waitUntil: 'networkidle0' });
    
    // 设置视口大小（可根据合同尺寸调整）
    await page.setViewport({ width: 794, height: 1123 });

    // 截图
    await page.screenshot({ path: outputPath, fullPage: true });

    await browser.close();
})();