
const FAPI='https://fapi.binance.com';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const logBox=document.getElementById('logBox');
const sysMsg=document.getElementById('sysMsg');
const progFill=document.getElementById('progFill');
const warnBox=document.getElementById('warnBox');

function log(msg){
  logBox.innerHTML+=`<div>${msg}</div>`;
  logBox.scrollTop=logBox.scrollHeight;
  sysMsg.textContent=msg;
}

async function fetchAPI(url){
  for(let i=0;i<3;i++){
    const r=await fetch(url);
    if(r.ok) return await r.json();
    if(r.status===429 || r.status===418) { 
        log(`⚠ 바이낸스 API 제한(${r.status}). ${i+1}초 대기 중...`); 
        await sleep(1000*(i+1)); 
        continue; 
    }
    throw new Error(`HTTP ${r.status}`);
  }
  throw new Error("HTTP 429/418 - 요청 한도 초과");
}

async function getTopSymbols(n){
  const a=await fetchAPI(`${FAPI}/fapi/v1/ticker/24hr`);
  return a.filter(t=>t.symbol.endsWith('USDT')&&+t.quoteVolume>5e6)
          .sort((x,y)=>+y.quoteVolume-+x.quoteVolume).slice(0,n).map(t=>t.symbol);
}

async function getKlines(sym,limit){
  const a=await fetchAPI(`${FAPI}/fapi/v1/klines?symbol=${sym}&interval=1h&limit=${limit}`);
  return a.map(k=>({t:k[0], o:+k[1], h:+k[2], l:+k[3], c:+k[4], v:+k[5], tbv:+k[9]}));
}

async function getFundingRates(){
  try{
    const res=await fetchAPI(`${FAPI}/fapi/v1/premiumIndex`);
    const frMap={}; res.forEach(r=>{ frMap[r.symbol] = +r.lastFundingRate; });
    return frMap;
  }catch(e){ return {}; }
}

async function getOIChangeMap(syms) {
  const map = {};
  log(`[백그라운드 수집] 멀티-호라이즌 OI(15m→1h·4h) 수집 중...`);
  let done = 0;
  for(const sym of syms) {
    try {
      const res = await fetch(`${FAPI}/futures/data/openInterestHist?symbol=${sym}&period=15m&limit=24`);
      if(res.ok) {
        const data = await res.json();
        if(data && data.length >= 5) {
          const val = data.map(d => +d.sumOpenInterestValue);
          const cur = val[val.length-1];
          const p1 = val[Math.max(0, val.length-1-4)];    // 약 1시간 전
          const p4 = val[Math.max(0, val.length-1-16)];   // 약 4시간 전
          map[sym] = { short: p1 ? (cur-p1)/p1 : 0, mid: p4 ? (cur-p4)/p4 : 0 };
        }
      }
    } catch(e) {} 
    done++;
    if(done % 30 === 0) log(` - OI 수집 진행률: ${done}/${syms.length}`);
    await sleep(60); 
  }
  return map;
}

function mean(a){let s=0;for(const x of a)s+=x;return a.length?s/a.length:0;}
function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
function ema(arr,p){let k=2/(p+1),e=arr[0];for(let z=1;z<arr.length;z++)e=arr[z]*k+e*(1-k);return e;}
function atr(arr,p=14){let s=0,n=0;for(let z=arr.length-p;z<arr.length;z++){if(z<1)continue;const tr=Math.max(arr[z].h-arr[z].l,Math.abs(arr[z].h-arr[z-1].c),Math.abs(arr[z].l-arr[z-1].c));s+=tr;n++;}return n?s/n:0;}

function btcRegime(btcClose,i){
  const def={f:1.0, bTrend:0, b24:0, label:'데이터 부족', color:'var(--tx2)'};
  if(!btcClose||i<48) return def;
  const sl=btcClose.slice(i-48,i+1);
  if(sl.length<30) return def;
  const ef=ema(sl.slice(-12),12), es=ema(sl.slice(-48),48);
  const bTrend=ef/es-1;
  const c=btcClose[i], p=btcClose[i-24];
  const b24=(c&&p)?(c-p)/p:0;
  
  const r=clamp(bTrend/0.012*0.6 + b24/0.05*0.4, -1, 1);
  const f=clamp(0.45+0.55*((r+1)/2), 0.45, 1.0);
  
  let label, color;
  if(f >= 0.90) { label = '강세 (상승장)'; color = 'var(--bull)'; }
  else if(f >= 0.72) { label = '중립 (탐색장)'; color = 'var(--cyan)'; }
  else if(f >= 0.58) { label = '약세 (조정장)'; color = 'var(--gold)'; }
  else { label = '위험 (폭락장)'; color = 'var(--bear)'; }
  
  return {f, bTrend, b24, label, color};
}

function renderBtcStatus(br) {
  const wrap = document.getElementById('btcBannerWrap');
  if(!br || !br.label) return;
  wrap.innerHTML = `
    <div class="card" style="border-color:${br.color}; border-width:2px; margin-bottom:0;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
          <span class="small" style="color:var(--tx3)">현재 비트코인 시장 상태 (점수 페널티: ×${br.f.toFixed(2)})</span><br>
          <span style="font-size:22px; font-weight:800; color:${br.color};">● ${br.label}</span>
        </div>
        <div class="mono" style="text-align:right;">
          <span class="small" style="color:var(--tx3)">최근 24시간:</span> 
          <b style="color:${br.b24 >= 0 ? 'var(--bull)' : 'var(--bear)'}">${(br.b24*100).toFixed(2)}%</b><br>
          <span class="small" style="color:var(--tx3)">단기 추세강도:</span> 
          <b style="color:${br.bTrend >= 0 ? 'var(--bull)' : 'var(--bear)'}">${(br.bTrend*100).toFixed(2)}%</b>
        </div>
      </div>
    </div>
  `;
}

