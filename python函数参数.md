## 1. **位置参数（Positional Arguments）**
最基本的参数传递方式
```python
def greet(name, greeting):
    print(f"{greeting}, {name}!")

greet("Alice", "Hello")  # Hello, Alice!
```
## 2. **关键字参数（Keyword Arguments）**

指定参数名传递，顺序无关
```python
def greet(name, greeting):
    print(f"{greeting}, {name}!")

greet(greeting="Hi", name="Bob")  # Hi, Bob!
greet(name="Charlie", greeting="Hey")  # Hey, Charlie!
```
## 3. **默认参数（Default Arguments）**
参数有默认值，调用时可省略
```python
def greet(name, greeting="Hello", punctuation="!"):
    print(f"{greeting}, {name}{punctuation}")

greet("Alice")           # Hello, Alice!
greet("Bob", "Hi")       # Hi, Bob!
greet("Charlie", "Hey", ".")  # Hey, Charlie.
```
## 4. **序列传参**，实参使用`*`号拆解，拆解后的数据和形参位置对应，注意实参必须时可迭代数据，且数量一致。

## 5. **可变位置参数（\*args）也叫做（*号元组形参）**

接收任意数量的位置参数
```python
def sum_all(*args):
    return sum(args)

print(sum_all(1, 2, 3))        # 6
print(sum_all(1, 2, 3, 4, 5))  # 15

# 结合其他参数
def concat(separator, *args):
    return separator.join(args)

print(concat("-", "a", "b", "c"))  # a-b-c
```

## 6. **可变关键字参数（**kwargs）**

接收任意数量的关键字参数
```python
def print_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=30, city="NYC")
# name: Alice
# age: 30
# city: NYC

# 混合使用
def register_user(username, password, **extra_info):
    user = {"username": username, "password": password}
    user.update(extra_info)
    return user

user = register_user("alice", "123456", email="alice@example.com", role="admin")
```



**注意**：函数调用时，若混合使用位置传参和关键字传参，python优先匹配位置参数，后匹配关键字参数

### 函数参数等寻找

 ```python
    import inspect
  
    inspect.signature(方法)
 ```
