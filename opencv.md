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
