import os
import json, re, chess, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from lineparse import norm, do_move, SAN_CORE
S=os.environ.get('KON1_WORK','work')
F=json.load(open(S+'/fens.json')); A=json.load(open(S+'/answers.json'))
bad=[]
for b in range(240):
    fen=F[b]['fen']; s=fen.split()[1]; t=norm(A[b]['text'])
    rx=re.compile(r'(?<![\d.])1' + (r'\.(?!\.)' if s=='w' else r'\.\.\.') + '(' + SAN_CORE + ')')
    wrong=re.compile(r'(?<![\d.])1' + (r'\.\.\.' if s=='w' else r'\.(?!\.)') + '(' + SAN_CORE + ')')
    for m in rx.finditer(t):
        if not do_move(chess.Board(fen),m.group(1)): bad.append((b,'illegal',m.group(1)))
    # первый ход не той стороны — признак перепутанной очереди
    ws=[m.group(1) for m in wrong.finditer(t)]
    if ws and not rx.search(t): bad.append((b,'side?',ws[:3]))
print(len(bad)); [print(x, F[x[0]]['fen']) for x in bad]
