"""
data_analysis.py
--------------------------------
功能: 用户行为分析核心模块，包含用户分层、时间维度分析、品类分析、复购分析等。
数据分析模块，包含：
    - load_data
    - summarize_behavior_metrics
    - behavior_type_distribution
    - user_level_funnel
    - user_item_sequential_funnel
    - daily_active_users
    - daily_purchase_trend
    - hourly_activity
    - top_categories_by_purchase
    - category_conversion_analysis
    - repurchase_analysis
    - cart_without_purchase_users
    - high_value_users
    - user_segmentation
        
    - comparison_between_weekday_and_weekend
    - hour_activity_comparison_within_week
    - distribution_of_behavior_within_week
    - user_tag_period
    - high_value_comparison_within_day
    - top_activity_category
    - activity_purchasing_segment_user
    - category_converison_decision_cycle
    - repurchase_cycle
    - purchase_category_combos
    
依赖: pandas, numpy  
"""



from __future__ import annotations 

import argparse
from pathlib import Path
import sys

import pandas as pd
import numpy as np


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "cleaned_user_behavior.csv"

PROJECT_ROOT = Path.cwd() if Path.cwd().name == 'user_behavior_analysis' else Path.cwd().parent
sys.path.append(str(PROJECT_ROOT / 'src'))

#1.读取清洗好的数据文件，并指定列为datetime类型
def load_data(input_path: Path = DEFAULT_INPUT) ->pd.DataFrame:
    df = pd.read_csv(input_path,parse_dates=['behavior_time'])
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df

#2.制作基础透视表：不同用户类型的基本计数和转化率
def summarize_behavior_metrics(df: pd.DataFrame) ->dict[str,float | int]:
    behavior_counts = df['behavior_type'].value_counts()

    user_behavior = df.pivot_table(
        index = 'user_id',
        columns = 'behavior_type',
        values = 'item_id',
        aggfunc = 'count',
        fill_value = 0,
    )

    for column in ['pv','cart','buy']:
        if column not in user_behavior.columns:
            user_behavior['column'] = 0

    pv_users = int((user_behavior['pv'] > 0).sum())
    cart_users = int((user_behavior['cart'] > 0).sum())
    buyers_after_view = int(((user_behavior['pv']>0) & (user_behavior['buy']>0)).sum())
    buyers_after_cart = int(((user_behavior['cart']>0) & (user_behavior['buy']>0)).sum())

    return {
        'total_behavior': int(len(df)),
        'uv': int(df['user_id'].nunique()),
        'item_count':int(df['item_id'].nunique()),
        'category_count':int(df['category_id'].nunique()),
        'pv_count':int(behavior_counts.get('pv',0)),
        'fav_count':int(behavior_counts.get('fav',0)),
        'cart_count':int(behavior_counts.get('cart',0)),
        'buy_count':int(behavior_counts.get('buy',0)),
        'browse_to_purchase_user_rate':round(buyers_after_view / pv_users,4),
        'cart_to_purchase_user_rate':round(buyers_after_cart / cart_users,4)
    }

#3.构建交叉表：基础的(行为是否发生)统计复合行为相对于基础行为的转化率
def user_level_funnel(df:pd.DataFrame) ->pd.DataFrame:
    user_flags = pd.crosstab(df['user_id'],df['behavior_type']) > 0
    for column in ['pv','fav','cart','buy']:
        if column not in user_flags.columns:
            user_flags[column] = False

    steps = [
        ('01_viewed',user_flags['pv']),
        ('02_favorited',user_flags['pv'] & user_flags['fav']),
        ('03_added_to_cart',user_flags['pv'] & user_flags['cart']),
        ('04_pruchased',user_flags['pv'] & user_flags['buy']),
    ]

    result = pd.DataFrame({
        'step':[step for step, _ in steps],   
        'users':[int(mask.sum()) for _, mask in steps]  
    })
    first_step_users = result.loc[0,'users'] if not result.empty else 0
    result['conversation_from_view'] = (
        result['users'].div(first_step_users).round(4) if first_step_users else 0
    )
    return result

