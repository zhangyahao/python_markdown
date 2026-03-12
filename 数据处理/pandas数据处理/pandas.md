# 基础信息

* 版本基本不限定，一般配合numpy组合使用
* `pip install pandas -i https://pypi.tuna.tsinghua.edu.cn/simple/`

# pandas创建的数组和字典的区别

| 特性维度        | Python 字典 (dict)       | pd.Series                                 |
|:------------|:-----------------------|:------------------------------------------|
| **数据结构与用途** | 通用的键值对映射，用于快速查找和管理关系数据 | 带标签的一维数组，专为数值计算和数据分析设计                    |
| **索引特性**    | 键是**无序**且唯一的           | 索引是**有序**的，允许重复                           |
| **数据操作**    | 操作基于键，通常使用循环或推导式       | **向量化操作**：支持对整个Series进行数学运算，并支持**自动索引对齐** |
| **数据类型**    | 值可以是任意Python对象         | 数据通常是**同构**的，效率更高，并支持缺失值处理                |
| **性能表现**    | 适合快速的单点查找和增删           | 为批量数值计算优化，在大数据量时运算效率更高                    |

# 转换注意

- 如果转换list，list中包换多种数据类型，例如同时包含字典、数组、元组。转换时对字典只保留key，同时数字类型转为float。
- `pd.Series()`生成的对象是一维结构，不存在行列概念。
- 数据删除方式
    - del dataframe[["columnName1","columnName2"]]
    - dataframe.pop(["columnName1","columnName2"])
    - dataframe.drop(["columnName1","columnName2"],axis=1,inplace=true) 需要指定删除的数据范围，行列，以及是否对元数据进行操作。axis默认为0，
      **0为行，1为列**。inplace表示是否对源数据进行操作，默认为**false**，若为true直接删除。

# dataframe数据获取

| 维度       | `loc` - 标签索引                | `iloc` - 位置索引             |
|:---------|:----------------------------|:--------------------------|
| **索引基础** | 基于**标签名** (index/columns名称) | 基于**整数位置** (0, 1, 2, ...) |
| **设计理念** | 语义化索引，贴近现实世界                | 程序化索引，贴近计算机底层             |
| **切片行为** | **包含**结束位置 (`a:c` 包含c)      | **不包含**结束位置 (`0:3` 不包含3)  |
| **数据类型** | 索引可以是任意类型                   | 索引必须是整数                   |
| **容错性**  | 标签不存在会报`KeyError`           | 位置越界会报`IndexError`        |

# 常用api

### Series

1. Series数据类型
   `pd.Series(可迭代对象,pd.Series(sales_data,index=['<UNK>','<UNK>','<UNK>','<UNK>']))`
   或者
   `pd.Series(可迭代对象,pd.Series(sales_data,index=list( "abc")))`
2. Series数据类型数据是可以使用str来调用string api进行数据修改
   注意：在pycharm中可能存在无法提示str后api情况。
   解决方案：
    * 安装pandas类型存根
       ```cmd
           pip install pandas-stubs
       ```
    * 临时解决方案
      ```pd.Series(sales_data,index=['<UNK>','<UNK>','<UNK>','<UNK>']) #type pd.Series```
    * pandas和pandas-stubs**版本必须匹配**
    * 测试过后能提示的版本为 **pandas1.5.** * 和 **pandas-stubs1.5.* **
      。版本超过3之后，pandas-stubs要求python版本3.10以上。但是版本2.*仍然不能提示，目前稍尚未解决
3. 映射关系 `map`/ `replace`
   将Series中的数据映射。

    ```python
      import pandas as pd
      usr_act = pd.Series(data=[1, 1, 2, 3, 4, 2, 1])
      act_info = {1: 'pv 浏览', 2: 'cart 加购物车', 3: 'collect 收藏', 4: 'buy 购买'}
      act_info_en = {k: v.split()[0] for k, v in act_info.items()}  # 英文映射关系map
      usr_act = usr_act.map(act_info_en)  # 映射结果
    ```
   映射注意：map映射是`类型严格匹配`，必须同类型，在实际使用过程中，遇到了 `np.int64` 匹配 `int` 后数据出现错误的情况
   大数据的情况下推荐使用`replace`，它不仅避免了类型严格匹配的问题，而且性能通常也优于 map（尤其是对大数据集）
