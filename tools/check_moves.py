"""Проверка книг Юсупова после сборки (запуск из корня репозитория: python3 tools/check_moves.py).
1) каждый кликабельный ход текста совпадает с ходом на доске (иначе — привязан не к той позиции);
2) у каждого упражнения есть решение на доске, в главе 12 упражнений и таблица очков."""
import json,re,sys
from collections import Counter
src=open('yus.js').read(); data=json.loads(src[src.index('=')+1:].rstrip().rstrip(';'))
def norm(s):
    s=s.replace("0-0-0","O-O-O").replace("0-0","O-O"); s=re.sub(r"^\d*\s*(\.\.\.|…|\.)?\s*","",s); s=s.replace(":","x")
    s=re.sub(r"[+#!?]","",s); s=s.replace('=','')
    return s
bad=Counter(); tot=0; ex=[]
for bk in data:
  for ch in bk['chapters']:
    nodes=ch['nodes']
    def walk(blocks,where):
      global tot
      for b in blocks:
        for seg in b.get('s') or []:
          if isinstance(seg,dict) and 'm' in seg and not seg.get('w'):
            tot+=1
            t=norm(seg['s']); san=norm(nodes[seg['m']][2])
            if re.fullmatch(r"[a-h][1-8]-[a-h][1-8]",t): continue
            ok = t==san or (('x' not in t) and t==san.replace('x','')) or t.replace('x','')==san.replace('x','') and len(t)>=len(san)-1
            if not ok:
                # короткая пешечная «ed»
                if re.fullmatch(r"[a-h][a-h]",t) and san[0]==t[0] and san[2]==t[1]: continue
                # лишнее уточнение («Nbd7» vs «Nd7»)
                if re.sub(r"^([KQRBN])[a-h1-8]",r"\1",t)==san.replace('x','').replace('x',''): continue
                bad[bk['id']]+=1; ex.append((bk['id'],ch['n'],where,seg['s'],nodes[seg['m']][2]))
    walk(ch['intro'],'intro')
    for e in ch['ex']: walk(e['a'],e['n'])
print('checked',tot,'mismatch',dict(bad))
for x in ex[:80]: print(x)

for bk in data:
    probs=[(ch['n'],e['n']) for ch in bk['chapters'] for e in ch['ex'] if not e['main']]
    print(bk['id'], 'упражнений', sum(len(ch['ex']) for ch in bk['chapters']), 'без решения', probs,
          'без очков', [ch['n'] for ch in bk['chapters'] if not ch['score'] and not ch.get('final')])
