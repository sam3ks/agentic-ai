# loan_data_service.py
import os
import pandas as pd
import numpy as np
from typing import Dict
from agentic_ai.core.config.constants import DATASET_PATH
from agentic_ai.core.utils.validators import is_pan, is_aadhaar

class LoanDataService:
    """Manages loan dataset operations."""

    def __init__(self, dataset_path: str = DATASET_PATH):
        if not os.path.exists(dataset_path):
            print(f"⚠️ Dataset {dataset_path} not found. Creating sample dataset.")
        self.df = self._load_or_create_dataset(dataset_path)

    def _load_or_create_dataset(self, path: str) -> pd.DataFrame:
        """Load existing dataset or create sample data."""
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                print(f"✓ Loading loan dataset with {df.shape[0]} records")
            except Exception as e:
                print(f"⚠️ Error loading dataset: {e}. Creating sample data.")
                df = self._create_sample_dataset()
        else:
            print("✓ Creating sample loan dataset")
            df = self._create_sample_dataset()
        
        return self._process_dataset(df)

    def _create_sample_dataset(self) -> pd.DataFrame:
        """Create sample dataset for testing."""
        np.random.seed(42)
        data = {
            'pan_number': ['ABCDE1234F', 'FGHIJ5678K', 'KLMNO9012P', 'PQRST3456U', 'VWXYZ7890A'],
            'aadhaar_number': ['123456789012', '234567890123', '345678901234', '456789012345', '567890123456'],
            'monthly_salary': [50000, 75000, 100000, 40000, 120000],
            'existing_emi': [5000, 10000, 15000, 8000, 20000],
            'credit_score': [720, 680, 760, 600, 800],
            'emi_to_income_ratio': [20, 30, 15, 35, 25],
            'delayed_payments': [1, 3, 0, 4, 0],
            'avg_monthly_balance': [25000, 35000, 50000, 15000, 60000],
            'avg_daily_transactions': [5, 8, 12, 3, 15],
            'city': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata']
        }
        return pd.DataFrame(data)

    def _process_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and enhance dataset."""
        # Ensure consistent column naming regardless of input format
        column_mapping = {
            'PAN': 'pan_number', 
            'Aadhaar': 'aadhaar_number',
            'pan': 'pan_number',
            'pan_no': 'pan_number',
            'aadhaar': 'aadhaar_number',
            'aadhaar_no': 'aadhaar_number',
            'aadhar': 'aadhaar_number'
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Make sure both pan_number and aadhaar_number columns exist
        if 'pan_number' not in df.columns:
            df['pan_number'] = None
            
        if 'aadhaar_number' not in df.columns:
            df['aadhaar_number'] = None
            
        # Fill NaN values in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        # Add city column if not present
        if 'city' not in df.columns:
            df['city'] = np.random.choice(
                ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad', 'Surat', 'Jaipur'],
                size=len(df)
            )
            
        # Ensure all strings are properly stripped
        for col in ['pan_number', 'aadhaar_number']:
            if col in df.columns:
                df[col] = df[col].astype(str).apply(lambda x: x.strip() if not pd.isna(x) else x)
                
        return df

    def get_user_data(self, identifier: str) -> Dict:
        """Query user data by PAN or Aadhaar."""
        try:
            # Clean identifier for comparison
            cleaned_identifier = identifier.strip()
            
            # Check for PAN first
            pan_mask = self.df['pan_number'] == cleaned_identifier
            
            # Then check for Aadhaar - try direct match first
            aadhaar_mask = self.df['aadhaar_number'] == cleaned_identifier
            
            # Combined mask
            mask = pan_mask | aadhaar_mask
            result = self.df[mask]
            
            if not result.empty:
                # Debug information about the match found
                matched_row = result.iloc[0]
                match_by = "PAN" if matched_row['pan_number'] == cleaned_identifier else "Aadhaar"
                print(f"✓ Found existing user via {match_by}: {cleaned_identifier}")
            else:
                print(f"⚠️ User not found in dataset: {cleaned_identifier}")
            
            if result.empty:
                user_data = {
                    "pan_number": cleaned_identifier if is_pan(cleaned_identifier) else None,
                    "aadhaar_number": cleaned_identifier if is_aadhaar(cleaned_identifier) else None,
                    "status": "new_user_found_proceed_to_salary_sheet"
                }
                return user_data
            
            user_data = result.iloc[0].to_dict()
            
            for key, value in user_data.items():
                if pd.isna(value):
                    user_data[key] = None
                elif hasattr(value, 'item'):
                    user_data[key] = value.item()
            
            user_data["status"] = "existing_user_data_retrieved"
            return user_data
            
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}
