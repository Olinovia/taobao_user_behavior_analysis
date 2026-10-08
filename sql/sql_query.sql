-- 此文件是为Taobao_behavior_analysis的sql代码查询复现

--1.创建表格，建立表头
CREATE TABLE user_behavior (
    user_id BIGINT,
    item_id BIGINT,
    category_id BIGINT,
    behavior_type VARCHAR(10),
    behavior_name_en VARCHAR(50),
    behavior_name_cn VARCHAR(20),
    timestamp BIGINT,
    behavior_time TIMESTAMP,
    date DATE,
    hour DATE,
    weekday VARCHAR
)

--2.读取csv文件(ctrl+h可以替换内容，有部分替换/全部替换)
LOAD DATA LOCAL INFILE 'C:/Users/Administrator/Desktop/User-Behavior-Conversion-Analysis-main/data/cleaned_user_behavior.csv'
INTO TABLE user_behavior 
CHARACTER set utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS

--读取csv文件时 如果遇到load data local infile命令的报错，检查数据库服务端、客户端要同时开启(如下两条命令)
--查看状态
SHOW VARIABLES LIKE 'local_infile';
--如果是off，执行开始命令
SET GLOBAL local_infile = 1;

--查看是否写入csv文件数据
SELECT COUNT(*) FROM user_behavior;
--查看前10条数据
SELECT * FROM user_behavior LIMIT 10;

--重复执行load data 会导致数据翻倍，需要先清空表格，重新导入一次（只他妈能导入一次，别手贱）
--清空表(此命令只清空表格数据，不清空表头哈，别手贱)
TRUNCATE TABLE user_behavior

SELECT * FROM user_behavior
--然后重新执行上面的导入csv数据+select查看表格容量

--1.统计用户行为、用户、品类、商品总量情况：
SELECT 
    COUNT(*) AS total_behaviors,
    COUNT(DISTINCT user_id) AS nv,  /*nunique visitors独立访问用户*/
    COUNT(DISTINCT item_id) AS item_count,
    COUNT(DISTINCT category_id) AS category_count
from user_behavior

/*count函数：统计有多少符合条件的行 类count在Python  
  count(*) count(列名)不包括空值 count(distinct 列名)某列非空且不重复
  
  distinct函数：找出不重复项
  count搭配使用/独立使用*/

--2.统计各用户行为的总次数的占比
SELECT
    behavior_type,
    behavior_name_en,
    behavior_name_cn,
    COUNT(*) AS behavior_count,
    /*ROUND(XXX,n)
      COUNT(*) * 1.0意思是变成小数 也可COUNT(*) AS DECIMAL(10,2)变成10位的2位小数
      OVER()意思是不分组不排序的统计所有组数的总和   
      COUNT(*) / SUM(COUNT(*) OVER () ) 计算分组数占总数占比
       */
    ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (),4) AS behavior_share
FROM user_behavior
GROUP BY behavior_type,behavior_name_en,behavior_name_cn
ORDER BY behavior_count DESC;

--3.统计每日的用户活跃度
SELECT date,
       COUNT(DISTINCT user_id) AS dau
FROM user_behavior
GROUP BY date
ORDER BY date;

--4.统计每日交易+/用户活跃度
SELECT date,
       COUNT(*) AS purchase_count,
       COUNT(DISTINCT user_id) AS purchase_users
FROM user_behavior
WHERE behavior_type = 'buy'
GROUP BY date
ORDER BY date;

--5.统计每小时用户活跃度
SELECT hour,
       behavior_type,
       COUNT(*) AS behavior_count,
       COUNT(DISTINCT user_id) AS active_users
FROM user_behavior
GROUP BY hour,behavior_type
ORDER BY hour,behavior_type;

--6.统计品类前10购买率
SELECT category_id,
       COUNT(*) AS purchase_count,
       COUNT(DISTINCT user_id) AS buyer_count
FROM user_behavior
WHERE behavior_type = 'buy'
GROUP BY category_id
ORDER BY purchase_count DESC,buyer_count DESC
LIMIT 10;

--7.统计由浏览到购买的转化率
WITH user_flags AS (
    SELECT user_id,
    /*每个用户只要有过behavior_type='pv' 的行为就返回1，否则返回0 */
           MAX(CASE when behavior_type = 'pv' THEN 1 ELSE 0 END) AS has_pv,
           MAX(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) AS has_buy
    FROM user_behavior
    GROUP BY user_id
)
SELECT SUM(has_pv) AS pv_users,
       SUM(has_buy) AS buyer_users,
       ROUND(SUM(has_buy) * 1.0 / NULLIF(SUM(has_pv),0),4) AS browse_to_purchse_rate
FROM user_flags;

