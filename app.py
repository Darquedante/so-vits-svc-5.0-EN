import os
import subprocess
import yaml
import sys
import webbrowser
import gradio as gr
from ruamel.yaml import YAML
import shutil
import soundfile
import shlex
import locale

class WebUI:
    def __init__(self):
        self.train_config_path = 'configs/train.yaml'
        self.info = Info()
        self.names = []
        self.names2 = []
        self.voice_names = []
        self.base_config_path = 'configs/base.yaml'
        
        if not os.path.exists(self.train_config_path):
            shutil.copyfile(self.base_config_path, self.train_config_path)
            print(i18n("Initialization successful"))
        else:
            print(i18n("Ready"))
        self.main_ui()

    def main_ui(self):
        with gr.Blocks(theme=gr.themes.Base(primary_hue=gr.themes.colors.green)) as ui:

            gr.Markdown('# so-vits-svc5.0 WebUI')

            with gr.Tab(i18n("Preprocessing-Training")):

                with gr.Accordion(i18n('Training Instructions'), open=False):

                    gr.Markdown(self.info.train)

                gr.Markdown(i18n('### Preprocessing Parameter Settings'))

                with gr.Row():

                    self.model_name = gr.Textbox(value='sovits5.0', label='model', info=i18n('Model Name'), interactive=True) # Suggest setting as non-modifiable

                    self.f0_extractor = gr.Textbox(value='crepe', label='f0_extractor', info=i18n('f0 Extractor'), interactive=False)

                    self.thread_count = gr.Slider(minimum=1, maximum=os.cpu_count(), step=1, value=2, label='thread_count', info=i18n('Number of preprocessing threads'), interactive=True)

                gr.Markdown(i18n('### Training Parameter Settings'))

                with gr.Row():

                    self.learning_rate = gr.Number(value=5e-5, label='learning_rate', info=i18n('Learning Rate'), interactive=True)

                    self.batch_size = gr.Slider(minimum=1, maximum=50, step=1, value=6, label='batch_size', info=i18n('Batch Size'), interactive=True)

                with gr.Row():

                    self.info_interval = gr.Number(value=50, label='info_interval', info=i18n('Training log record interval (step)'), interactive=True)

                    self.eval_interval = gr.Number(value=1, label='eval_interval', info=i18n('Validation set evaluation interval (epoch)'), interactive=True)

                    self.save_interval = gr.Number(value=5, label='save_interval', info=i18n('Checkpoint save interval (epoch)'), interactive=True)

                    self.keep_ckpts = gr.Number(value=0, label='keep_ckpts', info=i18n('Keep the latest checkpoint files (0 to save all)'),interactive=True)

                with gr.Row():

                    self.slow_model = gr.Checkbox(label=i18n("Add base model"), value=True, interactive=True)

                gr.Markdown(i18n('### Start Training'))

                with gr.Row():

                    self.bt_open_dataset_folder = gr.Button(value=i18n('Open Dataset Folder'))

                    self.bt_onekey_train = gr.Button(i18n('One-click Training'), variant="primary")

                    self.bt_tb = gr.Button(i18n('Launch Tensorboard'), variant="primary")

                gr.Markdown(i18n('### Resume Training'))

                with gr.Row():

                    self.resume_model = gr.Dropdown(choices=sorted(self.names), label='Resume training progress from checkpoints', info=i18n('Resume training progress from checkpoints'), interactive=True)

                    with gr.Column():

                        self.bt_refersh = gr.Button(i18n('Refresh'))

                        self.bt_resume_train = gr.Button(i18n('Resume Training'), variant="primary")

            with gr.Tab(i18n("Inference")):

                with gr.Accordion(i18n('Inference Instructions'), open=False):

                    gr.Markdown(self.info.inference)

                gr.Markdown(i18n('### Inference Parameter Settings'))

                with gr.Row():

                    with gr.Column():

                        self.keychange = gr.Slider(-24, 24, value=0, step=1, label=i18n('Key Change'))

                        self.file_list = gr.Markdown(value="", label=i18n("File List"))

                        with gr.Row():

                            self.resume_model2 = gr.Dropdown(choices=sorted(self.names2), label='Select the model you want to export',
                                                             info=i18n('Select the model to export'), interactive=True)
                            with gr.Column():

                                self.bt_refersh2 = gr.Button(value=i18n('Refresh Models and Timbres'))


                                self.bt_out_model = gr.Button(value=i18n('Export Model'), variant="primary")

                        with gr.Row():

                            self.resume_voice = gr.Dropdown(choices=sorted(self.voice_names), label='Select the sound file',
                                                            info=i18n('Select the timbre file'), interactive=True)

                        with gr.Row():

                            self.input_wav = gr.Audio(type='filepath', label=i18n('Select audio file to convert'), source='upload')

                        with gr.Row():

                            self.bt_infer = gr.Button(value=i18n('Start Conversion'), variant="primary")

                        with gr.Row():

                            self.output_wav = gr.Audio(label=i18n('Output Audio'), interactive=False)


            self.bt_open_dataset_folder.click(fn=self.openfolder)
            self.bt_onekey_train.click(fn=self.onekey_training,inputs=[self.model_name, self.thread_count,self.learning_rate,self.batch_size, self.info_interval, self.eval_interval,self.save_interval, self.keep_ckpts, self.slow_model])
            self.bt_out_model.click(fn=self.out_model, inputs=[self.model_name, self.resume_model2])
            self.bt_tb.click(fn=self.tensorboard)
            self.bt_refersh.click(fn=self.refresh_model, inputs=[self.model_name], outputs=[self.resume_model])
            self.bt_resume_train.click(fn=self.resume_train, inputs=[self.model_name, self.resume_model, self.learning_rate,self.batch_size, self.info_interval, self.eval_interval,self.save_interval, self.keep_ckpts, self.slow_model])
            self.bt_infer.click(fn=self.inference, inputs=[self.input_wav, self.resume_voice, self.keychange], outputs=[self.output_wav])
            self.bt_refersh2.click(fn=self.refresh_model_and_voice, inputs=[self.model_name],outputs=[self.resume_model2, self.resume_voice])

        ui.launch(inbrowser=True, server_port=2333, share=True)

    def openfolder(self):

        try:
            if sys.platform.startswith('win'):
                os.startfile('dataset_raw')
            elif sys.platform.startswith('linux'):
                subprocess.call(['xdg-open', 'dataset_raw'])
            elif sys.platform.startswith('darwin'):
                subprocess.call(['open', 'dataset_raw'])
            else:
                print(i18n('Failed to open folder!'))
        except BaseException:
            print(i18n('Failed to open folder!'))

    def preprocessing(self, thread_count):
        print(i18n('Starting preprocessing'))
        train_process = subprocess.Popen('python -u svc_preprocessing.py -t ' + str(thread_count), stdout=subprocess.PIPE)
        while train_process.poll() is None:
            output = train_process.stdout.readline().decode('utf-8')
            print(output, end='')

    def create_config(self, model_name, learning_rate, batch_size, info_interval, eval_interval, save_interval,
                      keep_ckpts, slow_model):
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.width = 1024
        with open("configs/train.yaml", "r") as f:
            config = yaml.load(f)
        config['train']['model'] = model_name
        config['train']['learning_rate'] = learning_rate
        config['train']['batch_size'] = batch_size
        config["log"]["info_interval"] = int(info_interval)
        config["log"]["eval_interval"] = int(eval_interval)
        config["log"]["save_interval"] = int(save_interval)
        config["log"]["keep_ckpts"] = int(keep_ckpts)
        if slow_model:
            config["train"]["pretrain"] = "vits_pretrain\sovits5.0.pretrain.pth"
        else:
            config["train"]["pretrain"] = ""
        with open("configs/train.yaml", "w") as f:
            yaml.dump(config, f)
        return f"{config['log']}"

    def training(self, model_name):
        print(i18n('Starting training'))
        train_process = subprocess.Popen('python -u svc_trainer.py -c ' + self.train_config_path + ' -n ' + str(model_name), stdout=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_CONSOLE)
        while train_process.poll() is None:
            output = train_process.stdout.readline().decode('utf-8')
            print(output, end='')

    def onekey_training(self, model_name, thread_count, learning_rate, batch_size, info_interval, eval_interval, save_interval, keep_ckpts, slow_model):
        print(self, model_name, thread_count, learning_rate, batch_size, info_interval, eval_interval,
              save_interval, keep_ckpts)
        self.create_config(model_name, learning_rate, batch_size, info_interval, eval_interval, save_interval, keep_ckpts, slow_model)
        self.preprocessing(thread_count)
        self.training(model_name)

    def out_model(self, model_name, resume_model2):
        print(i18n('Starting model export'))
        try:
            subprocess.Popen('python -u svc_export.py -c {} -p "chkpt/{}/{}"'.format(self.train_config_path, model_name, resume_model2),stdout=subprocess.PIPE)
            print(i18n('Model export successful'))
        except Exception as e:
            print(i18n("Error occurred:"), e)


    def tensorboard(self):
        if sys.platform.startswith('win'):
            tb_process = subprocess.Popen('tensorboard --logdir=logs --port=6006', stdout=subprocess.PIPE)
            webbrowser.open("http://localhost:6006")
        else:
            p1 = subprocess.Popen(["ps", "-ef"], stdout=subprocess.PIPE) #ps -ef | grep tensorboard | awk '{print $2}' | xargs kill -9
            p2 = subprocess.Popen(["grep", "tensorboard"], stdin=p1.stdout, stdout=subprocess.PIPE)
            p3 = subprocess.Popen(["awk", "{print $2}"], stdin=p2.stdout, stdout=subprocess.PIPE)
            p4 = subprocess.Popen(["xargs", "kill", "-9"], stdin=p3.stdout)
            p1.stdout.close()
            p2.stdout.close()
            p3.stdout.close()
            p4.communicate()
            tb_process = subprocess.Popen('tensorboard --logdir=logs --port=6007', stdout=subprocess.PIPE)  # AutoDL port set to 6007
        while tb_process.poll() is None:
            output = tb_process.stdout.readline().decode('utf-8')
            print(output)

    def refresh_model(self, model_name):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_root = os.path.join(self.script_dir, f"chkpt/{model_name}")
        self.names = []
        try:
            for self.name in os.listdir(self.model_root):
                if self.name.endswith(".pt"):
                    self.names.append(self.name)
            return {"choices": sorted(self.names), "__type__": "update"}
        except FileNotFoundError:
            return {"label": i18n("Missing model file"), "__type__": "update"}

    def refresh_model2(self, model_name):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_root = os.path.join(self.script_dir, f"chkpt/{model_name}")
        self.names2 = []
        try:
            for self.name in os.listdir(self.model_root):
                if self.name.endswith(".pt"):
                    self.names2.append(self.name)
            return {"choices": sorted(self.names2), "__type__": "update"}
        except FileNotFoundError:
            return {"label": i18n("缺少模型文件"), "__type__": "update"}

    def refresh_voice(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_root = os.path.join(self.script_dir, "data_svc/singer")
        self.voice_names = []
        try:
            for self.name in os.listdir(self.model_root):
                if self.name.endswith(".npy"):
                    self.voice_names.append(self.name)
            return {"choices": sorted(self.voice_names), "__type__": "update"}
        except FileNotFoundError:
            return {"label": i18n("缺少文件"), "__type__": "update"}

    def refresh_model_and_voice(self, model_name):
        model_update = self.refresh_model2(model_name)
        voice_update = self.refresh_voice()
        return model_update, voice_update

    def resume_train(self, model_name, resume_model ,learning_rate, batch_size, info_interval, eval_interval, save_interval, keep_ckpts, slow_model):
        print(i18n('开始恢复训练'))
        self.create_config(model_name, learning_rate, batch_size, info_interval, eval_interval, save_interval,keep_ckpts, slow_model)
        train_process = subprocess.Popen('python -u svc_trainer.py -c {} -n {} -p "chkpt/{}/{}"'.format(self.train_config_path, model_name, model_name, resume_model), stdout=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_CONSOLE)
        while train_process.poll() is None:
            output = train_process.stdout.readline().decode('utf-8')
            print(output, end='')

    def inference(self, input, resume_voice, keychange):
        if os.path.exists("test.wav"):
            os.remove("test.wav")
            print(i18n("已清理残留文件"))
        else:
            print(i18n("无需清理残留文件"))
        self.train_config_path = 'configs/train.yaml'
        print(i18n('开始推理'))
        shutil.copy(input, ".")
        input_name = os.path.basename(input)
        os.rename(input_name, "test.wav")
        input_name = "test.wav"
        if not input_name.endswith(".wav"):
            data, samplerate = soundfile.read(input_name)
            input_name = input_name.rsplit(".", 1)[0] + ".wav"
            soundfile.write(input_name, data, samplerate)
        train_config_path = shlex.quote(self.train_config_path)
        keychange = shlex.quote(str(keychange))
        cmd = ["python", "-u", "svc_inference.py", "--config", train_config_path, "--model", "sovits5.0.pth", "--spk",
               f"data_svc/singer/{resume_voice}", "--wave", "test.wav", "--shift", keychange]
        train_process = subprocess.run(cmd, shell=False, capture_output=True, text=True)
        print(train_process.stdout)
        print(train_process.stderr)
        print(i18n("推理成功"))
        return "svc_out.wav"

class Info:
    def __init__(self) -> None:
        self.train = i18n('### 2023.7.11|[@OOPPEENN](https://github.com/OOPPEENN)第一次编写|[@thestmitsuk](https://github.com/thestmitsuki)二次补完')

        self.inference = i18n('### 2023.7.11|[@OOPPEENN](https://github.com/OOPPEENN)第一次编写|[@thestmitsuk](https://github.com/thestmitsuki)二次补完')


LANGUAGE_LIST = ['zh_CN', 'en_US']
LANGUAGE_ALL = {
    'zh_CN': {
        'SUPER': 'END',
        'LANGUAGE': 'zh_CN',
        'Initialization successful': 'Initialization successful',
        'Ready': 'Ready',
        'Preprocessing-Training': 'Preprocessing-Training',
        'Training instructions': 'Training instructions',
        '### Preprocessing parameter settings': '### Preprocessing parameter settings',
        'Model name': 'Model name',
        'f0 extractor': 'f0 extractor',
        'Number of preprocessing threads': 'Number of preprocessing threads',
        '### Training parameter settings': '### Training parameter settings',
        'Learning rate': 'Learning rate',
        'Batch size': 'Batch size',
        'Training log recording interval (step)': 'Training log recording interval (step)',
        'Validation set validation interval (epoch)': 'Validation set validation interval (epoch)',
        'Checkpoint save interval (epoch)': 'Checkpoint save interval (epoch)',
        'Keep the latest checkpoint files (0 to save all)': 'Keep the latest checkpoint files (0 to save all)',
        'Whether to add base model': 'Whether to add base model',
        '### Start training': '### Start training',
        'Open dataset folder': 'Open dataset folder',
        'One-click training': 'One-click training',
        'Start Tensorboard': 'Start Tensorboard',
        '### Resume training': '### Resume training',
        'Resume training progress from checkpoint': 'Resume training progress from checkpoint',
        'Refresh': 'Refresh',
        'Resume training': 'Resume training',
        'Inference': 'Inference',
        'Inference instructions': 'Inference instructions',
        '### Inference parameter settings': '### Inference parameter settings',
        'Pitch shift': 'Pitch shift',
        'File list': 'File list',
        'Select the model to export': 'Select the model to export',
        'Refresh model and timbre': 'Refresh model and timbre',
        'Export model': 'Export model',
        'Select timbre file': 'Select timbre file',
        'Select audio to convert': 'Select audio to convert',
        'Start conversion': 'Start conversion',
        'Output audio': 'Output audio',
        'Failed to open folder!': 'Failed to open folder!',
        'Start preprocessing': 'Start preprocessing',
        'Start training': 'Start training',
        'Start exporting model': 'Start exporting model',
        'Model exported successfully': 'Model exported successfully',
        'Error occurred:': 'Error occurred:',
        'Missing model file': 'Missing model file',
        'Missing file': 'Missing file',
        'Residual files cleaned up': 'Residual files cleaned up',
        'No need to clean residual files': 'No need to clean residual files',
        'Start inference': 'Start inference',
        'Inference successful': 'Inference successful',

        '### 2023.7.11|[@OOPPEENN](https://github.com/OOPPEENN)第一次编写|[@thestmitsuk](https://github.com/thestmitsuki)二次补完': '### 2023.7.11|[@OOPPEENN](https://github.com/OOPPEENN)第一次编写|[@thestmitsuk](https://github.com/thestmitsuki)二次补完'
    },
    'en_US': {
        'SUPER': 'zh_CN',
        'LANGUAGE': 'en_US',
        '初始化成功': 'Initialization successful',
        '就绪': 'Ready',
        '预处理-训练': 'Preprocessing-Training',
        '训练说明': 'Training instructions',
        '### 预处理参数设置': '### Preprocessing parameter settings',
        '模型名称': 'Model name',
        'f0提取器': 'f0 extractor',
        '预处理线程数': 'Preprocessing thread number',
        '### 训练参数设置': '### Training parameter settings',
        '学习率': 'Learning rate',
        '批大小': 'Batch size',
        '训练日志记录间隔（step）': 'Training log recording interval (step)',
        '验证集验证间隔（epoch）': 'Validation set validation interval (epoch)',
        '检查点保存间隔（epoch）': 'Checkpoint save interval (epoch)',
        '保留最新的检查点文件(0保存全部)': 'Keep the latest checkpoint file (0 save all)',
        '是否添加底模': 'Whether to add the base model',
        '### 开始训练': '### Start training',
        '打开数据集文件夹': 'Open the dataset folder',
        '一键训练': 'One-click training',
        '启动Tensorboard': 'Start Tensorboard',
        '### 恢复训练': '### Resume training',
        '从检查点恢复训练进度': 'Restore training progress from checkpoint',
        '刷新': 'Refresh',
        '恢复训练': 'Resume training',
        "推理": "Inference",
        "推理说明": "Inference instructions",
        "### 推理参数设置": "### Inference parameter settings",
        "变调": "Pitch shift",
        "文件列表": "File list",
        "选择要导出的模型": "Select the model to export",
        "刷新模型和音色": "Refresh model and timbre",
        "导出模型": "Export model",
        "选择音色文件": "Select timbre file",
        "选择待转换音频": "Select audio to be converted",
        "开始转换": "Start conversion",
        "输出音频": "Output audio",
        "打开文件夹失败！": "Failed to open folder!",
        "开始预处理": "Start preprocessing",
        "开始训练": "Start training",
        "开始导出模型": "Start exporting model",
        "导出模型成功": "Model exported successfully",
        "出现错误：": "An error occurred:",
        "缺少模型文件": "Missing model file",
        '缺少文件': 'Missing file',
        "已清理残留文件": "Residual files cleaned up",
        "无需清理残留文件": "No need to clean up residual files",
        "开始推理": "Start inference",
        '### 2023.7.11|[@OOPPEENN](https://github.com/OOPPEENN)第一次编写|[@thestmitsuk](https://github.com/thestmitsuki)二次补完': '### 2023.7.11|[@OOPPEENN](https://github.com/OOPPEENN)first writing|[@thestmitsuk](https://github.com/thestmitsuki)second completion'
    }
}

class I18nAuto:
    def __init__(self, language=None):
        self.language_list = LANGUAGE_LIST
        self.language_all = LANGUAGE_ALL
        self.language_map = {}
        self.language = language or locale.getdefaultlocale()[0]
        if self.language not in self.language_list:
            self.language = 'en_US'
        self.read_language(self.language_all['en_US'])
        while self.language_all[self.language]['SUPER'] != 'END':
            self.read_language(self.language_all[self.language])
            self.language = self.language_all[self.language]['SUPER']

    def read_language(self, lang_dict: dict):
        self.language_map.update(lang_dict)

    def __call__(self, key):
        return self.language_map[key]

if __name__ == "__main__":
    i18n = I18nAuto()
    webui = WebUI()
