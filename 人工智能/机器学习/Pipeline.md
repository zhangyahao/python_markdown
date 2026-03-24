1. 作用  
   Pipeline（管道）是 scikit-learn 中一个强大的工具，用于将多个数据转换步骤和最终的估计器串联成一个统一的模型。它简化了机器学习工作流，确保代码简洁、可复现，
   并避免常见的数据泄露问题。  
   Pipeline 是一个将多个转换器（transformer）和一个最终估计器（estimator）串行组合的对象。数据依次经过每个步骤，最终输出预测结果。
   **核心思想**：将预处理（如标准化、特征工程）和模型训练封装成一个单一对象，这个对象具有与普通模型相同的 fit、predict 等方法。
2. Pipeline 的优势
    * 代码简洁：将多个步骤封装为一行，避免重复代码。
    * 防止数据泄露：确保在交叉验证或网格搜索时，预处理步骤（如标准化）仅基于训练数据计算参数，并正确应用到验证集。
    * 易于部署：训练好的 Pipeline 可以保存并直接用于预测，无需重复预处理步骤。
    * 参数统一管理：通过 Pipeline 对象，可以在网格搜索中同时调优预处理参数和模型参数。
    * 可读性高：清晰地展示整个建模流程。
3. 使用
    1. 创建
       通常使用`make_pipeline`来实现
        ```python
           from sklearn.pipeline import make_pipeline
           pipe = make_pipeline(StandardScaler(), LogisticRegression())
        ```
    2. 使用
       ```python
          pipe.fit(X_train, y_train)
          y_pred = pipe.predict(X_test)
          score = pipe.score(X_test, y_test)
 
       ```
    3. 访问步骤和参数
        1. 步骤列表：pipe.steps 返回步骤列表（名称，对象）。
        2. 按名称访问步骤：pipe.named_steps['step_name']。
        3. 获取参数：pipe.get_params() 返回所有步骤的参数，键格式为 step_name__param_name。
       ```python
          # 访问标准化步骤
          scaler = pipe.named_steps['standardscaler']
          # 查看所有参数
          print(pipe.get_params())
          # 输出类似 {'standardscaler__with_mean': True, 'logisticregression__C': 1.0, ...}
       ```

4. 总结  
   Pipeline 是 scikit-learn 中构建生产级机器学习工作流的基础工具。它将数据预处理、特征工程和模型训练整合为一个统一对象，保证代码整洁、避免数据泄露，并简化调参与部署过程。