--8.统计由收藏到购物行为的转化率
WITH user_flags AS (
    SELECT user_id,
           MAX(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 
           END) AS has_cart,
           MAX(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0
           END) AS has_buy
    FROM user_behavior
    GROUP BY user_id
)
SELECT SUM(has_cart) AS cart_user,
       SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 
       END) AS cart_and_buy_user,
       ROUND(
        SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0
       END) 
       * 1.0 /NULLIF(SUM(has_cart),0),
       4) AS cart_to_purchase_rate
FROM user_flags

--9.统计由收藏到购物行为转化率
WITH user_flags AS (
    SELECT user_id,
           MAX(CASE WHEN behavior_type = 'fav' THEN 1 ELSE 0 
           END) AS has_fav,
           MAX(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0
           END) AS has_buy
    FROM user_behavior
    GROUP BY user_id
)
SELECT SUM(has_fav) AS favorite_user,
       SUM(CASE WHEN has_fav = 1 AND has_buy = 1 THEN 1 ELSE 0
       END) AS favorite_and_buy_user,
       ROUND(
        SUM(CASE WHEN has_fav = 1 AND has_buy = 1 THEN 1 ELSE 0 END) 
        *1.0 / NULLIF(SUM(has_fav),0),
        4 
       ) AS favorite_to_purchase_rate
FROM user_flags;

--10.统计复购率
WITH user_purchase AS (
    SELECT
         user_id,
         COUNT(*) AS purchase_count  
    FROM user_behavior
    WHERE behavior_type = 'buy'
    GROUP BY user_id 
)
SELECT 
    COUNT(*) AS total_buyers,
    SUM(CASE WHEN purchase_count >= 2 THEN 1 ELSE 0 END)AS repurchase_users,
    ROUND(
        SUM(CASE WHEN purchase_count >= 2 THEN 1 ELSE 0 END) * 1.0
        /NULLIF(COUNT(*),0),
        4
    )AS repurchase_rate
    FROM user_purchase


--11.统计加购但没有购买用户
WITH user_flags AS (
    SELECT 
        user_id,
        MAX(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 END) AS has_cart,
        MAX(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) AS has_buy
        FROM user_behavior
        GROUP BY user_id
)
SELECT 
    COUNT(*) AS cart_without_purchase_users
FROM user_flags
WHERE has_cart = 1 AND has_buy = 0;


--12.统计高购买价值用户top 20
SELECT 
    user_id,
    COUNT(*) AS bought_action,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN item_id END) AS purchase_count,
    COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN category_id END) AS distinct_category_bought,
    COUNT(DISTINCT date) AS active_day,
    (
        COUNT(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) * 5
        + COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN item_id END) * 2
        + COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN category_id END) 
        +COUNT(DISTINCT `date`)
    )AS value_score
    FROM user_behavior
    GROUP BY user_id
    HAVING COUNT(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) > 0
    ORDER BY value_score DESC,purchase_count DESC
    LIMIT 20;


--13.统计行为漏斗转化率
WITH user_funnel AS (
    SELECT 
        user_id,
        MAX(CASE WHEN behavior_type = 'pv' THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN behavior_type = 'fav' THEN 1 ELSE 0 END) AS favorited,
        MAX(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 END) AS carted,
        MAX(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) AS bought
    FROM user_behavior
    GROUP BY user_id
),
funnel_steps AS (
    /*select的是行，这里意思是创建一个有四个行的查询，users列对应user_funnel临时表的各种行为列
      并进行上下非空值的拼接*/
    SELECT '01_viewed' AS step,COUNT(*) AS users FROM user_funnel WHERE viewed = 1
    UNION ALL
    SELECT 'p2_favorited' AS step,COUNT(*) AS users FROM user_funnel WHERE viewed = 1 AND favorited = 1
    UNION ALL
    SELECT '03_carted' AS step,COUNT(*) AS users FROM user_funnel WHERE viewed = 1 AND favorited = 1 AND carted = 1
    UNION ALL
    SELECT '04_bought' AS step,COUNT(*) AS users FROM user_funnel WHERE viewed = 1 AND favorited =1 AND carted = 1 AND bought = 1
)
SELECT 
   /*主查询沿用step*4行+users列，并新建conversion_to_view列计算每种行为的程度--漏斗转化率*/
    step,
    users,
    /*OVER(ORDER BY step)是按照常量字符串前缀01、02排序的，
      并通过  FIRST_VALUE(users)选择第一个01——viewed*/
    ROUND(users * 1.0 / FIRST_VALUE(users) OVER(ORDER BY step),4) AS conversion_from_view
    FROM funnel_steps
    ORDER BY step;
