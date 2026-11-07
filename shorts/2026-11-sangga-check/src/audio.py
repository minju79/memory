import numpy as np, wave
SR=44100; DUR=43.0; N=int(SR*DUR)
rng=np.random.default_rng(7)
bed=np.zeros(N); sfx=np.zeros(N)
def env_adsr(n,a,r):
    e=np.ones(n); ai=int(a*SR); ri=int(r*SR)
    if ai>0: e[:ai]=np.linspace(0,1,ai)
    if ri>0: e[-ri:]*=np.linspace(1,0,ri)
    return e
def add(buf,t0,sig):
    i=int(t0*SR); j=min(N,i+len(sig)); buf[i:j]+=sig[:j-i]
def lp(x,fc):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); X[f>fc]*=0; return np.fft.irfft(X,len(x))
def bp(x,lo,hi):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); X[(f<lo)|(f>hi)]*=0; return np.fft.irfft(X,len(x))
hz=lambda m:440*2**((m-69)/12)
# chord progression (midi roots) Am F C G, 4.8s each
prog=[(45,[57,60,64]),(41,[53,57,60]),(48,[55,60,64]),(43,[55,59,62])]
seg=4.8
t=np.arange(N)/SR
# pad
for k in range(int(np.ceil(DUR/seg))):
    root,ch=prog[k%4]; s=k*seg; n=int(seg*SR)+int(0.6*SR)
    tt=np.arange(n)/SR; sig=np.zeros(n)
    for m in ch:
        for det in (-0.12,0.12):
            sig+=np.sin(2*np.pi*hz(m+det)*tt)+0.25*np.sin(2*np.pi*2*hz(m+det)*tt)
    sig*=env_adsr(n,0.6,0.9)*0.035
    add(bed,s,sig)
# bass pulse (8ths) from 4.95 to 41.2
step=0.3
tp=4.95
while tp<41.2:
    k=int(tp//seg); root,_=prog[k%4]
    n=int(0.28*SR); tt=np.arange(n)/SR
    sig=(np.sin(2*np.pi*hz(root)*tt)+0.3*np.sin(2*np.pi*2*hz(root)*tt))*np.exp(-9*tt)*0.11
    add(bed,tp,sig); tp+=step
# soft kick on beats from 4.95
tp=4.95
while tp<41.2:
    n=int(0.25*SR); tt=np.arange(n)/SR
    f=55+60*np.exp(-30*tt); ph=2*np.pi*np.cumsum(f)/SR
    add(bed,tp,np.sin(ph)*np.exp(-14*tt)*0.18); tp+=0.6
# fade bed at end, lift-in at start
bed*=np.clip((DUR-t)/1.8,0,1)
# --- SFX ---
def boom(amp=0.9,dur=1.6):
    n=int(dur*SR); tt=np.arange(n)/SR; f=70*np.exp(-0.9*tt)+30; ph=2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)*np.exp(-2.6*tt)*amp
def thump():
    n=int(0.6*SR); tt=np.arange(n)/SR
    body=np.sin(2*np.pi*95*tt)*np.exp(-13*tt)
    nz=lp(rng.standard_normal(n),2500)*np.exp(-22*tt)*0.5
    return (body+nz)*0.75
def whoosh(dur=0.5,amp=0.22,lo=600,hi=7000):
    n=int(dur*SR); x=bp(rng.standard_normal(n),lo,hi); e=np.sin(np.pi*np.linspace(0,1,n))**2
    return x/np.max(np.abs(x))*e*amp
def ding(f=1320,amp=0.16,dec=7):
    n=int(0.6*SR); tt=np.arange(n)/SR
    return (np.sin(2*np.pi*f*tt)+0.4*np.sin(2*np.pi*f*2.01*tt))*np.exp(-dec*tt)*amp
def pop(f=1100,amp=0.10):
    n=int(0.12*SR); tt=np.arange(n)/SR
    return np.sin(2*np.pi*f*tt*(1+2*tt))*np.exp(-40*tt)*amp
add(sfx,0.0,boom())
add(sfx,2.97,thump())
add(sfx,6.12,whoosh(0.35,0.2,2000,9000))
for ts in [4.80,11.0,14.45,18.65,22.4,28.1,36.6]: add(sfx,ts,whoosh())
add(sfx,9.55,ding(988,0.15))
for i,ts in enumerate([12.05,12.45,12.85]): add(sfx,ts,ding([880,988,1175][i],0.13))
add(sfx,17.25,ding(740,0.15,6))
for i in range(10): add(sfx,19.95+i*0.17,pop(900+60*i,0.09))
for i,ts in enumerate([23.45,23.95,24.55,25.05]): add(sfx,ts,pop(700+80*i,0.10))
add(sfx,32.55,whoosh(0.3,0.18,1500,8000)); add(sfx,32.6,ding(1568,0.10,10))
add(sfx,34.3,ding(1175,0.14))
add(sfx,36.8,boom(0.5,1.4))
mix=bed+sfx
mix/=max(1e-9,np.max(np.abs(mix)))*1.12
st=np.stack([mix,mix],1)
w=wave.open('bed.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st*32767).astype('<i2').tobytes()); w.close()
print('ok')
