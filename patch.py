import io, sys, re

SRC = "/sessions/funny-tender-meitner/mnt/outputs/src.html"
OUT = "/sessions/funny-tender-meitner/mnt/outputs/WHISTLER_v6_realtime.html"

s = io.open(SRC, encoding="utf-8").read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n >= 1, f"NOT FOUND:\n{old[:120]}"
    s = s.replace(old, new, count)

# ---------- 1) CSS ----------
CSS_ANCHOR = """.sort-area { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; background: var(--bg2); padding: 10px 14px; border: 1px solid var(--bd); border-radius: 4px; }
</style>"""
CSS_ADD = """.sort-area { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; background: var(--bg2); padding: 10px 14px; border: 1px solid var(--bd); border-radius: 4px; }

/* 실시간 진입신호 토스트 */
#toastWrap { position: fixed; top: 14px; left: 50%; transform: translateX(-50%); z-index: 9999; display: flex; flex-direction: column; gap: 8px; align-items: center; pointer-events: none; width: 100%; max-width: 520px; padding: 0 12px; }
.toast { background: linear-gradient(135deg, rgba(255,194,75,0.96), rgba(255,140,0,0.96)); color: #0a0a0a; font-weight: 800; font-size: 14px; padding: 12px 18px; border-radius: 8px; box-shadow: 0 8px 24px rgba(255,140,0,0.45); display: flex; align-items: center; gap: 10px; width: 100%; animation: toastIn 0.4s ease-out, toastOut 0.5s ease-in 6.5s forwards; }
.toast.short { background: linear-gradient(135deg, rgba(255,59,92,0.96), rgba(180,30,60,0.96)); color: #fff; box-shadow: 0 8px 24px rgba(255,59,92,0.45); }
.toast b { font-size: 16px; letter-spacing: .02em; }
.toast .t-sub { font-size: 11px; font-weight: 600; opacity: 0.85; }
@keyframes toastIn { from { transform: translateY(-30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes toastOut { to { transform: translateY(-20px); opacity: 0; } }

/* 진입신호 패널 */
#signalPanel { background: linear-gradient(135deg, rgba(255,194,75,0.06), rgba(180,100,255,0.04)); border: 1px solid var(--gold); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: none; }
#signalPanel.active { display: block; animation: panelGlow 2s infinite alternate; }
@keyframes panelGlow { from { box-shadow: 0 0 0 rgba(255,194,75,0); } to { box-shadow: 0 0 16px rgba(255,194,75,0.25); } }
.sig-title { font-size: 13px; font-weight: 800; color: var(--gold); margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.sig-list { display: flex; flex-wrap: wrap; gap: 8px; }
.sig-chip { background: rgba(255,194,75,0.12); border: 1px solid var(--gold); border-radius: 20px; padding: 6px 12px; font-size: 12px; font-family: monospace; font-weight: 700; color: var(--gold); display: flex; align-items: center; gap: 6px; cursor: pointer; }
.sig-chip.short { background: rgba(255,59,92,0.12); border-color: var(--bear); color: var(--bear); }
.sig-chip .s-sym { color: #fff; font-size: 13px; }
.sig-empty { font-size: 12px; color: var(--tx3); }

/* 진입신호 카드 강조 */
.c-card.signal-long { border-color: var(--gold) !important; box-shadow: 0 0 0 1px var(--gold), 0 0 18px rgba(255,194,75,0.35); }
.c-card.signal-long::before { content: "TARGET"; position: absolute; top: 0; right: 0; background: var(--gold); color: #000; font-size: 10px; font-weight: 900; padding: 3px 8px; border-radius: 0 8px 0 8px; z-index: 5; }
.c-card.signal-short { border-color: var(--bear) !important; box-shadow: 0 0 0 1px var(--bear), 0 0 18px rgba(255,59,92,0.3); }
.c-card.signal-short::before { content: "AVOID"; position: absolute; top: 0; right: 0; background: var(--bear); color: #fff; font-size: 10px; font-weight: 900; padding: 3px 8px; border-radius: 0 8px 0 8px; z-index: 5; }
.live-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--bull); margin-right:5px; animation: livePulse 1.2s infinite; vertical-align:middle; }
@keyframes livePulse { 0%,100%{opacity:1;} 50%{opacity:0.25;} }
.delta-up{color:var(--bull);} .delta-down{color:var(--bear);}
</style>"""
rep(CSS_ANCHOR, CSS_ADD)

# fix emoji content for badges (use real emoji)
s = s.replace('content: "TARGET";', 'content: "\U0001F3AF 진입";')
s = s.replace('content: "AVOID";', 'content: "⚠ 회피";')

# ---------- 2) HTML: toast wrap + signal panel ----------
rep('<body class="notranslate">',
    '<body class="notranslate">\n<div id="toastWrap"></div>')

rep('<div id="scanResWrap" style="display:none;">',
    '''<div id="signalPanel">
    <div class="sig-title"><span class="live-dot"></span>🎯 실시간 진입신호 (라이브 점수 + 가격흐름 + OI/CVD 종합)</div>
    <div class="sig-list" id="sigList"><span class="sig-empty">조건을 만족하는 진입타점을 탐색 중입니다...</span></div>
  </div>

  <div id="scanResWrap" style="display:none;">''')

