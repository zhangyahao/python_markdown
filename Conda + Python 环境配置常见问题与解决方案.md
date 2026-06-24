# Conda + Python 环境配置常见问题与解决方案

## 文档说明
本文档整理了在 Windows 系统下使用 Conda 配置 Python 项目环境过程中遇到的典型问题及解决方案，涵盖环境管理、依赖安装、编译工具、命令兼容性等常见踩坑点。

---

## 1. PowerShell 脚本执行策略限制

### 问题现象
```powershell
. : 无法加载文件 C:\Users\xxx\Documents\WindowsPowerShell\profile.ps1，因为在此系统上禁止运行脚本。
```

### 原因分析

Windows PowerShell 默认执行策略为 `Restricted`，禁止运行任何脚本文件。Conda 在初始化时会修改 `profile.ps1`，需要执行脚本才能正常激活环境。

### 解决方案

以**管理员身份**运行 PowerShell，执行以下命令：

powershell

```powershell
# 修改执行策略为 RemoteSigned（允许本地脚本运行）
Set-ExecutionPolicy RemoteSigned
```



或仅修改当前用户策略：



```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

执行后输入 `Y` 确认，重启 PowerShell 即可。

## 2. Conda 环境激活后提示符不显示环境名称

### 问题现象

在 PowerShell 中执行 `conda activate env_name` 后，命令行前缀没有出现 `(env_name)` 标识，但在 CMD 中正常。

### 原因分析

PowerShell 的提示符修改功能需要 Conda 的初始化模块支持。`conda init powershell` 可能未正确执行，或执行策略限制导致初始化脚本未生效。

### 验证环境是否实际激活

powershell

```powershell
conda info --envs
```



查看当前激活环境前是否有 `*` 号，有则表示环境已激活，只是提示符未更新。

### 解决方案



```powershell
# 重新初始化 Conda
conda init powershell

# 重启 PowerShell 窗口后重试
conda activate env_name
```

## 3. `pip install -r requirements.txt` 报错：找不到指定版本

### 问题现象

text

```
ERROR: Could not find a version that satisfies the requirement click==8.2.1
ERROR: No matching distribution found for numpy==2.3.1
ERROR: No matching distribution found for onnxruntime==1.22.1
```



### 原因分析

项目的 `requirements.txt` 中指定的版本号在 PyPI 上不存在。常见原因：

- 作者使用了未发布的预发布版本
- 版本号写错
- 该版本已被移除或 yanked

### 解决方案

将所有 `==` 固定版本改为 `>=` 兼容范围：

## 4. Microsoft Visual C++ 14.0 编译错误

### 问题现象

text

```
error: Microsoft Visual C++ 14.0 or greater is required.
Failed to build wheel for greenlet
Failed to build installable wheels for some pyproject.toml based projects
```



### 原因分析

部分 Python 包（如 `greenlet`、`numpy`、`scipy`）在安装时需要从源码编译，而 Windows 系统缺少 C++ 编译工具链。

### 解决方案

**方案一：安装 Visual Studio Build Tools（推荐，一劳永逸）**

1. 访问 [Visual Studio 下载页面](https://visualstudio.microsoft.com/downloads/)
2. 找到“Visual Studio 2022”下的“**Build Tools**”并下载
3. 安装时勾选“**使用C++的桌面开发**”
4. 完成后重启终端，重新执行 `pip install`

**方案二：安装 Visual C++ Redistributable（快速尝试）**

- 下载并安装 [VC_redist.x64.exe](https://aka.ms/vc14/vc_redist.x64.exe)
- 如果问题依旧，需使用方案一

**方案三：使用 Conda 替代 Pip**



```powershell
conda install greenlet
```



Conda 通常会提供预编译的二进制包，可绕过编译过程。

**方案四：使用预编译 Wheel 文件**

1. 访问 https://www.lfd.uci.edu/~gohlke/pythonlibs/
2. 下载与 Python 版本匹配的 `.whl` 文件
3. 执行 `pip install 文件名.whl`

## 5. Conda / Pip 命令找不到或无法执行

### 常见场景

- `conda` 命令在 CMD 中找不到
- 在特定目录下无法激活环境
- 环境变量配置问题

### 解决方案

确保 Conda 已正确安装，并执行以下命令初始化：



```powershell
# 激活基础环境
conda init

# 针对 PowerShell 特殊初始化
conda init powershell

# 重启终端后生效
```



### 环境变量问题

如果 `conda` 命令仍不可用，手动检查环境变量 `PATH` 是否包含 Conda 的安装目录：