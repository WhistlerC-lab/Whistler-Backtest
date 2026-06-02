# -*- coding: utf-8 -*-
import re
p='index.html'
s=open(p,encoding='utf-8').read()
def rep(o,n,cnt=1):
    global s
    assert s.count(o)>=1, "NOT FOUND:\n"+o[:160]
    s=s.replace(o,n,cnt)

# ===== 4) 워크포워드(70/30) + 기대값 — 진화 루프 교체 =====
new_evo='''    const HOR = 36;
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
    }'''

old_evo_re=re.compile(r"    const HOR = 36; \n    log\(`\[3/3\].*?document\.getElementById\('autoBtn'\)\.disabled = false;\n    \}", re.S)
s2,ncnt=old_evo_re.subn(new_evo, s, count=1)
assert ncnt==1, "evolution block not replaced"
s=s2

# ===== 5) runLiveScan: 멀티-호라이즌 전달 + EV/필드 push =====
rep('    const oiChange = oiMap[sym] || 0;',
    '    const oi = oiMap[sym] || {short:0, mid:0};')
rep('    const f = calcFeatures(cs, cs.length-1, btcClose, BEST_WEIGHTS, fr, oiChange);',
    '    const f = calcFeatures(cs, cs.length-1, btcClose, BEST_WEIGHTS, fr, oi.short, oi.mid);')
rep('''      liveScanResults.push({ 
        sym: sym.replace('USDT',''), 
        raw: f.raw, 
        prob: prob, 
        cvdRatio: f.cvdRatio,
        funding: fr, 
        oiPct: oiChange,
        oiMsg: f.oiMsg,
        oiStatus: f.oiStatus,
        tp: tpPct, 
        sl: slPct 
      });''',
'''      const ev = prob * tpPct - (1 - prob) * slPct;   // 기대값 (손익비 반영)
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
      });''')
rep('''  document.getElementById('sortControl').value = 'prob_desc';
  sortConfig = { key: 'prob', dir: -1 };''',
'''  document.getElementById('sortControl').value = 'ev_desc';
  sortConfig = { key: 'ev', dir: -1 };''')

# ===== 6) performFastUpdate: 단기/중기 갱신 =====
rep('      if(oiMap[full] !== undefined) r.oiPct = oiMap[full];',
    '      if(oiMap[full] !== undefined) { r.oiShort = oiMap[full].short; r.oiMid = oiMap[full].mid; r.oiPct = oiMap[full].short; }')

open(p,'w',encoding='utf-8').write(s)
print("patch4 ok")