function calcFeatures(cs, i, btcClose, weights, currentFunding = 0, oiShort = 0, oiMid = 0){
  const need=130; if(i<need) return null;
  const C=cs.slice(i-need+1,i+1);
  const closes=C.map(x=>x.c), highs=C.map(x=>x.h), lows=C.map(x=>x.l), vols=C.map(x=>x.v);
  const cur=closes[closes.length-1];
  const atrVal=atr(C); const atrPct=cur?atrVal/cur:0;

  const recent24 = C.slice(-24);
  let sumVol = 0, sumTakerBuy = 0;
  for(let rc of recent24) { sumVol += rc.v; sumTakerBuy += (rc.tbv || 0); }
  const cvdRatio = sumVol > 0 ? sumTakerBuy / sumVol : 0.5;

  let emaFast=ema(closes.slice(-12),12), emaSlow=ema(closes.slice(-48),48);
  let trend=clamp((emaFast/emaSlow-1)/0.06,0,1); 
  let ret24=(cur-closes[closes.length-24])/closes[closes.length-24];
  let mom=clamp(ret24/0.15,0,1);

  const recV=mean(vols.slice(-10)), priorV=mean(vols.slice(-50,-10));
  const vRatio=priorV?recV/priorV:1;
  const volUp=clamp((vRatio-1)/1.0,0,1);

  let hi=Math.max(...highs.slice(-50)), lo=Math.min(...lows.slice(-50));
  let breakout=clamp((hi>lo)?(cur-lo)/(hi-lo):.5, 0, 1);

  let rs=0.5;
  if(btcClose){
    const bCur=btcClose[i], bPast=btcClose[i-24];
    if(bCur&&bPast){
      const bRet=(bCur-bPast)/bPast;
      const rsN=clamp((ret24-bRet)/(atrPct*5||0.05),-1.5,1.5);
      rs=clamp((rsN+0.5)/2,0,1);
    }
  }

  let oiMsg = "", oiStatus = "normal";

  if (oiShort !== 0 || oiMid !== 0) {
      // 단기(1h)=타이밍, 중기(4h)=지속성 확인
      if (ret24 > 0.02 && oiShort < -0.01) {
          breakout *= 0.5; mom *= 0.7; oiMsg = "📉 숏커버링"; oiStatus = "fake";
      } else if (ret24 > 0.02 && oiShort > 0.015) {
          trend = clamp(trend * 1.2, 0, 1);
          if (oiMid > 0.01) { oiMsg = "🔥 찐상승"; oiStatus = "real"; }
          else { oiMsg = "⚡ 초기유입"; oiStatus = "real"; }   // 단기↑ 중기 미약 = 막 시작
      }
      if (currentFunding < -0.0005 && oiShort > 0.025) {
          mom = clamp(mom * 1.5, 0, 1); oiMsg = "🧨 슈퍼 스퀴즈"; oiStatus = "nuke";
      }
      if (cvdRatio > 0.52 && ret24 > 0.02) {
          mom = clamp(mom * 1.2, 0, 1); oiMsg += oiMsg ? " (+CVD롱)" : "CVD 강매수";
      } else if (cvdRatio < 0.48 && ret24 > 0.02) {
          breakout *= 0.7; oiMsg += oiMsg ? " (CVD숏)" : "CVD 매도우위";
          if(oiStatus === "real") oiStatus = "fake"; 
      }
  }

  const ret3=(cur-closes[closes.length-3])/closes[closes.length-3];
  const overheat = ret3>0.18 ? 0.80 : 1.0;

  const br=btcRegime(btcClose,i);
  const base = weights.t*trend + weights.m*mom + weights.v*volUp + weights.b*breakout + weights.r*rs;
  const score = Math.round(clamp(base*overheat*br.f,0,1)*100);

  return { raw:score, atrPct, oiMsg, oiStatus, cvdRatio };
}

let CACHE = {}; 
let ACTIVE_SYMS = [];
let BEST_WEIGHTS = null;
let CALIB_TABLE = null;
let BASE_RATE = 0;
let liveScanResults = []; 
let sortConfig = { key: 'prob', dir: -1 }; 
let viewMode = 'card'; // 'card' | 'list'

let autoInterval = null;
let countdownTimer = null;
let nextUpdateTime = 0;

// === v6 실시간 진입신호 엔진 상태 ===
let scoreInterval = null;   // 점수(klines) 5분 갱신
let oiInterval = null;      // OI/펀딩 1분 경량 갱신
let signalInterval = null;  // 진입신호 판정 (가격흐름) 7초
let activeSignals = {};     // sym -> {dir, ts} 중복 알림 방지
let scanEntryPrice = {};    // 스캔 시점 기준가 (가격변화 측정용)
let ref24Price = {};        // 24시간 전 종가 (변화율 표시용)
const FAST_OI_MS = 60000;   // 1분
const SCORE_MS   = 300000;  // 5분
const SIGNAL_MS  = 7000;    // 7초

function toggleAuto() {
  const btn = document.getElementById('autoBtn');
  if (scoreInterval || autoInterval) {
    clearInterval(scoreInterval); clearInterval(oiInterval);
    clearInterval(signalInterval); clearInterval(countdownTimer);
    scoreInterval = oiInterval = signalInterval = autoInterval = null;
    document.getElementById('autoTimerTxt').innerText = "";
    btn.innerText = "🔄 2. 라이브 스캔 자동갱신: OFF"; btn.classList.remove('auto-on');
    log("⏸ 실시간 자동갱신 정지 (점수/OI/신호 루프 모두 중지).");
  } else {
    btn.innerText = "🔄 2. 라이브 스캔 자동갱신: ON (실시간)"; btn.classList.add('auto-on');
    log("▶ 실시간 자동갱신 시작 — 점수 5분 · OI/펀딩 1분 · 가격/신호 초단위.");
    nextUpdateTime = Date.now() + SCORE_MS;
    // 점수(과거봉) 갱신: 5분
    scoreInterval = setInterval(performAutoUpdate, SCORE_MS);
    // OI/펀딩 경량 갱신: 1분
    oiInterval = setInterval(performFastUpdate, FAST_OI_MS);
    // 진입신호 판정: 7초 (WS 가격 + 라이브 점수 종합)
    signalInterval = setInterval(evaluateSignals, SIGNAL_MS);
    countdownTimer = setInterval(() => {
      let diff = Math.max(0, Math.floor((nextUpdateTime - Date.now()) / 1000));
      let m = Math.floor(diff / 60).toString().padStart(2, '0');
      let s = (diff % 60).toString().padStart(2, '0');
      document.getElementById('autoTimerTxt').innerText = `다음 점수 재계산: ${m}:${s}`;
    }, 1000);
  }
}

