pandas的Series可以直接出图。直接调用相关api。
### api
`Series.plot(kind='')`
* kind中包含的参数有：
📈 'line': 折线图 (默认值)  
📊 'bar': 垂直条形图  
📉 'barh': 水平条形图  
📊 'hist': 直方图  
📦 'box': 箱线图  
📊 'kde': 核密度估计图  
📊 'density': 与 'kde' 相同  
📈 'area': 面积图  
🥧 'pie': 饼图  
需要注意的是，'scatter'（散点图）和 'hexbin'（六边形图）这两个类型仅适用于 DataFrame，不能用于 Series 的绘图方法中。
其他通用设置直接使用matplotlib中通用设置