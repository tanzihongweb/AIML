import os
import subprocess
import sys
import traceback
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import requests
from requests_oauthlib import OAuth2Session
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
from tkinter import simpledialog
import random

# 替换为你的Microsoft Azure中的相关值
CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
AUTHORIZATION_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
REDIRECT_URI = 'YOUR_REDIRECT_URI'
SCOPE = ['User.Read']

class MinecraftLauncher:
    def __init__(self, master):
        self.master = master
        self.master.title("Minecraft 启动器")
        self.master.geometry("600x400")
        self.minecraft_path = self.get_minecraft_path()
        self.load_author_info()
        self.style_ui()
        self.create_tabs()
        self.load_user_info()
    def init_opengl(self):
        pygame.init()
        self.model_window = pygame.display.set_mode((800, 600), pygame.DOUBLEBUF | pygame.OPENGL)
        glLoadIdentity()
        gluPerspective(45, (800 / 600), 0.1, 50.0)
        glTranslatef(0.0, 0.0, -5.0)
        while self.is_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                    pygame.quit()
                    return
            self.render_player_model()
            pygame.display.flip()
    def update_mods_list(self, event):
        # 清空模组下拉框
        self.mod_combobox['values'] = []
        
        # 获取所选版本的模组列表
        selected_version = self.version_combobox.get()
        if selected_version:
            mods_path = os.path.join(self.minecraft_path, "mods")
            if os.path.exists(mods_path):
                mod_files = [f.replace('.jar', '') for f in os.listdir(mods_path) if f.endswith('.jar')]
                self.mod_combobox['values'] = mod_files

        # 如果没有选择版本或者没有模组，清空模组下拉框
        if not self.mod_combobox['values']:
            self.mod_combobox.set('')
    def get_minecraft_path(self):
        return os.path.join(os.getenv("APPDATA"), ".minecraft")

    def style_ui(self):
        style = ttk.Style(self.master)
        style.configure('TButton', padding=6)
        style.configure('TLabel', padding=6)
        style.configure('TCombobox', padding=5)

    def create_tabs(self):
        self.tab_control = ttk.Notebook(self.master)
        
        self.login_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.login_tab, text="登录")
        self.create_login_widgets()

        self.mods_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.mods_tab, text="模组")
        self.create_mods_widgets()

        self.tab_control.pack(expand=1, fill='both', padx=20, pady=20)

    def create_login_widgets(self):
        ttk.Label(self.login_tab, text="用户名:", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10)
        self.username_entry = ttk.Entry(self.login_tab, font=("Arial", 12))
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)

        self.microsoft_login_button = ttk.Button(self.login_tab, text="微软登录", command=self.microsoft_login)
        self.microsoft_login_button.grid(row=1, columnspan=2, padx=10, pady=10)

        self.skin_button = ttk.Button(self.login_tab, text="选择皮肤", command=self.select_skin)
        self.skin_button.grid(row=2, column=0, padx=10, pady=10)

        self.offline_login_button = ttk.Button(self.login_tab, text="离线登录", command=self.offline_login)
        self.offline_login_button.grid(row=2, column=1, padx=10, pady=10)

        self.skin_path = ""

    def create_mods_widgets(self):
        ttk.Label(self.mods_tab, text="版本:", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10)
        self.version_combobox = ttk.Combobox(self.mods_tab, values=self.get_installed_versions(), font=("Arial", 12))
        self.version_combobox.bind("<<ComboboxSelected>>", self.update_mods_list)  # 关联更新模式列表的方法
        self.version_combobox.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(self.mods_tab, text="模组:", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10)
        self.mod_combobox = ttk.Combobox(self.mods_tab, font=("Arial", 12))
        self.mod_combobox.grid(row=1, column=1, padx=10, pady=10)

        ttk.Button(self.mods_tab, text="下载模组", command=self.download_mod).grid(row=2, columnspan=2, padx=10, pady=10)
        ttk.Button(self.mods_tab, text="删除模组", command=self.delete_mod).grid(row=3, columnspan=2, padx=10, pady=10)
        ttk.Button(self.mods_tab, text="启动游戏", command=self.launch_game).grid(row=4, columnspan=2, padx=10, pady=10)

    def load_author_info(self):
        config_path = os.path.join(self.minecraft_path, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as config_file:
                self.config = json.load(config_file)
        else:
            self.config = {}
            messagebox.showwarning("警告", "配置文件不存在，可能需要重新安装。")

    def get_installed_versions(self):
        versions_path = os.path.join(self.minecraft_path, "versions")
        try:
            return [version for version in os.listdir(versions_path) if os.path.isdir(os.path.join(versions_path, version))]
        except Exception as e:
            messagebox.showerror("错误", f"获取版本时发生异常: {str(e)}")
            return []

    def load_user_info(self):
        user_info_path = os.path.join(self.minecraft_path, "user_info.json")
        if os.path.exists(user_info_path):
            with open(user_info_path, 'r', encoding='utf-8') as user_info_file:
                user_info = json.load(user_info_file)
                self.username_entry.insert(0, user_info.get("username", ""))
    
    def microsoft_login(self):
        oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
        authorization_url, state = oauth.authorization_url(AUTHORIZATION_URL)
        messagebox.showinfo("请注意", "请在浏览器中打开以下链接进行登录并授权:\n\n" + authorization_url)
        
        # 在这里要求用户手动复制和粘贴重定向中的`code`
        code = simpledialog.askstring("输入授权码", "登录成功后，请输入浏览器中出现的授权码：")
        if code:
            try:
                token = oauth.fetch_token(TOKEN_URL, grant_type='authorization_code', code=code, client_secret=CLIENT_SECRET)
                user_info = oauth.get('https://graph.microsoft.com/v1.0/me')
                username = user_info.json().get("displayName", "玩家")
                self.username_entry.delete(0, tk.END)
                self.username_entry.insert(0, username)
                self.save_user_info(username)
                messagebox.showinfo("成功", f"{username} 已成功登录！")
            except Exception as e:
                messagebox.showerror("登录错误", f"登录失败: {e}")

    def select_skin(self):
        self.skin_path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if self.skin_path:
            self.load_skin_texture(self.skin_path)

    def load_skin_texture(self, skin_file):
        try:
            image = Image.open(skin_file)
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            image_data = image.convert("RGBA").tobytes()
            glEnable(GL_TEXTURE_2D)
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            self.skin_texture = texture_id
        except Exception as e:
            messagebox.showerror("错误", f"加载皮肤失败: {e}")

    def offline_login(self):
        username = self.username_entry.get() or "Player"
        self.save_user_info(username)
        messagebox.showinfo("成功", f"{username} 已以离线身份登录!")

    def save_user_info(self, username):
        user_info_path = os.path.join(self.minecraft_path, "user_info.json")
        with open(user_info_path, 'w', encoding='utf-8') as user_info_file:
            json.dump({"username": username}, user_info_file)

    def download_mod(self):
        mod_name = self.mod_combobox.get()
        if not mod_name:
            messagebox.showerror("错误", "请选择要下载的模组.")
            return

        mod_download_url = self.get_download_url(mod_name)
        if mod_download_url:
            mod_path = os.path.join(self.minecraft_path, "mods", f"{mod_name}.jar")
            self.download_file(mod_download_url, mod_path)
            messagebox.showinfo("成功", f"模组 {mod_name} 下载完成！")
        else:
            messagebox.showerror("错误", "模组的下载链接不存在.")

    def get_download_url(self, mod_name):
        return f"https://example.com/download/{mod_name}.jar"  # 伪代码

    def download_file(self, url, file_path):
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(file_path, 'wb') as file:
                file.write(response.content)
            messagebox.showinfo("下载完成", f"{file_path} 下载成功！")
        except requests.RequestException as e:
            messagebox.showerror("错误", f"下载失败: {e}")

    def delete_mod(self):
        mod_name = self.mod_combobox.get()
        if not mod_name:
            messagebox.showerror("错误", "请选择要删除的模组.")
            return
            
        mod_path = os.path.join(self.minecraft_path, "mods", f"{mod_name}.jar")
        if os.path.exists(mod_path):
            os.remove(mod_path)
            messagebox.showinfo("成功", f"模组 {mod_name} 已删除！")
            self.update_mods_list(None)
        else:
            messagebox.showerror("错误", "指定的模组文件不存在。")

    def launch_game(self):
        username = self.username_entry.get() or "Player"
        try:
                jar_path = os.path.join(self.minecraft_path, 'minecraft.jar')  # 指向minecraft.jar文件
                subprocess.Popen(['java', '-jar', jar_path, '--username', username], shell=True)
        except Exception as e:
            self.report_crash(e)
            messagebox.showerror("错误", "启动游戏失败，已记录错误信息.")

    def report_crash(self, exception):
        crash_info = f"崩溃信息:\n{traceback.format_exc()}"
        log_path = os.path.join(self.minecraft_path, "crash_report.log")
        with open(log_path, 'a') as log_file:
            log_file.write(crash_info + "\n")
        print("已记录崩溃报告，位置:", log_path)

    def render_player_model(self):
        if self.skin_texture:
            glBindTexture(GL_TEXTURE_2D, self.skin_texture)
            # Draw the player model here
            # Example code for rendering a model with OpenGL goes here.

    def mainloop(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
            self.render_player_model()

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftLauncher(root)
    root.after(0, app.mainloop)
    root.mainloop()
