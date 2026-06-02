# -*- coding: utf-8 -*-
p='index.html'
s=open(p,encoding='utf-8').read()
def rep(o,n,cnt=1):
    global s
    assert s.count(o)>=1, "NOT FOUND:\n"+o[:160]
    s=s.replace(o,n,cnt)

# helpers (앞에 추가)
rep('function change24(sym){',
'''function fmtPct(x){ if(x===undefined||x===null||x===0) return '-'; return (x>0?'+':'')+(x*100).toFixed(2)+'%'; }
function pctCls(x){ return x>0?'pos':(x<0?'neg':'mut'); }
function change24(sym){''')

# 카드: head 변수
rep('''    const probTxt = (r.prob*100).toFixed(1)+'%';
    const oiTxt = r.oiPct === 0 ? '-' : (r.oiPct > 0 ? '+' : '') + (r.oiPct*100).toFixed(2) + '%';
    const oiColor = r.oiPct > 0 ? 'pos' : (r.oiPct < 0 ? 'neg' : 'mut');
    const cvdPct = (r.cvdRatio*100).toFixed(1);
    const cvdColor = r.cvdRatio >= 0.5 ? 'var(--bull)' : 'var(--bear)';
    const cvdBar =''',
'''    const probTxt = (r.prob*100).toFixed(1)+'%';
    const oiSv = (r.oiShort!==undefined?r.oiShort:r.oiPct);
    const oiMv = r.oiMid;
    const evTxt = (r.ev!==undefined) ? ((r.ev>=0?'+':'')+(r.ev*100).toFixed(2)+'%') : '-';
    const cvdPct = (r.cvdRatio*100).toFixed(1);
    const cvdColor = r.cvdRatio >= 0.5 ? 'var(--bull)' : 'var(--bear)';
    const cvdBar =''')

# 카드: OI row → OI 1h/4h + EV row
rep('''      <div class="c-row">
        <span class="c-lbl">24h OI 증감</span> 
        <span class="c-val ${oiColor}">${oiTxt}</span>
      </div>
      <div class="c-row">
        <span class="c-lbl">현재 펀딩비</span> ''',
'''      <div class="c-row">
        <span class="c-lbl">OI 1h / 4h</span> 
        <span class="c-val"><span class="${pctCls(oiSv)}">${fmtPct(oiSv)}</span> <span style="color:var(--tx3)">/</span> <span class="${pctCls(oiMv)}">${fmtPct(oiMv)}</span></span>
      </div>
      <div class="c-row">
        <span class="c-lbl">기대값 (EV)</span> 
        <span class="c-val" style="color:${r.ev>=0?'var(--bull)':'var(--bear)'}; font-weight:800;">${evTxt}</span>
      </div>
      <div class="c-row">
        <span class="c-lbl">현재 펀딩비</span> ''')

# 목록: head 변수
rep('''    const probTxt = (r.prob*100).toFixed(1)+'%';
    const oiTxt = r.oiPct === 0 ? '-' : (r.oiPct > 0 ? '+' : '') + (r.oiPct*100).toFixed(2) + '%';
    const oiColor = r.oiPct > 0 ? 'var(--bull)' : (r.oiPct < 0 ? 'var(--bear)' : 'var(--tx3)');
    const cvdPct = (r.cvdRatio*100).toFixed(1);''',
'''    const probTxt = (r.prob*100).toFixed(1)+'%';
    const oiSv = (r.oiShort!==undefined?r.oiShort:r.oiPct);
    const oiMv = r.oiMid;
    const evTxt = (r.ev!==undefined) ? ((r.ev>=0?'+':'')+(r.ev*100).toFixed(2)+'%') : '-';
    const cvdPct = (r.cvdRatio*100).toFixed(1);''')

# 목록: row 교체
rep('''    rows += `<tr class="lrow" id="card-${r.sym}">
      <td><span class="l-sym">${r.sym}</span> ${chgHtml(r.sym)}</td>
      <td><span class="l-price" id="price-${r.sym}">${fmtPrice(lastPrices[r.sym])}</span></td>
      <td style="color:${r.raw>=60?'var(--bull)':'var(--tx)'};font-weight:800;">${r.raw}</td>
      <td style="color:var(--purp);font-weight:700;">${probTxt}</td>
      <td style="color:${cvdColor};font-weight:700;">${cvdPct}%</td>
      <td style="color:${oiColor};font-weight:700;">${oiTxt}</td>
      <td style="color:${r.funding<0?'var(--bear)':'var(--tx2)'};">${(r.funding*100).toFixed(4)}%</td>
      <td><span style="color:var(--bull)">+${(r.tp*100).toFixed(1)}%</span> / <span style="color:var(--bear)">-${(r.sl*100).toFixed(1)}%</span></td>
      <td style="text-align:left;">${pill}</td>
    </tr>`;''',
'''    rows += `<tr class="lrow" id="card-${r.sym}">
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
    </tr>`;''')

# 목록: 헤더
rep('''        <th>종목</th><th>가격</th><th>진화점수</th><th>성공률</th><th>CVD</th>
        <th>24h OI</th><th>펀딩비</th><th>TP / SL</th><th>상태</th>''',
'''        <th>종목</th><th>가격</th><th>진화점수</th><th>성공률</th><th>기대값</th><th>CVD</th>
        <th>OI 1h</th><th>OI 4h</th><th>펀딩비</th><th>TP / SL</th><th>상태</th>''')

# 테이블 최소폭 확대 (열 추가분)
rep('table.scan-table { width:100%; min-width:720px; border-collapse:collapse; font-size:13px; }',
    'table.scan-table { width:100%; min-width:880px; border-collapse:collapse; font-size:13px; }')

# 정렬 옵션: EV 추가 + 기본값 EV + OI 1h/4h 분리
rep('''          <option value="prob_desc" selected>예상 성공률 높은순 ▼</option>
          <option value="raw_desc">진화 점수 높은순 ▼</option>
          <option value="cvdRatio_desc">CVD 매수 우위순 ▼</option>
          <option value="oiPct_desc">OI 급증순 (자금유입) ▼</option>
          <option value="funding_asc">펀딩비 낮은순 (음수/스퀴즈) ▲</option>''',
'''          <option value="ev_desc" selected>기대값(EV) 높은순 ▼</option>
          <option value="prob_desc">예상 성공률 높은순 ▼</option>
          <option value="raw_desc">진화 점수 높은순 ▼</option>
          <option value="cvdRatio_desc">CVD 매수 우위순 ▼</option>
          <option value="oiPct_desc">OI 1h 급증순 (신규유입) ▼</option>
          <option value="oiMid_desc">OI 4h 유입순 (지속성) ▼</option>
          <option value="funding_asc">펀딩비 낮은순 (음수/스퀴즈) ▲</option>''')

open(p,'w',encoding='utf-8').write(s)
print("patch5 ok", len(s))
