import pandas as pd
import json

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import classification_report

clothing_file_path = './clothing_weather.csv'
data = pd.read_csv(clothing_file_path)
# print(data.columns)

# Turn JSON strings into individual dataframe columns
weather_data = pd.json_normalize(data['WeatherData'].apply(json.loads))
activity_data = pd.json_normalize(data['ActivityData'].apply(json.loads))
clothing_data = pd.json_normalize(data['ClothingData'].apply(json.loads))
sports_data = pd.json_normalize(data['SportsData'].apply(json.loads))

# Create a dataframe joining together weather and activity features
X = pd.concat([weather_data, activity_data], axis=1)
X['sunrise'] = pd.to_datetime(X['sunrise'], format='%H:%M').dt.hour * 60 + pd.to_datetime(X['sunrise'], format='%H:%M').dt.minute
X['sunset'] = pd.to_datetime(X['sunset'], format='%H:%M').dt.hour * 60 + pd.to_datetime(X['sunset'], format='%H:%M').dt.minute

print(X.describe())

# Experiment with what features (columns) to include
# * better without sunrise and sunset
features_to_exclude = [
    'sunrise', 
    'sunset',
    # 'shortwave_radiation_sum',
]
X = X.drop(features_to_exclude, axis=1)

# Define targets
y_clothing = clothing_data  # what clothing to wear
y_sports = sports_data      # what sports you can play
y_clothing = y_clothing.loc[:, (y_clothing.nunique() > 1)] # remove columns with no variation (outerwear.none, footwear.boots, and accessories.none are always false in the dataset)

# Train-test split (20% for testing)
X_train, X_test, y_train_clothing, y_test_clothing = train_test_split(X, y_clothing, test_size=0.2, random_state=8)
X_train_, X_test_, y_train_sports, y_test_sports = train_test_split(X, y_sports, test_size=0.2, random_state=8)

# Clothing weighting
# having issues with clothing_weights (ValueError: The classes, [False, True], are not in class_weight)
clothing_weights = {
    True: 2,
    False: 1
}

print(y_train_clothing.columns)

# Create models using RandomForest
clothing_model = RandomForestClassifier(class_weight=clothing_weights, random_state=8)
sports_model = RandomForestClassifier(random_state=8)

# Combine models in MultiOutputClassifier for discrete predictions
multi_output_model = MultiOutputClassifier(estimator=clothing_model)
multi_output_model.fit(X_train, pd.concat([y_train_clothing, y_train_sports], axis=1))

# Make predictions multi-output
y_pred = multi_output_model.predict(X_test)

# Evaluate
# for i, target in enumerate(pd.concat([y_clothing, y_sports], axis=1).columns):
#     print(f"--- Evaluation for {target} ---")
#     print(classification_report(y_test_clothing.iloc[:, i] if i < len(y_clothing.columns) else y_test_sports.iloc[:, i - len(y_clothing.columns)],
#                                 y_pred[:, i], zero_division=1)) # split the y_pred into clothing and sports, zero_division to stop warning

# Evaluate overall performance
report = classification_report(y_test_clothing, y_pred[:, :len(y_clothing.columns)], output_dict=True, zero_division=1)
report.update(classification_report(y_test_sports, y_pred[:, len(y_clothing.columns):], output_dict=True, zero_division=1))

overall_metrics = { 
    'Accuracy (clothing)': round((y_pred[:, :len(y_clothing.columns)] == y_test_clothing).mean(), 4),
    'Accuracy (sports)': round((y_pred[:, len(y_clothing.columns):] == y_test_sports).mean(), 4),
    'Accuracy (overall)': round((y_pred == pd.concat([y_test_clothing, y_test_sports], axis=1)).mean().mean(), 4),
    # 'Macro avg F1': round(report['macro avg']['f1-score'], 4),
    'Weighted avg F1': round(report['weighted avg']['f1-score'], 4),
    # 'Macro avg Precision': round(report['macro avg']['precision'], 4),
    'Weighted avg Precision': round(report['weighted avg']['precision'], 4),
    # 'Macro avg Recall': round(report['macro avg']['recall'], 4),
    'Weighted avg Recall': round(report['weighted avg']['recall'], 4)
} # weighted also accounts for class imbalance

for metric, value in overall_metrics.items():
    print(f"{metric}: {value}")

# precision: quality
# recall: quantity
# f1-score: balance between precision and recall
# support: number of occurrences of each class in y_true

# ? results of predictions clothing together, so combinations will appear which is good, although may not consider groupings during decision-making
# ? sources of inaccuracy: not much data points, some items only have few points, there are many categories to predict takes a lot of data to train

# supervised learning, classification (discrete output), random forest