async function performAutoUpdate() {
  if(!BEST_WEIGHTS || ACTIVE_SYMS.length === 0) return;
  let loaded = 0;
  for(const sym of ACTIVE_SYMS) {
    try { CACHE[sym] = await getKlines(sym, 150); } catch(e) {}
    loaded++;
    progFill.style.width = (loaded / ACTIVE_SYMS.length * 50) + '%';
    await sleep(20);
  }
  const btcClose = CACHE['BTCUSDT'].map(x=>x.c);
  renderBtcStatus(btcRegime(btcClose, btcClose.length-1));
  await runLiveScan(ACTIVE_SYMS.filter(s=>s!=='BTCUSDT'));
  progFill.style.width = '100%';
  nextUpdateTime = Date.now() + SCORE_MS;
  evaluateSignals();
  const now = new Date();
  document.getElementById('lastUpdateTxt').innerText = `(최근 점수 갱신: ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')})`;
}

// === [v6] OI/펀딩 경량 갱신 (1분) — klines 재다운로드 없이 OI/CVD/펀딩만 ===
async function performFastUpdate() {
  if(!BEST_WEIGHTS || liveScanResults.length === 0) return;
  try {
    const syms = liveScanResults.map(r => r.sym + 'USDT');
    const fundingMap = await getFundingRates();
    const oiMap = await getOIChangeMap(syms);
    for(const r of liveScanResults) {
      const full = r.sym + 'USDT';
      if(fundingMap[full] !== undefined) r.funding = fundingMap[full];
      if(oiMap[full] !== undefined) { r.oiShort = oiMap[full].short; r.oiMid = oiMap[full].mid; r.oiPct = oiMap[full].short; }
    }
    renderDashboard();
    log(`🔄 OI/펀딩 경량 갱신 완료 (${liveScanResults.length}종목).`);
    evaluateSignals();
  } catch(e) { log(`⚠ 경량 갱신 실패: ${e.message}`); }
}

// === [v6] 실시간 진입신호 판정 엔진 ===
// 라이브 점수(가격흐름 반영) + OI + CVD + 펀딩 + BTC장세 종합
function computeLiveScore(r) {
  // 스캔 시점 기준가 대비 실시간 가격 변화 (WS lastPrices 사용)
  const live = lastPrices[r.sym];
  const base = scanEntryPrice[r.sym];
  let drift = (live && base) ? (live - base) / base : 0; // 스캔 후 가격 변화율
  // 모멘텀 보너스: 스캔 후 살짝 눌렸다 올라오는 구간(과확장 아님)을 가점
  let bonus = 0;
  if (drift > 0 && drift < 0.015) bonus += 6;      // 갓 출발 (눌림 후 상승 초입)
  else if (drift >= 0.015 && drift < 0.04) bonus += 3;
  else if (drift >= 0.06) bonus -= 8;              // 이미 과확장 → 추격 위험
  else if (drift < -0.03) bonus -= 5;              // 신호 후 급락 = 무효
  return clamp(r.raw + bonus, 0, 100);
}

function entryVerdict(r) {
  const liveScore = computeLiveScore(r);
  const cvd = r.cvdRatio;
  const oiS = (r.oiShort !== undefined ? r.oiShort : r.oiPct) || 0;  // 단기(1h)
  const oiM = (r.oiMid !== undefined ? r.oiMid : 0) || 0;            // 중기(4h)
  const fund = r.funding;
  const live = lastPrices[r.sym], base = scanEntryPrice[r.sym];
  const drift = (live && base) ? (live - base) / base : 0;

  // 롱 진입타점: 점수↑ + 매수CVD우위 + 단기OI 유입 + 과확장 아님 + 가짜 아님
  const longOk = liveScore >= 62 && (r.prob >= 0.5) && cvd >= 0.5 &&
                 oiS > 0.0 && drift < 0.05 && r.oiStatus !== 'fake';
  // 회피: 가짜 or (매도우위+단기이탈) or (단기·중기 동반 이탈)
  const shortFlag = (r.oiStatus === 'fake') ||
                    (cvd < 0.46 && oiS < -0.02) ||
                    (oiS < -0.015 && oiM < -0.02);

  let dir = null, reasons = [];
  if (longOk) {
    dir = 'long';
    if (oiS > 0 && oiM > 0) reasons.push('OI지속유입');   // 단기+중기 동반 = 최상
    else if (oiS > 0) reasons.push('OI초기유입');         // 단기만 = 막 시작(빠른 포착)
    if (cvd >= 0.55) reasons.push('CVD강매수');
    if (oiS >= 0.03) reasons.push('OI급증');
    if (fund < -0.0003) reasons.push('숏스퀴즈');
    if (r.oiStatus === 'nuke') reasons.push('슈퍼스퀴즈');
    if (drift > 0 && drift < 0.015) reasons.push('상승초입');
  } else if (shortFlag) {
    dir = 'short';
    if (r.oiStatus === 'fake') reasons.push('숏커버/가짜');
    if (cvd < 0.46) reasons.push('매도우위');
    if (oiS < 0 && oiM < 0) reasons.push('자금이탈');
  }
  return { dir, liveScore, reasons };
}

