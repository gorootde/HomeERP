const fs = require('fs');
const path = require('path');

const vendorDir = path.join(__dirname, 'vendor');
fs.mkdirSync(vendorDir, { recursive: true });

const copies = [
  ['node_modules/html5-qrcode/html5-qrcode.min.js', 'vendor/html5-qrcode.min.js'],
  ['node_modules/lucide/dist/umd/lucide.min.js', 'vendor/lucide.min.js'],
];

for (const [src, dest] of copies) {
  const srcPath = path.join(__dirname, src);
  const destPath = path.join(__dirname, dest);
  fs.copyFileSync(srcPath, destPath);
  console.log(`Copied ${src} → ${dest}`);
}
console.log('Vendor files ready.');
