import os, sys; HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from style import plt, save
import numpy as np, pandas as pd, json
from matplotlib.patches import PathPatch
from matplotlib.path import Path
def split(s): return s.fillna("").str.split(";").explode().str.strip().replace("",pd.NA).dropna()
def load():
    d=pd.read_csv(os.path.join(HERE,"..","extraction","coded_studies.csv"),dtype=str,keep_default_na=False)
    d=d.rename(columns={"rec_id":"rec","decision":"dec","exclusion_reason":"reason","edu_level":"level","model_access":"access","adaptation":"adapt","uq_methods":"uq","actions":"action","human_role":"human","eval_technical":"etech","eval_human":"ehuman","eval_learning":"learn","fairness_analysis":"fair","key_finding":"finding","quality_0_8":"qual"})
    m=pd.read_csv(os.path.join(HERE,"..","fulltext","reports_sought.csv"),dtype=str)
    d=d.drop(columns=["title","year","doi"]).merge(m,left_on="rec",right_on="rec_id",how="left")
    d["source"]=d.rec.str[0].map({"R":"database","S":"citation"}); return d
OUT=os.path.join(HERE,"..","figures")+os.sep
d=load(); inc=d[d.dec=="include"].copy()
TASK=[("SCO","Scoring and grading"),("TQA","Tutoring and QA"),("FB","Feedback"),("GEN","Item / content generation"),
      ("USE","Student use of general LLMs"),("LA","Learning analytics / coding"),("ADV","Advising / administration"),("DIAG","Error diagnosis")]
UQ=[("VC","Verbalised\nconfidence"),("TP","Token\nprobability"),("SC","Sampling\nconsistency"),("EN","Ensemble /\nmulti-LLM"),
    ("CP","Conformal"),("CAL","Calibration /\nlearned"),("RV","Retrieval /\nverification"),("HR","Human or\nreference only"),("UT","User trust /\nreliance")]
def ptype(r):
    v=str(r.venue).lower(); t=str(r.type).lower()
    if any(k in v for k in ["arxiv","research square","zenodo","ssrn","preprint","osf","edarxiv","psyarxiv","techrxiv","medrxiv"]) or t in ("preprint","dataset"): return "Preprint"
    if "conference" in t or "meeting" in t or any(k in v for k in ["conference","proceedings","symposium","workshop"]): return "Conference"
    if t=="dissertation": return "Other"
    return "Journal"
inc["ptype"]=inc.apply(ptype,axis=1)
# --- 1. trends
yrs=[str(y) for y in range(2022,2027)]
ct=pd.crosstab(inc.year,inc.ptype).reindex(yrs,fill_value=0)
cols={"Journal":"#2F6F9F","Conference":"#3B8C7A","Preprint":"#B3742E","Other":"#9AA5B1"}
fig,ax=plt.subplots(figsize=(3.4,1.75)); b=np.zeros(len(yrs))
for k in ["Journal","Conference","Preprint","Other"]:
    if k in ct: ax.bar(yrs,ct[k],bottom=b,color=cols[k],width=0.62,label=k,lw=0); b+=ct[k].values
for i,v in enumerate(b): ax.text(i,v+1.5,int(v),ha="center",va="bottom",fontsize=6.5)
ax.set_ylabel("Included studies"); ax.set_ylim(0,max(b)*1.18); ax.grid(axis="x",visible=False)
ax.legend(ncol=2,loc="upper left",handlelength=1,columnspacing=0.8); ax.set_xticks(range(len(yrs))); ax.set_xticklabels(yrs[:-1]+["2026\n(to Oct.)"])
save(fig,OUT+"fig_trends")
# --- 2. heatmap task x uq
rows=[]
for _,r in inc.iterrows():
    for u in [x.strip() for x in r.uq.split(";") if x.strip()]: rows.append((r.task,u))
h=pd.crosstab(pd.Series([a for a,_ in rows],name="t"),pd.Series([b for _,b in rows],name="u"))
h=h.reindex(index=[t for t,_ in TASK],columns=[u for u,_ in UQ],fill_value=0)
tn=inc.task.value_counts()
fig,ax=plt.subplots(figsize=(3.45,2.35))
im=ax.imshow(h.values,cmap="Blues",aspect="auto",vmin=0,vmax=h.values.max()*1.05)
for i in range(h.shape[0]):
    for j in range(h.shape[1]):
        v=h.values[i,j]
        if v: ax.text(j,i,v,ha="center",va="center",fontsize=6.3,color="white" if v>h.values.max()*0.55 else "#1d1d1d")
