import numpy as np, wave
SR=44100; DUR=19.0; N=int(SR*DUR); rng=np.random.default_rng(3)
out=np.zeros(N); t=np.arange(N)/SR
hz=lambda m:440*2**((m-69)/12)
def add(t0,sig):
    i=int(t0*SR)
    if i>=N: return
    j=min(N,i+len(sig)); out[i:j]+=sig[:j-i]
def bp(x,lo,hi):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); X[(f<lo)|(f>hi)]=0; return np.fft.irfft(X,len(x))
BPM=120; beat=60/BPM; bar=4*beat
prog=[(48,[60,64,67]),(43,[59,62,67]),(45,[60,64,69]),(41,[60,65,69])]  # C G Am F
nb=int(np.ceil(DUR/bar))
for k in range(nb):
    root,ch=prog[k%4]; s=k*bar
    # stab chords on beats 1 and 2&
    for off in (0, 1.5*beat, 2.5*beat):
        n=int(0.35*SR); tt=np.arange(n)/SR; sig=np.zeros(n)
        for m in ch:
            for d in (-0.08,0.08): sig+=np.sin(2*np.pi*hz(m+12+d)*tt)+0.3*np.sin(2*np.pi*hz(m+24+d)*tt)
        add(s+off, sig*np.exp(-7*tt)*0.022)
    # bass 8ths
    for e in range(8):
        n=int(0.24*SR); tt=np.arange(n)/SR
        add(s+e*beat/2,(np.sin(2*np.pi*hz(root)*tt)+0.4*np.sin(2*np.pi*hz(root+12)*tt))*np.exp(-8*tt)*0.10)
    # kick on beats, clap on 2 and 4, hats on offbeats
    for b in range(4):
        n=int(0.25*SR); tt=np.arange(n)/SR; f=50+90*np.exp(-35*tt)
        add(s+b*beat,np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-12*tt)*0.30)
        if b in (1,3):
            n=int(0.2*SR); tt=np.arange(n)/SR
            add(s+b*beat,bp(rng.standard_normal(n),900,5000)*np.exp(-22*tt)*0.07)
        n=int(0.06*SR); tt=np.arange(n)/SR
        add(s+b*beat+beat/2,bp(rng.standard_normal(n),7000,15000)*np.exp(-60*tt)*0.05)
# intro riser into first beat is skipped; start full at 0 for hook energy
def whoosh(dur=0.45,amp=0.18):
    n=int(dur*SR); x=bp(rng.standard_normal(n),700,8000); e=np.sin(np.pi*np.linspace(0,1,n))**2
    return x/np.max(np.abs(x))*e*amp
def ding(f,amp=0.14,dec=6):
    n=int(0.7*SR); tt=np.arange(n)/SR
    return (np.sin(2*np.pi*f*tt)+0.5*np.sin(2*np.pi*f*2.0*tt)+0.25*np.sin(2*np.pi*f*3.01*tt))*np.exp(-dec*tt)*amp
def coin():
    n=int(0.5*SR); tt=np.arange(n)/SR; f=np.where(tt<0.07,1975.5,2637.0)
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-6*tt)*0.12
def alert():
    n=int(0.4*SR); tt=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*880*tt))*0.05*np.exp(-5*tt)*(np.sin(2*np.pi*8*tt)>0)
add(0.0,coin())
for b in [0.72,3.52,7.32,10.92,14.52]: add(b,whoosh())
add(7.55,ding(1318.5)); add(7.75,ding(1975.5,0.10))
add(11.05,alert()); add(11.95,alert()); add(12.85,alert())
add(14.65,coin()); add(15.0,coin())
out*=np.clip((DUR-t)/1.2,0,1)
out/=np.max(np.abs(out))*1.15
st=(np.stack([out,out],1)*32767).astype('<i2')
w=wave.open('bed.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
