import numpy as np
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex

# --- 颜色主题 (科技感深色系) ---
COLOR_BG = '#0d1117'       # 极深蓝黑背景
COLOR_PANEL = '#161b22'    # 面板背景
COLOR_BORDER = '#30363d'   # 边框
COLOR_ACCENT = '#58a6ff'   # 科技蓝高亮
COLOR_TEXT = '#c9d1d9'     # 主文本色
COLOR_NORMAL = '#3fb950'   # 正常-霓虹绿
COLOR_WARN = '#d29922'     # 警告-琥珀黄
COLOR_ERROR = '#f85149'    # 异常-警报红

class TechLabel(Label):
    """自定义科技感标签"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = get_color_from_hex(COLOR_TEXT)
        self.font_name = 'RobotoMono-Regular' # 等宽字体更有科技感 (安卓自带)

class DashboardApp(App):
    def build(self):
        self.is_monitoring = False
        self.simulation_step = 0

        # 根布局
        root = BoxLayout(orientation='vertical', padding=15, spacing=10)
        with root.canvas.before:
            Color(*get_color_from_hex(COLOR_BG))
            self.rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self.update_rect, pos=self.update_rect)

        # 1. 顶部标题栏
        header = BoxLayout(size_hint_y=0.1, spacing=10)
        self.status_light = Label(text='●', font_size='30sp', color=get_color_from_hex(COLOR_NORMAL))
        title = TechLabel(text='[b]工业声纹异常监测系统 v2.0[/b]', markup=True, font_size='24sp', halign='left', valign='middle')
        title.bind(size=title.setter('text_size'))
        header.add_widget(self.status_light)
        header.add_widget(title)

        # 2. 核心大指标：综合健康度
        health_panel = BoxLayout(orientation='vertical', size_hint_y=0.3, padding=20, spacing=5)
        with health_panel.canvas.before:
            Color(*get_color_from_hex(COLOR_PANEL))
            self.rect_hp = Rectangle(size=health_panel.size, pos=health_panel.pos)
        health_panel.bind(size=self.update_rect_hp, pos=self.update_rect_hp)
        
        self.lbl_health_title = TechLabel(text='设备综合健康度', font_size='18sp', halign='left')
        self.lbl_health_score = Label(text='100', font_size='80sp', color=get_color_from_hex(COLOR_NORMAL), bold=True)
        self.lbl_health_status = TechLabel(text='状态：运行平稳', font_size='20sp', halign='left')
        
        self.lbl_health_title.bind(size=self.lbl_health_title.setter('text_size'))
        self.lbl_health_status.bind(size=self.lbl_health_status.setter('text_size'))
        
        health_panel.add_widget(self.lbl_health_title)
        health_panel.add_widget(self.lbl_health_score)
        health_panel.add_widget(self.lbl_health_status)

        # 3. 中部：4个细分特征指标 (2x2 网格)
        metrics_grid = GridLayout(cols=2, rows=2, size_hint_y=0.4, spacing=10)
        self.m_spl = self.create_metric_card(metrics_grid, '总声压级 (SPL)', '0.00 dB')
        self.m_centroid = self.create_metric_card(metrics_grid, '频谱质心', '0.00 Hz')
        self.m_peak = self.create_metric_card(metrics_grid, '峰值频率', '0.00 Hz')
        self.m_hf_ratio = self.create_metric_card(metrics_grid, '高频能量比', '0.00 %')

        # 4. 底部控制按钮
        self.btn_control = Button(text='启动实时监测', font_size='20sp', 
                                  background_color=get_color_from_hex(COLOR_ACCENT), 
                                  size_hint_y=0.15)
        self.btn_control.bind(on_press=self.toggle_monitoring)

        root.add_widget(header)
        root.add_widget(health_panel)
        root.add_widget(metrics_grid)
        root.add_widget(self.btn_control)

        return root

    def create_metric_card(self, parent, title, default_val):
        card = BoxLayout(orientation='vertical', padding=15, spacing=5)
        with card.canvas.before:
            Color(*get_color_from_hex(COLOR_PANEL))
            r = Rectangle(size=card.size, pos=card.pos)
            card.bind(size=lambda i, v: setattr(r, 'size', v), pos=lambda i, v: setattr(r, 'pos', v))
        
        lbl_t = TechLabel(text=title, font_size='14sp', halign='left', color=get_color_from_hex(COLOR_ACCENT))
        lbl_v = TechLabel(text=default_val, font_size='32sp', bold=True, halign='left')
        lbl_t.bind(size=lbl_t.setter('text_size'))
        lbl_v.bind(size=lbl_v.setter('text_size'))
        
        card.add_widget(lbl_t)
        card.add_widget(lbl_v)
        parent.add_widget(card)
        return lbl_v

    # --- 算法核心：纯 Numpy 提取 5 大特征 ---
    def analyze_audio(self, audio_data, sample_rate):
        # 1. 计算总声压级 (RMS -> dB)
        rms = np.sqrt(np.mean(audio_data**2))
        spl = 20 * np.log10(rms + 1e-6) # 加小数防除零
        
        # 2. 快速傅里叶变换
        fft_data = np.fft.rfft(audio_data)
        power_spectrum = np.abs(fft_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1/sample_rate)
        
        # 3. 频谱质心 - 声音"亮度"，越高越刺耳
        centroid = np.sum(freqs * power_spectrum) / (np.sum(power_spectrum) + 1e-6)
        
        # 4. 峰值频率 - 最强的频率点
        peak_freq = freqs[np.argmax(power_spectrum)]
        
        # 5. 高频能量比 - 异响识别关键 (例如 >4000Hz)
        hf_mask = freqs > 4000
        lf_mask = freqs <= 1000
        hf_energy = np.sum(power_spectrum[hf_mask])
        lf_energy = np.sum(power_spectrum[lf_mask])
        hf_ratio = (hf_energy / (lf_energy + 1e-6)) * 100
        
        # 6. 综合健康度打分 (简易逻辑，可根据实际调参)
        score = 100
        if spl > -10: score -= 30  # 声音过大
        if centroid > 3000: score -= 30 # 声音太尖锐
        if hf_ratio > 50: score -= 40 # 高频异响严重
        score = max(0, min(100, score))
        
        return {
            'spl': spl, 'centroid': centroid, 
            'peak_freq': peak_freq, 'hf_ratio': hf_ratio, 'score': score
        }

    # --- UI 交互与模拟 ---
    def toggle_monitoring(self, instance):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.btn_control.text = '停止监测'
            self.btn_control.background_color = get_color_from_hex(COLOR_ERROR)
            Clock.schedule_interval(self.update_data, 1.0) # 每秒刷新一次
        else:
            self.btn_control.text = '启动实时监测'
            self.btn_control.background_color = get_color_from_hex(COLOR_ACCENT)
            Clock.unschedule(self.update_data)

    def update_data(self, dt):
        # 模拟真实场景的音频数据 (实际应用中替换为录音数据)
        sample_rate = 44100
        t = np.linspace(0, 1, sample_rate, endpoint=False)
        
        # 基础噪声 (模拟机器运转声)
        base_noise = 0.2 * np.sin(2 * np.pi * 120 * t) + 0.05 * np.random.randn(sample_rate)
        
        # 模拟偶发异响 (随时间推移，异响概率和强度增加，用于给领导演示恶化过程)
        self.simulation_step += 1
        anomaly_chance = min(0.8, self.simulation_step * 0.05)
        
        if np.random.rand() < anomaly_chance:
            # 产生高频摩擦/啸叫异响
            anomaly = 0.4 * np.sin(2 * np.pi * 6000 * t + np.random.rand() * 10)
            audio_data = base_noise + anomaly
        else:
            audio_data = base_noise
            
        # 调用核心算法
        results = self.analyze_audio(audio_data, sample_rate)
        
        # 更新 UI
        self.m_spl.text = f"{results['spl']:.2f} dB"
        self.m_centroid.text = f"{results['centroid']:.2f} Hz"
        self.m_peak.text = f"{results['peak_freq']:.2f} Hz"
        self.m_hf_ratio.text = f"{results['hf_ratio']:.2f} %"
        self.lbl_health_score.text = str(int(results['score']))
        
        # 根据分数变色
        if results['score'] >= 80:
            color = get_color_from_hex(COLOR_NORMAL)
            status_text = "状态：运行平稳"
        elif results['score'] >= 50:
            color = get_color_from_hex(COLOR_WARN)
            status_text = "状态：疑似轻微异响"
        else:
            color = get_color_from_hex(COLOR_ERROR)
            status_text = "状态：⚠️ 严重异常报警"
            
        self.lbl_health_score.color = color
        self.status_light.color = color
        self.lbl_health_status.text = status_text
        self.lbl_health_status.color = color

    # 画布背景绑定
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update_rect_hp(self, instance, value):
        self.rect_hp.pos = instance.pos
        self.rect_hp.size = instance.size

if __name__ == '__main__':
    DashboardApp().run()