4. 筛选数据是否存在 `Series.isin`
5. 数据去重 `Series.unique()`
6. 去重后类别计数 `Series.nunique()`
7. 分类技术 `Series.value_count()`
8. 行选择器 `Series.ioc(行选择条件)`  
   行选择条件可以使用:
    * 选择单个标签 `s.loc['b']`
    * 选择标签列表  `s.loc[['a', 'c']]`
    * 标签切片（包含结束标签） `s.loc['b':'c']   # 返回 b 20, c 30（包含 'c'）`
    * 使用布尔 Series `s.loc[s > 20]    # 返回值大于 20 的元素（c 30, d 40）`
    * 使用可调用函数 `s.loc[lambda x: x.index >= 'b']`
    * 修改数据 `s.loc['a'] = 100   # 将标签 'a' 对应的值改为 100`或者`s.loc[['b', 'c']] = [200, 300]  # 同时修改多个`

### DataFrame

1. 转换为DataFrame
   `pd.DataFrame(可迭代对象, columns=['<UNK>','<UNK>','<UNK>','<UNK>'])`
2. 获取DataFrame中最大值/最小值id
   最大值`df[index].idxmax()`
   最小值`df[index].idxmin()`
3. 将DataFrame中的某个值四舍五入
   `df[index].round(1)`
4. 行列选择器 `df.loc[行选择条件, 列选择条件]`
   是一种用于基于标签选择数据的方法。这里的逗号用于分隔行和列的选择：
    - 逗号前：指定要操作的行。
    - 逗号后：指定要操作的列。
    - 例如：
       ```python
             import pandas as pd
             data = {
                '学生ID': ['001', '002', '003', '004', '005', '006', '007', '008'],
                '姓名': ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十'],
                '年龄': [18, 19, 18, 20, 19, 18, 20, 19],
                '性别': ['男', '女', '男', '女', '男', '女', '男', '女'],
                '成绩': [85, 92, 78, 88, 95, 82, 90, 85],
                '科目': ['数学', '英语', '数学', '英语', '物理', '化学', '数学', '英语']
              }
              df = pd.DataFrame(data)
              df.loc[df['姓名'] == '张三', '姓名'] = '李三' # 将张三姓名修改为李三
      ```
5. 数据聚合
   数据聚合是指对一组数据执行汇总计算，例如求和、平均值、最大值等。在 Pandas 中，DataFrame 提供了丰富的聚合函数，可以沿着行（axis=0）或列
   （axis=1）方向进行计算。理解 axis 参数是正确使用聚合函数的关键。
   | 函数 | 说明 | 默认 axis | 常用场景 |
   |:-------|:-------------|:--------|:-------------|
   | `sum`  | 求和 | 0 | 计算总分、总销售额 |
   | `mean` | 求平均值 | 0 | 计算平均分、平均价格 |
   | `max`  | 最大值 | 0 | 找出最高分、最大销量 |
   | `min`  | 最小值 | 0 | 找出最低分、最小库存 |
   | `std`  | 标准差 | 0 | 找出标准差 |
   | `all`  | 检查是否全部为 True | 0 | 筛选全部满足条件的行或列 |
   | `describe`  | 描述性统计摘要 | 0 | 能够快速查看数据的分布情况、中心趋势、离散程度等关键指标 |
   需注意，在所有得聚合函数内都需要明确聚合方向。例如 `df.sum(axis=1)`

### 总结

* loc使用index和Colum来确定数据范围，iloc使用行和列的index来确定数据
* 使用两种编程思维的方式是因为index是可以重复的，可以防止误操作，以及对数据的修改确定性（个人理解）
* `loc`和`iloc` 属于pandas的通用解决办法，可能会导致数据数据循环依赖导致数据修改失败。推荐使用`at`和`iat`
* `at`和`iat`始终直接操作原始 DataFrame
  的单个元素，不会产生歧义。[详解](https://github.com/zhangyahao/python_markdown/blob/master/%E6%95%B0%E6%8D%AE%E5%A4%84%E7%90%86/pandas%E6%95%B0%E6%8D%AE%E5%A4%84%E7%90%86/Pandas%20%E7%B4%A2%E5%BC%95%E6%96%B9%E6%B3%95%20loc%E3%80%81iloc%E3%80%81at%E3%80%81iat%E5%8C%BA%E5%88%AB%E4%BD%9C%E7%94%A8.md)
