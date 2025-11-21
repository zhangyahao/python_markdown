# d设置默认源

1. 查看pip的配置文件

   ```cmd
       pip config list -v
   ```
   该命令会显示多行配置文件路径，

    - 站点配置（site-config）：针对整个系统生效，但可以被用户配置覆盖。
    - 用户配置（user-config）：针对当前用户生效，可以被环境变量覆盖。
    - 全局配置（global-config）：通常是指通过环境变量或命令行参数设置的配置，优先级最高。
2. 查看目前有效的配置文件

   ```cmd
      pip config list
   ```
   若显示出相关路径可更改其显示文件，若没有则表示pip使用默认文件

    - 未显示路径直接使用命令行进行修改
      ```cmd
          # 设置默认镜像源（以清华源为例）
          pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
          # 设置信任主机（避免SSL警告）
          pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
          # 可选：设置超时时间
          pip config set global.timeout 120
      ```
3. 常用源

| 镜像源名称	 | 镜像源 URL                                      |
|--------|----------------------------------------------|
| 清华源    | https://pypi.tuna.tsinghua.edu.cn/simple     |
| 阿里源    | https://mirrors.aliyun.com/pypi/simple/      |
| 豆瓣源    | https://pypi.douban.com/simple/              |
| 腾讯源	   | http://mirrors.cloud.tencent.com/pypi/simple |
| 中科大源   | https://pypi.mirrors.ustc.edu.cn/simple/     |