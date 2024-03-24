import pandas as pd

###########################
### Bond Data Structure ###
###########################
class Bond:
    """
    Class representing a bond's static information.
    The data contained in this class should not change over time.
    """
    isin: str
    fv: float
    coupon: float
    notional: float

    def __init__(self, isin: str, fv: float, coupon: float):
        self.isin = isin
        self.fv = fv
        self.coupon = coupon
        self.coupon_payment = fv*coupon
        self.notional = fv + fv*coupon


class DatedBond(Bond):
    """
    A class representing a bond at a current date.
    The data contained in this class is only valid for a specific date.
    """
    date: str
    maturity_period: int
    coupon_periods: list[int]

    def __init__(self, isin: str, fv: float, coupon: float, 
                 date: str, price: float,
                 maturity_period: int, coupon_periods: list[int]) -> None:
        super().__init__(isin, fv, coupon)
        self.date = date
        self.price = price
        self.maturity_period = maturity_period
        self.coupon_periods = coupon_periods


#############################
### Bond Data Consumption ###
#############################
def get_bonds(df: pd.DataFrame) -> list[Bond]:
    """
    Given a pandas DataFrame with the correct columns, returns a list of bonds.
    """
    bonds = []
    for _, row in df.iterrows():
        bonds.append(Bond(row["ISIN"],
                          row["FV"],
                          row["Coupon"]/2))
    return bonds


def get_dated_bonds(df: pd.DataFrame) -> list[DatedBond]:
    """
    Given a pandas DataFrame with the correct columns, returns a list of dated bonds sorted
    in order of maturity period.
    """
    df = df.sort_values("Maturity_Period", ascending=True)
    bonds = []
    for _, row in df.iterrows():
        bonds.append(DatedBond(row["ISIN"],
                               row["FV"],
                               row["Coupon"]/2,
                               row["Price Date"],
                               row["Dirty Price"],
                               row["Maturity Period"],
                               row["Coupon Periods"]))
    return bonds


def get_last_coupon_payment_date(row):
    """
    Given a row containing the first coupon date and the price date,
    returns the most recent coupon payment date.
    """
    date = row["Coupon Start Date"]
    while date + pd.DateOffset(months=6) < row["Price Date"]:
        date = date + pd.DateOffset(months=6)
    return date

def get_future_coupon_payments(row):
    date = row["Last Coupon Payment Date"] + pd.DateOffset(months=6)
    periods = []
    while date < row["Maturity Date"]:
        period = (date - row["Price Date"]).days
        periods.append(period)
        date = date + pd.DateOffset(months=6)
    return periods


def consume_info_csv(info_filename: str) -> pd.DataFrame:
    """
    Consumes the relevant csv files and builds a pandas dataframe with the bond data.
    === Parameters ===
    - info_filename: string containing the name of the CSV file 
        containing the constant information about the bonds. Requires the following columns:
        - ISIN: the ISIN of the bond
        - Coupon: the coupon in percentage format
        - FV: the face value of the bond
        - Issue Date: the date the bond was issued
        - Maturity Date: the date the bond will mature
        - Coupon Start Date: the first date on which a coupon was paid
    - price_filename: string containing the name of the CSV file containing the bond prices.
        - ISIN: the ISIN of the bond
        - Price Date: the date for that closing price
        - Price: the percentage of the notional the closing price is.
    - save_name: string containing the name of the CSV file to save the data to.
        If None is given, don't save the data.
    === Prerequisites ===
    - the two files are in CSV format
    """
    # Process info data
    info = pd.read_csv(info_filename)
    info["Coupon"] = info["Coupon"].astype(float) / 100.0
    info["FV"] = info["FV"]
    info["Issue Date"] = pd.to_datetime(info["Issue Date"])
    info["Maturity Date"] = pd.to_datetime(info["Maturity Date"])
    info["Coupon Start Date"] = pd.to_datetime(info["Coupon Start Date"])

    return info


def consume_price_csv(filename: str, bond_info: pd.DataFrame) -> pd.DataFrame:
    prices = pd.read_csv(filename)
    prices["Price Date"] = pd.to_datetime(prices["Price Date"])

    df = bond_info.merge(prices, on="ISIN", how="inner")

    # Construct needed columns
    df["Price"] = df["Price"] * df["FV"] / 100.0
    df["Last Coupon Payment Date"] = df.apply(get_last_coupon_payment_date, axis=1)
    df["Coupon Periods"] = df.apply(get_future_coupon_payments, axis=1)
    df["Dirty Price"] = df["Price"] + (df["FV"] * df["Coupon"]/2.0) * (df["Date Collected"] - df["Last Coupon Payment Date"]).dt.days / (365/2)
    df["Maturity Period"] = (df["Maturity Date"] - df["Date Collected"]).dt.days


def process_bond_data(info_filename: str, price_filename: str, save_filename: str|None=None) -> pd.DataFrame:
    info = consume_info_csv(info_filename)
    df = consume_price_csv(price_filename, info)
    if save_filename is not None:
        df.to_csv(save_filename)
    
    return df