# -*- coding: utf-8 -*-
import re
p='index.html'
s=open(p,encoding='utf-8').read()
def rep(o,n,cnt=1):
    global s
    assert s.count(o)>=1, "NOT FOUND:\n"+o[:160]
    s=s.replace(o,n,cnt)

# ===== 1) getOIChangeMap → 멀티-호라이즌(15m 1회 → 1h·4h 파생) =====
rep('''      const res = await fetch(`${FAPI}/futures/data/openInterestHist?symbol=${sym}&period=1d&limit=2`);
      if(res.ok) {
        const data = await res.json();
        if(data && data.length >= 2) {
          const prev = +data[0].sumOpenInterestValue;
          const cur = +data[data.length-1].sumOpenInterestValue;
          map[sym] = prev ? (cur - prev) / prev : 0;
        }
      }''',
'''      const res = await fetch(`${FAPI}/futures/data/openInterestHist?symbol=${sym}&period=15m&limit=24`);
      if(res.ok) {
        const data = await res.json();
        if(data && data.length >= 5) {
          const val = data.map(d => +d.sumOpenInterestValue);
          const cur = val[val.length-1];
          const p1 = val[Math.max(0, val.length-1-4)];    // 약 1시간 전
          const p4 = val[Math.max(0, val.length-1-16)];   // 약 4시간 전
          map[sym] = { short: p1 ? (cur-p1)/p1 : 0, mid: p4 ? (cur-p4)/p4 : 0 };
        }
      }''')
rep('  log(`[백그라운드 수집] 24h 미결제약정 데이터 갱신 중... (속도 조절 적용)`);',
    '  log(`[백그라운드 수집] 멀티-호라이즌 OI(15m→1h·4h) 수집 중...`);')

# ===== 2) calcFeatures: 시그니처 + OI 블록 =====
rep('function calcFeatures(cs, i, btcClose, weights, currentFunding = 0, oiChangePct = 0){',
    'function calcFeatures(cs, i, btcClose, weights, currentFunding = 0, oiShort = 0, oiMid = 0){')
rep('''  if (oiChangePct !== 0) {
      if (ret24 > 0.02 && oiChangePct < -0.02) {
          breakout *= 0.5; mom *= 0.7; oiMsg = "📉 숏커버링"; oiStatus = "fake";
      } else if (ret24 > 0.02 && oiChangePct > 0.05) {
          trend = clamp(trend * 1.2, 0, 1); oiMsg = "🔥 찐상승"; oiStatus = "real";
      }
      if (currentFunding < -0.0005 && oiChangePct > 0.08) {
          mom = clamp(mom * 1.5, 0, 1); oiMsg = "🧨 슈퍼 스퀴즈"; oiStatus = "nuke";
      }''',
'''  if (oiShort !== 0 || oiMid !== 0) {
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
      }''')

# ===== 3) entryVerdict: 단기/중기 OI 반영 =====
rep('''  const cvd = r.cvdRatio;
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
  }''',
'''  const cvd = r.cvdRatio;
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
  }''')

open(p,'w',encoding='utf-8').write(s)
print("patch3 part A ok")
