import os
import re, json, glob
S=os.environ.get('KON1_WORK','work')
buf=''
for p in range(52,129):
    t=open(f'{S}/sol_txt/p{p:03d}.txt').read().strip()
    t=re.sub(r'^\[\[CONT\]\]\s*','',t)
    # склейка переноса на стыке страниц
    if re.search(r'[а-яА-Яa-z]-$',buf) and re.match(r'[а-я]',t): buf=buf[:-1]+t
    else: buf+=('\n' if buf else '')+t
toks=re.split(r'(\[\[(?:PART|TEST|N) \d+\]\])',buf)
part=test=None; out=[]; cur=None
for tk in toks:
    m=re.fullmatch(r'\[\[(PART|TEST|N) (\d+)\]\]',tk)
    if m:
        k,v=m.group(1),int(m.group(2))
        if k=='PART': part=v
        elif k=='TEST': test=v
        else: cur={'part':part,'test':test,'i':v,'raw':''}; out.append(cur)
    elif cur is not None: cur['raw']+=tk
for o in out:
    raw=' '.join(o['raw'].split())
    # заголовок — до первой точки после года/города: берём первую «строку» исходника
    first,_,rest=o['raw'].strip().partition('\n')
    o['title']=first.strip(); o['text']=' '.join(rest.split())
    pm=re.findall(r'\((\d+) очк[а-я]*\)',raw); o['pts']=int(pm[-1]) if pm else None
    o.pop('raw')
keys=[(o['part'],o['test'],o['i']) for o in out]
exp=[(p,t,i) for p in (1,2) for t in range(1,11) for i in range(1,13)]
print(len(out), keys==exp)
if keys!=exp:
    import itertools
    for a,b in itertools.zip_longest(keys,exp):
        if a!=b: print('first mismatch',a,b); break
print([ (o['part'],o['test'],o['i']) for o in out if not o['pts']])
json.dump(out,open(f'{S}/answers.json','w'),ensure_ascii=False,indent=0)
print(out[0]['title'],'|',out[0]['text'][:200])