function evaluateSignals() {
  if (!liveScanResults.length) return;
  const now = Date.now();
  const longs = [], shorts = [];

  for (const r of liveScanResults) {
    const v = entryVerdict(r);
    r._liveScore = v.liveScore;
    r._sigDir = v.dir;
    const card = document.getElementById(`card-${r.sym}`);
    if (card) {
      card.classList.remove('signal-long','signal-short');
      if (v.dir === 'long') card.classList.add('signal-long');
      else if (v.dir === 'short') card.classList.add('signal-short');
    }
    if (v.dir === 'long') {
      longs.push({r, v});
      const prev = activeSignals[r.sym];
      // 새 신호이거나 5분 지나 재무장된 경우만 토스트
      if (!prev || prev.dir !== 'long' || now - prev.ts > 300000) {
        fireToast(r, v, 'long');
        activeSignals[r.sym] = { dir: 'long', ts: now };
      }
    } else if (v.dir === 'short') {
      shorts.push({r, v});
      activeSignals[r.sym] = { dir: 'short', ts: now };
    } else {
      delete activeSignals[r.sym];
    }
  }
  renderSignalPanel(longs, shorts);
}

function fireToast(r, v, dir) {
  const wrap = document.getElementById('toastWrap');
  if (!wrap) return;
  const t = document.createElement('div');
  t.className = 'toast' + (dir === 'short' ? ' short' : '');
  const live = lastPrices[r.sym];
  let dec = live < 0.1 ? 5 : (live < 10 ? 4 : (live > 1000 ? 1 : 2));
  const priceTxt = live ? '$' + live.toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec}) : '';
  if (dir === 'long') {
    t.innerHTML = `🎯 <span><b>${r.sym}</b> 진입타점!</span>
      <span class="t-sub">${priceTxt} · 라이브점수 ${v.liveScore} · 성공률 ${(r.prob*100).toFixed(0)}% · TP +${(r.tp*100).toFixed(1)}% / SL -${(r.sl*100).toFixed(1)}% ${v.reasons.length?'· '+v.reasons.join(' '):''}</span>`;
  } else {
    t.innerHTML = `⚠ <span><b>${r.sym}</b> 회피</span><span class="t-sub">${v.reasons.join(' ')||'매도우위'} — 추격매수 주의</span>`;
  }
  wrap.appendChild(t);
  setTimeout(() => { if (t.parentNode) t.remove(); }, 7200);
}

function renderSignalPanel(longs, shorts) {
  const panel = document.getElementById('signalPanel');
  const list = document.getElementById('sigList');
  if (!panel || !list) return;
  longs.sort((a,b) => b.v.liveScore - a.v.liveScore);
  let h = '';
  for (const {r, v} of longs) {
    h += `<span class="sig-chip" onclick="document.getElementById('card-${r.sym}')?.scrollIntoView({behavior:'smooth',block:'center'})">🎯 <span class="s-sym">${r.sym}</span> ${v.liveScore}점 · ${(r.prob*100).toFixed(0)}% · TP+${(r.tp*100).toFixed(1)}%</span>`;
  }
  for (const {r, v} of shorts) {
    h += `<span class="sig-chip short" onclick="document.getElementById('card-${r.sym}')?.scrollIntoView({behavior:'smooth',block:'center'})">⚠ <span class="s-sym">${r.sym}</span> ${v.reasons[0]||'회피'}</span>`;
  }
  if (!h) h = '<span class="sig-empty">현재 조건을 만족하는 진입타점이 없습니다. 모니터링 중...</span>';
  list.innerHTML = h;
  panel.classList.add('active');
}

// =======================================================
// [핵심] V5.5 무결점 애니메이션 & 디버그 웹소켓 
// =======================================================
let binanceWS = null;
let lastPrices = {}; 
let lastQuoteVol = {}; 
let lastWsMsgTime = 0;        // 마지막 WS 데이터 수신 시각
let pricePollTimer = null;    // REST 폴링 폴백 타이머
let wsWatchdog = null;        // WS 무응답 감시

// 가격 1건을 카드에 반영 (WS/REST 공용)
function applyTick(symStr, currentPrice, currentVol) {
  const priceEl = document.getElementById(`price-${symStr}`);
  if (!priceEl) return false;
  const cardEl = document.getElementById(`card-${symStr}`);
  const prevPrice = lastPrices[symStr] || currentPrice;
  const prevVol = lastQuoteVol[symStr] || currentVol;
  let dec = currentPrice < 0.1 ? 5 : (currentPrice < 10 ? 4 : (currentPrice > 1000 ? 1 : 2));
  priceEl.innerText = "$ " + currentPrice.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  priceEl.classList.remove('flash-up', 'flash-down');
  void priceEl.offsetWidth;
  if (currentPrice > prevPrice) priceEl.classList.add('flash-up');
  else if (currentPrice < prevPrice) priceEl.classList.add('flash-down');
  if (currentVol) {
    let deltaQ = currentVol - prevVol;
    if (deltaQ > 20000 && currentPrice >= prevPrice && cardEl) {
      let target = liveScanResults.find(x => x.sym === symStr);
      if (target && target.raw >= 50) triggerIgnition(symStr, deltaQ, cardEl);
    }
    lastQuoteVol[symStr] = currentVol;
  }
  lastPrices[symStr] = currentPrice;
  const chgEl = document.getElementById(`chg-${symStr}`);
  if (chgEl) { const c = change24(symStr); if (c !== null) { chgEl.style.color = c>=0?'var(--bull)':'var(--bear)'; chgEl.innerText = (c>=0?'+':'')+(c*100).toFixed(2)+'%'; } }
  return true;
}

