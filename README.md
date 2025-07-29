### 工具功能
分析函数调用关系，将分析结果导入neo4j中，

之后利用Cypher查询语句查找函数调用链（可以自定义source、sink点查询函数调用链）。

### 环境
需安装neo4j数据库(neo4j-community-5.20.0)，并安装apoc插件(需要和数据库同版本)，


### 使用方式
更改config.yaml配置文件，

<img width="499" height="267" alt="image" src="https://github.com/user-attachments/assets/284a5d40-9682-4527-83e2-162ee331ad87" />

更改search_vul函数中queue_2变量（自定义查询语句）
<img width="736" height="397" alt="image" src="https://github.com/user-attachments/assets/3c4e7c6b-1b52-4d04-943a-d0bcd7b7d7b4" />


运行phpast_creat_1_18.py，
<img width="762" height="629" alt="image" src="https://github.com/user-attachments/assets/a09d34db-09da-427a-b338-b4d5e665e37e" />


导入结果，这里是离线导入，不能开启neo4j，等导入成功后，再开启neo4j进行函数调用查询，
<img width="1125" height="619" alt="image" src="https://github.com/user-attachments/assets/9b651c0b-839a-41c0-a419-14747cdf4f54" />


开启neo4j console，
运行search_neo4j_19.py查询函数调用链，
输出结果，并保存到xlsx文件中，
<img width="1695" height="605" alt="image" src="https://github.com/user-attachments/assets/c9bca03b-f6a6-414c-bdfb-c043b1941881" />
<img width="1803" height="814" alt="image" src="https://github.com/user-attachments/assets/a8cde962-1f41-4f57-8645-97de1c6c8a24" />




### 参考

https://github.com/LoRexxar/Kunlun-M/

https://github.com/viraptor/phply

https://github.com/wh1t3p1g/tabby
