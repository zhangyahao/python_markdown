# 下载

1. 注意使用版本
2. 除了本体外还需要相关的贡献库
3. `pip install opencv-python==4.5.5.64 -i https://pypi.tuna.tsinghua.edu.cn/simple`
4. `pip install opencv-contrib-python==4.5.5.64 -i https://pypi.tuna.tsinghua.edu.cn/simple`

# 常用函数

1. 读取图片

    - 读取原图

      ```
         cv2.imread("路径值绝对路径/相对路径")
      ```
    - 读取为灰度图

      ```
      cv2.imread("路径值绝对路径/相对路径",0)
      ```

    1. 读取图片是三维数组，形状为高、宽、bgr通道数（注意不是rgb）或者高、宽、灰度图单通道
    2. 灰度图很难回转为彩色图。
2. 展示图片

   ```python
     cv2.imshow("test",im)
     cv2.waitKey()
   ```

   参数需要图片名和读取的三维数组，展示完成后需要使用waitKey来使图片保留展示
3. 保存图片

   ```python
       cv2.imwrite("路径地址", im)
   ```
4. 图片销毁/关闭

   ```python
    cv2.destroyWindow("test")

    cv2.destroyAllWindows()

   ```

   两种关闭方式

    - 指定特定图片销毁  `cv2.destroyWindow("test")`
    - 销毁所有图片  `cv2.destroyAllWindows()`
