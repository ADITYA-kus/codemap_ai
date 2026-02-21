import mlflow
import pandas as pd
import numpy as np
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from mlflow.models import infer_signature

# 1. Data Preparation
iris = load_iris()
# Use DataFrame from the start for better UI visibility
X = pd.DataFrame(iris.data, columns=iris.feature_names)
y = iris.target

x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 2. Grid Search Setup
estimator = RandomForestClassifier(random_state=42)
param_grid = {
    "n_estimators": [10, 50, 200],
    "max_depth": [4, 8, 5, 9],
    "min_impurity_decrease": [0, 0.1, 0.2, 0.3]
}
Grid_Search = GridSearchCV(estimator=estimator, param_grid=param_grid, cv=5, n_jobs=-1, verbose=True)

mlflow.set_experiment("Hyperparameter_tuning")

with mlflow.start_run(run_name="gridcv_parent", description="Best hyperparameter train RF MODEL") as parent:
    Grid_Search.fit(x_train, y_train)

    # 3. Log Child Runs (Hyperparameter Iterations)
    params_list = Grid_Search.cv_results_['params']
    scores_list = Grid_Search.cv_results_['mean_test_score']

    for i in range(len(params_list)):
        with mlflow.start_run(run_name=f"iteration_{i}", nested=True):
            mlflow.log_params(params_list[i])
            mlflow.log_metric("accuracy", scores_list[i])

    # 4. Log Best Results to Parent
    mlflow.log_params(Grid_Search.best_params_)
    mlflow.log_metric("best_accuracy", Grid_Search.best_score_)

    # 5. Log Dataset Metadata
    # Using from_pandas ensures the UI tracks column names correctly
    train_ds = mlflow.data.from_pandas(x_train, name="iris_train")
    test_ds = mlflow.data.from_pandas(x_test, name="iris_test")
    mlflow.log_input(train_ds, context="training")
    mlflow.log_input(test_ds, context="validation")
    mlflow.log_artifact(__file__)
    # 6. Create Signature & Input Example for UI Visibility
    # infer_signature on a DataFrame creates the 'Column-based' table view
    predictions = Grid_Search.best_estimator_.predict(x_train)
    signature = infer_signature(x_train, predictions)
    
    # input_example adds a 'Random Sample' preview in the UI
    input_example = x_train.iloc[[0]] 

    # 7. Log Final Model
    mlflow.sklearn.log_model(
        sk_model=Grid_Search.best_estimator_,
        name="random-forest-model",
        signature=signature,
        input_example=input_example
    )

print("Run complete. Check the 'Overview' tab in the MLflow UI for the Schema table.")
