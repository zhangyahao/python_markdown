## 详解

GridSearchCV 是 scikit-learn 中用于超参数调优的交叉验证工具。它通过穷举指定的参数组合，对每组参数进行交叉验证评估，自动选出性能最佳的参数组合，
是机器学习模型调参的标准方法。

## 作用

模型的性能不仅取决于算法本身，还强烈依赖于超参数（如 KNN 的 K 值、SVM 的 C 和 gamma、Lasso 的 alpha）。
手动调参费时费力且难以保证找到最优组合。GridSearchCV 通过自动化网格搜索，帮助你系统地寻找最佳参数，同时利用交叉验证评估泛化能力，避免过拟合。

## 基本概念

- 参数网格（param_grid）：一个字典，键是参数名，值是需要尝试的参数值列表（或字典列表）。
- 交叉验证（cv）：将训练数据分成 k 折，每折轮流作为验证集，其余作为训练集，计算 k 次平均性能。
- 最佳估计器（best_estimator_）：在最佳参数下重新训练（默认使用全部训练数据）得到的模型。
- 评分（scoring）：用于评估性能的指标，如分类任务用 `accuracy`，回归任务用 `neg_mean_squared_error`。

## 参数

| 参数                 | 说明                                                                         |
|:-------------------|:---------------------------------------------------------------------------|
| estimator          | 需要调参的模型对象（未训练），也就是需要调用的模型                                                  |
| param_grid         | 参数网格，可以是字典或字典列表                                                            |
| cv                 | 交叉验证折数（默认 5），也可以是生成器或预定义的交叉验证对象                                            |
| scoring            | 评估指标（字符串或可调用对象）。常用：'accuracy', 'roc_auc', 'neg_mean_squared_error', 'r2' 等 |
| n_jobs             | 并行运行的作业数（-1 表示使用所有 CPU 核心）                                                 |
| refit              | 是否在找到最佳参数后用全部训练数据重新训练模型（默认 True）                                           |
| verbose            | 控制输出详细程度（0 静默，1 少量，2 详细）                                                   |
| pre_dispatch       | 控制并行任务的分发数量                                                                |
| return_train_score | 是否返回训练集得分（默认 False）                                                        |
    
## 使用
1. 准备数据和模型
    ```python
     from sklearn.datasets import load_iris
     from sklearn.model_selection import train_test_split
     from sklearn.svm import SVC
     
     data = load_iris()
     X_train, X_test, y_train, y_test = train_test_split(data.data, data.target, test_size=0.2, random_state=42)
    ```
   
2. 定义参数网格
    ```python
      param_grid = {
         'C': [0.1, 1, 10, 100],
         'gamma': [0.01, 0.1, 1, 10],
         'kernel': ['rbf', 'linear']
          }
    ```
   当参数之间存在依赖时，使用字典列表：
    ```python
        param_grid = [
                  {'C': [0.1, 1, 10], 'kernel': ['linear']},
                  {'C': [0.1, 1, 10], 'gamma': [0.01, 0.1], 'kernel': ['rbf']}
                     ]
    ```
   
3. 创建 GridSearchCV 并拟合
   ````python
    from sklearn.model_selection import GridSearchCV
    
    grid = GridSearchCV(estimator=SVC(),param_grid= param_grid, cv=5, scoring='accuracy', n_jobs=-1)
    grid.fit(X_train, y_train)
   ````
   
4. 查看结果
    ```python
        print("最佳参数:", grid.best_params_)
        print("最佳交叉验证得分:", grid.best_score_)
        print("最佳模型:", grid.best_estimator_)
        
        # 在测试集上评估
        test_score = grid.score(X_test, y_test)
        print("测试集准确率:", test_score)
    ```
   
5. 获取详细结果
   cv_results_ 属性包含所有参数组合的详细得分信息：
   ```python
    results = grid.cv_results_
    print(f"参数组合数: {len(results['params'])}")
    print(f"平均测试得分: {results['mean_test_score']}")
    print(f"标准差: {results['std_test_score']}")
   ```
   
## 注意事项
1. **计算成本**：网格搜索会训练 n_params × n_folds 个模型，参数较多时可能非常耗时。可考虑：
   - 减少候选值数量
   - 使用 n_jobs=-1 并行计算。
   - 先用较粗的网格搜索确定大致范围，再细化。
2. **数据泄露**：务必在 GridSearchCV 中只传入训练数据，测试数据要等到调参完成后才能接触。
3. **管道与特征缩放**：如果预处理需要拟合（如标准化），必须将预处理步骤放入管道中，并用管道进行网格搜索，
   确保交叉验证时每次训练只基于训练集计算均值和标准差。
4. **分类任务的类别平衡**：可使用 cv=StratifiedKFold 保证每折的类别比例一致（默认已做）。
5. **替代方法**：当参数空间很大时，RandomizedSearchCV（随机搜索）比网格搜索更高效；贝叶斯优化（如 Optuna）则适合复杂场景。使用方式类似。