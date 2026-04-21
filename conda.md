## 1. Conda 更改下载地址（更换国内镜像源）

**解决方案**：

- 使用命令行添加清华镜像源：

  ```
    conda config --remove-key channels
   
   # 2. 添加清华 conda-forge 频道作为首要源
   conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
   # 3. 添加清华主频道
   conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
   conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r/
   conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2/
   # 4. 可选：添加 PyTorch 等专用频道
   conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/
   # 5. 设置频道优先级为 strict（严格模式）[2†L14-L16][7†L18-L20]
   conda config --set channel_priority strict
   # 6. 设置显示频道来源（方便排查问题）[4†L6]
   conda config --set show_channel_urls yes
   # 7. 清理索引缓存，使新配置立即生效[3†L5-L6][8†L6-L7]
   conda clean -i
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

或者直接绕过conda直接在**type**选项中选择 `python`或者`system`，下边的直接选择需要使用的环境的目录中的`python.exe`

### 6. conda解析慢

1. 开启Conda自带的libmamba求解器（最直接），Conda 23.9 版本起，libmamba已成为默认求解器。如果版本较旧，可以按以下步骤启用：

    ```cmd
    # 在base环境中安装libmamba求解器插件
    conda install --name base conda-libmamba-solver
    # 将其设置为默认求解器
    conda config --set solver libmamba
    ``` 

2. 直接使用Mamba（性能更强）
Mamba是一个用C++重写的、完全兼容Conda的命令行工具，其依赖解析速度比原生Conda快2-10倍。对于经常需要处理复杂环境或大型项目来说，这是个很好的选择。
Mamba比libmamba性能更强
    ```cmd
    # 在base环境中安装mamba
    conda install mamba -n base -c conda-forge
    
    # 之后，只需将命令中的'conda'替换为'mamba'即可
    mamba install <package_name>
    ```