5. 简单的图片处理

    - 转换图片色彩空间
      ```python
 
       cv2.cvtColor(cv2.imread(),cv2.COLOR_RGB2HSV)
      ```
      其他色彩空间转换类似 xxx2xxx
    - 镜像转换  
      `cv2.flip(im,0)`  
      0:垂直镜像/上下颠倒  
      1:水平镜像/左右颠倒  
      -1:水平垂直同时颠倒
    - 缩放偏移  
      `cv2.warpAffine(cv2.imread(),M,(w,h))`    
      M为 2*3矩阵。
      ```text
        M=[ [x轴缩放量1为不缩放，xy剪切量0为并不剪切，x偏移量]，
            [yx剪切量0为并不剪切,y轴缩放量1为不缩放,y轴偏移量]
          ]
      ```
      一般不进行缩放和剪切操作
    - 图片相加  
      注意图片相加时，两张图片的长宽通道值都必须相同，不然无法执行。
        * 直接相加 ` cv2.imread()+cv2.imread()`    
          是NumPy数组的加法操作。当结果超过最大值时，它会执行取模运算（类似于取余数）。例如，250 + 10 = 260，对256取模后，260 %
          256 = 4。这会导致本应很亮的像素点突然变暗，图像看起来不自然。
        * cv2提供的`cv2.add(im1,im2)`  
          相加像素点相加，当像素值相加结果超过当前数据类型能表示的最大值（例如8位无符号整型的最大值255）时，cv2.add()
          会将结果设置为该最大值（255）。这符合图像处理的常规需求，能避免过度曝光导致的信息丢失，让合成图像看起来更自然。
        * 权重相加 `cv2.addWeighted(im1,权重,im2,权重,伽马值)`
    - 图片相减  
      ` cv2.imread()-cv2.imread()`   
      `cv2.subtract(im1,im2)`
      主要用于查找图片不同，实际操作意义不大
    - 图片腐蚀/膨胀

      |    特性    | 腐蚀 (Erosion)  | 膨胀 (Dilation)  |
       |:--------:|:-------------:|:--------------:|
      |  **效果**  |    缩小前景物体     |     扩大前景物体     |
      |  **边界**  |     向内收缩      |      向外扩展      |
      | **小物体**  |    消除小的孤立点    |     连接相邻物体     |
      |  **应用**  |   去除噪声、分离物体   |   填补空洞、连接断点    |

        1. 需要指定区域一般为奇数范围区域基于numpy使用。3*3/5*5/7*7 。 `kernel = np.ones((3, 3), np.uint8)`
        2. `iterations`腐蚀/膨胀次数
        3. 写法都类似。腐蚀： `cv2.erode(im, kernel, iterations=3)`膨胀`cv2.dilate(im, kernel, iterations=3)`

    - 图片开运算/闭运算
      开运算：
        - 先腐蚀后膨胀
        - 效果：消除小物体，平滑边界
        - 应用：去除小噪声，同时保持主要物体大小基本不变
        - `cv2.morphologyEx(im, cv2.MORPH_OPEN, kernel,iterations=3)`
          闭运算：
        - 先膨胀后腐蚀
        - 效果：填充小空洞，连接邻近物体
        - 应用：填补物体内部空洞，连接断裂部分
        - `cv2.morphologyEx(im2, cv2.MORPH_CLOSE, kernel,iterations=5)`
    - 二值化  
      将灰度图像转换为只有黑白两种颜色的图像。
      ```python
            retval, dst = cv2.threshold(src, thresh, maxval, type)
      ```
      ```python
         # 1. 二进制阈值
         ret1, thresh1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
      ```   
      处理逻辑：
        - 像素值 > 阈值 → 设为最大值（255）
        - 像素值 ≤ 阈值 → 设为0
      效果：创建纯粹的黑白二值图像
      应用：标准的二值分割、轮廓检测
      ```python
         # 2. 反二进制阈值
         ret2, thresh2 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
      ```   
      处理逻辑：
        - 像素值 > 阈值 → 设为0
        - 像素值 ≤ 阈值 → 设为最大值（255）
      效果：反转的黑白图像
      应用：当背景比前景亮时、某些特定检测任务
      
      ```python
         # 3. 截断阈值
         ret3, thresh3 = cv2.threshold(gray, 127, 255, cv2.THRESH_TRUNC)
      ``` 
      处理逻辑：
        - 像素值 > 阈值 → 设为阈值本身（127）
        - 像素值 ≤ 阈值 → 保持不变
      效果：压缩高亮区域，保留暗部细节
      应用：动态范围压缩、高光抑制
      
      ```python
        # 4. 阈值化为0
        ret4, thresh4 = cv2.threshold(gray, 127, 255, cv2.THRESH_TOZERO)
      ```   
      处理逻辑：
        - 像素值 > 阈值 → 保持不变
        - 像素值 ≤ 阈值 → 设为0
      效果：保留亮部区域，消除暗部
      应用：提取亮特征、文本增强
      ```python
           # 5. 反阈值化为0
           ret5, thresh5 = cv2.threshold(gray, 127, 255, cv2.THRESH_TOZERO_INV)
      ```
      处理逻辑：
        - 像素值 > 阈值 → 设为0
        - 像素值 ≤ 阈值 → 保持不变
      效果：保留暗部区域，消除亮部
      应用：提取暗特征、阴影分析
      
      阈值中**127**一般为经验值，也可以自动计算设置搭配自动计算使用
      `cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)`
      `cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)`
    - 图片的其他处理方式
      #### 高斯滤波
        1. 工作原理
            * 用像素点周围邻域内所有像素的高斯加权平均值替代该像素值
            * 中心像素权重最大，越远权重越小
        2. 特点：
            * 对高斯噪声效果最好
            * 平滑效果好，边缘保护优于均值滤波
            * 可调节标准差控制平滑程度
            * 计算复杂度较高
            * 对椒盐噪声效果有限
        3. 函数：
           ` cv2.GaussianBlur(img, (ksize, ksize), sigmaX,sigmaY)` sigmaX/sigmaY表示在x/y轴上的偏移量，控制模糊强度，一般设置为0表示自动计算。
      #### 中值滤波
        1. 工作原理：
            * 用像素点周围邻域内所有像素的中值替代该像素值
            * 先排序，取中间值
        2. 特点：
            * 有效去除椒盐噪声
            * 保护边缘信息
            * 非线性处理，不产生新像素值
            * 计算量相对较大（需要排序）
            * 对高斯噪声效果一般
        3. 函数
           ` cv2.medianBlur(img, ksize)`
      #### 均值滤波
        1. 工作原理：
            * 用像素点周围邻域内所有像素的算术平均值替代该像素值
            * 核内所有位置权重相等
        2. 特点：
            * 计算简单快速
            * 对随机噪声有一定效果
            * 严重模糊边缘和细节
            * 对椒盐噪声效果差
        3. 函数实现
           ```python
               cv2.blur(img, (ksize, ksize))
                # 或
               cv2.boxFilter(img, -1, (ksize, ksize))
           ```
      #### 总结
      |     场景      | 推荐方法  |     理由     |
      |:-----------:|:-----:|:----------:|
      | **快速简单去噪**  | 均值滤波  |   计算速度最快   |
      |  **椒盐噪声**   | 中值滤波  | 专门针对孤立噪声点  |
      |  **高斯噪声**   | 高斯滤波  |  最优的平滑效果   |
      | **边缘保护重要**  | 中值滤波  |  最佳边缘保护能力  |
      |  **实时处理**   | 高斯滤波  |  效果和速度平衡   |
      | **未知噪声类型**  | 中值滤波  |   通用性最好    |
      
      #### 注意
       高斯滤波和均值滤波中参数ksize为**奇数元组**，中值滤波中ksize为**int**
    