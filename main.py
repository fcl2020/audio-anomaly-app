#!/usr/bin/env python3
"""音频异常检测系统 - Android 版 (Kivy)"""

import numpy as np
from scipy import signal as sci_signal
from scipy.fftpack import dct
import pywt
import json, os, warnings
warnings.filterwarnings('ignore')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock

# ============ 核心算法（与原版相同）============

import kivy
from kivy.app import App
from kivy.uix.label import Label

class TestApp(App):
    def build(self):
        try:
            import numpy
            msg = f"numpy OK ({numpy.__version__})"
        except Exception as e:
            msg = f"numpy FAIL: {e}"
        
        try:
            import scipy
            msg += f"\nscipy OK ({scipy.__version__})"
        except Exception as e:
            msg += f"\nscipy FAIL: {e}"
        
        try:
            import pywt
            msg += f"\npywt OK ({pywt.__version__})"
        except Exception as e:
            msg += f"\npywt FAIL: {e}"
        
        return Label(text=msg, font_size='14sp')

TestApp().run()

class AudioPreprocessor:
    @staticmethod
    def denoise(y, sr, method='spectral_gating', **kw):
        if method == 'spectral_gating':
            n_fft=kw.get('n_fft',2048); hop=kw.get('hop_length',512)
            noise_frames=kw.get('noise_frames',10)
            f,t,Zxx=sci_signal.stft(y,fs=sr,nperseg=n_fft,noverlap=n_fft-hop)
            mag=np.abs(Zxx); ph=np.angle(Zxx)
            nm=np.mean(mag[:,:min(noise_frames,mag.shape[1])],axis=1,keepdims=True)
            mc=np.maximum(mag-nm*1.5,0); Zc=mc*np.exp(1j*ph)
            _,yd=sci_signal.istft(Zc,fs=sr,nperseg=n_fft,noverlap=n_fft-hop)
            if len(yd)<len(y):yd=np.pad(yd,(0,len(y)-len(yd)))
            else:yd=yd[:len(y)]
            return yd
        elif method=='wavelet':
            c=pywt.wavedec(y,kw.get('wavelet','db4'),level=kw.get('level',5))
            sig=np.median(np.abs(c[-1]))/0.6745
            th=kw.get('threshold_scale',1.0)*sig*np.sqrt(2*np.log(len(y)))
            return pywt.waverec([c[0]]+[pywt.threshold(x,th,'soft') for x in c[1:]],kw.get('wavelet','db4'))[:len(y)]
        elif method=='lowpass':
            ny=sr/2;b,a=sci_signal.butter(kw.get('order',5),min(kw.get('cutoff',8000),ny*0.95)/ny,btype='low')
            return sci_signal.filtfilt(b,a,y)
        elif method=='wiener':
            return sci_signal.wiener(y,mysize=kw.get('mysize',51))

    @staticmethod
    def normalize(y, method='peak'):
        if method=='peak':mx=np.max(np.abs(y));return y/mx if mx>1e-10 else y
        elif method=='rms':r=np.sqrt(np.mean(y**2));return y/r if r>1e-10 else y
        elif method=='zscore':s=np.std(y);return(y-np.mean(y))/s if s>1e-10 else y-np.mean(y)

    def process(self,y,sr,dm='spectral_gating',nm='peak',**kw):
        return self.normalize(self.denoise(y,sr,method=dm,**kw),method=nm)


