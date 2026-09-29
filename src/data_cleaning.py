'''
data_cleaning.py
--------------------------------
功能: 淘宝用户行为数据清洗模块，负责读取原始 CSV、处理缺失值、去重、时间格式转换等。
数据清洗模块，包含：
    - read_behavior_csv
    - clean_user_behavior
输出内容：
    - 清洗后数据文件cleaned_user_behavior.csv
    
依赖：pandas 
'''



from __future__ import annotations

import argparse                
from pathlib import  Path     

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]  

DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw_user_behavior_sample.csv"

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "cleaned_user_behavior.csv"

DEFAULT_TIMEZONE = "Asia/Shanghai"

REQUIRED_COLUMNS = ["user_id","item_id","category_id","behavior_type","timestamp"]

VALID_BEHAVIORS = {
      "pv": ("page_view", "浏览"),
      "fav": ("favorite", "收藏"),
      "cart": ("add_to_cart", "加购"),
      "buy": ("purchase", "购买"),
}


#1.读取数据文件
def read_behavior_csv(input_path: Path) -> pd.DataFrame:
    preview = pd.read_csv(input_path,nrows=0)
    if set(REQUIRED_COLUMNS).issubset(preview.columns):
        return pd.read_csv(input_path,usecols=REQUIRED_COLUMNS)
    return pd.read_csv(input_path,header=None,names=REQUIRED_COLUMNS)


#2.清洗原始数据
def clean_user_behavior(
        input_path:Path = DEFAULT_INPUT,
        output_path:Path = DEFAULT_OUTPUT,
        start_date: str = "2017-11-25",
        end_date: str = "2017-12-04",
        timezone: str= DEFAULT_TIMEZONE,
) -> pd.DataFrame:                          

    df = read_behavior_csv(input_path)
    original_rows = len(df)

    df = df.drop_duplicates()
    df = df.dropna(subset=REQUIRED_COLUMNS)

    for column in ["user_id","item_id","category_id","timestamp"]:
        df[column] = pd.to_numeric(df[column],errors='coerce')
    df = df.dropna(subset=["user_id","item_id","category_id","timestamp"])

    df['behavior_type'] = df['behavior_type'].astype(str).str.lower().str.strip()
    df = df[df['behavior_type'].isin(VALID_BEHAVIORS)]

    df['behavior_time'] = (
        pd.to_datetime(df['timestamp'],unit='s',utc=True,errors='coerce')
        .dt.tz_convert(timezone)
        .dt.tz_localize(None)   
    )
    df = df.dropna(subset=['behavior_time'])

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    df = df[(df['behavior_time'] >= start_ts) & (df['behavior_time'] < end_ts)]

    for column in ['user_id','item_id','category_id','timestamp']:
        df[column] = df[column].astype("Int64")

    df['date'] = df['behavior_time'].dt.date.astype(str)
    df['hour'] = df['behavior_time'].dt.hour
    df['weekday'] = df["behavior_time"].dt.day_name()

    df['behavior_name_en'] = df['behavior_type'].map(lambda x: VALID_BEHAVIORS[x][0])
    df['behavior_name_cn'] = df['behavior_type'].map(lambda x: VALID_BEHAVIORS[x][1])

    df['weekname'] = df["behavior_time"].dt.dayofweek + 1

    ordered_columns = [
        'user_id',
        'item_id',
        'category_id',
        'behavior_type',
        'behavior_name_en',
        'behavior_name_cn', 
        'timestamp',
        'behavior_time',
        'date',
        'hour',
        'weekday',
        'weekname'
    ]
    df = df[ordered_columns].sort_values(by=['behavior_time','user_id','item_id']).reset_index(drop=True)


    output_path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(output_path,index=False)

    print("Cleaning summary")
    print(f"- Row row:{original_rows:,}")
    print(f"- Clean rows:{len(df):,}")
    print(f"- Removed rows:{original_rows - len(df):,}")
    print(f"- Output file:{output_path}")
    return df


#3.设置主函数
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean user-behavior-Taobao-style csv data."
        )
    
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Input CSV file path.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help='Cleaned CSV path.'
    )
    parser.add_argument(
        "--start-date",
        default="2017-11-25",
        help="Inclusive start date."
    )
    parser.add_argument(
        "--end-date",
        default="2017-12-04",
        help="Exclusive end date."
    )
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="Timezone for local business analysis."
    )

    args = parser.parse_args()

    clean_user_behavior(
        input_path=args.input,
        output_path=args.output,
        start_date=args.start_date,
        end_date=args.end_date,
        timezone=args.timezone,
    )

if __name__=="__main__":
    main()