/*SELECT后面可以加：表中列、常量(一行都会显示常量值)、表达式*/  

--14.统计每日购买量第一的商品
WITH daily_category_purchase AS (
    SELECT 
        date,
        category_id,
        COUNT(*) AS purchase_count
    FROM user_behavior
    WHERE behavior_type = 'buy'
    GROUP BY date,category_id
),
ranked AS (
    SELECT 
        date,
        category_id,
        purchase_count,
        /*DENSE_RANK()排名，并列是不跳过后续数字  1,1,2
          RANK()排名，并列是跳过后续数字 1,1,3
          OVER(PARTITION BY)
          OVER(ORDER BY)
          按每日计算购买量的排名*/
        DENSE_RANK() OVER(PARTITION BY date ORDER BY purchase_count DESC) AS purchase_rank
    FROM daily_category_purchase
)
SELECT 
    date,
    category_id,
    purchase_count
FROM ranked
WHERE purchase_rank = 1
ORDER BY date,category_id;

--15.统计pv_cart、pv_buy、cart_buy三种行为的转化率
WITH first_events AS (
    SELECT 
        user_id,
        item_id,
        MIN(CASE WHEN behavior_type = 'pv' THEN behavior_time END) AS pv_time,
        MIN(CASE WHEN behavior_type = 'fav' THEN behavior_time END) AS fav_time,
        MIN(CASE WHEN behavior_type = 'cart' THEN behavior_time END) AS cart_time,
        MIN(CASE WHEN behavior_type = 'buy' THEN behavior_time END) AS buy_time
    FROM user_behavior
    GROUP BY user_id,item_id
)
SELECT 
    COUNT(*) AS user_item_pairs,
    COUNT(CASE WHEN pv_time IS NOT NULL THEN 1 END) AS viewed_pairs,
    COUNT(CASE WHEN cart_time IS NOT NULL THEN 1 END) AS carted_pairs,
    COUNT(CASE WHEN buy_time IS NOT NULL THEN 1 END) AS bought_pairs,
    COUNT(CASE WHEN pv_time IS NOT NULL AND cart_time >= pv_time THEN 1 END) AS pv_to_cart_pairs,
    COUNT(CASE WHEN pv_time IS NOT NULL AND buy_time >= pv_time THEN 1 END) AS pv_to_buy_pairs,
    COUNT(CASE WHEN cart_time IS NOT NULL AND buy_time >=cart_time THEN 1 END) AS cart_to_buy_pairs,
    ROUND(
        COUNT(CASE WHEN pv_time IS NOT NULL AND buy_time >= pv_time THEN 1 END) * 1.0
        /NULLIF(COUNT(CASE WHEN pv_time IS NOT NULL THEN 1 END),0),
        4
    ) AS pv_to_buy_pair_rate,
    ROUND(
        COUNT(CASE WHEN cart_time IS NOT NULL AND buy_time >= cart_time THEN 1 END) * 1.0
        /NULLIF(COUNT(CASE WHEN cart_time IS NOT NULL THEN 1 END),0),
        4
    ) AS pv_to_buy_pair_rate,
    ROUND(
        COUNT(CASE WHEN cart_time IS NOT NULL AND buy_time >= cart_time THEN 1 END) * 1.0
        /NULLIF(COUNT(CASE WHEN cart_time IS NOT NULL THEN 1 END),0),
        4
    )AS cart_to_buy_pair_rate
FROM first_events;


--16.统计不同商品由pv、cart转化的购买行为转化率(商品引流率top 10)
SELECT 
    category_id,
    COUNT(CASE WHEN behavior_type = 'pv' THEN 1 END) AS pv_count,
    COUNT(CASE WHEN behavior_type = 'fav' THEN 1 END) AS fav_count,
    COUNT(CASE WHEN behavior_type = 'cart' THEN 1 END) AS cart_count,
    COUNT(CASE WHEN behavior_type = 'buy' THEN 1 END) AS buy_count,
    ROUND(
        COUNT(CASE WHEN behavior_type = 'buy' THEN 1 END) * 1.0
        /NULLIF(COUNT(CASE WHEN behavior_type = 'pv' THEN 1 END),0),
        4
    )AS browse_to_buy_rate,
    ROUND(
        COUNT(CASE WHEN behavior_type = 'buy' THEN 1 END) * 1.0
        /NULLIF(COUNT(CASE WHEN behavior_type = 'cart' THEN 1 END),0),
        4
    ) AS cart_to_buy_rate
FROM user_behavior
GROUP BY category_id
HAVING COUNT(CASE WHEN behavior_type = 'pv' THEN 1 END) >= 30
ORDER BY buy_count DESC,browse_to_buy_rate DESC
LIMIT 10;
