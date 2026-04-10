## 一、张量（Tensor）基础

### 1. 创建张量

python

```
import torch
import numpy as np

# 从标量、列表、NumPy 数组创建
tensor = torch.tensor(5)                 # 标量
tensor = torch.tensor([1, 2, 3])         # 列表
ary = np.arange(1, 10).reshape(3, 3)
tensor = torch.tensor(ary)               # NumPy 数组

# 使用 torch.Tensor（旧式API，传入 shape）
tensor = torch.Tensor(5)          # shape (5,)
tensor = torch.Tensor(2, 3)       # shape (2, 3)
tensor = torch.Tensor((2, 3))     # 元素为 (2, 3) 的张量

# 指定数据类型
torch.FloatTensor(1, 3)           # 32位浮点，shape (1,3)
torch.DoubleTensor((1, 3))        # 64位浮点
torch.LongTensor(1, 3)            # 64位整数
torch.IntTensor((1, 3))           # 32位整数
```

### 2. 固定值与随机张量

python

```
# 全0 / 全1
zeros = torch.zeros(2, 3)                # shape (2,3)
ones = torch.ones(2, 3)                  # shape (2,3)

# 模仿已有张量的形状/类型
ones_like = torch.ones_like(tensor)
zeros_like = torch.zeros_like(tensor)

# 均匀分布 [0,1)
rand = torch.rand(size=(1, 5))

# 标准正态分布
randn = torch.randn(size=(2, 2))

# 指定均值和标准差的正态分布
normal = torch.normal(mean=0.5, std=2.0, size=(3, 3))
```

### 3. 类型转换与判断

python

```
# 判断是否为张量
torch.is_tensor(obj)

# 转换类型
tensor = tensor.int()                    # 转为 int32
tensor = tensor.type(torch.int32)        # 同上
```

### 4. 张量与 NumPy 互转

python

```
# NumPy → Tensor
ary = np.arange(1, 10)
tensor = torch.from_numpy(ary)           # 共享内存

# Tensor → NumPy
ary = tensor.numpy()                     # 共享内存
ary = np.array(tensor)                   # 拷贝
```

> **注意**：`torch.from_numpy()` 与 `tensor.numpy()` 与原数组共享内存，修改一方会影响另一方。

### 5. 形状变换

python

```
tensor = torch.arange(1, 10)             # shape (9,)
tensor.reshape(3, 3)                     # 返回新视图
torch.reshape(tensor, (3, 3))            # 等价
```

### 6. 原地操作（in-place）

python

```
a = torch.tensor([200])
b = torch.tensor([300])
a.add_(b)        # a += b
a.sub_(b)        # a -= b
```

------

## 二、张量的组合与拆分

### 1. 组合 – `cat`

python

```
tensor_x = torch.Tensor(2, 2)
tensor_y = torch.Tensor(2, 2)

# 按维度 0（行）拼接 → (4,2)
torch.cat([tensor_x, tensor_y], dim=0)

# 按维度 1（列）拼接 → (2,4)
torch.cat([tensor_x, tensor_y], dim=1)
```

### 2. 拆分 – `chunk` 与 `split`

python

```
tensor = torch.Tensor(5, 3)

# 等份拆分，指定份数
x, y = torch.chunk(tensor, 2, dim=0)   # 两个 (2或3, 3)

# 按指定大小拆分
res = torch.split(tensor, split_size_or_sections=2, dim=1)
for i in res:
    print(i.shape)
```

------

## 三、梯度机制与自动求导

### 1. `requires_grad` 属性

python

```
# 创建时需要梯度的张量
w = torch.randn(3, 5, requires_grad=True)

# 由需要梯度的张量计算得到的新张量也会自动开启梯度
y = w * 2
print(y.requires_grad)   # True
```

### 2. 关闭/打开梯度上下文

python

```
# 方式1：with 语句
with torch.no_grad():
    y = w * 2            # y.requires_grad = False

# 方式2：装饰器
@torch.no_grad()
def func(x):
    return x * 2

# 方式3：全局开关
torch.set_grad_enabled(False)   # 关闭梯度
torch.set_grad_enabled(True)    # 打开梯度
```

### 3. 自动求导 – `backward()`

#### 标量输出

python

```
x = torch.tensor([[1.0, 2.0, 3.0]])   # 叶子节点，不需梯度
w = torch.randn(3, 5, requires_grad=True)
b = torch.ones(5, requires_grad=True)

y = torch.matmul(x, w)                # (1,5)
z = torch.add(y, b)
loss = torch.sum(z)                   # 标量

loss.backward()                       # 自动求导
print(w.grad)                         # 梯度
print(b.grad)
```

#### 非标量输出

python

```
z = torch.add(y, b)                   # shape (1,5) 非标量
g = torch.ones_like(z)                # 外部梯度
z.backward(gradient=g)                # 传入梯度
```

### 4. 梯度清零

python

```
optimizer.zero_grad()                 # 优化器方式
# 或手动
w.grad.zero_()
```

------

## 四、模型搭建与训练

### 1. 继承 `torch.nn.Module`

python

```
class LinearRegression(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(1, 1)   # 输入1，输出1

    def forward(self, x):
        return self.linear(x)
```

### 2. 损失函数与优化器

python

```
model = LinearRegression()
criterion = torch.nn.MSELoss()                # 均方误差
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
```

### 3. 典型训练循环

python

```
for epoch in range(300):
    pred = model(x)               # 前向传播
    loss = criterion(pred, y)     # 计算损失
    loss.backward()               # 反向传播
    optimizer.step()              # 更新参数
    optimizer.zero_grad()         # 梯度清零
```

------

## 五、容器模块

### 1. `ModuleList` – 索引式容器

python

```
class ModelNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linears = torch.nn.ModuleList(
            [torch.nn.Linear(10, 10) for _ in range(3)]
        )

    def forward(self, x):
        x = self.linears[2](x)
        x = self.linears[0](x)
        x = self.linears[1](x)
        return x
```

### 2. `Sequential` – 顺序容器

python

```
self.conv_block = torch.nn.Sequential(
    torch.nn.Conv2d(3, 32, kernel_size=5),
    torch.nn.ReLU(),
    torch.nn.MaxPool2d(2, 2)
)
```

------

## 六、完整卷积网络示例

python

```
class CNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv_block = torch.nn.Sequential(
            torch.nn.Conv2d(3, 32, 5),      # 输入3通道，输出32，5x5卷积
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(2, 2),       # 2x2池化，步长2

            torch.nn.Conv2d(32, 64, 5),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(2, 2)
        )
        self.linears = torch.nn.Sequential(
            torch.nn.Linear(53*53*64, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, 10),
            torch.nn.Softmax(dim=1)
        )

    def forward(self, x):
        conv = self.conv_block(x)
        flat = torch.flatten(conv, start_dim=1)   # 除batch外展平
        out = self.linears(flat)
        return out
```

------

## 七、常见注意事项

| 知识点            | 说明                                                |
|:---------------|:--------------------------------------------------|
| **梯度传播规则**     | 只要计算路径上有一个输入需要梯度，输出就会自动开启梯度                       |
| **原地操作**       | 用 `_` 后缀（如 `add_`），可能破坏计算图，谨慎使用                   |
| **叶子节点**       | 用户直接创建的张量，非叶子节点的梯度默认不保存                           |
| **梯度累积**       | 默认梯度会累加，每次反向传播后需手动清零                              |
| **与 NumPy 互转** | 小数据量用 `torch.tensor(ary)`，大数据共享内存用 `from_numpy()` |