// REST 폴링 폴백: WS 데이터가 안 들어올 때 3초마다 전 종목 가격 일괄 수신
async function pollPricesOnce() {
  try {
    const arr = await fetchAPI(`${FAPI}/fapi/v1/ticker/price`);
    if (!Array.isArray(arr)) return;
    let matched = 0;
    for (const t of arr) {
      if (!t.symbol || !t.symbol.endsWith('USDT')) continue;
      const symStr = t.symbol.replace('USDT','');
      if (applyTick(symStr, parseFloat(t.price), 0)) matched++;
    }
    const el = document.getElementById('wsStatus');
    if (el) el.innerHTML = `🟢 시세 수신중 <span style="color:var(--gold); font-family:monospace; font-size:12px; margin-left:4px;">[REST 폴백 · ${matched}종목 갱신]</span>`;
    if (matched) evaluateSignals();
  } catch(e) {
    const el = document.getElementById('wsStatus');
    if (el) el.innerHTML = `🔴 <span style="color:var(--bear)">가격 수신 실패: ${e.message}</span>`;
  }
}
function startPricePolling() {
  if (pricePollTimer) return;
  log("🛰 WS 데이터 미수신 → REST 폴링 폴백 시작 (3초 간격).");
  pollPricesOnce();
  pricePollTimer = setInterval(pollPricesOnce, 3000);
}
function stopPricePolling() {
  if (pricePollTimer) { clearInterval(pricePollTimer); pricePollTimer = null; log("✅ WS 시세 복구 → REST 폴백 중지."); }
}

function connectWebSocket() {
  if (binanceWS) {
    binanceWS.onclose = null; 
    binanceWS.close();
  }

  log("🌐 바이낸스 실시간 스트림(miniTicker) 접속 중...");
  document.getElementById('wsStatus').innerHTML = `🟡 서버에 연결 중...`;
  
  // 가장 확실하게 동작하는 Combined Stream 방식 사용
  let wsUrl = 'wss://fstream.binance.com/ws/!miniTicker@arr';
  binanceWS = new WebSocket(wsUrl);
  
  binanceWS.onopen = () => {
    document.getElementById('wsStatus').innerHTML = `🟢 서버 통신망 열림 (첫 데이터 대기중)`;
    log("✅ 웹소켓이 연결되었습니다. 시세 업데이트를 수신합니다.");
    // 워치독: 8초 내 데이터 없으면 REST 폴백으로 전환
    if (wsWatchdog) clearTimeout(wsWatchdog);
    wsWatchdog = setTimeout(() => {
      if (Date.now() - lastWsMsgTime > 7000) startPricePolling();
    }, 8000);
  };

  binanceWS.onmessage = (event) => {
    lastWsMsgTime = Date.now();
    stopPricePolling();
    if(!document.getElementById('scanResWrap') || document.getElementById('scanResWrap').style.display === 'none') return;
    
    try {
      let parsed = JSON.parse(event.data);
      // Combined stream 의 경우 data 키 안에 실제 페이로드가 있음
      let payload = parsed.data ? parsed.data : parsed;
      
      if (!Array.isArray(payload)) {
          if (payload.s && payload.c) payload = [payload];
          else return;
      }
      
      let matchedCount = 0;
      payload.forEach(tick => {
        if (!tick || !tick.s || !tick.c) return;
        
        // 종목명에서 잡동사니를 다 떼어내고 정확한 ID 추적
        const symStr = tick.s.toUpperCase().replace('USDT', '').trim();
        const currentPrice = parseFloat(tick.c);
        const currentVol = parseFloat(tick.q || 0);
        if (applyTick(symStr, currentPrice, currentVol)) matchedCount++;
      });

      // UI 디버그용 수신 상태판 업데이트
      if(payload.length > 0) {
          document.getElementById('wsStatus').innerHTML = `🟢 시세 수신중 <span style="color:var(--cyan); font-family:monospace; font-size:12px; margin-left:4px;">[전체 패킷: ${payload.length} / 내 화면과 일치: ${matchedCount}]</span>`;
      }
    } catch (err) {
      document.getElementById('wsStatus').innerHTML = `🔴 파싱 에러: ${err.message}`;
    }
  };

  binanceWS.onerror = () => {
    document.getElementById('wsStatus').innerHTML = `🔴 <span style="color:var(--bear)">네트워크 차단됨</span>`;
  };
  
  binanceWS.onclose = () => {
    if (wsWatchdog) clearTimeout(wsWatchdog);
    document.getElementById('wsStatus').innerHTML = `🟡 <span style="color:var(--gold)">재접속 대기중... (현재 REST 폴백 가동 가능)</span>`;
    if (Date.now() - lastWsMsgTime > 7000) startPricePolling();  // WS 불통이면 즉시 폴백
    setTimeout(connectWebSocket, 4000);
  };
}

function triggerIgnition(symStr, volumeUSD, cardEl) {
    let volFormat = volumeUSD > 1000000 ? (volumeUSD/1000000).toFixed(1) + 'M' : (volumeUSD/1000).toFixed(0) + 'k';
    
    // 기존 뱃지가 있다면 떼어냄
    let oldBadge = cardEl.querySelector('.ignite-badge');
    if(oldBadge) oldBadge.remove();
    
    let badge = document.createElement('div');
    badge.className = 'ignite-badge';
    badge.innerHTML = `🧨 $${volFormat} 폭발!`;
    cardEl.appendChild(badge);
    
    // 애니메이션 리셋 및 재시작
    cardEl.classList.remove('ignite-anim');
    void cardEl.offsetWidth; 
    cardEl.classList.add('ignite-anim');
    
    setTimeout(() => {
        if(badge && badge.parentNode) badge.remove();
    }, 3000);
}
// =======================================================

