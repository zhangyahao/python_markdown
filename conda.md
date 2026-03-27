## 1. Conda 更改下载地址（更换国内镜像源）

**解决方案**：

- 使用命令行添加清华镜像源：

  ```
  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
  conda config --set show_channel_urls yes
  ```
- 可选：添加 PyTorch、Bioconda 等频道。
- 验证：`conda info` 查看 channel URLs。
- 恢复默认源：`conda config --remove-key channels`。
- 补充：可同时更换 pip 源（如清华源）和考虑使用 `mamba` 加速。

## 2. 更改 Conda 环境文件本地地址（修改默认环境存储路径）

**解决方案**：

- **临时指定路径**（使用 `--prefix`）：

  ```
  conda create --prefix /path/to/envs/myenv python=3.9
  conda activate /path/to/envs/myenv
  ```
- **永久修改默认路径**（修改 `envs_dirs`）：

  ```
  conda config --add envs_dirs /your/new/envs/path
  ```

  查看结果：`conda config --show envs_dirs`。
- **环境变量临时修改**：

  - Linux/macOS：`export CONDA_ENVS_PATH=/new/path`
  - Windows：`set CONDA_ENVS_PATH=D:\new\path`
- 如果要使用Conda目录下得envs文件夹，更改该文件夹得权限

## 3. 修改包缓存目录（pkgs_dirs）

### 查看当前 pkgs 目录

```
conda config --show pkgs_dirs
```

### 永久修改 pkgs 目录

1. **添加新路径**（将以下命令中的路径替换为你希望的位置，例如 `e:/anaconda3/pkgs`）：

   ```
   conda config --add pkgs_dirs e:/anaconda3/pkgs
   ```

   该命令会将新路径添加到列表最前面，成为优先使用的缓存目录。
2. **验证修改**：

   ```
   conda config --show pkgs_dirs
   ```

   输出示例：

   ```
   pkgs_dirs:
     - e:/anaconda3/pkgs
     - C:\Users\Hasee\.conda\pkgs
     - C:\Users\Hasee\AppData\Local\conda\conda\pkgs
   ```

## 3. 删除已经创建的 Conda 环境

**问题描述**：如何彻底删除不再使用的 Conda 环境。

**解决方案**：

- **删除按名称创建的环境**：

  ```
  conda remove --name myenv --all
  # 或
  conda env remove --name myenv
  ```
- **删除按路径创建的环境**：

  ```
  conda env remove --prefix /path/to/env
  ```
- **手动删除**：若上述命令失败，可直接删除环境文件夹（位于 `envs_dirs` 下或自定义路径）。
- **注意事项**：删除前确保环境已停用 (`conda deactivate`)。

## 4. 解决Conda remove 后还剩余文件

**解决方案**：

1. **确保使用完整删除命令**：

   ```
   conda env remove --name env_name
   ```
2. **手动删除残留文件夹**：找到环境路径（通过 `conda env list`），直接删除整个目录。
3. **清理 Conda 缓存**：

   ```
   conda clean --all
   ```
4. **检查 `envs_dirs` 配置**：移除重复路径，避免混淆。
5. **终极方案**：备份 `.condarc` 后重置用户配置（删除 `.conda` 文件夹等）。
6. **预防**：以后删除环境始终使用 `conda env remove --name 环境名`。

## 5. 在 PyCharm 中配置 Conda

1. 配置conda 使用安装文件下得_conda.exe。可能存在不兼容导致无法加载环境得情况。
2. 使用 **System Interpreter**，直接指定目标环境中的 `python.exe` 路径。
3. 降级 Conda 到 24.x 版本：

```cmd
conda install -n base conda=24.11.3 --solver=classic
```
