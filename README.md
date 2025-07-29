### 工具功能
分析函数调用关系，将分析结果导入neo4j中，

之后利用Cypher查询语句查找函数调用链（可以自定义source、sink点查询函数调用链）。

### 环境
需安装neo4j数据库(neo4j-community-5.20.0)，并安装apoc插件(需要和数据库同版本)，


### 使用方式
1.更改parse_multiple_files函数的参数（项目根目录）

2.设置config.yaml文件（忽略解析报错的行数，这里也可以根据报错在convert_php7_to_php5函数中添加php转化逻辑使得php解析成功）

3.更改run_neo4j_admin_import函数的参数（导入分析结果，如run_neo4j_admin_import("D:/functions.csv", "D:/function_calls.csv")，这里的路径为py文件的运行路径）

4.更改GraphDatabase.driver函数的参数（neo4j的密码）

5.search_vul函数中queue_2变量（自定义查询语句）

6.更改wb.save函数的参数(自定义查询函数调用链的保存结果，"C:\\Users\\xxx\\Desktop\\output.xlsx")

7.运行phpast_creat_1_18.py分析函数调用关系并导入到neo4j数据库

8.运行search_neo4j_19.py查询函数调用关系并保存查询结果



### 参考

https://github.com/LoRexxar/Kunlun-M/

https://github.com/viraptor/phply

https://github.com/wh1t3p1g/tabby
