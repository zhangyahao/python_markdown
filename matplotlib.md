`pip install matplotlib -i https://pypi.tuna.tsinghua.edu.cn/simple/`

# 数据可视化

### pycharm设置

pycharm设置：如果只是看结果，不需要对pycharm进行专门的设置。如果需要对结果进行拖动查看，需要设置`Show plots in tool window`/`在工具窗口中显示绘图`勾选去掉

### 重要参数设置

- 汉语支持
     ```python
        import matplotlib.pyplot as plt
         plt.rcParams['font.sans-serif'] = ['SimHei']
     ```
- 负号处理
  ```python
      import matplotlib.pyplot as plt
      plt.rcParams['axes.unicode_minus'] = False
  ```