# ---------- 3) JS ----------
# 3a. global state additions
rep('let nextUpdateTime = 0;',
    '''let nextUpdateTime = 0;

// === v6 실시간 진입신호 엔진 상태 ===
let scoreInterval = null;   // 점수(klines) 5분 갱신
let oiInterval = null;      // OI/펀딩 1분 경량 갱신
let signalInterval = null;  // 진입신호 판정 (가격흐름) 7초
let activeSignals = {};     // sym -> {dir, ts} 중복 알림 방지
let scanEntryPrice = {};    // 스캔 시점 기준가 (가격변화 측정용)
const FAST_OI_MS = 60000;   // 1분
const SCORE_MS   = 300000;  // 5분
const SIGNAL_MS  = 7000;    // 7초''')

# 3b. toggleAuto rewrite to multi-loop (regex, whitespace-tolerant)
NEW_TOGGLE = """function toggleAuto() {
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
}"""
# replace existing toggleAuto(){ ... } block via regex (non-greedy to first "\n}\n")
s, nsub = re.subn(r"function toggleAuto\(\) \{.*?\n\}", NEW_TOGGLE, s, count=1, flags=re.S)
assert nsub == 1, "toggleAuto not replaced"

# 3c. after performAutoUpdate: reset nextUpdateTime to SCORE_MS (tolerant of trailing space)
s, nsub = re.subn(r"nextUpdateTime = Date\.now\(\) \+ 900000;\s*\n  const now = new Date\(\);",
                  "nextUpdateTime = Date.now() + SCORE_MS;\n  evaluateSignals();\n  const now = new Date();",
                  s, count=1)
assert nsub == 1, "performAutoUpdate nextUpdateTime not replaced"

# 3d. insert new engine functions after performAutoUpdate close
ANCHOR_FN = """  document.getElementById('lastUpdateTxt').innerText = `(최근 점수 갱신: ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')})`;
}

// ======================================================="""
NEW_FN = """  document.getElementById('lastUpdateTxt').innerText = `(최근 점수 갱신: ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')})`;
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
      if(oiMap[full] !== undefined) r.oiPct = oiMap[full];
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
  const oi = r.oiPct;
  const fund = r.funding;
  const live = lastPrices[r.sym], base = scanEntryPrice[r.sym];
  const drift = (live && base) ? (live - base) / base : 0;

  // 롱 진입타점: 점수↑ + 매수CVD우위 + 자금유입(OI↑) + 과확장 아님
  const longOk = liveScore >= 62 && (r.prob >= 0.5) && cvd >= 0.5 &&
                 oi > 0.0 && drift < 0.05 && r.oiStatus !== 'fake';
  // 숏커버 가짜/매도우위 → 회피 신호
  const shortFlag = (r.oiStatus === 'fake') || (cvd < 0.46 && oi < -0.03);

  let dir = null, reasons = [];
  if (longOk) {
    dir = 'long';
    if (cvd >= 0.55) reasons.push('CVD강매수');
    if (oi >= 0.05) reasons.push('OI급증');
    if (fund < -0.0003) reasons.push('숏스퀴즈');
    if (r.oiStatus === 'nuke') reasons.push('슈퍼스퀴즈');
    if (drift > 0 && drift < 0.015) reasons.push('상승초입');
  } else if (shortFlag) {
    dir = 'short';
    if (r.oiStatus === 'fake') reasons.push('숏커버/가짜');
    if (cvd < 0.46) reasons.push('매도우위');
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

// ======================================================="""
rep(ANCHOR_FN, NEW_FN)

# 3e. record scanEntryPrice in runLiveScan when initializing lastPrices
rep('''        lastPrices[sym.replace('USDT', '')] = curClose;
        lastQuoteVol[sym.replace('USDT', '')] = curVol;
    }''',
    '''        lastPrices[sym.replace('USDT', '')] = curClose;
        lastQuoteVol[sym.replace('USDT', '')] = curVol;
    }
    scanEntryPrice[sym.replace('USDT','')] = curClose; // 신호 판정용 기준가 갱신''')

# 3f. start signal eval right after first scan render in runEvolution
rep('await runLiveScan(ACTIVE_SYMS.filter(s=>s!==\'BTCUSDT\'));\n    \n    connectWebSocket();',
    'await runLiveScan(ACTIVE_SYMS.filter(s=>s!==\'BTCUSDT\'));\n    \n    connectWebSocket();\n    setTimeout(evaluateSignals, 2500);')

# 3g. version label bumps
s = s.replace('WHISTLER EVOLUTION v5.5', 'WHISTLER EVOLUTION v6.0')
s = s.replace('궁극의 호가창 렌더링 + 하이브리드 이그니션 탑재',
              '실시간 진입신호 엔진 — 점수5분·OI/CVD1분·신호초단위 자동갱신')

io.open(OUT, 'w', encoding='utf-8').write(s)
print("written", len(s), "bytes")
