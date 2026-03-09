`pip install matplotlib -i https://pypi.tuna.tsinghua.edu.cn/simple/`

# 数据可视化

### pycharm设置

pycharm设置：如果只是看结果，不需要对pycharm进行专门的设置。如果需要对结果进行拖动查看，需要设置`Show plots in tool window`/
`在工具窗口中显示绘图`勾选去掉

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
  - 通用设置
      * 设置标题
        `plt.title()`
      * 设置x/y轴标题
        `plt.xlabel(标题)` 和`plt.ylabel(标题)`
      * 设置x/y轴坐标显示
        `plt.xticks()`和`plt.yticks()`
          1. 如果值过长导致文字重叠可以将文字旋转。 `plt.xticks(rotation=45)` 旋转45°
          2. 轴过长或过短导致数据不直观。 `plt.xticks(np.arange(90,210,10))` 表示起始位置90，结束210（不包含该值），步长显示10
      *  设置x/y轴数据显示范围（坐标轴范围）
         ```python 
            import matplotlib.pyplot as plt
             plt.xlim(0, 10)          # x 轴显示 0 到 10
             plt.ylim(0, 10)          # y 轴显示 0 到 10
             # 或者只设置一边
             plt.xlim(left=0)         # 左边界为 0，右边界自动 
             plt.ylim(left=0)         # 左边界为 0，右边界自动 
             plt.xlim(right=100)      # 右边界为 100
             plt.ylim(right=100)      # 右边界为 100
         ```
      * 显示图例
        `plt.legend()`
        * 对一些需要展示数据的图展示数据（柱状图/条形图等）
           使用循环对数据点进行标注
            ```
                  for x,y in zip(x, y1):
                           plt.text(x=x,y=y,s=y,ha='center',va='bottom')
            ```
            ha:数据水平展示位置。
            va:数据垂直位置位置
- 折线图数据设置
  `plt.plot(x,y,color='r',marker='*',linestyle='--')`
  参数含义：
    * marker ：折现点标记
    * color : 颜色。可取范围包括颜色十六进制代码或者一些常见颜色首字母（蓝色：b，绿色：g，红色：r，青色：c，品红：m，黄色：y，黑色：k，白色：y）
    * linestyle ： 线条类型

- 柱形图
  ` plt.bar(
       x,            # 水平坐标数组
       height,       # 柱状图高度数组
       width=0.8,    # 柱子的宽度, 默认 0.8
       bottom=None,  # 柱子的y轴起点位置
       color=None,   # 填充颜色，可根据柱子数量传入对应数量得颜色组成的数组
       label='',     # 图例文字
       alpha=0.2     # 透明度
   )`

* 注意：
    * 当bottom设置数值之后，在图例中数据展示时， plt.text 中得 y得值应该加上bottom值，因为y值展示时是默认从0开始得。
        1. bottom 是柱子底部的绝对坐标，不是相对偏移。
        2. 柱子占据的区间是 [bottom, bottom+height]。
        3. 数据标签的位置需要基于 bottom + height 来计算。

- 条形图
  `plt.barh`参数与柱形图基本一样
- 饼状图
  ```  
        plt.pie(x=None,   #饼状图数据/百分比标签
           labels=None,    # 分类标签
           autopct='%.2f%%',  #数据格式
           pctdistance=0.6, # 设置百分比标签（x值）距离圆心的距离，以半径 radius 的倍数为单位。
           labeldistance=1.1, #设置分类标签（由 labels 指定）距离圆心的距离，同样以半径倍数为单位。
           radius=1,  #饼图的半径大小。默认值为 1，数值越大饼图越大。
           explode=bins)  #突出位置，为数组表示突出 对应值倍的半径。例如bins=[0.05, 0.01, 0.01, 0.01, 0.01, 0.01] 表示第一个突出0.05倍半径，其他的0.01倍
  ```
- 散点图

# 绘制散点图
# plt.scatter
# x,y数据
# s:点的大小
# marker:点的标记
# edgecolors：边缘 轮廓颜色
# facecolor:填充色
# label:标签名称  可以显示图例
```
    plt.scatter(x,y,s=50,edgecolors='red',
           facecolor='white',
           marker='*',label='sample')
```
- 子图
    *  设置画布大小
        ` fig=plt.figure(figsize=(10,8),dpi=100)` 
    *  添加子图  
        `fig.add_subplot(2,2,1)`  表示将画布分成2行2列，在第一块画布上生成图
