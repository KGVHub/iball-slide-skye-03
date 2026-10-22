import json
path="/home/kgvarunkanth/.claude/projects/-home-kgvarunkanth-claude/926eb76e-65af-4df5-a80e-08f6f0da8501.jsonl"
for l in open(path):
    try: d=json.loads(l)
    except: continue
    m=d.get("message") or {}
    r=m.get("role"); c=m.get("content")
    if isinstance(c,str):
        print("["+str(r)+"] "+c[:500]+"\n"); continue
    for b in c or []:
        t=b.get("type")
        if t=="text":
            print("["+str(r)+"] "+b["text"][:500]+"\n")
        elif t=="tool_use":
            print("["+str(r)+" TOOL "+str(b.get("name"))+"] "+json.dumps(b.get("input"))[:200]+"\n")
