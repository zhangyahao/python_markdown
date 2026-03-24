## lasso回归

1. 原理
   在线性回归的基础上增加了 L1 正则化项。L1 正则化会将某些系数压缩至 0，从而实现 **特征选择**。
2. 为什么 L1 能产生稀疏解
   L1 正则化的约束区域是菱形，与误差等值线相交时容易落在坐标轴上，导致部分系数为 0。这使得 Lasso 不仅能防止过拟合，还能自动筛选重要特征。
3. python实现

    ```python
    
    from sklearn.linear_model import Lasso, LassoCV
    
    # 创建 Lasso 模型（需手动指定 alpha）
    lasso = Lasso(alpha=0.1)
    lasso.fit(X_train, y_train)
    y_pred_lasso = lasso.predict(X_test)
    
    print("\nLasso 回归结果 (alpha=0.1)：")
    print(f"系数: {lasso.coef_}")
    print(f"MSE: {mean_squared_error(y_test, y_pred_lasso):.4f}")
    print(f"R²: {r2_score(y_test, y_pred_lasso):.4f}")
    ```

4. lassoCV

    ```python
    from sklearn.linear_model import LassoCV
    
    # 自动选择 alpha（默认5折交叉验证）
    lasso_cv = LassoCV(cv=5, random_state=42)
    lasso_cv.fit(X_train, y_train)
    
    print(f"最佳 alpha: {lasso_cv.alpha_}")
    ```

5. Lasso 和LassoCV核心区别
   
   | 特性           | Lasso                     | LassoCV                                                        |
   |:-------------|:--------------------------|:---------------------------------------------------------------|
   | 是否需要手动指定 `α` | 是，必须通过 `alpha` 参数传入       | 否，自动通过交叉验证选择最佳 α                                               |
   | **模型训练方式**   | 仅用指定的 α 训练一次              | 对多个 α 进行交叉验证，选择最优后再次训练（或直接使用）                                  |
   | **输出属性**     | 只有 `coef_`、`intercept_` 等 | 除 `coef_` 外，还有 `alpha_`（最佳 alpha）、`mse_path_`（各 alpha 的 CV 误差） |
   | **适用阶段**     | 已知最佳 α 后的最终训练             | 未知 α 时的调参和模型选择                                                 |
   
6. 总结

  * 用 Lasso：当你已经知道或通过其他方法确定了最佳的 α，只需用这个 α 训练最终模型。
  * 用 LassoCV：当你需要从多个候选α 中自动选择最优值，避免手动调参，同时得到交叉验证评估的误差。
  * 实际使用过程中，通常使用 `LassoCV`获取最优`α`，然后在使用这个`α`创建 `lasso`模型进行预测
