# -*- coding: utf-8 -*-
p='index.html'
s=open(p,encoding='utf-8').read()
def rep(o,n,cnt=1):
    global s
    assert s.count(o)>=1, "NOT FOUND:\n"+o[:200]
    s=s.replace(o,n,cnt)

# ===== entryVerdict → 점수제/등급제 =====
old_ev='''  const cvd = r.cvdRatio;
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
}'''
new_ev='''  const cvd = r.cvdRatio;
  const oiS = (r.oiShort !== undefined ? r.oiShort : r.oiPct) || 0;  // 단기(1h)
  const oiM = (r.oiMid !== undefined ? r.oiMid : 0) || 0;            // 중기(4h)
  const fund = r.funding;
  const live = lastPrices[r.sym], base = scanEntryPrice[r.sym];
  const drift = (live && base) ? (live - base) / base : 0;

  // ── 1) 회피(롱 금지) 우선 판정 ──
  const avoid = (r.oiStatus === 'fake') ||
                (cvd < 0.46 && oiS < -0.02) ||
                (oiS < -0.015 && oiM < -0.02);
  if (avoid) {
    const rs = [];
    if (r.oiStatus === 'fake') rs.push('숏커버/가짜');
    if (cvd < 0.46) rs.push('매도우위');
    if (oiS < 0 && oiM < 0) rs.push('자금이탈');
    return { dir:'short', tier:'avoid', score:0, liveScore, reasons:rs };
  }
  // 과확장(스캔 후 +5%↑)이면 추격 위험 → 관망
  if (drift >= 0.05) return { dir:null, tier:null, score:0, liveScore, reasons:['과확장'] };

  // ── 2) 롱 점수제(가점 합산, 단일 조건 미달로 탈락시키지 않음) ──
  let score = 0; const reasons = [];
  if (liveScore >= 70) score += 3;
  else if (liveScore >= 62) score += 2;
  else if (liveScore >= 55) score += 1;

  if (r.prob >= 0.55) score += 1.5;
  else if (r.prob >= 0.5) score += 1;

  if (cvd >= 0.55) { score += 1.5; reasons.push('CVD강매수'); }
  else if (cvd >= 0.50) { score += 1; }
  else if (cvd >= 0.48) { score += 0.5; reasons.push('CVD중립'); }   // 49%대도 일부 인정

  if (oiS > 0 && oiM > 0) { score += 2; reasons.push('OI지속유입'); }
  else if (oiS > 0) { score += 1; reasons.push('OI초기유입'); }

  if (r.oiStatus === 'nuke') { score += 2; reasons.push('슈퍼스퀴즈'); }
  else if (r.oiStatus === 'real') { score += 1; reasons.push('찐상승'); }

  if (fund < -0.0003) { score += 0.5; reasons.push('숏스퀴즈'); }
  if (drift > 0 && drift < 0.015) reasons.push('상승초입');

  // ── 3) 등급 결정 (OI 신규유입은 롱의 최소 전제) ──
  let dir = null, tier = null;
  if (oiS > 0) {
    if (score >= 5)      { dir='long'; tier='strong'; }   // 🎯 강한 진입
    else if (score >= 3) { dir='long'; tier='watch';  }   // 👀 관찰 진입
  }
  return { dir, tier, score: Math.round(score*10)/10, liveScore, reasons };
}'''
rep(old_ev,new_ev)

# ===== evaluateSignals → 강/관찰/회피 분리 + 강한 신호만 토스트 =====
old_es='''function evaluateSignals() {
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
}'''
new_es='''function evaluateSignals() {
  if (!liveScanResults.length) return;
  const now = Date.now();
  const strong = [], watch = [], shorts = [];

  for (const r of liveScanResults) {
    const v = entryVerdict(r);
    r._liveScore = v.liveScore;
    r._sigDir = v.dir;
    r._sigTier = v.tier;
    const card = document.getElementById(`card-${r.sym}`);
    if (card) {
      card.classList.remove('signal-long','signal-short','signal-watch');
      if (v.tier === 'strong') card.classList.add('signal-long');
      else if (v.tier === 'watch') card.classList.add('signal-watch');
      else if (v.dir === 'short') card.classList.add('signal-short');
    }
    if (v.dir === 'long') {
      (v.tier === 'strong' ? strong : watch).push({r, v});
      if (v.tier === 'strong') {
        const prev = activeSignals[r.sym];
        if (!prev || prev.dir !== 'long' || now - prev.ts > 300000) {
          fireToast(r, v, 'long');
          activeSignals[r.sym] = { dir: 'long', ts: now };
        }
      }
    } else if (v.dir === 'short') {
      shorts.push({r, v});
      activeSignals[r.sym] = { dir: 'short', ts: now };
    } else {
      delete activeSignals[r.sym];
    }
  }
  renderSignalPanel(strong, watch, shorts);
}'''
rep(old_es,new_es)

