#!/usr/bin/env python3
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
manifest_path=ROOT/'manifest.json'
files=[]
for p in sorted(ROOT.iterdir()):
    if not p.is_file() or p.name in {'manifest.json','SHA256SUMS.txt'}: continue
    b=p.read_bytes()
    files.append({'path':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest={'artifact':'slskdN PR #409 W75 independent primary semantic review','schemaVersion':1,'repository':'snapetech-org/slskdN','pullRequest':409,'window':'W75','candidateFreeInputManifestSha256':hashlib.sha256((ROOT.parent.parent/'candidate-free/input/manifest.json').read_bytes()).hexdigest(),'head':'99d6afbfb8cca4dccc018e72c01950bc304240db','tree':'f21cb5cde009ac35f5531ddc40612821aee6f471','sourceCount':25,'localeCount':12,'cellCount':300,'files':files}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
entries=[]
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name!='SHA256SUMS.txt': entries.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
(ROOT/'SHA256SUMS.txt').write_text('\n'.join(entries)+'\n',encoding='utf-8')
print(json.dumps({'result':'SEALED','files':len(files),'checksums':len(entries),'manifestSha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'checksumListSha256':hashlib.sha256((ROOT/'SHA256SUMS.txt').read_bytes()).hexdigest()}))