ax.set_xticks(range(len(UQ))); ax.set_xticklabels([l for _,l in UQ],fontsize=5.5,rotation=90)
ax.set_yticks(range(len(TASK))); ax.set_yticklabels([f"{l} ({tn.get(t,0)})" for t,l in TASK],fontsize=6.2)
ax.grid(False); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.axvline(5.5,color="#7A8899",lw=0.6,ls=(0,(2,2))); ax.axvline(6.5,color="#7A8899",lw=0.6,ls=(0,(2,2)))
ax.text(2.5,-0.9,"model-side signals",ha="center",fontsize=6,color="#3B5B7F",style="italic")
ax.text(7.0,-0.9,"external / human",ha="center",fontsize=6,color="#3B5B7F",style="italic")
save(fig,OUT+"fig_heatmap")
# --- 3. alluvial task -> uq family -> action
fam={"VC":"Model-side signal","TP":"Model-side signal","SC":"Model-side signal","EN":"Model-side signal","CP":"Model-side signal","CAL":"Model-side signal",
     "RV":"Retrieval / verification","HR":"Human or reference check only","UT":"User trust / reliance"}
def famof(s):
    c=[x.strip() for x in s.split(";") if x.strip()]
    order=["Model-side signal","Retrieval / verification","User trust / reliance","Human or reference check only"]
    f=[fam[x] for x in c]; return next(o for o in order if o in f)
def actof(s):
    c=[x.strip() for x in s.split(";") if x.strip()]
    for k,l in [("DEFER","Defer / selective automation"),("SEL","Defer / selective automation"),("ABST","Abstain"),("ASK","Ask / warn"),("WARN","Ask / warn"),
                ("DISP","Show to user"),("VER","Human or automatic verification"),("NONE","Measured only")]:
        if k in c: return l
inc["fam"]=inc.uq.map(famof); inc["act"]=inc.action.map(actof)
tg={"SCO":"Scoring and grading","TQA":"Tutoring and QA","FB":"Feedback","GEN":"Generation","USE":"Student use","LA":"Analytics / diagnosis","DIAG":"Analytics / diagnosis","ADV":"Advising / admin"}
inc["tg"]=inc.task.map(tg)
L0=["Scoring and grading","Tutoring and QA","Feedback","Generation","Student use","Analytics / diagnosis","Advising / admin"]
L1=["Model-side signal","Retrieval / verification","Human or reference check only","User trust / reliance"]
L2=["Defer / selective automation","Abstain","Show to user","Ask / warn","Human or automatic verification","Measured only"]
C0="#2F6F9F"; C1={"Model-side signal":"#3B8C7A","Retrieval / verification":"#6FA8A0","Human or reference check only":"#9AA5B1","User trust / reliance":"#8A4F8F"}
N=len(inc); gap=3.0
def layout(labels,counts):
    y=0; pos={}
    tot=sum(counts.get(l,0) for l in labels)+gap*(len(labels)-1)
    for l in labels:
        c=counts.get(l,0); pos[l]=[y,y+c]; y+=c+gap
    return pos,tot
p0,t0=layout(L0,inc.tg.value_counts()); p1,t1=layout(L1,inc.fam.value_counts()); p2,t2=layout(L2,inc.act.value_counts())
H=max(t0,t1,t2)
def flip(p,t): off=(H-t)/2; return {k:[H-(a+off),H-(b+off)] for k,(a,b) in p.items()}
p0,p1,p2=flip(p0,t0),flip(p1,t1),flip(p2,t2)
X=[0,1,2]; W=0.06
fig,ax=plt.subplots(figsize=(7.0,2.9)); ax.axis("off")
def band(xa,ya,xb,yb,color,alpha=0.42):
    (a1,a2),(b1,b2)=ya,yb; xm=(xa+xb)/2
    verts=[(xa,a1),(xm,a1),(xm,b1),(xb,b1),(xb,b2),(xm,b2),(xm,a2),(xa,a2),(xa,a1)]
    codes=[Path.MOVETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.LINETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts,codes),fc=color,ec="none",alpha=alpha))
