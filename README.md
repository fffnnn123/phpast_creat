### 环境
需安装neo4j数据库，并安装apoc插件，


### 使用方式
1.更改parse_multiple_files函数的参数（项目根目录）

2.设置config.yaml文件（忽略解析报错的行数，这里也可以根据报错在convert_php7_to_php5函数中添加php转化逻辑使得php解析成功）
3.更改run_neo4j_admin_import函数的参数（导入分析结果，如run_neo4j_admin_import("D:/functions.csv", "D:/function_calls.csv")，这里的路径为py文件的运行路径）
4.更改GraphDatabase.driver函数的参数（neo4j的密码）
5.search_vul函数中queue_2变量（自定义查询语句）
6.更改wb.save函数的参数(自定义查询函数调用链的保存结果，"C:\\Users\\xxx\\Desktop\\output.xlsx")