async function runEvolution(){
  const btn=document.getElementById('evoBtn'); 
  btn.disabled=true;
  btn.innerText = "⏳ 1. 엔진 가동 중 (데이터 다운로드)..."; 

  logBox.innerHTML='';
  warnBox.style.display='none';
  document.getElementById('scanResWrap').style.display='none';
  
  if(scoreInterval || autoInterval) toggleAuto();
  
  const nSyms = +document.getElementById('topN').value;
  const kLimit = +document.getElementById('kLimit').value;
  
  try{
    log(`[1/3] 거래량 상위 ${nSyms}개 심볼 수집...`);
    const syms = await getTopSymbols(nSyms);
    if(!syms || syms.length===0) throw new Error("심볼 목록을 가져오지 못했습니다.");
    syms.unshift('BTCUSDT'); 
    ACTIVE_SYMS = [...new Set(syms)];
    
    log(`[2/3] 과거 데이터(${kLimit}봉) 다운로드 중...`);
    let loaded=0;
    for(const sym of ACTIVE_SYMS){
      try{ CACHE[sym] = await getKlines(sym, kLimit); }catch(e){}
      loaded++;
      progFill.style.width=(loaded/ACTIVE_SYMS.length*30)+'%';
      await sleep(20); 
    }

    const btcData = CACHE['BTCUSDT'];
    if(!btcData || btcData.length === 0) {
        throw new Error("HTTP 429/418 - 요청 한도 초과 (IP 차단됨)");
    }
    const btcClose = btcData.map(x=>x.c);
    renderBtcStatus(btcRegime(btcClose, btcClose.length-1));

    const HOR = 36;
    const TRAIN_FRAC = 0.7;   // 앞 70% 학습 / 뒤 30% 검증(OOS)
    log(`[3/3] 🧬 자가 진화 엔진 가동 (워크포워드 70/30 검증)...`);

    let bestTrainLift = 0;
    let chosen = null;        // {w, trainLift, testLift, testBase, calib}
    let lastW = null;

    for(let iter=1; iter<=12; iter++){
      let w = { t:Math.random(), m:Math.random(), v:Math.random(), b:Math.random(), r:Math.random() };
      let sum = w.t + w.m + w.v + w.b + w.r;
      w = { t:w.t/sum, m:w.m/sum, v:w.v/sum, b:w.b/sum, r:w.r/sum };
      lastW = w;

      const train=[], test=[];
      for(const sym of ACTIVE_SYMS){
        if(sym==='BTCUSDT' || !CACHE[sym]) continue;
        const cs = CACHE[sym];
        const n = Math.min(cs.length, btcClose.length);
        const trainEnd = Math.floor(n * TRAIN_FRAC);
        for(let i=130; i<n-HOR; i+=6){
          const f = calcFeatures(cs, i, btcClose, w);
          if(!f) continue;
          const entry = cs[i].c;
          const tpPct = Math.max(0.04, f.atrPct * 2);
          const slPct = Math.max(0.02, f.atrPct * 1);
          const tp = entry * (1 + tpPct);
          const sl = entry * (1 - slPct);
          let win = 0;
          for(let j=i+1; j<=i+HOR; j++){
            if(cs[j].l <= sl) { win = 0; break; }
            if(cs[j].h >= tp) { win = 1; break; }
          }
          (i < trainEnd ? train : test).push({ raw:f.raw, label:win });
        }
      }

      const trBase = mean(train.map(s=>s.label));
      const trHi = train.filter(s=>s.raw>=60);
      const trHiProb = trHi.length ? mean(trHi.map(s=>s.label)) : 0;
      const trainLift = trBase ? trHiProb/trBase : 0;

      const teBase = mean(test.map(s=>s.label));
      const teHi = test.filter(s=>s.raw>=60);
      const teHiProb = teHi.length ? mean(teHi.map(s=>s.label)) : 0;
      const testLift = teBase ? teHiProb/teBase : 0;

      log(`   └ 세대 ${iter}: 학습 ${trainLift.toFixed(2)}x / 검증(OOS) ${testLift.toFixed(2)}x (검증 고득점 ${(teHiProb*100).toFixed(1)}%)`);
      progFill.style.width=(30 + (iter/12)*70)+'%';

      // 가중치 선택은 학습셋 기준, 단 확률표(CALIB)는 반드시 검증셋으로 산출 → 과최적화 방지
      if(trainLift > bestTrainLift && trHi.length > 40 && teHi.length > 20){
        bestTrainLift = trainLift;
        const buckets=[];
        for(let lo=0; lo<100; lo+=10){
          const inb=test.filter(s=>s.raw>=lo && s.raw<lo+10);
          if(inb.length>=12) buckets.push({lo, hi:lo+10, prob:mean(inb.map(s=>s.label))});
        }
        chosen = { w, trainLift, testLift, testBase: teBase, calib: buckets };
      }
      await sleep(10);
    }

    let bestLift = 0;
    if(chosen){
      BEST_WEIGHTS = chosen.w;
      CALIB_TABLE  = chosen.calib;
      BASE_RATE    = chosen.testBase;
      bestLift     = chosen.testLift;   // 정직한 지표 = 검증(OOS) 변별력
    } else {
      BEST_WEIGHTS = lastW; CALIB_TABLE = null; BASE_RATE = 0;
    }

    if(!chosen || bestLift < 1.15){
      warnBox.style.display = 'block';
      log(`⚠ 진화 실패: 검증(OOS)에서 통계적 우위 확보 실패 — 과최적화 의심, 매매 보류 권장.`);
      document.getElementById('calibState').textContent = `경고: 검증 변별력 부족`;
    } else {
      log(`✅ 진화 완료! 검증(OOS) 변별력 ${bestLift.toFixed(2)}x (학습 ${chosen.trainLift.toFixed(2)}x).`);
      document.getElementById('calibState').textContent = `진화 완료: 검증 ${bestLift.toFixed(2)}x / 학습 ${chosen.trainLift.toFixed(2)}x`;
      document.getElementById('autoBtn').disabled = false;
    }
    
    displayBestParams();
    await runLiveScan(ACTIVE_SYMS.filter(s=>s!=='BTCUSDT'));
    
    connectWebSocket();
    setTimeout(evaluateSignals, 2500);
    
    const now = new Date();
    document.getElementById('lastUpdateTxt').innerText = `(최근 점수 갱신: ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')})`;

  }catch(e){ 
      log(`❌ 오류: ${e.message}`); 
      if(e.message.includes("429") || e.message.includes("418") || e.message.includes("한도 초과")) {
          alert("🚨 바이낸스 서버 차단 (Rate Limit)!\n\n약 3~5분 대기 후 '50개' 종목으로 다시 시도해주세요.");
      } else {
          alert(`오류 발생: ${e.message}`);
      }
  } finally {
      btn.disabled=false;
      btn.innerText="🧬 1. 엔진 최적화 (수동/초기화)"; 
  }
}

