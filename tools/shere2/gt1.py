"""Эталон для 1-NN: FEN всех досок первой книги (shere.js) по порядку [[DIAG]] -> work/gt1.json"""
import json, re, os, chess
src=open('../../shere.js').read(); d=json.loads(src[src.index('=')+1:].rstrip().rstrip(';'))
boards=json.load(open('../shere/work/boards.json'))
seq=[]
for p in sorted(int(f[1:4]) for f in os.listdir('../shere/txt') if re.fullmatch(r'p\d{3}\.txt',f)):
    
    real=[k for k,b in enumerate(boards.get(str(p),[])) if 480<=b[2]<=580]
    i=0
    for l in open(f'../shere/txt/p{p:03d}.txt'):
        if l.startswith('[[GAME]]') and '(продолжение)' in l: seq.append(None)
        if l.startswith('[[DIAG'): seq.append((p,real[i])); i+=1
fens=[]
for ch in d[0]['chapters']:
    roots,nodes=ch['roots'],ch['nodes']; cache={}
    def f(i):
        if i<0: return roots[-i-1]
        if i not in cache:
            b=chess.Board(f(nodes[i][0])); b.push_uci(nodes[i][1]); cache[i]=b.fen()
        return cache[i]
    for b in ch['intro']:
        if b['t']=='d': fens.append(f(b['n']).split()[0] if b.get('n') is not None else None)
print(len(seq),len(fens))
json.dump([[x[0],x[1],fn] for x,fn in zip(seq,fens) if x],open('work/gt1.json','w'))