# ===== renderSignalPanel → 구역 분리 =====
old_rp='''function renderSignalPanel(longs, shorts) {
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
}'''
new_rp='''function renderSignalPanel(strong, watch, shorts) {
  const panel = document.getElementById('signalPanel');
  const list = document.getElementById('sigList');
  if (!panel || !list) return;
  strong.sort((a,b) => b.v.score - a.v.score);
  watch.sort((a,b) => b.v.score - a.v.score);
  shorts.sort((a,b) => a.r.sym.localeCompare(b.r.sym));

  const go = sym => `document.getElementById('card-${sym}')?.scrollIntoView({behavior:'smooth',block:'center'})`;
  const longChip = (r, v, cls) => {
    const icon = cls === 'strong' ? '🎯' : '👀';
    return `<span class="sig-chip ${cls}" onclick="${go(r.sym)}">${icon} <span class="s-sym">${r.sym}</span> ${v.score}점·성공률 ${(r.prob*100).toFixed(0)}%${cls==='strong'?` · TP+${(r.tp*100).toFixed(1)}%`:''}${v.reasons.length?` · ${v.reasons.slice(0,2).join(' ')}`:''}</span>`;
  };

  list.style.display = 'block';
  let h = '';

  // ── 진입 추천 구역 ──
  h += `<div class="sig-section">`;
  h += `<div class="sig-sec-title" style="color:var(--gold)">🎯 진입 추천 &nbsp;—&nbsp; 강한 ${strong.length} · 관찰 ${watch.length}</div>`;
  if (strong.length + watch.length === 0) {
    h += `<span class="sig-empty">현재 진입 타점 없음 — 모니터링 중...</span>`;
  } else {
    h += `<div class="sig-list">`;
    for (const {r, v} of strong) h += longChip(r, v, 'strong');
    for (const {r, v} of watch)  h += longChip(r, v, 'watch');
    h += `</div>`;
  }
  h += `</div>`;

  // ── 회피 주의 구역 ──
  if (shorts.length) {
    h += `<div class="sig-section">`;
    h += `<div class="sig-sec-title" style="color:var(--bear)">⚠ 회피 주의 &nbsp;—&nbsp; ${shorts.length}종목 (롱 진입 금지)</div>`;
    h += `<div class="sig-list">`;
    for (const {r, v} of shorts) {
      h += `<span class="sig-chip short" onclick="${go(r.sym)}">⚠ <span class="s-sym">${r.sym}</span> ${v.reasons[0]||'회피'}</span>`;
    }
    h += `</div></div>`;
  }

  list.innerHTML = h;
  panel.classList.add('active');
}'''
rep(old_rp,new_rp)

# ===== applySignalClasses: tier 반영 =====
old_asc='''function applySignalClasses(){
  for(const r of liveScanResults){
    const el = document.getElementById(`card-${r.sym}`);
    if(!el) continue;
    el.classList.remove('signal-long','signal-short');
    if(r._sigDir==='long') el.classList.add('signal-long');
    else if(r._sigDir==='short') el.classList.add('signal-short');
  }
}'''
new_asc='''function applySignalClasses(){
  for(const r of liveScanResults){
    const el = document.getElementById(`card-${r.sym}`);
    if(!el) continue;
    el.classList.remove('signal-long','signal-short','signal-watch');
    if(r._sigTier==='strong') el.classList.add('signal-long');
    else if(r._sigTier==='watch') el.classList.add('signal-watch');
    else if(r._sigDir==='short') el.classList.add('signal-short');
  }
}'''
rep(old_asc,new_asc)

# ===== CSS: 관찰 등급 + 구역 + 칩 스타일 =====
rep('.live-dot { display:inline-block;',
'''.c-card.signal-watch { border-color: var(--cyan) !important; box-shadow: 0 0 0 1px var(--cyan), 0 0 14px rgba(52,214,255,0.25); }
.c-card.signal-watch::before { content:"👀 관찰"; position:absolute; top:0; right:0; background:var(--cyan); color:#001018; font-size:10px; font-weight:900; padding:3px 8px; border-radius:0 8px 0 8px; z-index:5; }
.lrow.signal-watch td:first-child { box-shadow: inset 4px 0 0 var(--cyan); }
.lrow.signal-watch .l-sym::after { content:" 👀"; }
.sig-section { margin-bottom:10px; }
.sig-section:last-child { margin-bottom:0; }
.sig-sec-title { font-size:11px; font-weight:800; letter-spacing:.03em; margin:2px 0 7px; }
.sig-chip.watch { background:rgba(52,214,255,0.10); border-color:var(--cyan); color:var(--cyan); }
.sig-chip.strong { background:rgba(255,194,75,0.14); border-color:var(--gold); color:var(--gold); }
.live-dot { display:inline-block;''')

open(p,'w',encoding='utf-8').write(s)
print("patch6 ok", len(s))
