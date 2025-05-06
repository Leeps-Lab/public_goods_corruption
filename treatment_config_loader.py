import pandas as pd
from collections import namedtuple

TreatmentConfig = namedtuple('TreatmentConfig', [
    'private_interaction',
    'resource_allocation',
    'heterogenous_citizens',
    'random_multiplier',
    'random_audits',
    'officer_interactions_public',
])

def load_treatments_from_csv(filepath='treatments.csv'):
    df = pd.read_csv(filepath)

    bool_cols = df.columns.drop('treatment')
    for col in bool_cols:
     df[col] = df[col].astype(str).str.lower() == 'true'

    return {
        row['treatment']: TreatmentConfig(
            row['private_interaction'],
            row['resource_allocation'],
            row['heterogenous_citizens'],
            row['random_multiplier'],
            row['random_audits'],
            row['officer_interactions_public'],
        )
        for _, row in df.iterrows()
    }
