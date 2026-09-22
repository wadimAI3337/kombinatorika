import os
import json, re, sys
from collections import Counter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from lineparse import norm, pick_move
S=os.environ.get('KON1_WORK','work')
F=json.load(open(S+'/fens.json')); A=json.load(open(S+'/answers_fixed.json'))
out=[]; susp=[]
for b in range(240):
    a=A[b]; fen=F[b]['fen']; s=fen.split()[1]; x=norm(a['text'])
    pick,line,cands=pick_move(fen,s,x)
    rec=dict(n=b+1,t=a['title'],f=fen,s=s,v=1,pts=a['pts'],tt=a['test'],pt=a['part'],x=x,m=[])
    for i,mv in enumerate(line):
        st=mv['end']; e=line[i+1]['start'] if i+1<len(line) else len(x)
        head=x[st:st+10]; evm=re.match(r'^[\s!?+#.,;:]*(\+-|-\+|[±∓∞=])',head); ev=''
        if evm:
            ev={'+-':'+−','-+':'−+'}.get(evm.group(1),evm.group(1)); st+=len(evm.group(0))
        else: st+=len(re.match(r'^[\s!?+#.,;:]*',head).group(0))
        rec['m'].append([mv['uci'],mv['san'],mv['fen'],[min(st,e),e],ev])
    bang=[c['san'].rstrip('+#') for c in cands if '!' in c['ann']]
    if rec['m'] and bang and rec['m'][0][1].rstrip('+#') not in bang: susp.append((b+1,rec['m'][0][1],bang))
    out.append(rec)
print('без решения:',[o['n'] for o in out if not o['m']])
print('длина (ходов решающей стороны):',sorted(Counter((len(o['m'])+1)//2 for o in out).items()))
print('выбран не ход с «!»:',susp)
json.dump(out,open(S+'/kon1.json','w'),ensure_ascii=False,separators=(',',':'))
print(len(json.dumps(out,ensure_ascii=False,separators=(',',':'))))