#4.深度的(时间逻辑上)协调行为的转化率
def user_item_sequential_funnel(df:pd.DataFrame) ->dict[str,float|int]:
    events = df[df['behavior_type'].isin(['pv','fav','cart','buy'])].copy()
    first_times = events.pivot_table(
        index=['user_id','item_id'],
        columns='behavior_type',
        values='behavior_time',
        aggfunc='min',
    )
    for column in ['pv','fav','cart','buy']:
        if column not in first_times.columns:
            first_times[column] = pd.NaT

    viewed = first_times['pv'].notna()
    favorited = first_times['fav'].notna()
    carted = first_times['cart'].notna()
    bought = first_times['buy'].notna()

    pv_to_buy = viewed & bought & (first_times['buy'] >= first_times['pv'])
    pv_to_cart = viewed & carted & (first_times['cart'] >= first_times['pv'])
    cart_to_buy = carted & bought & (first_times['buy'] >= first_times['cart'])
    fav_to_buy = favorited & bought &(first_times['buy'] >= first_times['fav'])

    viewed_pairs = int(viewed.sum())
    carted_pairs = int(carted.sum())
    favorited_pairs = int(favorited.sum())

    return {
        'user_item_pairs':int(len(first_times)),

        #单个行为计数：
        'viewed_pairs':viewed_pairs,
        'carted_pairs':carted_pairs,
        'favorited_pairs':favorited_pairs,

        #协调行为分层计数：
        'pv_to_cart_pairs':int(pv_to_cart.sum()),
        'pv_to_buy_pairs':int(pv_to_buy.sum()),
        'cart_to_buy_pairs':int(cart_to_buy.sum()),
        'fav_to_buy_pairs':int(fav_to_buy.sum()),

        #协调行为/单个行为的转化率：
        'pv_to_cart_pair_rate':round(int(pv_to_cart.sum()) / viewed_pairs,4) if viewed_pairs else 0,
        'pv_to_buy_pair_rate':round(int(pv_to_buy.sum()) / viewed_pairs,4) if viewed_pairs else 0,
        'cart_to_buy_pair_rate':round(int(cart_to_buy.sum()) / carted_pairs,4) if carted_pairs else 0,
        'fav_to_buy_pair_rate':round(int(fav_to_buy.sum()) / favorited_pairs,4) if favorited_pairs else 0,
    }


#5.用户行为占比
def behavior_type_distribution(df:pd.DataFrame) ->pd.DataFrame:
    counts = df['behavior_type'].value_counts().rename_axis('behavior_type').reset_index(name='behavior_count')
    counts['behavior_share'] = (counts['behavior_count'] / counts['behavior_count'].sum()).round(4)
    return counts


#6.每日用户活跃度
def daily_active_users(df:pd.DataFrame) -> pd.DataFrame:
    return df.groupby('date')['user_id'].nunique().reset_index(name='dau')


#7.统计每日使用度+每日用户留存度
def daily_purchase_trend(df:pd.DataFrame) -> pd.DataFrame:
    buy_df = df[df['behavior_type'] == 'buy']
    return (
        buy_df.groupby('date')
        .agg(purchase_count=('behavior_type','size'),purchase_users=('user_id','nunique'))
        .reset_index()
    )


#8.统计每小时用户活跃度
def hourly_activity(df:pd.DataFrame) -> pd.DataFrame:
    return df.groupby(['hour','behavior_type']).size().reset_index(name='behavior_count')


#9.统计各品类的用户行为+用户留存
def top_categories_by_purchase(df:pd.DataFrame,top_n: int = 10) -> pd.DataFrame:
    buy_df = df[df['behavior_type'] == 'buy']
    return (
        buy_df.groupby('category_id')
        .agg(
            purchase_count=('behavior_type','size'),
            buyer_count=('user_id','nunique'))
        .sort_values(['purchase_count','buyer_count'],ascending=False)
        .head(top_n)
        .reset_index()
    )


