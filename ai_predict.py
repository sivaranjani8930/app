from sklearn.ensemble import RandomForestClassifier
import pandas as pd

def predict_risk(features):
    df = pd.read_csv('disaster_data.csv')
    model = RandomForestClassifier()
    model.fit(df[['feature1', 'feature2']], df['risk_level'])
    return model.predict([features])
