const fs = require('fs');
const path = require('path');
const studioJs = fs.readFileSync(path.join(__dirname, '../static/js/studio.js'), 'utf8');

const idxFetch = studioJs.indexOf('async function fetchPaperMetadataClient(rawId)');
const idxDecode = studioJs.indexOf('async function runDecodePaper(payload)');
const idxPdf = studioJs.indexOf('matrixPdfInput.addEventListener("change"');

console.log('=== VERIFYING DECODER TIMEOUTS ACROSS ALL 3 WORKFLOWS ===');

// 1. fetchPaperMetadataClient
const fetchChunk = studioJs.slice(idxFetch, idxFetch + 1200);
const hasFetchAbort = fetchChunk.includes('new AbortController()');
const hasFetch30s = fetchChunk.includes('30000');
const hasFetchClear = fetchChunk.includes('clearTimeout(timeoutId)');
console.log('1. fetchPaperMetadataClient: AbortController=' + hasFetchAbort + ', 30s=' + hasFetch30s + ', cleanup=' + hasFetchClear);

// 2. runDecodePaper (text/JSON)
const decodeChunk = studioJs.slice(idxDecode, idxDecode + 1600);
const hasDecodeAbort = decodeChunk.includes('new AbortController()');
const hasDecode30s = decodeChunk.includes('30000');
const hasDecodeClear = decodeChunk.includes('clearTimeout(timeoutId)');
const hasDecodeSignal = decodeChunk.includes('signal: controller ? controller.signal : undefined');
console.log('2. runDecodePaper: AbortController=' + hasDecodeAbort + ', 30s=' + hasDecode30s + ', cleanup=' + hasDecodeClear + ', signal=' + hasDecodeSignal);

// 3. PDF upload decoder
const pdfChunk = studioJs.slice(idxPdf, idxPdf + 1600);
const hasPdfAbort = pdfChunk.includes('new AbortController()');
const hasPdf30s = pdfChunk.includes('30000');
const hasPdfClear = pdfChunk.includes('clearTimeout(timeoutId)');
const hasPdfSignal = pdfChunk.includes('signal: controller.signal');
console.log('3. PDF upload decoder: AbortController=' + hasPdfAbort + ', 30s=' + hasPdf30s + ', cleanup=' + hasPdfClear + ', signal=' + hasPdfSignal);

const allOk = hasFetchAbort && hasFetch30s && hasFetchClear &&
              hasDecodeAbort && hasDecode30s && hasDecodeClear && hasDecodeSignal &&
              hasPdfAbort && hasPdf30s && hasPdfClear && hasPdfSignal;
console.log('\nAll 3 decoder timeout workflows verified:', allOk ? 'PASS' : 'FAIL');
process.exit(allOk ? 0 : 1);