#10.各品类用户购买转化率+品类策略效果
def category_conversion_analysis(df:pd.DataFrame,top_n : int = 20,min_pv:int = 30) ->pd.DataFrame:
    category_behavior = (
        df.pivot_table(
            index='category_id',
            columns='behavior_type',
            values='user_id',
            aggfunc='count',
            fill_value=0,
        )
        .rename_axis(None,axis=1)
        .reset_index()
    )
    for column in ['pv','fav','cart','buy']:
        if column not in category_behavior.columns:
            category_behavior[column] = 0

    category_behavior = category_behavior.rename(
        columns={
            'pv':'pv_count',
            'fav':'fav_count',
            'cart':'cart_count',
            'buy':'buy_count',
        }
    )
    #pv_to_buy的协调行为的转化率
    category_behavior['browse_to_buy_rate'] = (
        category_behavior['buy_count'] / category_behavior['pv_count'].replace(0,float('nan'))
    ).fillna(0.0).round(4)
    category_behavior['cart_to_buy_rate'] = (
        category_behavior['buy_count'] / category_behavior['cart_count'].replace(0,float('nan'))
    ).fillna(0.0).round(4)

    return (
        category_behavior[category_behavior['pv_count'] >= min_pv]                  
        .sort_values(['buy_count','browse_to_buy_rate'],ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


#11.统计复购率
def repurchase_analysis(df:pd.DataFrame) -> dict[str,float|int]:
    user_buy_counts=df[df['behavior_type'] == 'buy'].groupby('user_id').size()
    total_buyers = int(user_buy_counts.shape[0])
    repurchase_users = int((user_buy_counts >= 2).sum())
    return {
        'total_buyers':total_buyers,
        'repurchase_users':repurchase_users,
        'repurchase_rate':round(repurchase_users / total_buyers,4) if total_buyers else 0,
    }


#12.统计只加购物车但不买的用户
def cart_without_purchase_users(df:pd.DataFrame) -> pd.DataFrame:
    user_flags = df.pivot_table(
        index='user_id',
        columns='behavior_type',
        values='item_id',
        aggfunc='count',
        fill_value=0,
    )
    user_flags.columns.name = None
    for column in ['cart','buy']:
        if column not in user_flags.columns:
            user_flags[column] = 0

    result = user_flags[(user_flags['cart'] > 0) & (user_flags['buy'] == 0)].reset_index()
    return result[['user_id','cart']].rename(columns={'cart':'cart_count'})


#13.统计用户习惯(行为习惯、购买习惯、品类偏好)+用户价值评分
def high_value_users(df:pd.DataFrame,top_n: int = 20) ->pd.DataFrame:
    buy_df = df[df['behavior_type'] == 'buy']
    if buy_df.empty:
        return pd.DataFrame(columns=['user_id','purchase_count','distinct_items_bought','active_days','value_score'])

    user_purchase = buy_df.groupby('user_id').agg(
        purchase_count=('behavior_type','size'),
        distinct_items_bought=('item_id','nunique'),
        distinct_categories_bought=('category_id','nunique'),
    )
    user_active_days = df.groupby('user_id')['date'].nunique().rename('active_days')
    result = user_purchase.join(user_active_days,how='left').fillna(0)
    result['value_score'] = (
        result['purchase_count'] * 5
        +result['distinct_items_bought'] * 2
        +result['distinct_categories_bought'] 
        +result['active_days']
    )
    return result.sort_values(['value_score','purchase_count'],ascending=False).head(top_n).reset_index()


#14.深度探究用户行为逻辑
def user_segmentation(df:pd.DataFrame) -> pd.DataFrame:
    user_behavior = (
        df.pivot_table(
            index='user_id',
            columns='behavior_type',
            values='item_id',
            aggfunc='count',
            fill_value=0,
        )
        .rename_axis(None,axis=1)
        .reset_index()
    )
    for column in ['pv','fav','cart','buy']:
        if column not in user_behavior.columns:
            user_behavior[column] = 0

    active_days = df.groupby('user_id')['date'].nunique().rename('active_days').reset_index()
    user_behavior = user_behavior.merge(active_days,on='user_id',how='left')
    user_behavior['purchase_segment'] = pd.cut(
        user_behavior['buy'],
        bins=[-1,0,1,3,float('inf')],
        labels=['no_purchase','one_pruchase','two_to_three','four_plus'],
    )
    user_behavior['activity_segment'] = pd.cut(
        user_behavior['active_days'],
        bins=[0,2,5,float('inf')],
        labels=['low_active','medium_active','high_active'],
        include_lowest=True,
    )
    user_behavior['behavior_depth'] = 'browse_only'
    user_behavior.loc[user_behavior['fav'] > 0,'behavior_depth'] = 'favorited'
    user_behavior.loc[user_behavior['cart'] > 0,'behavior_depth'] ='added_to_cart'
    user_behavior.loc[user_behavior['buy'] > 0,'behavior_depth'] = 'purchased'

    return (
        user_behavior.groupby(['behavior_depth','purchase_segment'],observed=True)
        .agg(
            users=('user_id','nunique'),
            avg_active_days=('active_days','mean'),
            total_purchases=('buy','sum'),
            avg_purchase_count=('buy','mean'),
            avg_cart_count=('cart','mean')
        )
        .reset_index()
        .sort_values(['behavior_depth','purchase_segment'])
    )

#1.工作日和周末的总体平均行为量对比
def comparison_between_weekday_and_weekend(df:pd.DataFrame) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    daily_stats = df.groupby(['date','day_type']).agg(
        behavior_count = ('behavior_type','size'),
        unique_users = ('user_id','nunique')
    ).reset_index()

    summary = daily_stats.groupby(['date','day_type']).agg(
     avg_behavior = ('behavior_count','mean'),
     avg_unique = ('unique_users','mean')
    ).round(4)

    return summary

#2.工作日和周末的小时行为量对比
def hour_activity_comparison_within_week(df:pd.DataFrame) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    hourly = df.groupby(['hour', 'day_type']).size().reset_index(name='count')
    return pd.DataFrame(hourly)

#3.不同用户在工作日和周末的对比
def distribution_of_behavior_within_week(df:pd.DataFrame) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    behavior_dist = df.groupby(['behavior_type', 'day_type']).size().reset_index(name='count')
    #计算百分比（按 day_type 归一化）
    behavior_dist['pct'] = behavior_dist.groupby('day_type')['count'].transform(lambda x: x / x.sum())

    return pd.DataFrame(behavior_dist)

#4.浏览转换率和转化行为量在不同时段不同活跃天数的对比
def user_tag_period(df:pd.DataFrame) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    df['time_period'] = pd.cut(
    df['hour'],
    bins=[0, 6, 12, 18, 24],
    labels=['00-06点', '06-12点', '12-18点', '18-24点'],
    right=False,
    include_lowest=True
    )
    user_flags = pd.crosstab(df['user_id'], df['behavior_type']) > 0
    for col in ['pv', 'fav', 'cart', 'buy']:
        if col not in user_flags.columns:
         user_flags[col] = False

    #按用户 + 时段 + 日型聚合画像指标
    user_profile = df.groupby(['user_id', 'day_type', 'time_period']).agg(
        pv_count=('behavior_type', lambda x: (x == 'pv').sum()),
        fav_count=('behavior_type', lambda x: (x == 'fav').sum()),
        cart_count=('behavior_type', lambda x: (x == 'cart').sum()),
        buy_count=('behavior_type', lambda x: (x == 'buy').sum()),
        active_days=('date', 'nunique'),
        item_count=('item_id', 'nunique'),
        category_count=('category_id', 'nunique'),
    ).reset_index()

    # 计算总行为量和购买转化率
    user_profile['total_behavior'] = (
         user_profile['pv_count'] + user_profile['fav_count'] +
        user_profile['cart_count'] + user_profile['buy_count']
    )
    user_profile['buy_rate'] = (
         user_profile['buy_count'] / user_profile['pv_count'].replace(0, np.nan)
    ).fillna(0).round(4)

    return user_profile

#5.复购用户活跃行为不同时段工作日和周末的对比
def high_value_comparison_within_day(df:pd.DataFrame) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    buy_df = df[df['behavior_type'] == 'buy']
    user_buy_counts = buy_df.groupby('user_id').size()
    high_value_users = user_buy_counts[user_buy_counts >= 2].index

    # 筛选高价值用户的行为
    hv_df = df[df['user_id'].isin(high_value_users)]
    hv_hourly = hv_df.groupby(['hour', 'day_type']).size().reset_index(name='count')

    return hv_hourly

#6.top10品类在不同工作日的行为量对比
def top_activity_category(df: pd.DataFrame,
                          top_n: int = 10,
                          ascending:bool = False) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    # 按类目 + 工作日/周末统计
    category_time = df.groupby(['category_id', 'day_type']).size().reset_index(name='count')
    category_total = category_time.groupby('category_id')['count'].sum()

    if ascending:
        top_categories = category_total.nsmallest(top_n).index
    else:
        top_categories = category_total.nlargest(top_n).index

    category_time_top = category_time[category_time['category_id'].isin(top_categories)].copy()
    category_time_top['total'] = category_time_top['category_id'].map(category_total)         #给每行附上行为量总数

    category_time_top = (
        category_time_top
        .sort_values(['total', 'day_type'], ascending=[False, True])
        .reset_index(drop=True)
    )

    return category_time_top


#7.不同活跃度+购买力分层用户
def activity_purchasing_segment_user(df:pd.DataFrame) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    user_profile = df.groupby('user_id').agg(
        pv_count = ('behavior_type', lambda x: (x == 'pv').sum()),
        fav_count = ('behavior_type', lambda x: (x == 'fav').sum()),
        cart_count = ('behavior_type', lambda x: (x == 'cart').sum()),
        buy_count = ('behavior_type', lambda x: (x == 'buy').sum()),
        active_days = ('date','nunique'),
        item_count = ('item_id','nunique'),
        category_count = ('category_id','nunique'),
    ).reset_index()

    user_profile['is_buyer'] = user_profile['buy_count'] > 0
    user_profile['is_repurchase'] = user_profile['buy_count'] >= 2
    user_profile['is_multi_category'] = user_profile['category_count'] >= 3

    conditions = [
        (user_profile['buy_count'] >= 3) & (user_profile['active_days'] >= 5),
        user_profile['buy_count'] >= 1,
        (user_profile['cart_count'] >= 1) & (user_profile['fav_count'] >= 1),
    ]
    choices = ['core_user', 'buy_user', 'willing_user']

    user_profile['segment_user'] = np.select(conditions, choices, default='browsing_user')

    return pd.DataFrame(user_profile['segment_user'])


#8.pv_buy转换率和决策周期
def category_converison_decision_cycle(df:pd.DataFrame,
                                       top_n :int = 10,
                                       ascending:bool = False) -> dict[str,object]:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    #品类pv-buy转化率
    category_pivot = pd.crosstab(df['category_id'],df['behavior_type']).reset_index()
    for col in ['pv','buy']:
        if col not in category_pivot.columns:
            category_pivot[col] = pd.NaT

    category_pivot['pv_to_buy_rate'] = (
       category_pivot['buy'] / category_pivot['pv'].replace(0,np.nan)
    ).fillna(0).round(4)

    category_pivot = category_pivot[category_pivot['pv'] >= 50]

    first_times = df.pivot_table(
        index=['user_id', 'item_id'],
        columns='behavior_type',
        values='behavior_time',
        aggfunc='min',
    )
    for col in ['pv', 'fav', 'cart', 'buy']:
      if col not in first_times.columns:
            first_times[col] = pd.NaT

    first_times['pv_to_buy_minutes'] = (
     (first_times['buy'] - first_times['pv']) / pd.Timedelta(minutes=1)
    )

    valid = first_times[
         first_times['pv'].notna() &
         first_times['buy'].notna() &
         (first_times['buy'] >= first_times['pv'])
    ]

    if ascending:
        top_categories = category_pivot.nsmallest(top_n, 'pv_to_buy_rate')
    else:
        top_categories = category_pivot.nlargest(top_n, 'pv_to_buy_rate')

    return {
        'pv_to_buy_conversion': top_categories[['category_id', 'pv', 'buy', 'pv_to_buy_rate']],
        'conversion_total': len(valid),
        'avg_decision_length': round(valid['pv_to_buy_minutes'].mean(), 2) if len(valid) else 0,
        'median_decision_length': round(valid['pv_to_buy_minutes'].median(), 2) if len(valid) else 0,
        'all_category_rates': category_pivot['pv_to_buy_rate'],
        'all_decision_minutes': valid['pv_to_buy_minutes'].dropna(),
    }


#9.复购周期
def repurchase_cycle(df:pd.DataFrame) -> dict[str,object]:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    buy_df = df[df['behavior_type'] == 'buy'].copy()

    buy_df = buy_df.sort_values(['user_id', 'behavior_time'])
    buy_df['prev_buy_time'] = buy_df.groupby('user_id')['behavior_time'].shift(1)   
    buy_df['days_between'] = ((buy_df['behavior_time'] - buy_df['prev_buy_time']) / pd.Timedelta(days=1))

    repurchase = buy_df[buy_df['days_between'].notna()]

    return {
        'repurchase_list':repurchase,
        'repurchases_length': len(repurchase),
        'avg_repurchase_interval':repurchase['days_between'].mean().round(2) if len(repurchase) else 0,
        'median_repurchase_interval':repurchase['days_between'].median().round(2) if len(repurchase) else 0,
    }


#10.用户购买品类组合
def purchase_category_combos(df:pd.DataFrame,top_n:int = 10) -> pd.DataFrame:
    df['day_type'] = df['weekname'].apply(lambda x: 'weekend' if int(x) >= 6 else 'weekday')

    user_categories = df[df['behavior_type'] == 'buy'].groupby('user_id')['category_id'].apply(set)   #.apply(set)意思是变成set集合哈 🐮

    # 类目关联分析:购物篮分析--找出经常被同一用户一起购买的类品组合
    from itertools import combinations  
    from collections import Counter     

    pair_counter = Counter()
    for cats in user_categories:
        if len(cats) >= 2:              
          for pair in combinations(sorted(cats), 2): 
                pair_counter[pair] += 1                 

    pair_df = pd.DataFrame(
        [(a, b, c) for (a, b), c in pair_counter.items()],
        columns=['category_a', 'category_b', 'co_count']
    ).sort_values('co_count', ascending=False)  

    return pair_df.head(top_n)


#15.打印函数
def print_section(title:str,value:object) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    print(value)


#16.主函数：设置复用+调用各指标计算函数
def main() ->None:
    parser = argparse.ArgumentParser(description="Run Taobao behavior analysis.")
    parser.add_argument(
        '--input',
        type=Path,
        default=DEFAULT_INPUT,
        help='Cleaned CSV path.'
    )
    args = parser.parse_args()

    df = load_data(args.input)
    print_section('Core Metrics',pd.Series(summarize_behavior_metrics(df)))
    print_section('Behavior Type Distribution',behavior_type_distribution(df))
    print_section('User-level Funnel',user_level_funnel(df))
    print_section('User-Item-sequential Funnel',pd.Series(user_item_sequential_funnel(df)))
    print_section('Daily Active Users',daily_active_users(df))
    print_section('Daily Purchase Trend',daily_purchase_trend(df))
    print_section('Hourly',hourly_activity(df))
    print_section('Top 10 Categories By Purchase',top_categories_by_purchase(df))
    print_section('Category Conversion Analysis',category_conversion_analysis(df))
    print_section('Rupurchase Analysis',repurchase_analysis(df))
    print_section('Cart Without Purchase Users',cart_without_purchase_users(df))
    print_section('High Value Users',high_value_users(df))
    print_section('User Segmentation',user_segmentation(df))

    print_section('Behavior Bwtween Weekday and Weekend',comparison_between_weekday_and_weekend(df))
    print_section('Hour Activity Comparison Within Week',hour_activity_comparison_within_week(df))
    print_section('Funnel Comparison Within Week',distribution_of_behavior_within_week(df))
    print_section('User Behavior in different Time solt',user_tag_period(df))
    print_section('Comparison of High Value Users Within Week',high_value_comparison_within_day(df))
    print_section('Top 10 Most Active Categories',top_activity_category(df))
    print_section('Users Segmentation Based On Activity Levels and spending',activity_purchasing_segment_user(df))
    print_section('Category Conversion Rate and Decision Making Cycle',category_converison_decision_cycle(df))
    print_section('User Repurchase Cycle',repurchase_cycle(df))
    print_section('Top 10 Category Purchase Combos',purchase_category_combos(df))





if __name__=='__main__':
    main()






