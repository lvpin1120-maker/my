#!/usr/bin/env python3
"""Configure a system credential manager for this repository; never save a PAT in files."""
import argparse
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import sys

EXPECTED = "https://github.com/lvpin1120-maker/my.git"
REPOSITORY_PATH = "lvpin1120-maker/my.git"
ROOT = Path(__file__).resolve().parent

def git(*args, **kwargs):
    return subprocess.run(["git", "-C", str(ROOT), *args], **kwargs)

def find_helper():
    if sys.platform == "darwin":
        exec_path = subprocess.check_output(["git", "--exec-path"], text=True).strip()
        if (Path(exec_path) / "git-credential-osxkeychain").exists() or shutil.which("git-credential-osxkeychain"):
            return "osxkeychain"
    for name in ["manager", "manager-core"]:
        try:
            result = subprocess.run(["git", "credential-" + name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                return name
        except OSError:
            pass
    exec_path = subprocess.check_output(["git", "--exec-path"], text=True).strip()
    if (Path(exec_path) / "git-credential-libsecret").exists() or shutil.which("git-credential-libsecret"):
        return "libsecret"
    raise RuntimeError("未找到系统安全凭证管理器。请先安装并配置适合系统的 Git Credential Manager；本脚本不会使用明文 store。")

def main():
    parser = argparse.ArgumentParser(description="仅为当前 my 仓库配置系统凭证管理器。令牌需要在这台电脑隐藏输入一次。")
    parser.parse_args()
    if not shutil.which("git"):
        raise RuntimeError("请先安装 Git。")
    remote = git("remote", "get-url", "origin", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if remote.returncode or remote.stdout.strip().rstrip("/") != EXPECTED:
        raise RuntimeError("请在通过 HTTPS 克隆的 lvpin1120-maker/my 仓库中运行；origin 应为 " + EXPECTED)
    helper = find_helper()
    if not sys.stdin.isatty():
        raise RuntimeError("请在交互终端运行，避免令牌输入被回显或记录。")
    print("将使用系统凭证管理器：" + helper)
    print("仅配置当前仓库，并按 GitHub 仓库路径查找凭证。")
    username = input("GitHub 用户名 [lvpin1120-maker]：").strip() or "lvpin1120-maker"
    if any(c in username for c in "\r\n\0"):
        raise RuntimeError("用户名格式不正确。")
    token = getpass.getpass("PAT（隐藏输入，不会显示）：").strip()
    if not token or any(c in token for c in "\r\n\0"):
        raise RuntimeError("未收到有效格式的令牌。")
    fields = "protocol=https\nhost=github.com\npath=" + REPOSITORY_PATH + "\nusername=" + username + "\npassword=" + token + "\n\n"
    try:
        stored = subprocess.run(["git", "credential-" + helper, "store"], input=fields, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if stored.returncode:
            raise RuntimeError("系统凭证管理器未能保存凭证，请检查钥匙串或系统凭证管理器状态。")
        for args in [
            ["config", "--local", "--replace-all", "credential.helper", ""],
            ["config", "--local", "--add", "credential.helper", helper],
            ["config", "--local", "credential.useHttpPath", "true"],
            ["config", "--local", "credential.username", username],
        ]:
            git(*args, check=True)
    finally:
        fields = ""
        token = ""
    print("本机配置完成。令牌由系统凭证管理器保存，仓库文件中不包含令牌。")
    print("以后可在此目录执行 git pull / git push。服务端仍会按令牌权限与有效期校验。")
    print("如果令牌已公开或泄露，应到 GitHub 撤销并更换，再重新运行本脚本。")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print("配置未完成：" + str(error), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\n已取消，未完成的操作请检查后重试。", file=sys.stderr)
        sys.exit(1)

