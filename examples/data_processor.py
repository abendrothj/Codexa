"""
Example: Data processing with pandas.

This module demonstrates common data processing patterns using pandas.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any


class DataProcessor:
    """A class for processing tabular data using pandas."""

    def __init__(self, data: pd.DataFrame) -> None:
        """
        Initialize the data processor.

        Args:
            data: Input DataFrame to process
        """
        self.data = data.copy()

    def clean_data(self) -> pd.DataFrame:
        """
        Clean the data by removing duplicates and handling missing values.

        Returns:
            Cleaned DataFrame
        """
        # Remove duplicates
        self.data = self.data.drop_duplicates()

        # Fill missing numerical values with mean
        numeric_columns = self.data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            self.data[col].fillna(self.data[col].mean(), inplace=True)

        # Fill missing categorical values with mode
        categorical_columns = self.data.select_dtypes(include=["object"]).columns
        for col in categorical_columns:
            self.data[col].fillna(self.data[col].mode()[0], inplace=True)

        return self.data

    def filter_data(self, column: str, condition: Any) -> pd.DataFrame:
        """
        Filter data based on a condition.

        Args:
            column: Column name to filter on
            condition: Condition to apply

        Returns:
            Filtered DataFrame
        """
        return self.data[self.data[column] == condition]

    def aggregate_data(self, group_by: str, agg_dict: Dict[str, str]) -> pd.DataFrame:
        """
        Aggregate data by grouping.

        Args:
            group_by: Column to group by
            agg_dict: Dictionary of aggregation functions

        Returns:
            Aggregated DataFrame
        """
        return self.data.groupby(group_by).agg(agg_dict).reset_index()

    def add_calculated_column(self, new_column: str, calculation: callable) -> pd.DataFrame:
        """
        Add a new calculated column.

        Args:
            new_column: Name of the new column
            calculation: Function to calculate values

        Returns:
            DataFrame with new column
        """
        self.data[new_column] = calculation(self.data)
        return self.data


def analyze_sales_data(sales_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze sales data and return insights.

    Args:
        sales_df: DataFrame containing sales data

    Returns:
        Dictionary with analysis results
    """
    processor = DataProcessor(sales_df)
    clean_data = processor.clean_data()

    total_sales = clean_data["amount"].sum()
    average_sale = clean_data["amount"].mean()
    top_products = (
        clean_data.groupby("product")["amount"].sum().sort_values(ascending=False).head(5)
    )

    return {
        "total_sales": total_sales,
        "average_sale": average_sale,
        "top_products": top_products.to_dict(),
    }


def main() -> None:
    """Main function demonstrating data processing."""
    # Example data
    data = {
        "product": ["A", "B", "A", "C", "B", "A"],
        "amount": [100, 200, 150, 300, 250, None],
        "region": ["North", "South", "North", "West", "South", "North"],
    }

    df = pd.DataFrame(data)
    processor = DataProcessor(df)

    # Clean and process data
    clean_df = processor.clean_data()
    print("Cleaned Data:")
    print(clean_df)

    # Aggregate by region
    agg_data = processor.aggregate_data("region", {"amount": "sum"})
    print("\nAggregated by Region:")
    print(agg_data)


if __name__ == "__main__":
    main()
