import json,sys
for f in sys.argv[1:]:
    d=json.load(open(f,encoding='utf-8'))
    print("=====",f, {k:v for k,v in d.items() if k!='items'})
    items=d['items']
    for k,i in sorted(items.items(), key=lambda kv:(kv[1].get('type')!='branch', kv[1].get('branchId',0), kv[0])):
        extra={x:i[x] for x in i if x not in ('type','content','one','two','side')}
        c=(i.get('content') or '').replace('\n','\\n')
        print(f"  {k:>4} {i['type']:<11} one={i.get('one','')!s:<4} two={i.get('two','')!s:<4} side={i.get('side','')!s:<3} {extra} | {c}")
