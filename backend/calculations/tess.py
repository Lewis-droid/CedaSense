import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import os
import json
from urllib.request import urlopen, Request
from urllib.parse import urlparse, urlencode
import requests

# Optional .env loading if python-dotenv is available
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()  # load variables from .env if present
except Exception:
    pass


def _safe_float(value: object) -> float:
    """Best-effort conversion to float.

    - Treats None/NaN/invalid as 0.0
    - Strips commas and whitespace from strings
    - Leaves numbers unchanged
    """
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float, np.integer, np.floating)):
            # Handle nan
            if pd.isna(value):
                return 0.0
            return float(value)
        # Convert strings like "1,234.56" or with spaces
        s = str(value).strip().replace(',', '')
        if s == '' or s.lower() in {'nan', 'none', 'null'}:
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def _coerce_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Coerce selected columns to numeric, replacing invalids with 0."""
    for col in columns:
        if col in df.columns:
            # Remove thousands separators, spaces, and coerce
            df[col] = (
                pd.to_numeric(
                    df[col]
                    .astype(str)
                    .str.replace(',', '', regex=False)
                    .str.strip(),
                    errors='coerce'
                )
                .fillna(0)
            )
    return df


class OandaExchangeRates:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://exchange-rates-api.oanda.com/v2"
        self._cache = {}
        
        # Fallback exchange rates (approximate rates to KES as of 2024)
        self.fallback_rates = {
            'USD': 150.0,  # 1 USD = 150 KES
            'EUR': 165.0,  # 1 EUR = 165 KES
            'GBP': 190.0,  # 1 GBP = 190 KES
            'EGP': 3.2,    # 1 EGP = 3.2 KES
            'PHP': 2.7,    # 1 PHP = 2.7 KES
            'INR': 1.8,    # 1 INR = 1.8 KES
            'ZAR': 8.0,    # 1 ZAR = 8.0 KES
            'TZS': 0.065,  # 1 TZS = 0.065 KES
            'UGX': 0.04,   # 1 UGX = 0.04 KES
        }

    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> float:
        """Get fallback exchange rate when API fails"""
        if to_currency == 'KES':
            return self.fallback_rates.get(from_currency, 1.0)
        elif from_currency == 'KES':
            # Reverse rate calculation
            kes_rate = self.fallback_rates.get(to_currency, 1.0)
            return 1.0 / kes_rate if kes_rate != 1.0 else 1.0
        else:
            # Convert through KES
            from_kes = self._get_fallback_rate(from_currency, 'KES')
            to_kes = self._get_fallback_rate(to_currency, 'KES')
            return from_kes / to_kes if to_kes != 0 else 1.0

    def _get_latest_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Get the latest FX rate using OANDA Exchange Rates API (end-of-day).
        Falls back to static rates if API fails.
        """
        from_currency = (from_currency or '').upper()
        to_currency = (to_currency or '').upper()
        if not from_currency or not to_currency:
            raise ValueError('Invalid currency symbols')
        if from_currency == to_currency:
            return 1.0

        cache_key = (from_currency, to_currency)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try OANDA API first
        try:
            url = f"{self.base_url}/rates/latest.json"
            params = {
                "api_key": self.api_key,
                "base": from_currency
            }
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if "quotes" in data and to_currency in data["quotes"]:
                    rate = float(data["quotes"][to_currency])
                    self._cache[cache_key] = rate
                    return rate
        except Exception:
            pass  # Fall through to fallback rates

        # Use fallback rates if API fails
        print(f"🔄 Using fallback rate for {from_currency}->{to_currency}")
        rate = self._get_fallback_rate(from_currency, to_currency)
        self._cache[cache_key] = rate
        return rate

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Convert an amount from one currency to another.
        """
        try:
            rate = self._get_latest_rate(from_currency, to_currency)
            return _safe_float(amount) * rate
        except Exception as e:
            print(f"⚠️ FX conversion failed {from_currency}->{to_currency}: {e}")
            return np.nan  # safer than silently returning the wrong value


class FacultativeReinsuranceCalculator:
    """
    A comprehensive calculator for Facultative Reinsurance Working Sheet
    based on the provided guideline document.
    """
    
    def __init__(self):
        # OANDA Exchange Rates API v2 configuration
        # Defaults provided; override via environment
        self.oanda_exr_api_key = os.getenv('OANDA_EXR_API_KEY', '9caeed9b-aee6-463d-8c83-378ead699f01').strip()
        self.oanda_exr_base_url = os.getenv('OANDA_EXR_BASE_URL', 'https://exchange-rates-api.oanda.com/v2').rstrip('/')
        # Initialize FX helper
        self.fx = OandaExchangeRates(self.oanda_exr_api_key)
        # Simple in-memory cache for FX pairs: (from,to) -> rate (kept for backward compatibility)
        self._fx_cache = {}
    
    def _get_latest_rate(self, from_currency: str, to_currency: str) -> float:
        """Deprecated: use self.fx._get_latest_rate instead. Retained for compatibility."""
        return self.fx._get_latest_rate(from_currency, to_currency)
    
    def calculate_premium_rate_percentage(self, premium, tsi):
        """Calculate premium rate as percentage"""
        premium = _safe_float(premium)
        tsi = _safe_float(tsi)
        if tsi == 0:
            return 0
        return (premium / tsi) * 100
    
    def calculate_premium_rate_permille(self, premium, tsi):
        """Calculate premium rate as per mille (‰)"""
        premium = _safe_float(premium)
        tsi = _safe_float(tsi)
        if tsi == 0:
            return 0
        return (premium / tsi) * 1000
    
    def calculate_premium_from_rate_percentage(self, tsi, rate_percentage):
        """Calculate premium when rate is given as percentage"""
        tsi = _safe_float(tsi)
        rate_percentage = _safe_float(rate_percentage)
        return tsi * (rate_percentage / 100)
    
    def calculate_premium_from_rate_permille(self, tsi, rate_permille):
        """Calculate premium when rate is given as per mille"""
        tsi = _safe_float(tsi)
        rate_permille = _safe_float(rate_permille)
        return tsi * (rate_permille / 1000)
    
    def calculate_loss_ratio(self, paid_losses, outstanding_reserves, recoveries, earned_premium):
        """Calculate loss ratio percentage"""
        paid_losses = _safe_float(paid_losses)
        outstanding_reserves = _safe_float(outstanding_reserves)
        recoveries = _safe_float(recoveries)
        earned_premium = _safe_float(earned_premium)
        if earned_premium == 0:
            return 0
        incurred_losses = paid_losses + outstanding_reserves - recoveries
        return (incurred_losses / earned_premium) * 100
    
    def calculate_accepted_premium(self, gross_premium, accepted_share_pct):
        """Calculate accepted premium based on share percentage"""
        gross_premium = _safe_float(gross_premium)
        accepted_share_pct = _safe_float(accepted_share_pct)
        return gross_premium * (accepted_share_pct / 100)
    
    def calculate_accepted_liability(self, tsi, accepted_share_pct):
        """Calculate accepted liability based on share percentage"""
        tsi = _safe_float(tsi)
        accepted_share_pct = _safe_float(accepted_share_pct)
        return tsi * (accepted_share_pct / 100)
    
    def convert_currency(self, amount, from_currency, to_currency='KES'):
        """Convert currency using OANDA Exchange Rates API v2 latest end-of-day rate via helper class."""
        if from_currency == to_currency:
            return _safe_float(amount)
        
        from_currency = (from_currency or '').upper()
        to_currency = (to_currency or '').upper()

        return self.fx.convert(amount, from_currency, to_currency)
    
    def calculate_all_metrics(self, df):
        """Calculate all derived metrics for the DataFrame"""
        
        # First, coerce known numeric columns safely to numeric with 0 defaults
        numeric_cols = [
            'TSI_Original_Currency', 'Premium_Original_Currency',
            'Paid_Losses_3_Years', 'Outstanding_Reserves_3_Years', 'Recoveries_3_Years',
            'Earned_Premium_3_Years', 'Share_Offered_Pct', 'PML_Pct', 'Retention_of_Cedant_Pct'
        ]
        df = _coerce_numeric_columns(df, numeric_cols)
        
        # Convert currencies to KES
        df['TSI_KES'] = df.apply(lambda row: self.convert_currency(
            row['TSI_Original_Currency'], 
            row['Original_Currency'], 
            'KES'
        ), axis=1)
        
        df['Premium_KES'] = df.apply(lambda row: self.convert_currency(
            row['Premium_Original_Currency'], 
            row['Original_Currency'], 
            'KES'
        ), axis=1)
        
        # Calculate premium rates
        df['Premium_Rate_Percentage'] = df.apply(lambda row: self.calculate_premium_rate_percentage(
            row['Premium_KES'], row['TSI_KES']
        ), axis=1)
        
        df['Premium_Rate_Permille'] = df.apply(lambda row: self.calculate_premium_rate_permille(
            row['Premium_KES'], row['TSI_KES']
        ), axis=1)
        
        # Calculate loss ratios
        df['Loss_Ratio_Pct'] = df.apply(lambda row: self.calculate_loss_ratio(
            row['Paid_Losses_3_Years'],
            row['Outstanding_Reserves_3_Years'],
            row['Recoveries_3_Years'],
            row['Earned_Premium_3_Years']
        ), axis=1)
        
        # Calculate accepted amounts
        df['Accepted_Premium_KES'] = df.apply(lambda row: self.calculate_accepted_premium(
            row['Premium_KES'], row['Share_Offered_Pct']
        ), axis=1)
        
        df['Accepted_Liability_KES'] = df.apply(lambda row: self.calculate_accepted_liability(
            row['TSI_KES'], row['Share_Offered_Pct']
        ), axis=1)
        
        # Calculate PML amounts
        df['PML_Amount_KES'] = _safe_float(1.0) * df['TSI_KES'] * (df['PML_Pct'] / 100)
        
        # Calculate retention amounts
        df['Retention_Amount_KES'] = _safe_float(1.0) * df['TSI_KES'] * (df['Retention_of_Cedant_Pct'] / 100)
        
        return df
    
    def generate_summary_report(self, df):
        """Generate a summary report of the calculations"""
        
        print("="*80)
        print("FACULTATIVE REINSURANCE CALCULATION SUMMARY REPORT")
        print("="*80)
        
        for idx, row in df.iterrows():
            print(f"\nRISK #{idx + 1}: {row['Insured']}")
            print("-" * 50)
            print(f"Cedant: {row['Cedant']}")
            print(f"Broker: {row['Broker']}")
            print(f"Occupation: {row['Occupation_of_Insured']}")
            print(f"Location: {row['Situation_of_Risk']}")
            
            print(f"\nFINANCIAL SUMMARY:")
            print(f"  TSI (Original): {row['Original_Currency']} {row['TSI_Original_Currency']:,.2f}")
            print(f"  TSI (KES): KES {row['TSI_KES']:,.2f}")
            print(f"  Premium (Original): {row['Original_Currency']} {row['Premium_Original_Currency']:,.2f}")
            print(f"  Premium (KES): KES {row['Premium_KES']:,.2f}")
            print(f"  Premium Rate: {row['Premium_Rate_Percentage']:.4f}% | {row['Premium_Rate_Permille']:.2f}‰")
            
            print(f"\nRISK SHARING:")
            print(f"  Cedant Retention: {row['Retention_of_Cedant_Pct']}% (KES {row['Retention_Amount_KES']:,.2f})")
            print(f"  Share Offered: {row['Share_Offered_Pct']}%")
            print(f"  Accepted Premium: KES {row['Accepted_Premium_KES']:,.2f}")
            print(f"  Accepted Liability: KES {row['Accepted_Liability_KES']:,.2f}")
            
            print(f"\nRISK ASSESSMENT:")
            print(f"  PML: {row['PML_Pct']}% (KES {row['PML_Amount_KES']:,.2f})")
            print(f"  Loss Ratio (3 years): {row['Loss_Ratio_Pct']:.2f}%")
            print(f"  Climate Risk: {row['Climate_Change_Risk']}")
            print(f"  ESG Risk: {row['ESG_Risk_Level']}")
            
        print("\n" + "="*80)
        print("END OF REPORT")
        print("="*80)


def _is_url(path_or_url: str) -> bool:
    try:
        parsed = urlparse(path_or_url)
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def load_json_input(input_source: str) -> pd.DataFrame:
    """Load JSON input from a local file path or HTTP(S) URL into a DataFrame.
    Accepts list-of-records or column-oriented dicts."""
    if _is_url(input_source):
        with urlopen(input_source) as response:
            data = json.loads(response.read().decode('utf-8'))
    else:
        with open(input_source, 'r', encoding='utf-8') as f:
            data = json.load(f)

    if isinstance(data, dict):
        # Support either {"records": [...]} or column-oriented {col: [..]}
        if 'records' in data and isinstance(data['records'], list):
            return pd.DataFrame(data['records'])
        return pd.DataFrame(data)

    if isinstance(data, list):
        return pd.DataFrame(data)

    raise ValueError('Unsupported JSON structure for input data')


def save_json_output(df: pd.DataFrame, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_json(output_path, orient='records', indent=2)


# Main execution
if __name__ == "__main__":
    # Initialize calculator
    calculator = FacultativeReinsuranceCalculator()
    
    # Resolve input/output paths from environment or defaults
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_input = os.path.join(project_root, 'calculations', 'sample_input.json')
    default_output = os.path.join(project_root, 'calculations', 'facultative_reinsurance_calculations.json')

    input_source = os.getenv('INPUT_JSON', default_input)
    output_path = os.getenv('OUTPUT_JSON', default_output)

    # Load input data
    print(f"Loading input data from: {input_source}")
    df = load_json_input(input_source)

    # Calculate all metrics
    print("\nCalculating all metrics...")
    df_calculated = calculator.calculate_all_metrics(df)

    # Optionally display key results
    key_columns = [
        'Insured', 'TSI_KES', 'Premium_KES', 'Premium_Rate_Percentage', 
        'Premium_Rate_Permille', 'Loss_Ratio_Pct', 'Accepted_Premium_KES', 
        'Accepted_Liability_KES', 'PML_Amount_KES'
    ]
    existing_key_columns = [c for c in key_columns if c in df_calculated.columns]
    if existing_key_columns:
        print("\nCalculated Results (selected columns):")
        print(df_calculated[existing_key_columns].to_string(index=False))

    # Generate detailed summary report
    calculator.generate_summary_report(df_calculated)

    # Save to JSON output
    save_json_output(df_calculated, output_path)
    print(f"\nResults saved to '{output_path}'")