import pytest
import pandas as pd
import numpy as np

def test_donchian_channels():
    # Simple dummy price data
    highs = pd.Series([10, 12, 15, 14, 18])
    lows = pd.Series([8, 9, 10, 11, 12])
    
    # Calculate 3-period Donchian High
    donchian_high = highs.rolling(window=3).max()
    assert donchian_high.iloc[2] == 15
    assert donchian_high.iloc[4] == 18