function displayBestParams(){
  if(!BEST_WEIGHTS) return;
  const w = BEST_WEIGHTS;
  const pBox = document.getElementById('bestParams');
  pBox.innerHTML = `
    <div><span>추세 (Trend)</span><b style="color:var(--cyan)">${(w.t*100).toFixed(0)}%</b></div>
    <div><span>모멘텀 (Momentum)</span><b style="color:var(--cyan)">${(w.m*100).toFixed(0)}%</b></div>
    <div><span>거래량 (Volume)</span><b style="color:var(--cyan)">${(w.v*100).toFixed(0)}%</b></div>
    <div><span>고점위치 (Breakout)</span><b style="color:var(--cyan)">${(w.b*100).toFixed(0)}%</b></div>
    <div><span>상대강세 (RS)</span><b style="color:var(--cyan)">${(w.r*100).toFixed(0)}%</b></div>
  `;
}

function handleSort(val) {
  const parts = val.split('_');
  sortConfig.key = parts[0];
  sortConfig.dir = parts[1] === 'desc' ? -1 : 1;
  renderDashboard();
}

function setView(mode) {
  viewMode = mode;
  document.getElementById('viewCardBtn').classList.toggle('on', mode==='card');
  document.getElementById('viewListBtn').classList.toggle('on', mode==='list');
  const grid = document.getElementById('scanGrid');
  grid.className = mode==='card' ? 'grid-board' : 'list-board';
  renderDashboard();
}

function fmtPrice(p){
  if(!p) return "";
  let dec = p < 0.1 ? 5 : (p < 10 ? 4 : (p > 1000 ? 1 : 2));
  return "$ " + p.toLocaleString('en-US', {minimumFractionDigits:dec, maximumFractionDigits:dec});
}

function fmtPct(x){ if(x===undefined||x===null||x===0) return '-'; return (x>0?'+':'')+(x*100).toFixed(2)+'%'; }
function pctCls(x){ return x>0?'pos':(x<0?'neg':'mut'); }
function change24(sym){
  const ref = ref24Price[sym], live = lastPrices[sym];
  if(!ref || !live) return null;
  return (live - ref) / ref;
}
function chgHtml(sym){
  const c = change24(sym);
  if(c === null) return '';
  const col = c >= 0 ? 'var(--bull)' : 'var(--bear)';
  return `<span class="chg" id="chg-${sym}" style="color:${col}">${c>=0?'+':''}${(c*100).toFixed(2)}%</span>`;
}

function applySignalClasses(){
  for(const r of liveScanResults){
    const el = document.getElementById(`card-${r.sym}`);
    if(!el) continue;
    el.classList.remove('signal-long','signal-short');
    if(r._sigDir==='long') el.classList.add('signal-long');
    else if(r._sigDir==='short') el.classList.add('signal-short');
  }
}

function renderDashboard() {
  document.getElementById('scanResWrap').style.display = 'block';
  document.getElementById('resCount').innerText = liveScanResults.length;
  const grid = document.getElementById('scanGrid');
  grid.className = viewMode==='card' ? 'grid-board' : 'list-board';

  liveScanResults.sort((a,b) => {
    let valA = a[sortConfig.key];
    let valB = b[sortConfig.key];
    if(typeof valA === 'string') return sortConfig.dir * valA.localeCompare(valB);
    return sortConfig.dir * (valA - valB);
  });

  if(viewMode==='list'){ renderListView(); applySignalClasses(); return; }

  let h = '';
  for(const r of liveScanResults){
    const probTxt = (r.prob*100).toFixed(1)+'%';
    const oiSv = (r.oiShort!==undefined?r.oiShort:r.oiPct);
    const oiMv = r.oiMid;
    const evTxt = (r.ev!==undefined) ? ((r.ev>=0?'+':'')+(r.ev*100).toFixed(2)+'%') : '-';
    const cvdPct = (r.cvdRatio*100).toFixed(1);
    const cvdColor = r.cvdRatio >= 0.5 ? 'var(--bull)' : 'var(--bear)';
    const cvdBar = `<div class="bar-wrap"><div class="bar-fill" style="width:${cvdPct}%; background:${cvdColor}"></div></div>`;
    let pillHtml = r.oiMsg ? `<span class="pill ${r.oiStatus}" style="font-size:11px; margin-top:6px;">${r.oiMsg}</span>` : '';
    let displayPrice = fmtPrice(lastPrices[r.sym]);

    h += `
    <div class="c-card" id="card-${r.sym}">
      <div class="c-hdr">
        <div>
          <div class="c-sym">${r.sym} ${chgHtml(r.sym)}</div>
          <div class="c-price" id="price-${r.sym}">${displayPrice}</div>
          ${pillHtml}
        </div>
        <div style="text-align:right;">
          <div class="c-lbl" style="font-size:10px;">진화점수</div>
          <div class="c-score ${r.raw >= 60 ? 'pos' : ''}">${r.raw}</div>
        </div>
      </div>
      <div class="c-row">
        <span class="c-lbl">TP 터치 확률</span> 
        <span class="c-val" style="color:var(--purp); font-size:14px;">${probTxt}</span>
      </div>
      <div class="c-row">
        <span class="c-lbl">CVD 매수 비율</span> 
        <span class="c-val" style="color:${cvdColor}">${cvdPct}% ${cvdBar}</span>
      </div>
      <div class="c-row">
        <span class="c-lbl">OI 1h / 4h</span> 
        <span class="c-val"><span class="${pctCls(oiSv)}">${fmtPct(oiSv)}</span> <span style="color:var(--tx3)">/</span> <span class="${pctCls(oiMv)}">${fmtPct(oiMv)}</span></span>
      </div>
      <div class="c-row">
        <span class="c-lbl">기대값 (EV)</span> 
        <span class="c-val" style="color:${r.ev>=0?'var(--bull)':'var(--bear)'}; font-weight:800;">${evTxt}</span>
      </div>
      <div class="c-row">
        <span class="c-lbl">현재 펀딩비</span> 
        <span class="c-val ${r.funding<0?'neg':''}">${(r.funding*100).toFixed(4)}%</span>
      </div>
      <div class="c-foot">
        <div class="c-tpsl" style="color:var(--bull)">TP +${(r.tp*100).toFixed(1)}%</div>
        <div class="c-tpsl" style="color:var(--bear)">SL -${(r.sl*100).toFixed(1)}%</div>
      </div>
    </div>`;
  }
  grid.innerHTML = h;
  applySignalClasses();
}

