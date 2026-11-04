#!/usr/bin/env python3
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
files=[]
for p in sorted(ROOT.iterdir()):
    if not p.is_file() or p.name in {"manifest.json","SHA256SUMS.txt"}: continue
    b=p.read_bytes(); files.append({"path":p.name,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
summary=json.loads((ROOT/"summary.json").read_text())
manifest={"artifact":"slskdN PR #409 W76 independent primary semantic review","schemaVersion":1,
"repository":"snapetech-org/slskdN","pullRequest":409,"window":"W76",
"candidateFreeInputManifestSha256":summary["candidateFreeInputManifestSha256"],
"head":"674156749ee86021ef91d896b1824be62cff9a93","tree":"86483dbf9227130cade6a3f4c9dc9ef5cf232450",
"sourceCount":25,"localeCount":12,"cellCount":300,"dispositions":summary["dispositions"],
"proposalCount":summary["proposedTargetCount"],"textFreeHoldCount":summary["holds"],
"blindReviewUsed":False,"crossReviewUsed":False,"nativeSpeakerSignoff":False,"browserReview":False,"files":files}
(ROOT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
entries=[]
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name!="SHA256SUMS.txt": entries.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
(ROOT/"SHA256SUMS.txt").write_text("\n".join(entries)+"\n",encoding="utf-8")
print(json.dumps({"result":"SEALED","files":len(files),"checksums":len(entries),
"manifestSha256":hashlib.sha256((ROOT/"manifest.json").read_bytes()).hexdigest(),
"checksumListSha256":hashlib.sha256((ROOT/"SHA256SUMS.txt").read_bytes()).hexdigest()}))