cur0={k:v[0] for k,v in p0.items()}; cur1a={k:v[0] for k,v in p1.items()}
for a in L0:
    for b in L1:
        n=((inc.tg==a)&(inc.fam==b)).sum()
        if n: band(X[0]+W/2,(cur0[a],cur0[a]-n),X[1]-W/2,(cur1a[b],cur1a[b]-n),C1[b]); cur0[a]-=n; cur1a[b]-=n
cur1b={k:v[0] for k,v in p1.items()}; cur2={k:v[0] for k,v in p2.items()}
for b in L1:
    for c in L2:
        n=((inc.fam==b)&(inc.act==c)).sum()
        if n: band(X[1]+W/2,(cur1b[b],cur1b[b]-n),X[2]-W/2,(cur2[c],cur2[c]-n),C1[b]); cur1b[b]-=n; cur2[c]-=n
def nodes(p,x,col,side):
    for k,(a,b) in p.items():
        if a==b: continue
        c=col[k] if isinstance(col,dict) else col
        ax.add_patch(plt.Rectangle((x-W/2,b),W,a-b,fc=c,ec="none"))
        ax.text(x+(W/2+0.02)*side,(a+b)/2,f"{k} ({int(a-b)})",ha="left" if side>0 else "right",va="center",fontsize=6.4,
                bbox=dict(boxstyle="round,pad=0.15",fc="white",ec="none",alpha=0.85) if x==1 else None)
nodes(p0,X[0],C0,-1); nodes(p1,X[1],C1,1); nodes(p2,X[2],"#B3742E",1)
for x,t in zip(X,["Educational task (RQ1)","Uncertainty signal (RQ2)","Action on uncertainty (RQ3)"]):
    ax.text(x,H+4,t,ha="center",fontsize=7,fontweight="bold")
ax.set_xlim(-0.55,2.62); ax.set_ylim(-2,H+8)
save(fig,OUT+"fig_flow")
# --- 4. evidence
tech=split(inc.etech).value_counts(); hum=split(inc.ehuman).value_counts()
TL=[("AGR","Agreement (kappa/QWK/ICC)"),("ACC","Accuracy / error"),("HALL","Hallucination / error rate"),("CALIB","Calibration (ECE/Brier)"),
    ("ROB","Robustness / adversarial"),("SELR","Coverage-risk / selective"),("DISC","Discrimination (AUROC)")]
HL=[("PERCEPTION","Perceptions"),("RELIANCE","Reliance behaviour"),("TRUST","Trust"),("WORKLOAD","Workload / time")]
fig,axs=plt.subplots(1,2,figsize=(7.0,2.05),gridspec_kw={"width_ratios":[1.25,1]})
ax=axs[0]; lab=[l for _,l in TL]+[""]+[l for _,l in HL]; val=[tech.get(k,0) for k,_ in TL]+[0]+[hum.get(k,0) for k,_ in HL]
colr=["#2F6F9F"]*len(TL)+["w"]+["#8A4F8F"]*len(HL)
y=np.arange(len(lab))[::-1]; ax.barh(y,val,color=colr,height=0.68)
for yi,v in zip(y,val):
    if v: ax.text(v+0.8,yi,f"{v} ({v/N*100:.0f}%)",va="center",fontsize=6)
ax.set_yticks(y); ax.set_yticklabels(lab,fontsize=6.3); ax.grid(axis="y",visible=False); ax.set_xlabel("Studies (multiple codes possible)")
ax.set_xlim(0,max(val)*1.3); ax.set_title("(a) Evaluation measures (technical, human)",loc="left",fontsize=7)
ax=axs[1]; q=inc[inc.basis=="full text"].qual.astype(int).value_counts().reindex(range(0,9),fill_value=0)
ax.bar(q.index,q.values,color=["#C98A8A"]*4+["#9AA5B1"]*2+["#3B8C7A"]*3,width=0.7)
for i,v in q.items():
    if v: ax.text(i,v+0.6,v,ha="center",fontsize=6)
ax.set_xticks(range(0,9)); ax.set_xlabel("Quality score (0-8)"); ax.set_ylabel("Studies"); ax.grid(axis="x",visible=False)
ax.set_title("(b) Quality of studies coded from full text",loc="left",fontsize=7)
fig.tight_layout(w_pad=1.5); save(fig,OUT+"fig_evidence")
# --- numbers
print("figures written to", OUT)
