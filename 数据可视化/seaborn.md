1. 简介
   Seaborn 是基于 Matplotlib 的 Python 数据可视化库，提供了更简洁的 API 和美观的默认样式，
    2. 常用函数
        1. `histplot` 直方图
            - 作用
              绘制单变量或双变量（联合）直方图，并可叠加核密度估计、地毯图等。相比已弃用的 `distplot`，`histplot`
              提供了更丰富的参数和更清晰的语法，支持分面绘图和灵活的分组
                - 参数

                  | 参数            | 类型                | 说明                                                                                                   |
                                                                                                          |---------------|-------------------|------------------------------------------------------------------------------------------------------|
                  | `data`        | DataFrame / array | 数据源。                                                                                                 |
                  | `x`, `y`      | str / vector      | 指定变量。若只提供 `x`，绘制单变量直方图；若同时提供 `x` 和 `y`，则绘制二维直方图（用颜色表示频数）。                                            |
                  | `hue`         | str / vector      | 分组变量，按不同颜色绘制并列直方图。                                                                                   |
                  | `weights`     | str / vector      | 观测值的权重。                                                                                              |
                  | `stat`        | str               | 统计量：`'count'`（计数）、`'frequency'`（频率）、`'probability'`（概率，和为 1）、`'percent'`（百分比）、`'density'`（密度，面积为 1）。 |
                  | `bins`        | int / list / str  | 直方图区间数或边界，也可传入 `'auto'`、`'fd'` 等规则。                                                                  |
                  | `binwidth`    | number            | 指定区间宽度（覆盖 `bins`）。                                                                                   |
                  | `discrete`    | bool              | 如果数据是离散值，设为 `True` 可让区间对齐到数据值。                                                                       |
                  | `kde`         | bool              | 是否叠加核密度估计曲线（仅单变量）。                                                                                   |
                  | `element`     | str               | 直方图的显示元素：`'bars'`（条形）、`'step'`（阶梯线）、`'poly'`（多边形填充）。                                                 |
                  | `fill`        | bool              | 是否填充条形内部，默认为 `True`。                                                                                 |
                  | `multiple`    | str               | 当使用 `hue` 时，控制分组直方图的显示方式：`'layer'`（叠加）、`'dodge'`（并列）、`'stack'`（堆叠）、`'fill'`（填充至 1）。                  |
                  | `common_norm` | bool              | 是否对所有组使用同一归一化，默认为 `True`。                                                                            |
                  | `common_bins` | bool              | 是否对所有组使用相同的区间划分，默认为 `True`。                                                                          |
                  | `log_scale`   | bool / number     | 是否对轴使用对数刻度。                                                                                          |
                  | `legend`      | bool              | 是否显示图例。                                                                                              |

        2. `distplot`分布直方图，已弃用

            - 作用
              绘制单变量分布的直方图，并可叠加核密度估计曲线（KDE）、地毯图（rug）或拟合参数分布，帮助观察数据的分布形状、集中趋势和异常值。
            - 参数详解

              | 参数          | 类型                | 说明                                    |
                                                                                     |:------------|:------------------|:--------------------------------------|
              | `a`         | Series / 1D array | 输入数据，可以是 Pandas Series、NumPy 数组或列表。   |
              | `bins`      | int / list / str  | 直方图的区间数量或边界，也可传入 `'auto'`、`'fd'` 等规则。 |
              | `hist`      | bool              | 是否绘制直方图，默认为 `True`。                   |
              | `kde`       | bool              | 是否叠加核密度估计曲线，默认为 `True`。               |
              | `rug`       | bool              | 是否在坐标轴上绘制数据点的小线段（地毯图），默认为 `False`。    |
              | `fit`       | scipy.stats 分布    | 拟合参数分布（如 `stats.norm`），并绘制其概率密度函数。    |
              | `color`     | matplotlib color  | 图形颜色。                                 |
              | `vertical`  | bool              | 是否垂直显示（即交换 x 轴和 y 轴），默认为 `False`。     |
              | `norm_hist` | bool              | 是否将直方图归一化为密度（面积和为 1），默认为 `False`。     |
              | `axlabel`   | str               | x 轴标签，若为 `False` 则不显示标签。              |
              | `label`     | str               | 图例标签（仅当 `kde` 或 `fit` 为 `True` 时有效）。  |

        3. `countplot`计数图
            - 作用
              用于分类变量，显示每个类别中观测值的数量（频数）。实际上是以条形图形式展示分类频数，非常适用于查看类别分布或比较不同组别的样本量。
            - 参数

              | 参数                    | 类型                  | 说明                                            |
                                                                       |:----------------------|:--------------------|:----------------------------------------------|
              | `x` / `y`             | str / vector        | 指定分类变量。若只传 `x`，则 x 轴为分类，y 轴为计数；若只传 `y`，则水平显示。 |
              | `hue`                 | str / vector        | 第二个分类变量，用于分组着色，产生并列的条形。                       |
              | `data`                | DataFrame           | 数据源，当 `x`、`y`、`hue` 传入字符串时需指定。                |
              | `order` / `hue_order` | list                | 指定分类的显示顺序。                                    |
              | `orient`              | 'v' / 'h'           | 强制指定垂直或水平方向（通常可自动推断）。                         |
              | `color`               | matplotlib color    | 所有条形的统一颜色（若未使用 `hue`）。                        |
              | `palette`             | palette name / list | 当使用 `hue` 时的颜色映射方案。                           |
              | `saturation`          | float               | 颜色的饱和度，默认为 0.75。                              |
              | `dodge`               | bool                | 当使用 `hue` 时，是否将条形分开（避免重叠），默认为 `True`。         |
              | `ax`                  | matplotlib Axes     | 绘制的坐标轴对象。                                     |

        4. `boxenplot`增强箱线图 / 字母值图
            - 作用
              类似于箱线图，但能展示更多分位数信息，尤其适用于大数据集。它绘制多个分位框（类似“字母值图”），让观察者更清晰地看到分布尾部的情况，而仅靠传统的箱线图可能掩盖多模态或尾部特征。
            - 参数

              | 参数                    | 类型              | 说明                                                                    |
                             |:----------------------|:----------------|:----------------------------------------------------------------------|
              | `x` / `y` / `hue`     | str / vector    | 数据映射，`hue` 用于分组。                                                      |
              | `data`                | DataFrame       | 数据源。                                                                  |
              | `order` / `hue_order` | list            | 分类顺序。                                                                 |
              | `orient`              | 'v' / 'h'       | 方向。                                                                   |
              | `color` / `palette`   | color / palette | 颜色设置。                                                                 |
              | `width`               | float           | 箱体的宽度（以轴为单位）。                                                         |
              | `dodge`               | bool            | 当使用 `hue` 时，是否将不同组的箱体分开。                                              |
              | `k_depth`             | str / int       | 计算“字母”（分位数层数）的方法，可选 `'proportion'`、`'tukey'`、`'trustworthy'` 或直接指定层数。 |
              | `linewidth`           | float           | 轮廓线的宽度。                                                               |
              | `scale`               | str             | 控制箱体宽度随层数变化的方式，可选 `'linear'`、`'exponential'`、`'area'`。                |
              | `fliersize`           | float           | 异常值点的大小。                                                              |
              | `whis`                | float           | 控制尾须的长度（类似箱线图的 whisker 参数）。                                           |

        5. `stripplot`散点条图
            - 作用
              将分类变量对应的数值数据以散点形式绘制，每个点代表一个观测值。可以很好地展示数据分布和样本量，常与箱线图或小提琴图叠加使用。通过抖动（jitter）避免点重叠。
            - 参数
           
                | 参数                    | 类型              | 说明                                              |
                |:----------------------|:----------------|:------------------------------------------------|
                | `x` / `y` / `hue`     | str / vector    | 数据映射。                                           |
                | `data`                | DataFrame       | 数据源。                                            |
                | `order` / `hue_order` | list            | 分类顺序。                                           |
                | `jitter`              | bool / float    | 是否添加随机抖动（避免重叠）。若为 `True`，抖动幅度约为 0.2；也可传入具体抖动宽度。 |
                | `dodge`               | bool            | 当使用 `hue` 时，是否将不同组的点沿分类轴分开。                     |
                | `orient`              | 'v' / 'h'       | 方向。                                             |
                | `color` / `palette`   | color / palette | 颜色。                                             |
                | `size`                | float           | 点的大小。                                           |
                | `edgecolor`           | color           | 点的边缘颜色。                                         |
                | `linewidth`           | float           | 点边缘线的宽度。                                        |
                | `marker`              | str             | 点的形状，默认为圆形 `'o'`。                               |
                | `alpha`               | float           | 点的透明度。                                          |