class FeatureExtractor:
    def __init__(self,sr,fl=2048,hl=512):
        self.sr=sr;self.fl=fl;self.hl=hl
    def _frames(self,y):
        n=max(1,1+(len(y)-self.fl)//self.hl);o=np.zeros((n,self.fl))
        for i in range(n):s=i*self.hl;e=min(s+self.fl,len(y));o[i,:e-s]=y[s:e]
        return o
    def _pspec(self,y):return np.abs(np.fft.rfft(self._frames(y)*np.hanning(self.fl),axis=1))**2
    def _mel_fb(self,nb,nm=40):
        hz2m=lambda h:2595*np.log10(1+h/700);m2h=lambda m:700*(10**(m/2595)-1)
        ms=np.linspace(hz2m(0),hz2m(self.sr/2),nm+2);hs=m2h(ms)
        bn=np.clip(np.floor(nb*hs/self.sr).astype(int),0,nb-1);fb=np.zeros((nm,nb))
        for i in range(nm):
            l,c,r=bn[i],bn[i+1],bn[i+2]
            if c>l:fb[i,l:c]=(np.arange(l,c)-l)/(c-l)
            if r>c:fb[i,c:r]=(r-np.arange(c,r))/(r-c)
        fb*=2.0/(hs[2:nm+2]-hs[:nm])[:,None];return fb
    def rms(self,y):return np.sqrt(np.mean(self._frames(y)**2,axis=1))
    def mfcc(self,y,n_mfcc=13):
        ps=self._pspec(y);fb=self._mel_fb(ps.shape[1]);mel=np.maximum(np.dot(ps,fb.T),1e-10)
        return dct(np.log(mel),axis=1,type=2,norm='ortho')[:,:n_mfcc].T
    def spectral_centroid(self,y):
        ps=self._pspec(y);fr=np.linspace(0,self.sr/2,ps.shape[1])
        return np.sum(ps*fr,axis=1)/(np.sum(ps,axis=1)+1e-10)
    def zero_crossing_rate(self,y):return np.sum(np.abs(np.diff(np.sign(self._frames(y)),axis=1)),axis=1)/(2*self.fl)
    def spectral_rolloff(self,y,pct=0.85):
        ps=self._pspec(y);fr=np.linspace(0,self.sr/2,ps.shape[1]);cs=np.cumsum(ps,axis=1);ro=np.zeros(ps.shape[0])
        for i in range(ps.shape[0]):idx=np.searchsorted(cs[i],pct*cs[i,-1]);ro[i]=fr[min(idx,len(fr)-1)]
        return ro
    def spectral_bandwidth(self,y):
        ps=self._pspec(y);fr=np.linspace(0,self.sr/2,ps.shape[1]);sc=self.spectral_centroid(y)
        return np.sqrt(np.sum(((fr-sc[:,None])**2)*ps,axis=1)/(np.sum(ps,axis=1)+1e-10))
    def spectral_flatness(self,y):
        ps=np.maximum(self._pspec(y),1e-10);return np.exp(np.mean(np.log(ps),axis=1))/(np.mean(ps,axis=1)+1e-10)
    def extract_all(self,y,n_mfcc=13):
        r=self.rms(y);m=self.mfcc(y,n_mfcc);sc=self.spectral_centroid(y)
        zcr=self.zero_crossing_rate(y);sro=self.spectral_rolloff(y)
        sbw=self.spectral_bandwidth(y);sf=self.spectral_flatness(y)
        ml=min(len(r),len(sc),len(zcr),len(sro),len(sbw),len(sf),m.shape[1])
        feats={'rms':r[:ml],'spectral_centroid':sc[:ml],'zero_crossing_rate':zcr[:ml],
               'spectral_rolloff':sro[:ml],'spectral_bandwidth':sbw[:ml],'spectral_flatness':sf[:ml]}
        for k in range(n_mfcc):feats[f'mfcc_{k+1}']=m[k,:ml]
        if m.shape[1]>1:
            d=np.diff(m[:,:ml],axis=1);feats['mfcc_delta_mean']=np.pad(np.mean(np.abs(d),axis=0),(1,0),'edge')[:ml]
        else:feats['mfcc_delta_mean']=np.zeros(ml)
        return feats,m[:,:ml]


class AnomalyDetector:
    def __init__(self,sigma_level=3.0,method='zscore'):
        self.sigma_level=sigma_level;self.method=method;self.thresholds={}
    def fit(self,feats):
        for n,v in feats.items():
            v=np.asarray(v).flatten();mu,sd=np.mean(v),np.std(v)
            self.thresholds[n]=(mu-self.sigma_level*sd,mu+self.sigma_level*sd)
        return self
    def predict(self,feats):
        ml=min(len(v) for v in feats.values());nf=len(feats);cnt=np.zeros(ml);fa={}
        for n,v in feats.items():
            v=np.asarray(v).flatten()[:ml];lo,hi=self.thresholds[n]
            a=(v<lo)|(v>hi);fa[n]=a;cnt+=a.astype(int)
        sc=cnt/nf;r=np.mean(sc>0.3)
        return{'frame_anomaly':sc>0.3,'feature_anomaly':fa,'anomaly_score':sc,'is_anomaly':r>0.15,'anomaly_ratio':r}


def gen_sim(sr=22050,dur=10.0,as2=6.0,ad=2.5,seed=42):
    np.random.seed(seed);t=np.arange(int(sr*dur))/sr;n=len(t)
    yn=(0.4*np.sin(2*np.pi*120*t)+0.25*np.sin(2*np.pi*240*t)+0.15*np.sin(2*np.pi*360*t)+0.1*np.sin(2*np.pi*480*t)+0.05*np.sin(2*np.pi*600*t)+0.02*np.random.randn(n))
    s=int(as2*sr);e=int((as2+ad)*sr)
    hf=0.3*np.sin(2*np.pi*3500*t)+0.2*np.sin(2*np.pi*5500*t);imp=np.zeros(n)
    for p in np.arange(s,e,int(sr*0.05)):imp[p:min(p+int(0.005*sr),e)]=0.5*np.random.randn(min(int(0.005*sr),e-p))
    am=1+0.5*np.sin(2*np.pi*15*t);ya=yn.copy();ya[s:e]+=hf[s:e]+imp[s:e];ya[s:e]*=am[s:e]
    yp=yn+0.03*np.random.RandomState(123).randn(n)
    return yp.astype(np.float32),ya.astype(np.float32),sr,(as2,as2+ad)


# ============ Kivy GUI ============

class AudioAnomalyApp(App):
    def build(self):
        self.title = '🔊 音频异常检测'
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))

        # 标题
        title = Label(text='🔊 音频异常检测系统', font_size='24sp', size_hint_y=0.1,
                      color=(0.91, 0.27, 0.38, 1))
        layout.add_widget(title)

        # 降噪方法
        row1 = BoxLayout(size_hint_y=0.08, spacing=dp(10))
        row1.add_widget(Label(text='降噪方法:', font_size='16sp'))
        self.denoise_sp = Spinner(text='谱减法', values=('谱减法', '小波降噪', '低通滤波', '维纳滤波'),
                                   size_hint_x=0.6)
        row1.add_widget(self.denoise_sp)
        layout.add_widget(row1)

        # 阈值滑块
        row2 = BoxLayout(size_hint_y=0.08, spacing=dp(10))
        row2.add_widget(Label(text='阈值倍数:', font_size='16sp'))
        self.sigma_slider = Slider(min=1.0, max=5.0, value=2.5, size_hint_x=0.5)
        row2.add_widget(self.sigma_slider)
        self.sigma_label = Label(text='2.5', font_size='18sp', color=(0.91,0.27,0.38,1), size_hint_x=0.2)
        row2.add_widget(self.sigma_label)
        self.sigma_slider.bind(value=lambda i,v: self.sigma_label.setter('text')(self.sigma_label, f'{v:.1f}'))
        layout.add_widget(row2)

        # 按钮
        btn_layout = BoxLayout(size_hint_y=0.12, spacing=dp(15))
        sim_btn = Button(text='🧪 仿真演示', font_size='18sp',
                        background_color=(0.96,0.65,0.14,1))
        sim_btn.bind(on_press=self.run_simulation)
        btn_layout.add_widget(sim_btn)

        file_btn = Button(text='📁 选择音频', font_size='18sp',
                         background_color=(0.06,0.2,0.38,1))
        file_btn.bind(on_press=self.choose_file)
        btn_layout.add_widget(file_btn)
        layout.add_widget(btn_layout)

        # 结果显示区
        scroll = ScrollView(size_hint_y=0.62)
        self.result_label = Label(text='点击上方按钮开始检测', font_size='16sp',
                                  halign='left', valign='top', size_hint_y=None,
                                  color=(0.8,0.8,0.8,1))
        self.result_label.bind(width=lambda *x: self.result_label.setter('text_size')(self.result_label, (self.result_label.width, None)))
        self.result_label.bind(texture_size=self.result_label.setter('size'))
        scroll.add_widget(self.result_label)
        layout.add_widget(scroll)

        return layout

    def get_denoise_method(self):
        m = {'谱减法':'spectral_gating','小波降噪':'wavelet','低通滤波':'lowpass','维纳滤波':'wiener'}
        return m.get(self.denoise_sp.text, 'spectral_gating')

    def run_simulation(self, instance):
        self.result_label.text = '⏳ 正在分析仿真数据...'
        Clock.schedule_once(lambda dt: self._do_detect(None), 0.1)

    def choose_file(self, instance):
        fc = FileChooserListView(path='/', filters=['*.wav','*.mp3'])
        popup = Popup(title='选择音频文件', content=fc, size_hint=(0.9,0.9))
        def on_select(instance2, selection, touch=None):
            if selection:
                popup.dismiss()
                self.result_label.text = f'⏳ 正在分析: {selection[0]}...'
                Clock.schedule_once(lambda dt: self._do_detect(selection[0]), 0.1)
        fc.bind(on_selection=on_select)
        popup.open()

    def _do_detect(self, filepath):
        try:
            denoise = self.get_denoise_method()
            sigma = self.sigma_slider.value

            if filepath is None:
                y_normal, y_test, sr, anom_range = gen_sim()
            else:
                from scipy.io import wavfile
                sr, y_test = wavfile.read(filepath)
                if y_test.dtype == np.int16: y_test = y_test.astype(np.float32)/32768.0
                if y_test.ndim > 1: y_test = y_test.mean(axis=1)
                y_normal = y_test[:int(sr*0.5)] if len(y_test) > sr else y_test
                anom_range = (0, len(y_test)/sr)

            pp = AudioPreprocessor()
            yn = pp.process(y_normal, sr, dm=denoise)
            yt = pp.process(y_test, sr, dm=denoise)

            ex = FeatureExtractor(sr=sr)
            fn, _ = ex.extract_all(yn)
            ft, mc = ex.extract_all(yt)

            det = AnomalyDetector(sigma_level=sigma)
            det.fit(fn)
            res = det.predict(ft)

            ia = res['is_anomaly']
            emoji = '⚠️' if ia else '✅'
            verdict = '异常 ANOMALY' if ia else '正常 NORMAL'
            ratio = res['anomaly_ratio']
            n_anom = int(np.sum(res['frame_anomaly']))
            total = len(res['frame_anomaly'])

            txt = f"{'━'*30}\n"
            txt += f"  {emoji} 检测结果: {verdict}\n"
            txt += f"{'━'*30}\n\n"
            txt += f"  异常帧: {n_anom}/{total}\n"
            txt += f"  异常比例: {ratio:.2%}\n"
            txt += f"  采样率: {sr} Hz\n\n"
            txt += f"{'━'*30}\n  各特征异常率:\n{'━'*30}\n\n"

            for name, fa in res['feature_anomaly'].items():
                c = int(np.sum(fa))
                p = c/len(fa)*100 if len(fa) > 0 else 0
                bar = '█' * int(p/5) + '░' * (20-int(p/5))
                txt += f"  {name[:16]}\n  {bar} {p:.1f}%\n"

            self.result_label.text = txt

        except Exception as e:
            self.result_label.text = f'❌ 错误: {str(e)}'


if __name__ == '__main__':
    AudioAnomalyApp().run()