function renderListView(){
  let rows = '';
  for(const r of liveScanResults){
    const probTxt = (r.prob*100).toFixed(1)+'%';
    const oiSv = (r.oiShort!==undefined?r.oiShort:r.oiPct);
    const oiMv = r.oiMid;
    const evTxt = (r.ev!==undefined) ? ((r.ev>=0?'+':'')+(r.ev*100).toFixed(2)+'%') : '-';
    const cvdPct = (r.cvdRatio*100).toFixed(1);
    const cvdColor = r.cvdRatio >= 0.5 ? 'var(--bull)' : 'var(--bear)';
    const pill = r.oiMsg ? `<span class="pill ${r.oiStatus}" style="font-size:10px;">${r.oiMsg}</span>` : '<span style="color:var(--tx3)">-</span>';
    rows += `<tr class="lrow" id="card-${r.sym}">
      <td><span class="l-sym">${r.sym}</span> ${chgHtml(r.sym)}</td>
      <td><span class="l-price" id="price-${r.sym}">${fmtPrice(lastPrices[r.sym])}</span></td>
      <td style="color:${r.raw>=60?'var(--bull)':'var(--tx)'};font-weight:800;">${r.raw}</td>
      <td style="color:var(--purp);font-weight:700;">${probTxt}</td>
      <td style="color:${r.ev>=0?'var(--bull)':'var(--bear)'};font-weight:800;">${evTxt}</td>
      <td style="color:${cvdColor};font-weight:700;">${cvdPct}%</td>
      <td class="${pctCls(oiSv)}" style="font-weight:700;">${fmtPct(oiSv)}</td>
      <td class="${pctCls(oiMv)}" style="font-weight:700;">${fmtPct(oiMv)}</td>
      <td style="color:${r.funding<0?'var(--bear)':'var(--tx2)'};">${(r.funding*100).toFixed(4)}%</td>
      <td><span style="color:var(--bull)">+${(r.tp*100).toFixed(1)}%</span> / <span style="color:var(--bear)">-${(r.sl*100).toFixed(1)}%</span></td>
      <td style="text-align:left;">${pill}</td>
    </tr>`;
  }
  document.getElementById('scanGrid').innerHTML = `
    <table class="scan-table">
      <thead><tr>
        <th>종목</th><th>가격</th><th>진화점수</th><th>성공률</th><th>기대값</th><th>CVD</th>
        <th>OI 1h</th><th>OI 4h</th><th>펀딩비</th><th>TP / SL</th><th>상태</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

async function runLiveScan(syms){
  const fundingMap = await getFundingRates();
  const oiMap = await getOIChangeMap(syms); 
  
  liveScanResults = []; 
  const btcClose = CACHE['BTCUSDT'].map(x=>x.c);
  
  for(const sym of syms){
    if(!CACHE[sym]) continue;
    const cs = CACHE[sym];
    const fr = fundingMap[sym] || 0;
    const oi = oiMap[sym] || {short:0, mid:0};
    
    // 초기화용
    const curClose = cs[cs.length-1].c;
    const curVol = cs[cs.length-1].v * curClose; 
    if(!lastPrices[sym.replace('USDT', '')]) {
        lastPrices[sym.replace('USDT', '')] = curClose;
        lastQuoteVol[sym.replace('USDT', '')] = curVol;
    }
    scanEntryPrice[sym.replace('USDT','')] = curClose; // 신호 판정용 기준가 갱신
    { const _k=sym.replace('USDT',''); const _i=cs.length-25; ref24Price[_k] = (_i>=0? cs[_i].c : cs[0].c); }
    
    const f = calcFeatures(cs, cs.length-1, btcClose, BEST_WEIGHTS, fr, oi.short, oi.mid);
    if(f){
      let prob = 0;
      if(CALIB_TABLE){
        const b = CALIB_TABLE.find(b=> f.raw>=b.lo && f.raw<b.hi);
        prob = b ? b.prob : (f.raw>=90 ? CALIB_TABLE[CALIB_TABLE.length-1].prob : BASE_RATE);
      }
      
      const tpPct = Math.max(0.04, f.atrPct * 2);
      const slPct = Math.max(0.02, f.atrPct * 1);
      
      const ev = prob * tpPct - (1 - prob) * slPct;   // 기대값 (손익비 반영)
      liveScanResults.push({ 
        sym: sym.replace('USDT',''), 
        raw: f.raw, 
        prob: prob, 
        ev: ev,
        cvdRatio: f.cvdRatio,
        funding: fr, 
        oiPct: oi.short,
        oiShort: oi.short,
        oiMid: oi.mid,
        oiMsg: f.oiMsg,
        oiStatus: f.oiStatus,
        tp: tpPct, 
        sl: slPct 
      });
    }
  }
  document.getElementById('sortControl').value = 'ev_desc';
  sortConfig = { key: 'ev', dir: -1 };
  renderDashboard(); 
}
